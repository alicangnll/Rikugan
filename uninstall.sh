#!/usr/bin/env bash
# Rikugan uninstaller for Linux and macOS
# Usage: ./uninstall.sh [--all] [--ida] [--binja] [--keep-deps] [--force]
#   --all        Uninstall from all hosts (default)
#   --ida        Uninstall from IDA Pro only
#   --binja      Uninstall from Binary Ninja only
#   --keep-deps  Keep Python dependencies installed
#   --force      Skip confirmation prompts

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { printf "${CYAN}[*]${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}[+]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err()   { printf "${RED}[-]${NC} %s\n" "$*" >&2; }

banner() {
    printf "\n${BOLD}"
    cat << 'EOF'
    ╔══════════════════════════════════════════╗
    ║            六眼  Rikugan                 ║
    ║           Uninstall Script               ║
    ╚══════════════════════════════════════════╝
EOF
    printf "${NC}\n"
}

# Parse arguments
UNINSTALL_IDA=false
UNINSTALL_BINJA=false
KEEP_DEPS=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --all)       UNINSTALL_IDA=true; UNINSTALL_BINJA=true ;;
        --ida)       UNINSTALL_IDA=true ;;
        --binja|--bn) UNINSTALL_BINJA=true ;;
        --keep-deps) KEEP_DEPS=true ;;
        --force)     FORCE=true ;;
        --help|-h)
            echo "Usage: ./uninstall.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --all        Uninstall from all hosts (default)"
            echo "  --ida        Uninstall from IDA Pro only"
            echo "  --binja      Uninstall from Binary Ninja only"
            echo "  --keep-deps  Keep Python dependencies installed"
            echo "  --force      Skip confirmation prompts"
            echo ""
            echo "Examples:"
            echo "  ./uninstall.sh              # Uninstall from all hosts"
            echo "  ./uninstall.sh --ida        # Uninstall from IDA Pro only"
            echo "  ./uninstall.sh --binja      # Uninstall from Binary Ninja only"
            echo "  ./uninstall.sh --keep-deps  # Uninstall but keep dependencies"
            echo "  ./uninstall.sh --force      # Uninstall without prompts"
            exit 0
            ;;
    esac
done

# Auto-detect if no target specified
if [[ "$UNINSTALL_IDA" == false ]] && [[ "$UNINSTALL_BINJA" == false ]]; then
    UNINSTALL_IDA=true
    UNINSTALL_BINJA=true
fi

banner

# ─── Helper functions ─────────────────────────────────────────────────────

remove_link() {
    local target="$1"
    if [[ -L "$target" ]]; then
        rm "$target"
        ok "Removed symlink: $target"
    elif [[ -e "$target" ]]; then
        warn "Skipping non-symlink: $target (use --force to remove)"
        if [[ "$FORCE" == true ]]; then
            rm -rf "$target"
            ok "Removed: $target"
        fi
    else
        info "Already removed: $target"
    fi
}

remove_directory() {
    local target="$1"
    if [[ -d "$target" ]]; then
        rm -rf "$target"
        ok "Removed directory: $target"
    else
        info "Already removed: $target"
    fi
}

# ─── IDA Pro uninstallation ───────────────────────────────────────────────

uninstall_ida() {
    info "Uninstalling Rikugan from IDA Pro..."
    echo ""

    local ida_dirs=()
    local found=false

    # Detect IDA user directories
    if [[ "$(uname)" == "Darwin" ]]; then
        [[ -d "$HOME/.idapro" ]] && { ida_dirs+=("$HOME/.idapro"); found=true; }
        [[ -d "$HOME/Library/Application Support/Hex-Rays/IDA Pro" ]] && { ida_dirs+=("$HOME/Library/Application Support/Hex-Rays/IDA Pro"); found=true; }
    else
        [[ -d "$HOME/.idapro" ]] && { ida_dirs+=("$HOME/.idapro"); found=true; }
        [[ -d "$HOME/.ida" ]] && { ida_dirs+=("$HOME/.ida"); found=true; }
    fi

    if [[ "$found" == false ]]; then
        warn "No IDA Pro installation found"
        echo ""
        return 0
    fi

    for ida_dir in "${ida_dirs[@]}"; do
        info "Processing IDA directory: $ida_dir"

        # Remove plugin symlinks
        remove_link "$ida_dir/plugins/rikugan_plugin.py"
        remove_link "$ida_dir/plugins/rikugan"

        # Remove config directory
        remove_directory "$ida_dir/rikugan"

        # Remove old "iris" symlinks if they exist
        remove_link "$ida_dir/plugins/iris_plugin.py"
        remove_link "$ida_dir/plugins/iris"

        echo ""
    done

    ok "IDA Pro uninstallation complete"
    echo ""
}

# ─── Binary Ninja uninstallation ───────────────────────────────────────────

uninstall_binja() {
    info "Uninstalling Rikugan from Binary Ninja..."
    echo ""

    local bn_dirs=()
    local found=false

    # Detect Binary Ninja user directories
    if [[ "$(uname)" == "Darwin" ]]; then
        [[ -d "$HOME/Library/Application Support/Binary Ninja" ]] && { bn_dirs+=("$HOME/Library/Application Support/Binary Ninja"); found=true; }
        [[ -d "$HOME/.binaryninja" ]] && { bn_dirs+=("$HOME/.binaryninja"); found=true; }
    else
        [[ -d "$HOME/.binaryninja" ]] && { bn_dirs+=("$HOME/.binaryninja"); found=true; }
    fi

    if [[ "$found" == false ]]; then
        warn "No Binary Ninja installation found"
        echo ""
        return 0
    fi

    for bn_dir in "${bn_dirs[@]}"; do
        info "Processing Binary Ninja directory: $bn_dir"

        # Remove plugin symlink
        remove_link "$bn_dir/plugins/rikugan"

        # Remove config directory
        remove_directory "$bn_dir/rikugan"

        # Remove old "iris" symlink if it exists
        remove_link "$bn_dir/plugins/iris"

        echo ""
    done

    ok "Binary Ninja uninstallation complete"
    echo ""
}

# ─── Remove repository directory (optional) ───────────────────────────────

uninstall_repo() {
    local repo_dir="$HOME/.rikugan"

    if [[ -d "$repo_dir" ]]; then
        if [[ "$FORCE" == true ]]; then
            remove_directory "$repo_dir"
        else
            warn "Repository directory exists: $repo_dir"
            info "This directory contains the Rikugan source code."
            info "You may want to keep it for future use or manual inspection."
            echo ""
            read -p "Remove repository directory? [y/N] " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                remove_directory "$repo_dir"
            else
                info "Keeping repository directory"
            fi
        fi
    else
        info "Repository directory not found: $repo_dir"
    fi
    echo ""
}

# ─── Remove Python dependencies (optional) ─────────────────────────────────

uninstall_dependencies() {
    if [[ "$KEEP_DEPS" == true ]]; then
        info "Skipping Python dependency removal (--keep-deps specified)"
        echo ""
        return 0
    fi

    info "Python dependencies were installed via pip."
    info "To remove them, run the following command manually:"
    echo ""
    printf "${CYAN}  pip uninstall -y anthropic httpx pydantic${NC}"
    echo ""
    echo ""
    info "Note: This may affect other tools that use these packages."
    echo ""
}

# ─── Confirmation prompt ───────────────────────────────────────────────────

confirm_uninstall() {
    if [[ "$FORCE" == true ]]; then
        return 0
    fi

    local targets=()
    [[ "$UNINSTALL_IDA" == true ]] && targets+=("IDA Pro")
    [[ "$UNINSTALL_BINJA" == true ]] && targets+=("Binary Ninja")

    warn "This will remove Rikugan from: ${targets[*]}"
    warn "Configuration and user data will be permanently deleted."
    echo ""
    read -p "Continue with uninstallation? [y/N] " -n 1 -r
    echo ""
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Uninstallation cancelled"
        exit 0
    fi
}

# ─── Main uninstallation flow ─────────────────────────────────────────────

main() {
    # Show what will be uninstalled
    info "Uninstall targets:"
    [[ "$UNINSTALL_IDA" == true ]] && echo "  - IDA Pro"
    [[ "$UNINSTALL_BINJA" == true ]] && echo "  - Binary Ninja"
    echo ""

    # Confirm before proceeding
    confirm_uninstall

    # Run uninstallations
    if [[ "$UNINSTALL_IDA" == true ]]; then
        uninstall_ida
    fi

    if [[ "$UNINSTALL_BINJA" == true ]]; then
        uninstall_binja
    fi

    # Ask about repository directory
    uninstall_repo

    # Show dependency removal instructions
    uninstall_dependencies

    # Final summary
    printf "${GREEN}${BOLD}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "           Uninstallation Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "${NC}"
    echo ""
    info "Thank you for using Rikugan!"
    info "If you have any feedback, please visit:"
    echo "  https://github.com/alicangnll/Rikugan/issues"
    echo ""
}

main
