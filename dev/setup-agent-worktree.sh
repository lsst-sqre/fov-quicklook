#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

STELLAR_GLOBE_DIR="${REPO_ROOT}/frontend/lib/stellar-globe"

PHALANX_DIR="${REPO_ROOT}/k8s/phalanx"
PHALANX_URL="https://github.com/lsst-sqre/phalanx.git"

BEST_EFFORT=false
MISSING_ONLY=false
INSTALL_HOOKS=true

log() {
    printf '[setup-agent-worktree] %s\n' "$*"
}

warn() {
    printf '[setup-agent-worktree] warning: %s\n' "$*" >&2
}

fail() {
    printf '[setup-agent-worktree] error: %s\n' "$*" >&2
    exit 1
}

run_step() {
    if "$BEST_EFFORT"; then
        "$@" || warn "command failed: $*"
        return 0
    fi
    "$@"
}

is_expected_remote_url() {
    local actual="$1"
    local expected="$2"
    case "$actual" in
        "$expected"|"$expected".git)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

validate_remote_url() {
    local repo_dir="$1"
    local expected_url="$2"
    local name="$3"
    local actual_url

    actual_url="$(git -C "$repo_dir" remote get-url origin 2>/dev/null || true)"
    if [[ -z "$actual_url" ]]; then
        fail "${name} repo at ${repo_dir} does not have origin"
    fi
    if ! is_expected_remote_url "$actual_url" "$expected_url"; then
        fail "${name} repo at ${repo_dir} points to unexpected origin: ${actual_url}"
    fi
}

ensure_vendored_stellar_globe() {
    local manifest="${STELLAR_GLOBE_DIR}/stellar-globe/package.json"

    if [[ -f "$manifest" ]]; then
        return 0
    fi

    fail "vendored stellar-globe snapshot is missing: ${manifest}"
}

ensure_phalanx() {
    if git -C "$PHALANX_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        run_step validate_remote_url "$PHALANX_DIR" "$PHALANX_URL" "phalanx"
        if ! "$MISSING_ONLY"; then
            log "fetching ${PHALANX_DIR}"
            run_step git -C "$PHALANX_DIR" fetch --prune origin
        fi
        return 0
    fi

    log "cloning ${PHALANX_URL} into ${PHALANX_DIR}"
    run_step git clone "$PHALANX_URL" "$PHALANX_DIR"
    if git -C "$PHALANX_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        run_step validate_remote_url "$PHALANX_DIR" "$PHALANX_URL" "phalanx"
    fi
}

install_hooks() {
    local hooks_dir="${REPO_ROOT}/.githooks"

    if [[ ! -d "$hooks_dir" ]]; then
        fail "hooks directory not found: ${hooks_dir}"
    fi

    log "installing worktree hook path"
    git -C "$REPO_ROOT" config extensions.worktreeConfig true
    git -C "$REPO_ROOT" config --worktree core.bare false
    git -C "$REPO_ROOT" config --worktree core.hooksPath "$hooks_dir"
}

usage() {
    cat <<'EOF'
Usage: ./dev/setup-agent-worktree.sh [options]

Synchronize external repositories used by this worktree.

Options:
  --best-effort   Continue with warnings when a step fails.
  --missing-only  Only materialize missing external repos; skip fetch/update.
  --no-hooks      Do not install the worktree hook path.
  -h, --help      Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --best-effort)
            BEST_EFFORT=true
            shift
            ;;
        --missing-only)
            MISSING_ONLY=true
            shift
            ;;
        --no-hooks)
            INSTALL_HOOKS=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "unknown option: $1"
            ;;
    esac
done

ensure_vendored_stellar_globe
ensure_phalanx

if "$INSTALL_HOOKS"; then
    install_hooks
fi

log "done"
