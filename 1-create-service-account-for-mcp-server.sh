#!/bin/bash
# -*- mode:shell-script; coding:utf-8; -*-

set -e

source ./lib/utils.sh

check_shell_variables CLOUDRUN_PROJECT_ID CLOUDRUN_SHORT_SA

# Each element is "role,project"
REQUIRED_ROLES_AND_PROJECTS=(
)

check_and_maybe_create_sa() {
  local short_sa project sa_email
  short_sa="$1"
  sa_project="$2"
  sa_email="${short_sa}@${sa_project}.iam.gserviceaccount.com"

  if gcloud iam service-accounts describe "$sa_email" &>/dev/null; then
    printf "The Service Account '%s' exists.\n" "$sa_email"
  else
    printf "Creating the Service Account '%s'...\n" "$sa_email"
    gcloud iam service-accounts create "$short_sa" --project "${sa_project}"
    printf "Sleeping a bit, before granting roles....\n"
    sleep 12
  fi
}

check_and_apply_roles() {
  local short_sa sa_project sa_email role project_for_role item
  short_sa="$1"
  sa_project="$2"
  sa_email="${short_sa}@${sa_project}.iam.gserviceaccount.com"

  for item in "${REQUIRED_ROLES_AND_PROJECTS[@]}"; do
    IFS=',' read -r role project_for_role <<< "$item"

    printf "\nChecking for '%s' role on project '%s'....\n" "${role}" "${project_for_role}"

    # shellcheck disable=SC2076
    ARR=($(gcloud projects get-iam-policy "${project_for_role}" \
      --flatten="bindings[].members" \
      --filter="bindings.members:${sa_email}" --format="value(bindings.role)" 2>/dev/null))

    if ! [[ ${ARR[*]} =~ "${role}" ]]; then
      printf "Adding role '%s' on project '%s' for SA '%s'....\n" "${role}" "${project_for_role}" "${sa_email}"
      gcloud projects add-iam-policy-binding "${project_for_role}" \
        --member="serviceAccount:${sa_email}" \
        --role="$role" --quiet
    else
      printf "Role '%s' is already applied to service account on project '%s'.\n" "${role}" "${project_for_role}"
    fi
  done
}

check_and_maybe_create_sa "$CLOUDRUN_SHORT_SA" "$CLOUDRUN_PROJECT_ID"

# In this demo,  no special roles for the MCP Server.
#check_and_apply_roles "$sa_name" "$CLOUDRUN_PROJECT_ID"
