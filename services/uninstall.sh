#!/bin/bash
# Script: uninstall.sh
# Purpose: Uninstalls all KombiOS services by calling uninstall.sh in each subfolder
# Behavior: Verbose, safe, and idempotent

set -euo pipefail

########################################
# Config (can be overridden via env)
########################################
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VERBOSE="${VERBOSE:-1}"            # 1 = detailed logs; 0 = quieter
DEBUG_TRACE="${DEBUG_TRACE:-0}"    # 1 = set -x

########################################
# Logging utilities
########################################
ts()    { date +"%Y-%m-%d %H:%M:%S%z"; }
log()   { echo "[$(ts)] [INFO] $*"; }
warn()  { echo "[$(ts)] [WARN] $*" >&2; }
error() { echo "[$(ts)] [ERROR] $*" >&2; }

run() {      # Log + execute command (argument-safe; no eval)
  if [ "${VERBOSE}" = "1" ]; then
    printf '[%s] [RUN ]' "$(ts)"
    for arg in "$@"; do printf ' %q' "$arg"; done
    echo
  fi
  "$@"
}

if [ "${DEBUG_TRACE}" = "1" ]; then set -x; fi

########################################
# Error trap
########################################
on_error() {
  local exit_code=$?
  error "Script failed at line ${BASH_LINENO[0]} while running: '${BASH_COMMAND}' (exit: ${exit_code})"
  exit "${exit_code}"
}
trap on_error ERR

########################################
# Pre-run check for sudo
########################################
if ! command -v sudo >/dev/null 2>&1; then
  warn "sudo not found; continuing without it. You may encounter permission issues."
  SUDO=""
else
  SUDO="sudo"
fi

########################################
# STEP 1: Locate all child uninstall.sh files
########################################
log "Scanning for uninstall.sh scripts under: ${BASE_DIR} (depth=2)"
mapfile -t SCRIPTS < <(find "${BASE_DIR}" -mindepth 2 -maxdepth 2 -type f -name "uninstall.sh" ! -path "${BASE_DIR}/uninstall.sh" | sort)

TOTAL=${#SCRIPTS[@]}
log "Found ${TOTAL} uninstall.sh script(s)."

if [ "${TOTAL}" -eq 0 ]; then
  warn "No child uninstall scripts found. Nothing to uninstall."
  exit 0
fi

########################################
# STEP 2: Execute each uninstall.sh safely
########################################
COUNT=1
for SCRIPT in "${SCRIPTS[@]}"; do
  SERVICE_DIR="$(dirname "${SCRIPT}")"
  SERVICE_NAME="$(basename "${SERVICE_DIR}")"
  log "[${COUNT}/${TOTAL}] Uninstalling service '${SERVICE_NAME}' from '${SERVICE_DIR}'"
  
  (
    cd "${SERVICE_DIR}"
    if [ -x "./uninstall.sh" ]; then
      run bash "./uninstall.sh"
    else
      warn "Skipping: uninstall.sh not found or not executable in '${SERVICE_DIR}'"
    fi
  )

  COUNT=$((COUNT + 1))
done

########################################
# Summary
########################################
log "All uninstall scripts executed successfully."
