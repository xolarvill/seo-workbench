#!/usr/bin/env bash
set -euo pipefail

# ── SEO Workbench Setup ──────────────────────────────────────────────────
# Installs and verifies the standalone workbench runtimes.
# Run this once after cloning seo-workbench:
#   git clone https://github.com/<your-org>/seo-workbench.git
#   cd seo-workbench
#   ./setup.sh
# ─────────────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()  { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err()   { printf "${RED}[✗]${NC} %s\n" "$*"; }
header(){ printf "\n${BOLD}── %s ──${NC}\n" "$*"; }

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="${PROJECT_ROOT}/.runtime"
BROWSER_DIR="${RUNTIME_DIR}/playwright"
TECH_BIN="${RUNTIME_DIR}/bin/technology-detector"
CHECK_ONLY=0
ASSUME_YES=0
LOCAL_BROWSER=0

usage() {
  cat <<EOF
Usage: ./setup.sh [--check] [--yes] [--local-browser]

  --check          Verify the complete environment without installing anything.
  --yes            Install missing Homebrew prerequisites without prompting.
  --local-browser  Install Playwright's pinned Chromium instead of reusing system Chrome.
EOF
}

for arg in "$@"; do
  case "${arg}" in
    --check) CHECK_ONLY=1 ;;
    --yes) ASSUME_YES=1 ;;
    --local-browser) LOCAL_BROWSER=1 ;;
    -h|--help) usage; exit 0 ;;
    *) err "unknown option: ${arg}"; usage; exit 2 ;;
  esac
done

version_at_least() {
  local current="$1" required_major="$2" required_minor="$3"
  [[ "${current}" =~ ^([0-9]+)\.([0-9]+) ]] || return 1
  (( BASH_REMATCH[1] > required_major || (BASH_REMATCH[1] == required_major && BASH_REMATCH[2] >= required_minor) ))
}

node_is_24() {
  [[ "$1" =~ ^24\.([0-9]+)\.([0-9]+) ]]
}

confirm() {
  local prompt="$1" reply
  if (( ASSUME_YES )); then
    return 0
  fi
  read -r -p "${prompt} [y/N] " reply
  [[ "${reply}" =~ ^[Yy]$ ]]
}

node_path() {
  local brew_node brew_prefix
  if command -v brew &>/dev/null && brew_prefix="$(brew --prefix node@24 2>/dev/null)"; then
    brew_node="${brew_prefix}/bin/node"
    if [[ -x "${brew_node}" ]]; then
      printf '%s\n' "${brew_node}"
      return
    fi
  fi
  if [[ -x "${RUNTIME_DIR}/bin/node" ]]; then
    printf '%s\n' "${RUNTIME_DIR}/bin/node"
    return
  fi
  command -v node 2>/dev/null || true
}

go_path() {
  local brew_go brew_prefix
  if command -v brew &>/dev/null && brew_prefix="$(brew --prefix go 2>/dev/null)"; then
    brew_go="${brew_prefix}/bin/go"
    if [[ -x "${brew_go}" ]]; then
      printf '%s\n' "${brew_go}"
      return
    fi
  fi
  command -v go 2>/dev/null || true
}

npm_path() {
  local node_bin="$1"
  if [[ -n "${node_bin}" && -x "$(dirname "${node_bin}")/npm" ]]; then
    printf '%s/npm\n' "$(dirname "${node_bin}")"
    return
  fi
  command -v npm 2>/dev/null || true
}

# ── Prerequisite checks ──────────────────────────────────────────────────

header "Checking system prerequisites"

if ! command -v git &>/dev/null; then
  err "git is not installed. Install it first: https://git-scm.com"
  exit 1
fi
info "git found: $(git --version | head -1)"

NEEDS_SYSTEM=0
command -v uv &>/dev/null || NEEDS_SYSTEM=1
GO_BIN="$(go_path)"
if [[ -z "${GO_BIN}" ]] || ! version_at_least "$(${GO_BIN} env GOVERSION 2>/dev/null | sed 's/^go//' || true)" 1 25; then
  NEEDS_SYSTEM=1
fi
NODE_BIN="$(node_path)"
if [[ -z "${NODE_BIN}" ]] || ! node_is_24 "$(${NODE_BIN} -p 'process.versions.node' 2>/dev/null || true)"; then
  NEEDS_SYSTEM=1
fi

if (( NEEDS_SYSTEM )); then
  if (( CHECK_ONLY )); then
    err "missing required system runtimes; run ./setup.sh to install them"
    exit 1
  fi
  if [[ "$(uname -s)" != "Darwin" ]] || ! command -v brew &>/dev/null; then
    err "automatic system installation currently requires macOS and Homebrew"
    exit 1
  fi
  if ! confirm "Install missing uv, Go, and Node 24 LTS with Homebrew?"; then
    err "setup cancelled"
    exit 1
  fi
  HOMEBREW_NO_AUTO_UPDATE=1 brew bundle --file "${PROJECT_ROOT}/Brewfile"
  NODE_BIN="$(node_path)"
  GO_BIN="$(go_path)"
fi

UV_BIN="$(command -v uv 2>/dev/null || true)"
NPM_BIN="$(npm_path "${NODE_BIN}")"

[[ -n "${UV_BIN}" ]] || { err "uv is unavailable"; exit 1; }
[[ -n "${GO_BIN}" ]] || { err "Go is unavailable"; exit 1; }
[[ -n "${NODE_BIN}" && -n "${NPM_BIN}" ]] || { err "Node 24/npm is unavailable"; exit 1; }

GO_VERSION="$(${GO_BIN} env GOVERSION 2>/dev/null | sed 's/^go//')"
version_at_least "${GO_VERSION}" 1 25 || { err "Go 1.25+ is required; found ${GO_VERSION:-unknown}"; exit 1; }
NODE_VERSION="$(${NODE_BIN} -p 'process.versions.node')"
node_is_24 "${NODE_VERSION}" || { err "Node 24 LTS is required; found ${NODE_VERSION:-unknown}"; exit 1; }

info "uv found: $(${UV_BIN} --version | head -1)"
info "go found: $(${GO_BIN} version)"
info "node found: ${NODE_VERSION}"
info "npm found: $(${NPM_BIN} --version)"

if [ ! -f "${PROJECT_ROOT}/templates/state.json" ]; then
  err "templates/state.json is missing"
  exit 1
fi
info "standalone templates found"

if (( CHECK_ONLY )); then
  header "Checking project-local runtime"
  [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]] || { err "Python environment is missing"; exit 1; }
  [[ -x "${TECH_BIN}" ]] || { err "compiled technology detector is missing"; exit 1; }
  [[ -x "${PROJECT_ROOT}/node_modules/.bin/lighthouse" ]] || { err "Lighthouse dependency is missing"; exit 1; }
  "${PROJECT_ROOT}/.venv/bin/python" -c "import wappalyzer" \
    || { err "balanced Wappalyzer technology detector is missing"; exit 1; }
  "${PROJECT_ROOT}/.venv/bin/python" -c "import google.auth, google_auth_oauthlib" \
    || { err "Google API authentication support is missing"; exit 1; }
  env PLAYWRIGHT_BROWSERS_PATH="${BROWSER_DIR}" "${PROJECT_ROOT}/.venv/bin/python" \
    -m seo_workbench_tools.browser_runtime --print >/dev/null \
    || { err "Chrome or Chromium is missing"; exit 1; }
  (cd "${PROJECT_ROOT}" && "${NODE_BIN}" seo_workbench_tools/lighthouse_runner.mjs --self-test >/dev/null)
  "${TECH_BIN}" -h >/dev/null 2>&1
  info "project-local Python, Go helper, Wappalyzer, Google auth, Lighthouse, and browser runtime are ready"
  exit 0
fi

header "Installing project-local runtimes"
for private_path in "${RUNTIME_DIR}" "${RUNTIME_DIR}/google" "${RUNTIME_DIR}/google/profiles"; do
  if [[ -L "${private_path}" ]]; then
    err "private runtime path cannot be a symlink: ${private_path}"
    exit 1
  fi
done
mkdir -p "${RUNTIME_DIR}/bin" "${BROWSER_DIR}" "${RUNTIME_DIR}/google/profiles"
chmod 700 "${RUNTIME_DIR}/google" "${RUNTIME_DIR}/google/profiles"
ln -sf "${NODE_BIN}" "${RUNTIME_DIR}/bin/node"

env UV_CACHE_DIR="${PROJECT_ROOT}/.uv-cache" UV_PYTHON_INSTALL_DIR="${PROJECT_ROOT}/.uv-python" \
  "${UV_BIN}" python install 3.11
env UV_CACHE_DIR="${PROJECT_ROOT}/.uv-cache" UV_PYTHON_INSTALL_DIR="${PROJECT_ROOT}/.uv-python" \
  "${UV_BIN}" sync --frozen --python 3.11 --extra rendered --extra technology --extra google --group dev

(cd "${PROJECT_ROOT}" && env PATH="$(dirname "${NODE_BIN}"):${PATH}" "${NPM_BIN}" ci)

if (( ! LOCAL_BROWSER )) && BROWSER_EXECUTABLE="$(env PLAYWRIGHT_BROWSERS_PATH="${BROWSER_DIR}" \
  "${PROJECT_ROOT}/.venv/bin/python" -m seo_workbench_tools.browser_runtime --print 2>/dev/null)"; then
  info "browser found: ${BROWSER_EXECUTABLE}"
else
  info "installing project-local Chromium"
  env PLAYWRIGHT_BROWSERS_PATH="${BROWSER_DIR}" UV_CACHE_DIR="${PROJECT_ROOT}/.uv-cache" \
    PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=120000 \
    "${UV_BIN}" run --frozen --python 3.11 --extra rendered --extra technology --extra google python -m playwright install chromium
fi

(cd "${PROJECT_ROOT}/seo_workbench_tools/technology_detector" && \
  env GOPROXY="${SEO_WORKBENCH_GOPROXY:-https://proxy.golang.org|https://goproxy.cn|direct}" \
  "${GO_BIN}" build -trimpath -o "${TECH_BIN}" .)

if [[ -f "${PROJECT_ROOT}/seo_workbench_tools/lighthouse_runner.mjs" ]]; then
  (cd "${PROJECT_ROOT}" && "${NODE_BIN}" seo_workbench_tools/lighthouse_runner.mjs --self-test)
fi

"${TECH_BIN}" -h >/dev/null 2>&1
env PLAYWRIGHT_BROWSERS_PATH="${BROWSER_DIR}" "${PROJECT_ROOT}/.venv/bin/python" \
  -m seo_workbench_tools.browser_runtime --print >/dev/null
env PLAYWRIGHT_BROWSERS_PATH="${BROWSER_DIR}" UV_CACHE_DIR="${PROJECT_ROOT}/.uv-cache" \
  "${UV_BIN}" run --frozen --python 3.11 --extra rendered --extra google python -m seo_workbench_tools.rendered_probe --self-test

# ── Done ─────────────────────────────────────────────────────────────────

header "Setup complete"

cat <<EOF

Environment ready. Next steps:
  1. Initialize a project with the agent-neutral CLI:
       env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench init shopify --name "My Store" --url "https://example.com"

  2. Check the next workflow step:
       env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next

  3. Optional Google evidence requires credentials after setup:
       export SEO_WORKBENCH_CRUX_API_KEY="..."
       python -m seo_workbench gsc auth --client-secret /path/to/oauth-client.json

EOF
