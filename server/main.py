# Copyright © 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import asyncio
import json
import logging
import os
import random
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Annotated, List, Optional, Sequence

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from pydantic import BaseModel, Field

TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY")
OPENAQ_API_KEY = os.environ.get("OPENAQ_API_KEY")
TOMTOM_API_ENDPOINT = "https://api.tomtom.com"
OPENAQ_ENDPOINT = "https://api.openaq.org"
DEGREE_RANGE = 3.0

mcp = FastMCP()


class UserInfoMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        # Access the tool object to check its metadata
        if context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(
                    context.message.name
                )
                headers = get_http_headers()
                user_info = headers.get("user-info")
                # Check that the user_info variable is not None here
                if user_info is not None:
                    logging.info(f"tool={tool.name}; {user_info}")
                else:
                    logging.info(f"user_info is unavailable")
                # Here, could check user_info scope, against the tags
                # on the tool, if desired.

            except Exception:
                # Tool not found or other error - let execution continue
                # and handle the error naturally
                pass

            return await call_next(context)


mcp.add_middleware(UserInfoMiddleware())


class AirQualityResult(BaseModel):
    """Air quality reading result"""

    sensor_id: Annotated[
        int,
        Field(description="the sensor ID from the Open AQ data store."),
    ]
    placename: Annotated[
        str,
        Field(
            description="the placename associated to the sensor for the air quality reading."
        ),
    ]
    timestamp: Annotated[
        str,
        Field(
            description="a string representing UTC time for the air quality reading."
        ),
    ]
    pm25: Annotated[
        float,
        Field(description="PM 2.5 count"),
    ]
    status: Annotated[
        str,
        Field(
            description="a status message indicating the success or failure of the lookup."
        ),
    ]


class GeocodePlacenameResponse(BaseModel):
    """Response for the placename-to-latlon tool."""

    latitude: Annotated[
        float,
        Field(
            description="the resolved latitude for the placename. This will be 0 in the case of failure."
        ),
    ]
    longitude: Annotated[
        float,
        Field(
            description="the resolved longitude for the placename. This will be 0 in the case of failure."
        ),
    ]
    placename: Annotated[
        str,
        Field(description="the placename that was resolved to a latitude & longitude."),
    ]
    message: Annotated[
        str,
        Field(
            description="a diagnostic message that is helpful when the resolution effort fails."
        ),
    ]


async def _geocode_one_placename(
    placename: str, client: httpx.AsyncClient
) -> GeocodePlacenameResponse:
    try:
        path = f"/search/2/geocode/{placename}.json"
        logging.info("GET %s", path)
        response = await client.get(
            f"{TOMTOM_API_ENDPOINT}{path}",
            params={"key": TOMTOM_API_KEY},
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results")
        if not results:
            return GeocodePlacenameResponse(
                latitude=0.0,
                longitude=0.0,
                message="error resolving placename",
                placename=placename,
            )

        position = results[0]["position"]
        return GeocodePlacenameResponse(
            latitude=position["lat"],
            longitude=position["lon"],
            message="ok",
            placename=placename,
        )
    except httpx.HTTPStatusError as e:
        return GeocodePlacenameResponse(
            latitude=0.0,
            longitude=0.0,
            placename=placename,
            message=f"upstream error (status code={e.response.status_code})",
        )


@mcp.tool(
    name="placename-to-latlon",
    description="Resolves a placename to a latitude/longitude location. This uses an upstream web API to satisfy the request.",
    tags={"place", "placename", "latitude", "longitude"},
)
async def placename_to_latlon(
    placename: Annotated[
        str, Field(description="the placename to resolve to a latitude & longitude")
    ],
) -> GeocodePlacenameResponse:
    """
    This description is ignored for the purposes of MCP, if a description is provided in the decorator above.
    """
    async with httpx.AsyncClient() as client:
        return await _geocode_one_placename(placename, client)


@mcp.tool(
    name="placenames-to-latlons",
    description="Resolves an explicitly-provided batch of placenames to a set of corresponding latitude/longitude locations. This uses an upstream web API to satisfy the request.",
    tags={"place", "placename", "latitude", "longitude"},
)
async def placenames_to_latlons(
    placenames: Annotated[
        List[str],
        Field(description="the set of placenames to resolve to latitude & longitude"),
    ],
) -> List[GeocodePlacenameResponse]:
    """
    ignored. See description above.
    """
    async with httpx.AsyncClient() as client:
        semaphore = asyncio.Semaphore(2)
        rate_limit_lock = asyncio.Lock()
        # Initialize to allow the first call to proceed without delay.
        last_call_time = time.monotonic() - 0.180

        async def _get_one_semaphored(placename: str) -> GeocodePlacenameResponse:
            nonlocal last_call_time
            async with semaphore:
                async with rate_limit_lock:
                    now = time.monotonic()
                    if now < last_call_time + 0.180:
                        await asyncio.sleep(last_call_time + 0.180 - now)
                    last_call_time = time.monotonic()

                return await _geocode_one_placename(placename, client)

        tasks = [_get_one_semaphored(placename) for placename in placenames]
        results = await asyncio.gather(*tasks)
        return list(results)


@mcp.tool(
    name="get-air-quality",
    description="Returns a list of current air quality information for a specific location, specified by {latitude, longitude} pair .",
    tags={"air", "placename", "latitude", "longitude", "pm2.5"},
)
async def get_air_quality(
    latitude: Annotated[
        float,
        Field(description="the latitude for the place."),
    ],
    longitude: Annotated[
        float,
        Field(description="the longitude for the place."),
    ],
) -> Sequence[AirQualityResult]:
    """See above"""

    async with httpx.AsyncClient() as client:
        try:
            path = "/v3/locations"
            logging.info("get_air_quality GET %s", path)
            response = await client.get(
                f"{OPENAQ_ENDPOINT}{path}",
                params={
                    "coordinates": f"{latitude},{longitude}",
                    "radius": 12000,
                    "limit": 25,
                },
                headers={"X-API-KEY": OPENAQ_API_KEY},
            )
            logging.info("get_air_quality response1")
            response.raise_for_status()
            data = response.json()

            results = data.get("results")
            logging.info("get_air_quality results1")

            if not results:
                logging.info("get_air_quality no results")
                return [
                    AirQualityResult(
                        sensor_id=0,
                        placename="",
                        timestamp="",
                        pm25=-1,
                        status="Error. No locations found near coordinates.",
                    )
                ]

            eight_hours_ago = datetime.now(timezone.utc) - timedelta(hours=8)
            logging.info("get_air_quality looking for suitable locations")

            suitable_locations = []
            for loc in results:
                # json_string = json.dumps(loc)
                # logging.info(f"get_air_quality looking at loc {json_string}")

                last_updated_str = (loc.get("datetimeLast") or {}).get("utc")
                if not last_updated_str:
                    continue
                last_updated = datetime.fromisoformat(
                    last_updated_str.replace("Z", "+00:00")
                )
                if last_updated < eight_hours_ago:
                    continue

                sensors = loc.get("sensors", [])
                has_pm25 = any(
                    s.get("parameter", {}).get("name") == "pm25" for s in sensors
                )
                if has_pm25:
                    suitable_locations.append(loc)

            if not suitable_locations:
                logging.info("get_air_quality no suitable locations")
                return []

            logging.info(
                f"get_air_quality found ({len(suitable_locations)}) suitable locations"
            )

            random.shuffle(suitable_locations)
            air_quality_results = []
            for selected_location in suitable_locations:
                if len(air_quality_results) >= 3:
                    break

                logging.info("get_air_quality looking for sensors")
                pm25_sensor = next(
                    (
                        s
                        for s in selected_location["sensors"]
                        if s.get("parameter", {}).get("name") == "pm25"
                    ),
                    None,
                )

                if not pm25_sensor:
                    logging.info("get_air_quality no pm25 sensor")
                    continue

                logging.info("get_air_quality found pm25 sensor")
                sensor_id = pm25_sensor["id"]
                from_datetime = eight_hours_ago.isoformat().replace("+00:00", "Z")

                try:
                    path = f"/v3/sensors/{sensor_id}/measurements/hourly"
                    logging.info("get_air_quality GET %s", path)
                    response = await client.get(
                        f"{OPENAQ_ENDPOINT}{path}",
                        params={"datetime_from": from_datetime},
                        headers={"X-API-KEY": OPENAQ_API_KEY},
                    )
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPStatusError as e:
                    logging.info(
                        f"upstream error for sensor {sensor_id} (status code={e.response.status_code})"
                    )
                    continue
                results = data.get("results")

                if not results:
                    logging.info("get_air_quality no sensor readings")
                    continue

                logging.info("get_air_quality getting most recent sensor reading")

                last_measurement = None
                for measurement in reversed(results):
                    if (
                        measurement.get("period", {}).get("datetimeTo", {}).get("utc")
                        is not None
                        and measurement.get("value") is not None
                    ):
                        last_measurement = measurement
                        break

                if last_measurement:
                    air_quality_results.append(
                        AirQualityResult(
                            sensor_id=sensor_id,
                            placename=selected_location["name"],
                            timestamp=last_measurement["period"]["datetimeTo"]["utc"],
                            pm25=last_measurement["value"],
                            status="Success.",
                        )
                    )
            return air_quality_results

        except httpx.HTTPStatusError as e:
            logging.info(f"upstream error (status code={e.response.status_code})")
            return [
                AirQualityResult(
                    sensor_id=0,
                    placename="",
                    timestamp="",
                    pm25=-1,
                    status=f"API error: {e.response.status_code}",
                )
            ]
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            logging.info(
                f"get_air_quality some other exception at line {line_number}: {exc_value}"
            )
            return [
                AirQualityResult(
                    sensor_id=0,
                    placename="",
                    timestamp="",
                    pm25=-1,
                    status=f"An unexpected error occurred at line {line_number}: {exc_value}",
                )
            ]


if __name__ == "__main__":
    LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(level=LOGLEVEL)
    if not TOMTOM_API_KEY or not OPENAQ_API_KEY:
        logging.info("missing environment variables")
        raise SystemExit

    TOMTOM_API_KEY = TOMTOM_API_KEY.strip()
    OPENAQ_API_KEY = OPENAQ_API_KEY.strip()

    port = int(os.environ.get("PORT", 9247))
    mcp.run(
        transport="http", host="0.0.0.0", port=port, path="/mcp", stateless_http=True
    )
