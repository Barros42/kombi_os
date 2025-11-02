#!/bin/bash
# Script: bootstrap.sh
# Purpose: Prepare KombiOS environment (venv, user, env file), install requirements,
#          and execute per-service install.sh scripts. Verbose and idempotent.

set -euo pipefail

########################################
# Config (can be overridden via env)
########################################
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${VENV_DIR:-/opt/kombios/venv}"
USER_NAME="${USER_NAME:-kombios}"
ENV_FILE="${ENV_FILE:-/etc/kombios.env}"
VERBOSE="${VERBOSE:-1}"            # 1 = detailed logs; 0 = quieter
DEBUG_TRACE="${DEBUG_TRACE:-0}"    # 1 = set -x

########################################
# Logging utilities
########################################
ts()     { date +"%Y-%m-%d %H:%M:%S%z"; }
log()    { echo "[$(ts)] [INFO] $*"; }
warn()   { echo "[$(ts)] [WARN] $*" >&2; }
error()  { echo "[$(ts)] [ERROR] $*" >&2; }
run() {  # print + exec with proper arg-splitting (no eval)
  if [ "${VERBOSE}" = "1" ]; then
    printf '[%s] [RUN ]' "$(ts)"
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  fi
  "$@"
}

if [ "${DEBUG_TRACE}" = "1" ]; then set -x; fi

########################################
# Error trap to show failing line/cmd
########################################
on_error() {
  local exit_code=$?
  error "Script failed at line ${BASH_LINENO[0]} running command: '${BASH_COMMAND}' (exit: ${exit_code})"
  exit "${exit_code}"
}
trap on_error ERR

########################################
# 0) Preconditions
########################################
if ! command -v python3 >/dev/null 2>&1; then
  error "python3 not found in PATH."
  exit 1
fi
PYTHON_BIN="$(command -v python3)"
log "Using python3 at: ${PYTHON_BIN}"
run "${PYTHON_BIN}" -V

if ! command -v sudo >/dev/null 2>&1; then
  warn "sudo not found; running without sudo. You may hit permission errors."
  SUDO=""
else
  SUDO="sudo"
fi

########################################
# 1) Ensure system user
########################################
if id -u "${USER_NAME}" >/dev/null 2>&1; then
  log "User '${USER_NAME}' already exists."
else
  log "Creating system user '${USER_NAME}' (no login shell)."
  run ${SUDO} useradd -r -s /bin/false "${USER_NAME}"
fi

########################################
# 2) Ensure virtualenv
########################################
if [ ! -d "${VENV_DIR}" ]; then
  log "Creating virtual environment at: ${VENV_DIR}"
  run ${SUDO} mkdir -p "${VENV_DIR}"
  run ${SUDO} "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  run ${SUDO} chown -R "${USER_NAME}:${USER_NAME}" "${VENV_DIR}"
else
  log "Virtual environment already present at: ${VENV_DIR}"
fi

PIP_BIN="${VENV_DIR}/bin/pip"
PY_BIN="${VENV_DIR}/bin/python"

if [ ! -x "${PIP_BIN}" ]; then
  error "pip not found at ${PIP_BIN}"
  exit 1
fi

log "Upgrading pip/setuptools/wheel inside venv:"
run "${PIP_BIN}" --version
run "${PIP_BIN}" install --upgrade pip setuptools wheel
run "${PY_BIN}" -V

########################################
# 3) Create or refresh environment file
########################################
create_env_file() {
  local tmpfile
  tmpfile="$(mktemp)"
  cat > "${tmpfile}" <<'EOF'
SERVER_URL=secret
KOMBI_ID=secret
PYTHONUNBUFFERED=1
EOF

  if [ -f "${ENV_FILE}" ] && cmp -s "${tmpfile}" "${ENV_FILE}"; then
    log "Environment file unchanged at ${ENV_FILE}"
    rm -f "${tmpfile}"
    return
  fi

  if [ -f "${ENV_FILE}" ]; then
    log "Updating environment file at ${ENV_FILE}"
  else
    log "Creating environment file at ${ENV_FILE}"
  fi
  run ${SUDO} tee "${ENV_FILE}" >/dev/null < "${tmpfile}"
  run ${SUDO} chmod 0644 "${ENV_FILE}"
  rm -f "${tmpfile}"
}
create_env_file

########################################
# STEP 1 - Install all requirements.txt
########################################
log "Scanning for requirements.txt files under: ${BASE_DIR} (depth=2)"
mapfile -t REQ_FILES < <(find "${BASE_DIR}" -mindepth 2 -maxdepth 2 -type f -name "requirements.txt" | sort)

TOTAL_REQ=${#REQ_FILES[@]}
log "Found ${TOTAL_REQ} requirements.txt file(s)."

if [ "${TOTAL_REQ}" -eq 0 ]; then
  warn "No requirements.txt found. Skipping Python dependencies installation."
else
  COUNT_REQ=1
  for REQ in "${REQ_FILES[@]}"; do
    SERVICE_DIR="$(dirname "${REQ}")"
    SERVICE_NAME="$(basename "${SERVICE_DIR}")"
    log "[${COUNT_REQ}/${TOTAL_REQ}] Installing requirements for service '${SERVICE_NAME}'"
    if [ "${VERBOSE}" = "1" ]; then
      run wc -l "${REQ}"
    fi
    # ensure we install into the venv
    run "${PIP_BIN}" install --require-virtualenv -r "${REQ}"
    COUNT_REQ=$((COUNT_REQ + 1))
  done
  log "All Python requirements installed."
fi

########################################
# STEP 2 - Run each install.sh inside subfolders
########################################
log "Scanning for install.sh scripts under: ${BASE_DIR} (depth=2)"
mapfile -t SCRIPTS < <(find "${BASE_DIR}" -mindepth 2 -maxdepth 2 -type f -name "install.sh" ! -path "${BASE_DIR}/install.sh" | sort)

TOTAL_SH=${#SCRIPTS[@]}
log "Found ${TOTAL_SH} install.sh script(s)."

if [ "${TOTAL_SH}" -eq 0 ]; then
  warn "No child install.sh scripts found. Skipping service setup stage."
else
  COUNT_SH=1
  export VENV_DIR USER_NAME ENV_FILE
  for SCRIPT in "${SCRIPTS[@]}"; do
    SERVICE_DIR="$(dirname "${SCRIPT}")"
    SERVICE_NAME="$(basename "${SERVICE_DIR}")"
    log "[${COUNT_SH}/${TOTAL_SH}] Running install for service '${SERVICE_NAME}' at '${SERVICE_DIR}'"
    (
      cd "${SERVICE_DIR}"
      run bash "./install.sh"
    )
    COUNT_SH=$((COUNT_SH + 1))
  done
  log "All service install scripts executed successfully."
fi

########################################
# Summary
########################################
log "Summary:"
log "- Base dir: ${BASE_DIR}"
log "- Venv dir: ${VENV_DIR}"
log "- Env file: ${ENV_FILE}"
log "- Requirements processed: ${TOTAL_REQ}"
log "- Install scripts executed: ${TOTAL_SH}"

log "Bootstrap completed successfully."
