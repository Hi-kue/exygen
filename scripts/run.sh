#!/usr/bin/env bash

# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script runs the Exygen monorepo packages under
# `apps/` (`agent`, `api`, `web`) either separately,
# in custom combinations (e.g., `api web`), or all at
# once in sequential order (`agent` -> `api` -> `web`)
# or parallel mode.
#
# Compatible with Linux and macOS (Bash 3.2+).
#
# Current File: run.sh
# Commands: [all|agent|api|web ...] [--sequential|-s] [--parallel|-p] [--strict-sequential] [--dry-run] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/logs.sh"

set -eo pipefail

VALID_APPS=("agent" "api" "web")
CHILD_PIDS=()
NORMALIZED_TARGET=""
JOINED_CSV=""

usage() {
    info "Usage: ./scripts/run.sh [targets...] [options]"
    info "Targets:"
    info "  all                   Run all applications in sequential order: agent -> api -> web (default)"
    info "  agent                 Run apps/agent (Python multi-agent pipeline CLI)"
    info "  api                   Run apps/api (FastAPI server on port 8000)"
    info "  web                   Run apps/web (React + TanStack dev server on port 3000)"
    info "Options:"
    info "  --sequential, -s      Start targets in sequential order (default)"
    info "  --strict-sequential   Run each target in foreground strictly one after another"
    info "  --parallel, -p        Run selected targets concurrently via Nx run-many"
    info "  --dry-run             Log the commands that would be executed without running them"
    info "  --help, -h            Show this help message"
    info "Examples:"
    info "  ./scripts/run.sh"
    info "  ./scripts/run.sh agent"
    info "  ./scripts/run.sh api"
    info "  ./scripts/run.sh web"
    info "  ./scripts/run.sh api web"
    info "  ./scripts/run.sh all --parallel"
}

cleanup_children() {
    if (( ${#CHILD_PIDS[@]} > 0 )); then
        info "Stopping running services (${CHILD_PIDS[*]})..."
        for pid in "${CHILD_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done
        wait 2>/dev/null || true
    fi
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
            --strict-sequential)
                mode="strict-sequential"
                ;;
            --parallel | -p | --together)
                mode="parallel"
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
                        error "Unknown application target: '$t'. Expected one of: all, agent, api, web."
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
    for item in "${requested[@]}"; do
        if ! contains_target "$item" "${targets[@]}"; then
            targets+=("$item")
        fi
    done

    cd "$ROOT_DIR"

    info "Selected applications (${mode}): ${targets[*]}"

    if (( ${#targets[@]} == 1 )); then
        local app="${targets[0]}"
        local cmd=(pnpm nx run "${app}:dev")
        if $dry_run; then
            info "[dry-run] Would run '${app}': ${cmd[*]}"
            return 0
        fi
        info "Running '${app}' (apps/${app})..."
        "${cmd[@]}"
        success "Finished running '${app}'."
        return 0
    fi

    if [[ "$mode" == "parallel" ]]; then
        join_by_comma "${targets[@]}"
        local cmd=(pnpm nx run-many -t dev "--projects=${JOINED_CSV}")
        if $dry_run; then
            info "[dry-run] Would run in parallel: ${cmd[*]}"
            return 0
        fi
        info "Starting applications in parallel via Nx: ${JOINED_CSV}"
        "${cmd[@]}"
        return 0
    fi

    if [[ "$mode" == "strict-sequential" ]]; then
        local step=1
        local total="${#targets[@]}"
        for app in "${targets[@]}"; do
            local cmd=(pnpm nx run "${app}:dev")
            if $dry_run; then
                info "[dry-run] (${step}/${total}) Would run '${app}': ${cmd[*]}"
            else
                info "(${step}/${total}) Running '${app}' (apps/${app})..."
                "${cmd[@]}"
                success "(${step}/${total}) Finished '${app}'."
            fi
            step=$(( step + 1 ))
        done
        return 0
    fi

    local step=1
    local total="${#targets[@]}"
    local services=()

    for app in "${targets[@]}"; do
        if [[ "$app" == "agent" ]]; then
            local cmd=(pnpm nx run "agent:dev")
            if $dry_run; then
                info "[dry-run] (${step}/${total}) Would run 'agent': ${cmd[*]}"
            else
                info "(${step}/${total}) Running 'agent' pipeline (apps/agent)..."
                "${cmd[@]}"
                success "(${step}/${total}) Completed 'agent' pipeline."
            fi
            step=$(( step + 1 ))
        else
            services+=("$app")
        fi
    done

    if (( ${#services[@]} == 0 )); then
        return 0
    fi

    if (( ${#services[@]} == 1 )); then
        local svc="${services[0]}"
        local cmd=(pnpm nx run "${svc}:dev")
        if $dry_run; then
            info "[dry-run] (${step}/${total}) Would run '${svc}': ${cmd[*]}"
            return 0
        fi
        info "(${step}/${total}) Starting '${svc}' (apps/${svc})..."
        "${cmd[@]}"
        return 0
    fi

    if $dry_run; then
        for svc in "${services[@]}"; do
            info "[dry-run] (${step}/${total}) Would start service '${svc}': pnpm nx run ${svc}:dev"
            step=$(( step + 1 ))
        done
        return 0
    fi

    trap cleanup_children EXIT INT TERM

    for svc in "${services[@]}"; do
        info "(${step}/${total}) Starting service '${svc}' (apps/${svc})..."
        pnpm nx run "${svc}:dev" &
        local pid=$!
        CHILD_PIDS+=("$pid")
        sleep 1
        step=$(( step + 1 ))
    done

    success "All requested services started in sequential order (${services[*]}). Press Ctrl+C to stop."
    wait "${CHILD_PIDS[@]}"
}

main "$@"
