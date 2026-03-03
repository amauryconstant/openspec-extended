#!/bin/bash
# OpenSpec-extended Installer
# Usage: curl -sSL https://raw.githubusercontent.com/<org>/OpenSpec-extended/main/install.sh | bash
#
# Options (via environment variables):
#   VERSION=v0.9.0    - Install specific version (default: latest)
#   PREFIX=/usr/local - Install prefix (default: ~/.local)
#   REPO=org/repo     - GitHub repository (default: Fission-AI/OpenSpec-extended)
#
# Options (via arguments):
#   --uninstall       - Remove installation
#   --help            - Show help

set -euo pipefail

readonly SCRIPT_NAME="openspecx"
readonly SCRIPT_VERSION="0.1.0"

# Configurable via environment
PREFIX="${PREFIX:-$HOME/.local}"
VERSION="${VERSION:-latest}"
REPO="${REPO:-Fission-AI/OpenSpec-extended}"

# Derived paths
INSTALL_DIR=""
BIN_DIR=""

# Colors
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_RED='\033[0;31m'
readonly COLOR_YELLOW='\033[0;33m'
readonly COLOR_CYAN='\033[0;36m'
readonly COLOR_RESET='\033[0m'

log_info() {
    echo -e "${COLOR_CYAN}→${COLOR_RESET} $*"
}

log_success() {
    echo -e "${COLOR_GREEN}✓${COLOR_RESET} $*"
}

log_warn() {
    echo -e "${COLOR_YELLOW}!${COLOR_RESET} $*" >&2
}

log_error() {
    echo -e "${COLOR_RED}✗${COLOR_RESET} $*" >&2
}

show_version() {
    echo "OpenSpec-extended installer v$SCRIPT_VERSION"
}

show_help() {
    cat << 'EOF'
OpenSpec-extended Installer

Usage:
  curl -sSL https://raw.githubusercontent.com/<org>/OpenSpec-extended/main/install.sh | bash
  ./install.sh [options]

Environment Variables:
  VERSION=v0.9.0    Install specific version (default: latest)
  PREFIX=/usr/local Install prefix (default: ~/.local)
  REPO=org/repo     GitHub repository (default: Fission-AI/OpenSpec-extended)

Options:
  --version         Show version
  --uninstall       Remove installation
  --help            Show this help message

Examples:
  # Install latest to ~/.local
  curl -sSL https://.../install.sh | bash

  # Install specific version
  VERSION=v0.9.0 curl -sSL https://.../install.sh | bash

  # System-wide install
  PREFIX=/usr/local curl -sSL https://.../install.sh | bash

  # Uninstall
  ./install.sh --uninstall
EOF
}

check_dependencies() {
    local missing=()
    
    if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
        missing+=("curl or wget")
    fi
    
    if ! command -v tar &>/dev/null; then
        missing+=("tar")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing[*]}"
        log_error "Please install them and try again."
        exit 1
    fi
}

get_latest_version() {
    local api_url="https://api.github.com/repos/$REPO/releases/latest"
    local version
    
    if command -v curl &>/dev/null; then
        version=$(curl -sSL "$api_url" 2>/dev/null | grep -m1 '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')
    else
        version=$(wget -qO- "$api_url" 2>/dev/null | grep -m1 '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')
    fi
    
    if [[ -z "$version" ]]; then
        log_warn "Could not determine latest version, using 'main' branch"
        echo "main"
    else
        echo "$version"
    fi
}

download_tarball() {
    local version="$1"
    local output_file="$2"
    local tarball_url
    
    if [[ "$version" == "main" ]]; then
        tarball_url="https://github.com/$REPO/archive/refs/heads/main.tar.gz"
    else
        tarball_url="https://github.com/$REPO/archive/refs/tags/v$version.tar.gz"
    fi
    
    log_info "Downloading OpenSpec-extended ${version}..."
    
    if command -v curl &>/dev/null; then
        if ! curl -sSL --fail "$tarball_url" -o "$output_file" 2>/dev/null; then
            log_error "Failed to download from $tarball_url"
            return 1
        fi
    else
        if ! wget -q "$tarball_url" -O "$output_file" 2>/dev/null; then
            log_error "Failed to download from $tarball_url"
            return 1
        fi
    fi
    
    return 0
}

install() {
    local version="$VERSION"
    
    # Resolve 'latest' to actual version
    if [[ "$version" == "latest" ]]; then
        version=$(get_latest_version)
    fi
    
    log_info "Installing OpenSpec-extended ${version} to $PREFIX"
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # Download tarball
    local temp_dir
    temp_dir=$(mktemp -d)
    local tarball="$temp_dir/openspecx.tar.gz"
    
    if ! download_tarball "$version" "$tarball"; then
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Extract
    log_info "Extracting..."
    tar -xzf "$tarball" -C "$temp_dir"
    
    # Find extracted directory (GitHub tarballs include a prefix)
    local extracted_dir
    extracted_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "OpenSpec-extended*" | head -1)
    
    if [[ -z "$extracted_dir" ]]; then
        log_error "Could not find extracted directory"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Remove old installation
    if [[ -d "$INSTALL_DIR/resources" ]]; then
        log_info "Removing previous installation..."
        rm -rf "$INSTALL_DIR/resources"
        rm -f "$INSTALL_DIR/bin/$SCRIPT_NAME"
    fi
    
    # Copy files
    log_info "Installing files..."
    cp -r "$extracted_dir/resources" "$INSTALL_DIR/"
    
    mkdir -p "$INSTALL_DIR/bin"
    cp "$extracted_dir/bin/$SCRIPT_NAME" "$INSTALL_DIR/bin/"
    chmod +x "$INSTALL_DIR/bin/$SCRIPT_NAME"
    
    # Create symlink in bin directory
    ln -sf "$INSTALL_DIR/bin/$SCRIPT_NAME" "$BIN_DIR/$SCRIPT_NAME"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    # Verify
    if ! "$BIN_DIR/$SCRIPT_NAME" --help &>/dev/null; then
        log_error "Installation verification failed"
        exit 1
    fi
    
    log_success "Installed OpenSpec-extended ${version}"
    echo ""
    
    # PATH check
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        log_warn "$BIN_DIR is not in your PATH"
        echo ""
        echo "  Add this to your shell configuration:"
        echo ""
        echo "    export PATH=\"$BIN_DIR:\$PATH\""
        echo ""
        if [[ -f "$HOME/.bashrc" ]]; then
            echo "  Or run: echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
        elif [[ -f "$HOME/.zshrc" ]]; then
            echo "  Or run: echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
        fi
    else
        log_success "Ready to use: openspecx install opencode"
    fi
}

uninstall() {
    log_info "Uninstalling OpenSpec-extended..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log_success "Removed $INSTALL_DIR"
    else
        log_info "Installation directory not found: $INSTALL_DIR"
    fi
    
    if [[ -L "$BIN_DIR/$SCRIPT_NAME" ]]; then
        rm -f "$BIN_DIR/$SCRIPT_NAME"
        log_success "Removed $BIN_DIR/$SCRIPT_NAME"
    elif [[ -f "$BIN_DIR/$SCRIPT_NAME" ]]; then
        rm -f "$BIN_DIR/$SCRIPT_NAME"
        log_success "Removed $BIN_DIR/$SCRIPT_NAME"
    else
        log_info "Binary not found: $BIN_DIR/$SCRIPT_NAME"
    fi
    
    log_success "Uninstall complete"
}

main() {
    local action="install"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --uninstall)
                action="uninstall"
                shift
                ;;
            --version|-V)
                show_version
                exit 0
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Set derived paths
    INSTALL_DIR="$PREFIX/share/openspecx"
    BIN_DIR="$PREFIX/bin"
    
    check_dependencies
    
    case "$action" in
        install)
            install
            ;;
        uninstall)
            uninstall
            ;;
    esac
}

main "$@"
