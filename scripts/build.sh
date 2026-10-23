#!/usr/bin/env bash

# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script builds the Exygen monorepo packages
# under `apps/` (`agent`, `api`, `web`) either
# separately, in custom combinations, or all at once
# in sequential order (`agent` -> `api` -> `web`).
#
# Compatible with Linux and macOS (Bash 3.2+).
#
# Current File: build.sh
# Commands: [all|agent|api|web ...] [--parallel|-p] [--no-cache] [--dry-run] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/logs.sh"

set -eo pipefail

VALID_APPS=("agent" "api" "web")
NORMALIZED_TARGET=""

usage() {
    info "Usage: ./scripts/build.sh [targets...] [options]"
    info "Targets:"
    info "  all                 Build all packages in sequential order: agent -> api -> web (default)"
    info "  agent               Build apps/agent (Python exygen-agent package)"
    info "  api                 Build apps/api (Python FastAPI exygen-api package)"
    info "  web                 Build apps/web (TypeScript React + TanStack web application)"
    info "Options:"
    info "  --sequential, -s    Build targets one after another in order (default)"
    info "  --parallel, -p      Build targets concurrently via Nx run-many"
    info "  --no-cache          Bypass Nx build cache (--skip-nx-cache)"
    info "  --dry-run           Log the build commands without executing them"
    info "  --help, -h          Show this help message"
    info "Examples:"
    info "  ./scripts/build.sh"
    info "  ./scripts/build.sh agent"
    info "  ./scripts/build.sh agent api"
    info "  ./scripts/build.sh all --no-cache"
}

normalize_target() {
    local raw="${1#apps/}"
    raw="${raw%/}"
    case "$raw" in
        agent | api | web | all)
            NORMALIZED_TARGET="$raw"
            return 0
            ;;
        *)
            NORMALIZED_TARGET=""
            return 1
            ;;
    esac
}

contains_target() {
    local needle="$1"
    shift
    local item
    for item in "$@"; do
        if [[ "$item" == "$needle" ]]; then
            return 0
        fi
    done
    return 1
}

join_by_comma() {
    local IFS=','
    JOINED_CSV="$*"
}

main() {
    local mode="sequential"
    local no_cache=false
    local dry_run=false
    local requested=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help | -h)
                usage
                exit 0
                ;;
            --sequential | -s)
                mode="sequential"
                ;;
            --parallel | -p)
                mode="parallel"
                ;;
            --no-cache | --skip-nx-cache)
                no_cache=true
                ;;
            --dry-run)
                dry_run=true
                ;;
            --all)
                requested+=("all")
                ;;
            --agent)
                requested+=("agent")
                ;;
            --api)
                requested+=("api")
                ;;
            --web)
                requested+=("web")
                ;;
            -*)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                IFS=',' read -r -a split_targets <<< "$1"
                for t in "${split_targets[@]}"; do
                    if ! normalize_target "$t"; then
                        error "Unknown build target: '$t'. Expected one of: all, agent, api, web."
                        exit 1
                    fi
                    requested+=("$NORMALIZED_TARGET")
                done
                ;;
        esac
        shift
    done

    if (( ${#requested[@]} == 0 )) || contains_target "all" "${requested[@]}"; then
        requested=("${VALID_APPS[@]}")
    fi

    local targets=()
    local item
    for item in "${requested[@]}"; do
        if ! contains_target "$item" "${targets[@]}"; then
            targets+=("$item")
        fi
    done

    local nx_flags=()
    if $no_cache; then
        nx_flags+=("--skip-nx-cache")
    fi

    cd "$ROOT_DIR"

    info "Selected build targets (${mode}): ${targets[*]}"

    if [[ "$mode" == "parallel" && ${#targets[@]} -gt 1 ]]; then
        join_by_comma "${targets[@]}"
        local cmd=(pnpm nx run-many -t build "--projects=${JOINED_CSV}" "${nx_flags[@]}")
        if $dry_run; then
            info "[dry-run] Would run: ${cmd[*]}"
            return 0
        fi
        info "Running parallel build for: ${JOINED_CSV}"
        "${cmd[@]}"
        success "Completed parallel build for: ${targets[*]}"
        return 0
    fi

    local step=1
    local total="${#targets[@]}"
    for app in "${targets[@]}"; do
        local cmd=(pnpm nx run "${app}:build" "${nx_flags[@]}")
        if $dry_run; then
            info "[dry-run] (${step}/${total}) Would build '${app}': ${cmd[*]}"
        else
            info "(${step}/${total}) Building '${app}' (apps/${app})..."
            "${cmd[@]}"
            success "(${step}/${total}) Built '${app}' successfully."
        fi
        step=$(( step + 1 ))
    done

    if $dry_run; then
        info "Dry-run complete. No packages were built."
    else
        success "All requested packages built (${targets[*]})."
    fi
}

main "$@"
