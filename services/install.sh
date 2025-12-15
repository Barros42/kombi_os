#!/bin/bash
# Script: install.sh
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

# Verbosity levels:
# 0 = minimal
# 1 = detailed (default)
# 2 = very detailed (extra context + env + debug dumps)
VERBOSE="${VERBOSE:-1}"

# DEBUG_TRACE=1 enables `set -x` (very noisy)
DEBUG_TRACE="${DEBUG_TRACE:-0}"

# Log files
LOG_ROOT="${LOG_ROOT:-/var/log/kombios/bootstrap}"
RUN_ID="${RUN_ID:-$(date +'%Y%m%d-%H%M%S')}"
MAIN_LOG="${MAIN_LOG:-${LOG_ROOT}/bootstrap-${RUN_ID}.log}"

########################################
# Logging utilities
########################################
ts()     { date +"%Y-%m-%d %H:%M:%S%z"; }

_log_line() {
  local level="$1"; shift
  echo "[$(ts)] [${level}] $*"
}

log()    { _log_line "INFO" "$@"; }
warn()   { _log_line "WARN" "$@" >&2; }
error()  { _log_line "ERROR" "$@" >&2; }

# Print + exec with proper arg-splitting (no eval)
run() {
  if [ "${VERBOSE}" -ge 1 ]; then
    printf '[%s] [RUN ]' "$(ts)"
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  fi
  "$@"
}

# Same as run, but tee stdout/stderr to main log (useful for noisy commands)
run_tee() {
  if [ "${VERBOSE}" -ge 1 ]; then
    printf '[%s] [RUN ]' "$(ts)"
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  fi
  # Preserve exit code of the command in a pipeline
  set +e
  "$@" 2>&1 | tee -a "${MAIN_LOG}"
  local rc=${PIPESTATUS[0]}
  set -e
  return "${rc}"
}

# Per-service runner that prefixes each output line with service name, and logs to its own file
run_service_script() {
  local service_name="$1"
  local script_path="$2"
  local service_dir
  service_dir="$(dirname "${script_path}")"

  local service_log="${LOG_ROOT}/${service_name}-${RUN_ID}.log"

  log "Service log: ${service_log}"
  if [ "${VERBOSE}" -ge 1 ]; then
    log "Executing: ( cd ${service_dir}; bash ./install.sh )"
  fi

  set +e
  (
    cd "${service_dir}"
    # prefix each line with service name
    bash "./install.sh" 2>&1 \
      | awk -v svc="${service_name}" -v tsfmt="$(ts)" '{ print "["strftime("%Y-%m-%d %H:%M:%S%z")"] [SVC:"svc"] " $0 }'
  ) | tee -a "${service_log}" | tee -a "${MAIN_LOG}"
  local rc=${PIPESTATUS[0]}
  set -e

  if [ "${rc}" -ne 0 ]; then
    error "Service '${service_name}' install failed (exit: ${rc}). See: ${service_log}"
    return "${rc}"
  fi

  log "Service '${service_name}' install completed successfully."
}

########################################
# Enable debug trace if requested
########################################
if [ "${DEBUG_TRACE}" = "1" ]; then
  set -x
fi

########################################
# Ensure log dir + redirect main output to log (while still showing on console)
########################################
if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
fi

# Ensure log root exists (best effort)
if [ -n "${SUDO}" ]; then
  ${SUDO} mkdir -p "${LOG_ROOT}" || true
  ${SUDO} chmod 0755 "${LOG_ROOT}" || true
  ${SUDO} chown "$(id -un):$(id -gn)" "${LOG_ROOT}" 2>/dev/null || true
else
  mkdir -p "${LOG_ROOT}" || true
  chmod 0755 "${LOG_ROOT}" || true
fi

touch "${MAIN_LOG}" 2>/dev/null || true

# Tee everything printed by this script into the main log
# (keeps console output + writes to file)
exec > >(tee -a "${MAIN_LOG}") 2>&1

########################################
# Error trap to show failing line/cmd + context
########################################
on_error() {
  local exit_code=$?
  error "Script failed at line ${BASH_LINENO[0]} running command: '${BASH_COMMAND}' (exit: ${exit_code})"
  error "Context: cwd='$(pwd)' user='$(id -un)' uid='$(id -u)' host='$(hostname)'"
  error "Main log: ${MAIN_LOG}"
  if [ "${VERBOSE}" -ge 2 ]; then
    error "Last 50 log lines:"
    tail -n 50 "${MAIN_LOG}" || true
  fi
  exit "${exit_code}"
}
trap on_error ERR

########################################
# 0) Preconditions / Context
########################################
log "Bootstrap starting"
log "Base dir: ${BASE_DIR}"
log "Run id: ${RUN_ID}"
log "Main log: ${MAIN_LOG}"

log "Runtime context:"
run id
run pwd
run uname -a || true

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
log "Using sudo: ${SUDO:-no}"

if [ "${VERBOSE}" -ge 2 ]; then
  log "Env (sanitized):"
  env | sort | sed -E 's/(TOKEN|KEY|SECRET|PASSWORD)=.*/\1=***REDACTED***/g' || true
fi

########################################
# Directório de destino
########################################
KOMBIOS_BIN_DIR="/usr/local/bin/kombios"

if [ ! -d "${KOMBIOS_BIN_DIR}" ]; then
  log "Creating directory: ${KOMBIOS_BIN_DIR}"
  run ${SUDO} mkdir -p "${KOMBIOS_BIN_DIR}"
  run ${SUDO} chmod 0755 "${KOMBIOS_BIN_DIR}"
else
  log "Directory already exists: ${KOMBIOS_BIN_DIR}"
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

log "Upgrading pip/setuptools/wheel inside venv"
run "${PIP_BIN}" --version
run_tee "${PIP_BIN}" install --upgrade pip setuptools wheel
run "${PY_BIN}" -V

########################################
# 3) Create or refresh environment file
########################################
create_env_file() {
  local tmpfile
  tmpfile="$(mktemp)"
  cat > "${tmpfile}" <<'EOF'
SERVER_URL=https://api.kombi.digital
KOMBI_ID=000000000f272617
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

  if [ "${VERBOSE}" -ge 2 ]; then
    log "ENV_FILE contents:"
    run cat "${ENV_FILE}"
  fi
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
    log "[${COUNT_REQ}/${TOTAL_REQ}] Installing requirements for service '${SERVICE_NAME}' (${REQ})"

    if [ "${VERBOSE}" -ge 1 ]; then
      run wc -l "${REQ}" || true
    fi

    # ensure we install into the venv
    run_tee "${PIP_BIN}" install --require-virtualenv -r "${REQ}"

    if [ "${VERBOSE}" -ge 2 ]; then
      log "pip freeze (tail) after '${SERVICE_NAME}':"
      run "${PIP_BIN}" freeze | tail -n 20 || true
    fi

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
  export VENV_DIR USER_NAME ENV_FILE VERBOSE DEBUG_TRACE

  for SCRIPT in "${SCRIPTS[@]}"; do
    SERVICE_DIR="$(dirname "${SCRIPT}")"
    SERVICE_NAME="$(basename "${SERVICE_DIR}")"

    log "#######################################"
    log "[${COUNT_SH}/${TOTAL_SH}] Service '${SERVICE_NAME}'"
    log "Dir: ${SERVICE_DIR}"
    log "Script: ${SCRIPT}"

    if [ "${VERBOSE}" -ge 2 ]; then
      log "Directory listing:"
      run ls -la "${SERVICE_DIR}" || true
    fi

    run_service_script "${SERVICE_NAME}" "${SCRIPT}"

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
