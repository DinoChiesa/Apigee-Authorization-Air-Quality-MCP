# MCP Example - Air Quality Server

This is an example MCP Server, that provides air quality sensor readings for
places. I built this to use as a basis for illustrating governance
that I can apply on MCP, through Apigee.

## Disclaimer

This example is not an official Google product, nor is it part of an
official Google product.

## Screencast

[This Screecast](https://youtu.be/za69HZuhNiE) walks through the process.
[![screencast](./img/C4h46qTuWLU5pKA.png)](https://youtu.be/za69HZuhNiE)

## Using it

You can do it yourself.

To set this up, you need a GCP project suitable for Cloud Run, and an Apigee
instance. You need the proper roles and permissions:
 - to create service accounts,
 - deploy services to Cloud Run,
 - create and manage secrets in Secret Manager
 - and import + deploy Apigee proxies.

The setup scripts use things like apigeecli, and gcloud.

### Prerequisites

1. You will need to obtain credentials (API Keys) for the TomTom and Open Air
   Quality services by visiting:

   - https://developer.tomtom.com/
   - https://docs.openaq.org/

2. You also need an API Key for Gemini. Get one at https://ai.studio

3. You need to set up an OpenID Connect IDP, and provision a new
   Client ID and Secret pair. Steps for this varies, depending on
   your IDP. For setting up Auth0, you can try [these steps](./Auth0-setup.md).



### Service and Proxy Provisioning Steps

0. With a text editor, open the [env-sample.txt](./env-sample.txt) file,
   modify it to use your settings, and save it, to a file, perhaps named `.env`.

1. Open a terminal window.
   _Source_ the file to get all of those settings into your environment.
   ```sh
   source .env
   ```

1. Create the service account for the Cloud Run service.
   ```sh
   ./1-create-service-account-for-mcp-server.sh
   ```

2. Provision the secrets into Secret Manager. These include the
   TomTom and OpenAQ keys.
   ```sh
   ./2-provision-secrets.sh
   ```

3. Deploy the MCP Server to Cloud Run
   ```sh
   ./3-deploy-mcp-to-cloud-run.sh
   ```

   You should now be able to interact with the MCP Server
   at the endpoint emitted by the deployment script.

   You can use the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) to do this.


   Or, to use [Gemini CLI](https://github.com/google-gemini/gemini-cli), open or create the file `~/.gemini/settings.json` and
   provide this configuration:
   ```json
   {
     "mcpServers": {
       "air-quality": {
         "httpUrl": "https://air-quality-1923-999999222.us-west1.run.app/mcp"
       }
     }
     ....
   }
   ```
   Replace the URL with the one from your Cloud Run service. Then, start Gemini CLI and you should be
   able to interact with the MCP Server.


4. If you do not already have it, install the `apigeecli`
   ```sh
   ./8-install-apigeecli.sh
   ```

4. Import and deploy the Apigee proxy:
   ```sh
   ./9-import-and-deploy-apigee-proxy.sh
   ```

   At this point you should be able to invoke the MCP through the Apigee proxy.

   To do this with Gemini CLI, modify the  `~/.gemini/settings.json` file to
   provide this configuration:
   ```json
   {
     "mcpServers": {
       "air-quality-oauth": {
         "httpUrl": "https://apigee.endpoint.for.you/air-quality-oauth/mcp",
         "timeout": 4400,
         "oauth": {
           "enabled": true,
           "clientId": "OPENID_CLIENT_ID",
           "clientSecret": "OPENID_CLIENT_SECRET",
           "audiences": ["air-quality-oauth"]
         }
       }
     }
     ....
   }
   ```
   Replace the URL with the one from your Apigee proxy, and use the appropriate CLIENT ID and Secret from your
   OpenID IDP. Then, re-start Gemini CLI and you should be able to interact with the service.


## License

This material is [Copyright © 2025 Google LLC](./NOTICE).
and is licensed under the [Apache 2.0 License](LICENSE).

## Support

This example is open-source software. If
you need assistance, you can try inquiring on [the Google Cloud Community forum
dedicated to Apigee](https://goo.gle/apigee-community) There is no service-level
guarantee for responses to inquiries posted to that site.
