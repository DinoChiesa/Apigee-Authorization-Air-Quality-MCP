#!/bin/bash
# -*- mode:shell-script; coding:utf-8; -*-

set -e

source ./lib/utils.sh

check_shell_variables CLOUDRUN_PROJECT_ID CLOUDRUN_REGION CLOUDRUN_SERVICE_NAME CLOUDRUN_SHORT_SA

sa_email="${CLOUDRUN_SHORT_SA}@${CLOUDRUN_PROJECT_ID}.iam.gserviceaccount.com"

gcloud run deploy "$CLOUDRUN_SERVICE_NAME" \
  --source ./server \
  --service-account "$sa_email" \
  --cpu 1 \
  --memory '256Mi' \
  --min-instances 0 \
  --max-instances 1 \
  --update-secrets=TOMTOM_API_KEY=tomtom-api-key:latest \
  --update-secrets=OPENAQ_API_KEY=openaq-api-key:latest \
  --allow-unauthenticated \
  --project "$CLOUDRUN_PROJECT_ID" \
  --region "$CLOUDRUN_REGION"
