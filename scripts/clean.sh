#!/usr/bin/env bash

# README
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*
# This script removes build and cache artifacts from
# the entire Exygen codebase or from specific app
# folders under `apps/` (`agent`, `api`, `web`).
# It never descends into `.git` directories.
#
# Compatible with Linux and macOS (Bash 3.2+).
#
# Current File: clean.sh
# Commands: [all|agent|api|web|path ...] [--dry-run] [--yes|-y] [--help|-h]
# *=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/logs.sh"

set -eo pipefail

ARTIFACT_DIRS=(
    node_modules .npm .yarn .pnp .nx
    dist build out .output .vinxi
    .vite vite-temp .tanstack .wrangler .mf
    .tsbuildinfo coverage .vitest .nyc_output
    .biome .eslintcache
    __pycache__ .mypy_cache .ruff_cache .pytest_cache
    .hypothesis htmlcov .tox .eggs .venv venv env .env_dir
    .cache .parcel-cache .turbo .next .nuxt .svelte-kit
    storybook-static .storybook-out
)

GLOB_PATTERNS=("*.egg-info" "*.dist-info")
RESOLVED_ROOTS=()

usage() {
    info "Usage: ./scripts/clean.sh [targets...] [options]"
    info "Targets:"
    info "  all, .              Clean artifacts across the entire repository (default)"
    info "  agent               Clean artifacts in apps/agent (and dist/apps/agent)"
    info "  api                 Clean artifacts in apps/api (and dist/apps/api)"
    info "  web                 Clean artifacts in apps/web (and dist/apps/web)"
    info "  <path>              Clean artifacts in a specific directory path"
    info "Options:"
    info "  --dry-run           List directories that would be deleted without removing them"
    info "  --yes, -y           Skip confirmation prompt"
    info "  --help, -h          Show this help message"
    info "Examples:"
    info "  ./scripts/clean.sh --dry-run"
    info "  ./scripts/clean.sh web --yes"
    info "  ./scripts/clean.sh agent api -y"
    info "  ./scripts/clean.sh all -y"
}

resolve_scan_roots() {
    local arg="$1"
    RESOLVED_ROOTS=()
    case "$arg" in
        all | .)
            RESOLVED_ROOTS+=("$ROOT_DIR")
            ;;
        agent | api | web)
            RESOLVED_ROOTS+=("$ROOT_DIR/apps/$arg")
            if [[ -d "$ROOT_DIR/dist/apps/$arg" ]]; then
                RESOLVED_ROOTS+=("$ROOT_DIR/dist/apps/$arg")
            fi
            ;;
        apps/agent | apps/api | apps/web | apps/agent/ | apps/api/ | apps/web/)
            local app_name="${arg#apps/}"
            app_name="${app_name%/}"
            RESOLVED_ROOTS+=("$ROOT_DIR/apps/$app_name")
            if [[ -d "$ROOT_DIR/dist/apps/$app_name" ]]; then
                RESOLVED_ROOTS+=("$ROOT_DIR/dist/apps/$app_name")
            fi
            ;;
        *)
            if [[ -d "$arg" ]]; then
                RESOLVED_ROOTS+=("$(cd "$arg" && pwd)")
            elif [[ -d "$ROOT_DIR/$arg" ]]; then
                RESOLVED_ROOTS+=("$(cd "$ROOT_DIR/$arg" && pwd)")
            else
                return 1
            fi
            ;;
    esac
    return 0
}

main() {
    local dry_run=false
    local skip_confirm=false
    local raw_targets=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help | -h)
                usage
                exit 0
                ;;
            --dry-run)
                dry_run=true
                ;;
            --yes | -y)
                skip_confirm=true
                ;;
            --all)
                raw_targets+=("all")
                ;;
            --agent)
                raw_targets+=("agent")
                ;;
            --api)
                raw_targets+=("api")
                ;;
            --web)
                raw_targets+=("web")
                ;;
            -*)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                IFS=',' read -r -a split_args <<< "$1"
                for item in "${split_args[@]}"; do
                    raw_targets+=("$item")
                done
                ;;
        esac
        shift
    done

    if (( ${#raw_targets[@]} == 0 )); then
        raw_targets=("all")
    fi

    local scan_roots=()
    for raw in "${raw_targets[@]}"; do
        if ! resolve_scan_roots "$raw"; then
            error "'$raw' is not a valid app name (agent, api, web, all) or directory."
            exit 1
        fi
        for r in "${RESOLVED_ROOTS[@]}"; do
            local exists=false
            for existing in "${scan_roots[@]}"; do
                if [[ "$existing" == "$r" ]]; then
                    exists=true
                    break
                fi
            done
            if ! $exists; then
                scan_roots+=("$r")
            fi
        done
    done

    local name_args=()
    local first=true
    for name in "${ARTIFACT_DIRS[@]}"; do
        $first || name_args+=(-o)
        name_args+=(-name "$name")
        first=false
    done
    for pattern in "${GLOB_PATTERNS[@]}"; do
        name_args+=(-o -name "$pattern")
    done

    local targets=()
    for root in "${scan_roots[@]}"; do
        info "Scanning: $root"
        if [[ "$root" == "$ROOT_DIR/dist/apps/"* && -d "$root" ]]; then
            targets+=("$root")
            continue
        fi
        while IFS= read -r found_dir; do
            if [[ -n "$found_dir" ]]; then
                targets+=("$found_dir")
            fi
        done < <(
            find "$root" \
                \( -name ".git" -o -name ".hg" -o -name ".svn" \) -prune \
                -o \( "${name_args[@]}" \) -type d -print -prune \
                2>/dev/null
        )
    done

    if (( ${#targets[@]} == 0 )); then
        info "Nothing to clean up."
        return 0
    fi

    local word="directories"
    (( ${#targets[@]} == 1 )) && word="directory"

    info "Found ${#targets[@]} $word to remove:"
    for target_path in "${targets[@]}"; do
        info "  - $target_path"
    done

    if $dry_run; then
        info "Dry-run was set, nothing was deleted."
        return 0
    fi

    if ! $skip_confirm; then
        read -r -p "Delete all of the above? [y/N] " answer
        case "$answer" in
            [yY] | [yY][eE][sS]) ;;
            *) info "Aborted."; return 0 ;;
        esac
    fi

    local removed=0 errors=0
    for path in "${targets[@]}"; do
        if rm -rf "$path"; then
            removed=$(( removed + 1 ))
        else
            warn "Could not remove: $path"
            errors=$(( errors + 1 ))
        fi
    done

    local done_word="directories"
    (( removed == 1 )) && done_word="directory"

    if (( errors > 0 )); then
        warn "Removed $removed $done_word. $errors error(s), see output above."
    else
        success "Removed $removed $done_word."
    fi
}

main "$@"
