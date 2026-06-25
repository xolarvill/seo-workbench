#!/usr/bin/env bash
set -euo pipefail

# ── SEO Workbench Setup ──────────────────────────────────────────────────
# Optionally clones third-party source packs into the project root.
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

# ── Repositories ─────────────────────────────────────────────────────────

REPO_NAMES=("superseo-skills" "seomachine" "claude-seo")
REPO_URLS=(
  "https://github.com/inhouseseo/superseo-skills.git"
  "https://github.com/TheCraigHewitt/seomachine.git"
  "https://github.com/AgriciDaniel/claude-seo.git"
)

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Prerequisite checks ──────────────────────────────────────────────────

header "Checking prerequisites"

if ! command -v git &>/dev/null; then
  err "git is not installed. Install it first: https://git-scm.com"
  exit 1
fi
info "git found: $(git --version | head -1)"

# ── Clone repos ──────────────────────────────────────────────────────────

header "Checking optional source packs"

for index in "${!REPO_NAMES[@]}"; do
  name="${REPO_NAMES[$index]}"
  url="${REPO_URLS[$index]}"
  target="${PROJECT_ROOT}/${name}"

  if [ -d "$target/.git" ]; then
    info "${name} already exists; leaving pinned local copy untouched"
  elif [ -d "$target" ]; then
    warn "${name} directory exists but is not a git repo — skipping (remove it manually if you want a fresh clone)"
  else
    printf "Cloning %s..." "$name"
    git clone --depth 1 "$url" "$target" &>/dev/null
    info "${name} cloned; pin or update it manually when needed"
  fi
done

# ── Done ─────────────────────────────────────────────────────────────────

header "Setup complete"

cat <<EOF

Next steps:
  1. Initialize a project with the agent-neutral CLI:
       env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench init shopify --name "My Store" --url "https://example.com"

  2. Check the next workflow step:
       env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next

EOF
