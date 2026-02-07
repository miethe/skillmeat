#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Setup shared local agent artifacts across platform-specific directories.

Usage:
  scripts/setup_agent_platform_links.sh [options]

Options:
  --install-codex-home-skills   Also symlink local .claude/skills into $CODEX_HOME/skills/skillmeat-local/
  --codex-home PATH             Override CODEX_HOME (default: $HOME/.codex)
  --no-agents-link              Do not create AGENTS.md -> CLAUDE.md when AGENTS.md is missing
  -h, --help                    Show help

Notes:
  - This script never overwrites existing non-symlink files/directories.
  - Existing symlinks are updated in place.
EOF
}

log() {
  printf '%s\n' "$*"
}

link_or_skip() {
  local source_path="$1"
  local link_path="$2"

  mkdir -p "$(dirname "$link_path")"

  if [[ -L "$link_path" ]]; then
    local current_target
    current_target="$(readlink "$link_path" || true)"
    if [[ "$current_target" == "$source_path" ]]; then
      log "[ok] $link_path -> $source_path"
      return 0
    fi
    rm "$link_path"
    ln -s "$source_path" "$link_path"
    log "[update] $link_path -> $source_path"
    return 0
  fi

  if [[ -e "$link_path" ]]; then
    log "[skip] $link_path exists and is not a symlink"
    return 0
  fi

  ln -s "$source_path" "$link_path"
  log "[new] $link_path -> $source_path"
}

install_codex_home_skills() {
  local repo_root="$1"
  local codex_home="$2"
  local source_root="$repo_root/.claude/skills"
  local target_root="$codex_home/skills/skillmeat-local"

  if [[ ! -d "$source_root" ]]; then
    log "[warn] Missing source directory: $source_root"
    return 0
  fi

  mkdir -p "$target_root"

  local skill_dir
  for skill_dir in "$source_root"/*; do
    [[ -d "$skill_dir" ]] || continue
    local skill_name
    skill_name="$(basename "$skill_dir")"
    link_or_skip "$skill_dir" "$target_root/$skill_name"
  done
}

INSTALL_CODEX_HOME_SKILLS=0
CREATE_AGENTS_LINK=1
CODEX_HOME_DEFAULT="${CODEX_HOME:-$HOME/.codex}"
CODEX_HOME_PATH="$CODEX_HOME_DEFAULT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-codex-home-skills)
      INSTALL_CODEX_HOME_SKILLS=1
      shift
      ;;
    --codex-home)
      CODEX_HOME_PATH="${2:-}"
      if [[ -z "$CODEX_HOME_PATH" ]]; then
        log "[error] --codex-home requires a path"
        exit 1
      fi
      shift 2
      ;;
    --no-agents-link)
      CREATE_AGENTS_LINK=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "[error] Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

link_or_skip "$REPO_ROOT/.claude/skills" "$REPO_ROOT/.codex/skills"
link_or_skip "$REPO_ROOT/.claude/agents" "$REPO_ROOT/.codex/agents"
link_or_skip "$REPO_ROOT/.claude/commands" "$REPO_ROOT/.codex/commands"
link_or_skip "$REPO_ROOT/.claude/context" "$REPO_ROOT/.codex/context"
link_or_skip "$REPO_ROOT/.claude/rules" "$REPO_ROOT/.codex/rules"
link_or_skip "$REPO_ROOT/.claude/hooks" "$REPO_ROOT/.codex/hooks"

link_or_skip "$REPO_ROOT/.claude/skills" "$REPO_ROOT/.gemini/skills"
link_or_skip "$REPO_ROOT/.claude/agents" "$REPO_ROOT/.gemini/agents"
link_or_skip "$REPO_ROOT/.claude/commands" "$REPO_ROOT/.gemini/commands"

if [[ $CREATE_AGENTS_LINK -eq 1 ]]; then
  if [[ ! -e "$REPO_ROOT/AGENTS.md" ]]; then
    link_or_skip "$REPO_ROOT/CLAUDE.md" "$REPO_ROOT/AGENTS.md"
  else
    log "[skip] $REPO_ROOT/AGENTS.md already exists"
  fi
fi

if [[ $INSTALL_CODEX_HOME_SKILLS -eq 1 ]]; then
  install_codex_home_skills "$REPO_ROOT" "$CODEX_HOME_PATH"
fi

log "Done."
