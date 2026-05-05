#!/usr/bin/env bash
set -euo pipefail

# ── SEO Workbench Setup ──────────────────────────────────────────────────
# Clones the three required external skill packs into the project root.
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

declare -A REPOS=(
  ["superseo-skills"]="https://github.com/inhouseseo/superseo-skills.git"
  ["seomachine"]="https://github.com/TheCraigHewitt/seomachine.git"
  ["claude-seo"]="https://github.com/AgriciDaniel/claude-seo.git"
)

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Prerequisite checks ──────────────────────────────────────────────────

header "Checking prerequisites"

if ! command -v git &>/dev/null; then
  err "git is not installed. Install it first: https://git-scm.com"
  exit 1
fi
info "git found: $(git --version | head -1)"

# ── Clone / update repos ─────────────────────────────────────────────────

header "Syncing skill packs"

for name in "${!REPOS[@]}"; do
  url="${REPOS[$name]}"
  target="${PROJECT_ROOT}/${name}"

  if [ -d "$target/.git" ]; then
    info "${name} already exists, pulling latest..."
    git -C "$target" pull --ff-only
  elif [ -d "$target" ]; then
    warn "${name} directory exists but is not a git repo — skipping (remove it manually if you want a fresh clone)"
  else
    printf "Cloning %s..." "$name"
    git clone --depth 1 "$url" "$target" &>/dev/null
    info "${name} cloned"
  fi
done

# ── Done ─────────────────────────────────────────────────────────────────

header "Setup complete"

cat <<EOF

Next steps:
  1. Start Claude Code in this directory:
       claude

  2. Inside Claude Code, initialize your project:
       /workflow:init shopify --name "My Store" --url "https://example.com"

  See README.md for all project types and full documentation.

EOF
