#!/usr/bin/env bash
# OpenSpec-extended Installer
# Usage: curl -sSL https://raw.githubusercontent.com/<org>/OpenSpec-extended/main/install.sh | bash
#
# Options (via environment variables):
#   VERSION=v0.9.2    - Install specific version (default: latest)
#   PREFIX=/usr/local - Install prefix (default: ~/.local)
#   REPO=org/repo     - GitHub repository (default: amauryconstant/openspec-extended)
#
# Options (via arguments):
#   --uninstall       - Remove installation
#   --help            - Show help

set -euo pipefail

readonly SCRIPT_NAME="openspec-extended"
readonly SCRIPT_VERSION="0.2.0"

# Configurable via environment
PREFIX="${PREFIX:-$HOME/.local}"
VERSION="${VERSION:-latest}"
REPO="${REPO:-amauryconstant/openspec-extended}"

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

# Temporary directory tracking for cleanup
temp_dir=""

cleanup_temp() {
    if [[ -n "${temp_dir:-}" ]] && [[ -d "$temp_dir" ]]; then
        rm -rf "$temp_dir"
    fi
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
  VERSION=v0.9.2    Install specific version (default: latest)
  PREFIX=/usr/local Install prefix (default: ~/.local)
  REPO=org/repo     GitHub repository (default: amauryconstant/openspec-extended)

Options:
  --version         Show version
  --uninstall       Remove installation
  --help            Show this help message

Examples:
  # Install latest to ~/.local
  curl -sSL https://.../install.sh | bash

  # Install specific version
  VERSION=v0.9.2 curl -sSL https://.../install.sh | bash

  # System-wide install
  PREFIX=/usr/local curl -sSL https://.../install.sh | bash

  # Uninstall
  ./install.sh --uninstall
EOF
}

# Validate GitHub repo format (owner/repo)
validate_repo() {
    local repo="$1"
    
    # GitHub format: alphanumeric, underscores, hyphens, single slash
    if [[ ! "$repo" =~ ^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$ ]]; then
        log_error "Invalid REPO format: $repo"
        log_error "Expected format: owner/repo (e.g., amauryconstant/openspec-extended)"
        return 1
    fi
    
    return 0
}

# Validate Epoch SemVer format
# Supports: X.Y.Z, vX.Y.Z, X.Y.Z-PRERELEASE, X.Y.Z+BUILD, X.Y.Z-PRERELEASE+BUILD
validate_version() {
    local version="$1"
    
    # Allow special keywords
    if [[ "$version" == "latest" ]] || [[ "$version" == "main" ]]; then
        return 0
    fi
    
    # Strip optional 'v' prefix
    local version_without_v="${version#v}"
    
    # Epoch SemVer regex
    # Core: X.Y.Z (where X, Y, Z are non-negative integers)
    # Optional prerelease: -alphanumeric.dots.hyphens
    # Optional build: +alphanumeric.dots.hyphens
    if [[ ! "$version_without_v" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z\.-]+)?(\+[0-9A-Za-z\.-]+)?$ ]]; then
        log_error "Invalid VERSION format: $version"
        log_error "Expected: latest, main, or valid SemVer (e.g., 1.2.3, v1.2.3-alpha.1, 1.2.3+build)"
        return 1
    fi
    
    return 0
}

# Validate PREFIX to prevent path traversal
validate_prefix() {
    local prefix="$1"
    
    # Prevent path traversal attacks
    if [[ "$prefix" == *../* ]] || [[ "$prefix" == */.. ]] || [[ "$prefix" == *../..* ]]; then
        log_error "Invalid PREFIX: contains parent directory references"
        log_error "Prefix: $prefix"
        return 1
    fi
    
    # Prevent absolute paths to sensitive directories (optional warning)
    if [[ "$prefix" == "/etc" ]] || [[ "$prefix" == "/bin" ]] || [[ "$prefix" == "/usr/bin" ]]; then
        log_error "Invalid PREFIX: installation to system directories not recommended"
        log_error "Prefix: $prefix"
        log_error "Use your home directory: PREFIX=\$HOME/.local ./install.sh"
        return 1
    fi
    
    return 0
}

# Verify download integrity using SHA256 checksum
verify_checksum() {
    local tarball="$1"
    local version="$2"
    
    # Skip verification for 'main' branch (no release checksums)
    if [[ "$version" == "main" ]]; then
        log_warn "Checksum verification skipped for 'main' branch"
        return 0
    fi
    
    local checksums_url="https://github.com/$REPO/releases/download/v$version/SHA256SUMS"
    local checksums_file
    checksums_file=$(mktemp)
    
    # Download checksums file
    if command -v curl &>/dev/null; then
        if ! curl -sSL "$checksums_url" -o "$checksums_file" 2>/dev/null; then
            log_warn "Checksum file not found for v$version, skipping verification"
            rm -f "$checksums_file"
            return 0
        fi
    else
        if ! wget -q "$checksums_url" -O "$checksums_file" 2>/dev/null; then
            log_warn "Checksum file not found for v$version, skipping verification"
            rm -f "$checksums_file"
            return 0
        fi
    fi
    
    # Find checksum for our tarball
    local tarball_name
    tarball_name=$(basename "$tarball")
    local expected_checksum
    expected_checksum=$(grep "$tarball_name" "$checksums_file" | awk '{print $1}')
    
    if [[ -z "$expected_checksum" ]]; then
        log_warn "Checksum not found for $tarball_name, skipping verification"
        rm -f "$checksums_file"
        return 0
    fi
    
    # Calculate actual checksum
    if ! command -v sha256sum &>/dev/null; then
        log_warn "sha256sum command not found, skipping verification"
        rm -f "$checksums_file"
        return 0
    fi
    
    local actual_checksum
    actual_checksum=$(sha256sum "$tarball" | awk '{print $1}')
    
    # Verify checksum matches
    if [[ "$actual_checksum" != "$expected_checksum" ]]; then
        log_error "Checksum verification failed!"
        log_error "  Expected: $expected_checksum"
        log_error "  Actual:   $actual_checksum"
        log_error ""
        log_error "The downloaded file may be corrupted or tampered with."
        log_error "Please try again or contact support."
        rm -f "$checksums_file"
        return 1
    fi
    
    log_success "Checksum verified"
    rm -f "$checksums_file"
    return 0
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
        echo ""
        echo "Install them with:"
        # Detect OS and suggest commands
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  brew install ${missing[*]}"
        elif command -v apt-get &>/dev/null; then
            echo "  sudo apt-get install -y ${missing[*]}"
        elif command -v yum &>/dev/null; then
            echo "  sudo yum install -y ${missing[*]}"
        elif command -v pacman &>/dev/null; then
            echo "  sudo pacman -S ${missing[*]}"
        else
            echo "  See your package manager documentation"
        fi
        echo ""
        exit 1
    fi
}

suggest_path_setup() {
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        log_warn "$BIN_DIR is not in your PATH"
        echo ""
        echo "  Add this to your shell configuration:"
        echo ""
        echo "    export PATH=\"$BIN_DIR:\$PATH\""
        echo ""
        
        # Detect shell and provide specific instructions
        if [[ -n "$SHELL" ]]; then
            case "$SHELL" in
                */bash)
                    if [[ -f "$HOME/.bashrc" ]]; then
                        echo "  Or run:"
                        echo "    echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
                    fi
                    ;;
                */zsh)
                    if [[ -f "$HOME/.zshrc" ]]; then
                        echo "  Or run:"
                        echo "    echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
                    fi
                    ;;
                */fish)
                    if [[ -f "$HOME/.config/fish/config.fish" ]]; then
                        echo "  Or run:"
                        echo "    echo 'set -gx PATH \"$BIN_DIR\" \$PATH' >> ~/.config/fish/config.fish"
                        echo "    source ~/.config/fish/config.fish"
                    fi
                    ;;
                *)
                    echo "  Detected shell: $SHELL"
                    echo "  Add to export command to your shell's configuration file"
                    ;;
            esac
        fi
    fi
}

get_latest_version() {
    local api_url="https://api.github.com/repos/$REPO/releases/latest"
    local version
    
    if command -v curl &>/dev/null; then
        # Extract version from GitHub API JSON: "tag_name": "v1.2.3" → "1.2.3"
        # Pattern: .* matches prefix, "v\([^"]*\)" captures version without 'v', .* matches suffix
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
    
    # Strip 'v' prefix if present (e.g., "v1.2.3" → "1.2.3")
    version="${version#v}"
    
    log_info "Installing OpenSpec-extended ${version} to $PREFIX"
    
    # Create directories
    log_info "Creating installation directories: $INSTALL_DIR, $BIN_DIR"
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # Download tarball
    local temp_dir
    temp_dir=$(mktemp -d)
    chmod 700 "$temp_dir"  # Owner-only access
    trap cleanup_temp EXIT INT TERM
    local tarball="$temp_dir/openspec-extended.tar.gz"
    
    if ! download_tarball "$version" "$tarball"; then
        cleanup_temp
        exit 1
    fi
    
    # Verify download integrity
    if ! verify_checksum "$tarball" "$version"; then
        cleanup_temp
        exit 1
    fi
    
    # Extract
    log_info "Extracting..."
    tar -xzf "$tarball" -C "$temp_dir" --no-same-owner
    
    # Find extracted directory (GitHub tarballs include a prefix)
    local extracted_dir
    extracted_dir=$(find "$temp_dir" -maxdepth 1 -type d ! -path "$temp_dir" | head -1)
    
    if [[ -z "$extracted_dir" ]]; then
        log_error "Could not find extracted directory"
        cleanup_temp
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
    # Warn if overwriting regular file
    if [[ -e "$BIN_DIR/$SCRIPT_NAME" ]] && [[ ! -L "$BIN_DIR/$SCRIPT_NAME" ]]; then
        log_warn "Overwriting existing file: $BIN_DIR/$SCRIPT_NAME"
    fi
    ln -sf "$INSTALL_DIR/bin/$SCRIPT_NAME" "$BIN_DIR/$SCRIPT_NAME"
    
    # Cleanup
    cleanup_temp
    
    # Verify
    if [[ ! -x "$BIN_DIR/$SCRIPT_NAME" ]]; then
        log_error "Installation verification failed"
        log_error "  Binary not found or not executable: $BIN_DIR/$SCRIPT_NAME"
        log_error "  Check permissions and try running with sudo if needed"
        exit 1
    fi
    
    log_success "Installed OpenSpec-extended ${version}"
    echo ""
    
    # Verify and suggest PATH setup
    suggest_path_setup
}

uninstall() {
    log_info "Uninstalling OpenSpec-extended..."
    
    # Check if anything to remove
    local has_installation=false
    [[ -d "$INSTALL_DIR" ]] && has_installation=true
    [[ -L "$BIN_DIR/$SCRIPT_NAME" ]] && has_installation=true
    [[ -f "$BIN_DIR/$SCRIPT_NAME" ]] && has_installation=true
    
    if [[ "$has_installation" == false ]]; then
        log_info "No installation found"
        exit 0
    fi
    
    # Show what will be removed
    log_warn "The following will be removed:"
    [[ -d "$INSTALL_DIR" ]] && echo "  - $INSTALL_DIR"
    [[ -L "$BIN_DIR/$SCRIPT_NAME" ]] && echo "  - $BIN_DIR/$SCRIPT_NAME (symlink)"
    [[ -f "$BIN_DIR/$SCRIPT_NAME" ]] && echo "  - $BIN_DIR/$SCRIPT_NAME (file)"
    echo ""
    
    # Always require confirmation
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi
    
    # Remove installation directory
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log_success "Removed $INSTALL_DIR"
    fi
    
    # Remove binary (symlink or file) - single check covers both cases
    if [[ -L "$BIN_DIR/$SCRIPT_NAME" ]] || [[ -f "$BIN_DIR/$SCRIPT_NAME" ]]; then
        rm -f "$BIN_DIR/$SCRIPT_NAME"
        log_success "Removed $BIN_DIR/$SCRIPT_NAME"
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
                echo "Run './install.sh --help' for usage information."
                show_help
                exit 1
                ;;
        esac
    done
    
    # Set derived paths
    INSTALL_DIR="$PREFIX/share/openspec-extended"
    BIN_DIR="$PREFIX/bin"
    
    check_dependencies
    
    # Validate inputs
    validate_repo "$REPO" || exit 1
    validate_version "$VERSION" || exit 1
    validate_prefix "$PREFIX" || exit 1
    
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
