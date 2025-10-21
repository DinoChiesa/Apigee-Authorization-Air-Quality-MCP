#!/bin/bash
# -*- mode:shell-script; coding:utf-8; -*-

set -e
sa_name=air-quality-mcp-sa

source ./lib/utils.sh

import_secret_and_grant_access() {
  local secret_name secret_value sa_email
  secret_name=$1
  secret_value=$2
  sa_email=$3
  project=$4

  if gcloud secrets describe "$secret_name" --project="$project" --quiet >/dev/null 2>&1; then
    printf "\nThe secret (%s) already exists.\n" "${secret_name}"
  else
    printf "\nThe secret (%s) does not exist.\n" "${secret_name}"

    if ! gcloud secrets create "$secret_name" --project="$project" --data-file <(printf "${secret_value}") --quiet; then
      printf "\nDid not succeed creating the secret.\n"
      printf "Aborting.\n"
      exit 1
    fi
  fi

  # AI! Modify this logic to check to see if the principal "serviceAccount:${sa_email}"
  # has secretAccessor role, and only use add-iam-policy-binding if necessary.
  if ! gcloud secrets add-iam-policy-binding "projects/${project}/secrets/${secret_name}" \
    --project "${project}" \
    --member "serviceAccount:${sa_email}" \
    --role "roles/secretmanager.secretAccessor"; then
    printf "\nCould not apply the role for that secret.\n"
    printf "Aborting.\n"
    exit 1
  fi
}

check_shell_variables GOOGLE_CLOUD_PROJECT TOMTOM_API_KEY OPENAQ_API_KEY

sa_email="${sa_name}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

import_secret_and_grant_access "tomtom-api-key" "$TOMTOM_API_KEY" "$sa_email" "$GOOGLE_CLOUD_PROJECT "

import_secret_and_grant_access "openaq-api-key" "$OPENAQ_API_KEY" "$sa_email" "$GOOGLE_CLOUD_PROJECT "
