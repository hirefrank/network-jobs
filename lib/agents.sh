#!/usr/bin/env bash
# Shared agent skill directory map for Network Jobs.
# shellcheck shell=bash

# Agent ids we support. Paths are resolved at call time (so HOME overrides work).
NETWORK_JOBS_AGENT_IDS=(
  claude-code
  cursor
  codex
  opencode
  pi
  gemini-cli
  hermes-agent
  agents
)

# Skill folders this suite installs (must match skills/ and setup).
NETWORK_JOBS_SKILL_IDS=(
  network-jobs-setup
  network-jobs-import
  careers-discover
  jobs-ingest
  network-jobs
  intro-email-generator
)

network_jobs_agent_dir() {
  local name="$1"
  case "$name" in
    claude-code) echo "$HOME/.claude/skills" ;;
    cursor) echo "$HOME/.cursor/skills" ;;
    codex) echo "$HOME/.codex/skills" ;;
    opencode) echo "$HOME/.config/opencode/skills" ;;
    pi) echo "$HOME/.pi/agent/skills" ;;
    gemini-cli) echo "$HOME/.gemini/skills" ;;
    hermes-agent) echo "$HOME/.hermes/skills" ;;
    agents) echo "$HOME/.agents/skills" ;;
    *) return 1 ;;
  esac
}

network_jobs_agent_hint() {
  local name="$1"
  case "$name" in
    claude-code) echo "$HOME/.claude" ;;
    cursor) echo "$HOME/.cursor" ;;
    codex) echo "$HOME/.codex" ;;
    opencode) echo "$HOME/.config/opencode" ;;
    pi) echo "$HOME/.pi" ;;
    gemini-cli) echo "$HOME/.gemini" ;;
    hermes-agent) echo "$HOME/.hermes" ;;
    agents) echo "$HOME/.agents" ;;
    *) return 1 ;;
  esac
}

network_jobs_detect_agents() {
  local name hint
  local -a found=()
  for name in "${NETWORK_JOBS_AGENT_IDS[@]}"; do
    hint="$(network_jobs_agent_hint "$name")"
    if [[ -d "$hint" ]]; then
      found+=("$name")
    fi
  done
  if ((${#found[@]} == 0)); then
    found=("claude-code")
  fi
  printf '%s\n' "${found[@]}"
}

network_jobs_list_agents() {
  local name dir hint
  for name in "${NETWORK_JOBS_AGENT_IDS[@]}"; do
    dir="$(network_jobs_agent_dir "$name")"
    hint="$(network_jobs_agent_hint "$name")"
    if [[ -d "$hint" ]]; then
      printf '%s\t%s\tdetected\n' "$name" "$dir"
    else
      printf '%s\t%s\t\n' "$name" "$dir"
    fi
  done
}
