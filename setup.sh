#!/usr/bin/env bash
set -euo pipefail

# ── SEO Workbench Setup ──────────────────────────────────────────────────
# Checks local prerequisites for the standalone workbench.
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

# ── Prerequisite checks ──────────────────────────────────────────────────

header "Checking prerequisites"

if ! command -v git &>/dev/null; then
  err "git is not installed. Install it first: https://git-scm.com"
  exit 1
fi
info "git found: $(git --version | head -1)"

if ! command -v uv &>/dev/null; then
  warn "uv is not installed. Install it first: https://docs.astral.sh/uv/"
else
  info "uv found: $(uv --version | head -1)"
fi

if ! command -v go &>/dev/null; then
  warn "go 1.25+ is not installed; technology detection will be unavailable"
else
  GO_VERSION="$(go env GOVERSION 2>/dev/null || true)"
  if [[ "${GO_VERSION}" =~ ^go([0-9]+)\.([0-9]+) ]] && (( BASH_REMATCH[1] > 1 || (BASH_REMATCH[1] == 1 && BASH_REMATCH[2] >= 25) )); then
    info "go found: $(go version)"
  else
    warn "go 1.25+ is required for technology detection; found ${GO_VERSION:-unknown version}"
  fi
fi

if [ ! -f "${PROJECT_ROOT}/templates/state.json" ]; then
  err "templates/state.json is missing"
  exit 1
fi
info "standalone templates found"

# ── Done ─────────────────────────────────────────────────────────────────

header "Setup complete"

cat <<EOF

Next steps:
  1. Initialize a project with the agent-neutral CLI:
       env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench init shopify --name "My Store" --url "https://example.com"

  2. Check the next workflow step:
       env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next

EOF
