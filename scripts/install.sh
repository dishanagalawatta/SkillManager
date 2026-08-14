#!/usr/bin/env bash
# ==============================================================================
# SkillManager Universal Installer / Updater / Uninstaller for Linux
# Repository: https://github.com/dishanagalawatta/SkillManager
#
# Quick Install / Update (Ubuntu/Debian/Linux):
#   curl -fsSL https://raw.githubusercontent.com/dishanagalawatta/SkillManager/main/scripts/install.sh | bash
#
# Quick Uninstall:
#   curl -fsSL https://raw.githubusercontent.com/dishanagalawatta/SkillManager/main/scripts/install.sh | bash -s -- --uninstall
# ==============================================================================

set -eo pipefail

REPO="dishanagalawatta/SkillManager"
APP_NAME="SkillManager"
BIN_NAME="skill-manager"

# Styling & Colors
if [ -t 1 ]; then
    COLOR_RESET="\033[0m"
    COLOR_BOLD="\033[1m"
    COLOR_GREEN="\033[32m"
    COLOR_BLUE="\033[34m"
    COLOR_YELLOW="\033[33m"
    COLOR_RED="\033[31m"
    COLOR_CYAN="\033[36m"
else
    COLOR_RESET=""
    COLOR_BOLD=""
    COLOR_GREEN=""
    COLOR_BLUE=""
    COLOR_YELLOW=""
    COLOR_RED=""
    COLOR_CYAN=""
fi

log_info() {
    echo -e "${COLOR_BLUE}${COLOR_BOLD}[INFO]${COLOR_RESET} $1"
}

log_success() {
    echo -e "${COLOR_GREEN}${COLOR_BOLD}[SUCCESS]${COLOR_RESET} $1"
}

log_warn() {
    echo -e "${COLOR_YELLOW}${COLOR_BOLD}[WARN]${COLOR_RESET} $1"
}

log_error() {
    echo -e "${COLOR_RED}${COLOR_BOLD}[ERROR]${COLOR_RESET} $1" >&2
}

banner() {
    echo -e "${COLOR_CYAN}${COLOR_BOLD}"
    echo "  ___ _    _ _ _ __  __                                 "
    echo " / __| |__(_) | |  \/  |__ _ _ _  __ _ __ _ ___ _ _     "
    echo " \__ \ / / | | | | |\/| / _\` | ' \/ _\` / _\` / -_) '_| "
    echo " |___/_\_\_|_|_|_|_|  |_\__,_|_||_\__,_\__, \___|_|     "
    echo "                                       |___/            "
    echo -e "${COLOR_RESET}"
    echo -e "${COLOR_BOLD}SkillManager Linux Setup & Package Manager${COLOR_RESET}"
    echo "--------------------------------------------------------"
}

show_help() {
    banner
    echo -e "Usage: ${COLOR_BOLD}$0 [OPTIONS]${COLOR_RESET}"
    echo ""
    echo "Options:"
    echo "  -h, --help            Show this help message and exit"
    echo "  -u, --update          Check for updates and install if a new version is available"
    echo "      --uninstall       Uninstall SkillManager from the system"
    echo "      --purge           Remove all configuration, cache, and user data during uninstall"
    echo "      --deb             Force installation via Debian package (.deb)"
    echo "      --appimage        Force installation via portable AppImage"
    echo "  -v, --version <VER>   Install a specific version (e.g. 1.9.0 or v1.9.0)"
    echo "      --dry-run         Print the actions without executing modifications"
    echo "  -y, --yes             Run non-interactively, accepting all prompts"
    echo ""
    echo "Examples:"
    echo "  # Install / Upgrade to latest version (auto-detects Debian vs AppImage):"
    echo "  curl -fsSL https://raw.githubusercontent.com/$REPO/main/scripts/install.sh | bash"
    echo ""
    echo "  # Update to latest version:"
    echo "  curl -fsSL https://raw.githubusercontent.com/$REPO/main/scripts/install.sh | bash -s -- --update"
    echo ""
    echo "  # Uninstall SkillManager:"
    echo "  curl -fsSL https://raw.githubusercontent.com/$REPO/main/scripts/install.sh | bash -s -- --uninstall"
    echo ""
    echo "  # Complete removal including settings and cache:"
    echo "  curl -fsSL https://raw.githubusercontent.com/$REPO/main/scripts/install.sh | bash -s -- --uninstall --purge"
    echo ""
}

# Defaults
MODE="install"
PURGE=false
FORCE_DEB=false
FORCE_APPIMAGE=false
SPECIFIC_VERSION=""
DRY_RUN=false
ASSUME_YES=false

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -u|--update)
                MODE="update"
                shift
                ;;
            --uninstall)
                MODE="uninstall"
                shift
                ;;
            --purge)
                PURGE=true
                shift
                ;;
            --deb)
                FORCE_DEB=true
                shift
                ;;
            --appimage)
                FORCE_APPIMAGE=true
                shift
                ;;
            -v|--version)
                SPECIFIC_VERSION="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -y|--yes)
                ASSUME_YES=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Dependency checks
check_dependencies() {
    local missing=()
    if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
        missing+=("curl or wget")
    fi
    if ! command -v grep &>/dev/null; then
        missing+=("grep")
    fi
    if ! command -v sed &>/dev/null; then
        missing+=("sed")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required utilities: ${missing[*]}"
        log_error "Please install them using your package manager (e.g. sudo apt install curl grep sed)"
        exit 1
    fi
}

download_file() {
    local url="$1"
    local dest="$2"

    if command -v curl &>/dev/null; then
        curl -fSL "$url" -o "$dest"
    elif command -v wget &>/dev/null; then
        wget -q "$url" -O "$dest"
    else
        log_error "Neither curl nor wget is available for downloading."
        exit 1
    fi
}

get_http_text() {
    local url="$1"
    if command -v curl &>/dev/null; then
        curl -fsSL "$url"
    elif command -v wget &>/dev/null; then
        wget -qO- "$url"
    fi
}

# Resolve latest version from GitHub
resolve_latest_version() {
    local tag=""
    
    # Method 1: GitHub API
    local api_url="https://api.github.com/repos/${REPO}/releases/latest"
    local json
    json=$(get_http_text "$api_url" 2>/dev/null || true)
    if [ -n "$json" ]; then
        tag=$(echo "$json" | grep -m1 '"tag_name":' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
    fi

    # Method 2: Fallback to redirect header inspection
    if [ -z "$tag" ]; then
        if command -v curl &>/dev/null; then
            local redirect_url
            redirect_url=$(curl -s -o /dev/null -w "%{url_effective}" -L "https://github.com/${REPO}/releases/latest" || true)
            tag="${redirect_url##*/}"
        fi
    fi

    if [ -z "$tag" ] || [ "$tag" = "latest" ]; then
        log_error "Failed to detect latest release from GitHub."
        log_error "You can specify a version explicitly using --version <version>"
        exit 1
    fi

    echo "$tag"
}

# Determine installed version
get_installed_version() {
    # Check Debian package
    if command -v dpkg &>/dev/null && dpkg -s skill-manager &>/dev/null; then
        dpkg -s skill-manager 2>/dev/null | grep -i '^Version:' | awk '{print $2}'
        return 0
    fi

    # Check AppImage / standalone binary in PATH
    if command -v skill-manager &>/dev/null; then
        local ver
        ver=$(skill-manager --version 2>/dev/null || true)
        if [ -n "$ver" ]; then
            echo "$ver" | sed -E 's/[^0-9.]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/'
            return 0
        fi
    fi

    echo ""
}

# Sudo wrapper
run_as_root() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    elif command -v sudo &>/dev/null; then
        sudo "$@"
    else
        log_error "This action requires root privileges. Please run as root or install sudo."
        exit 1
    fi
}

# Detect package type
determine_package_type() {
    if [ "$FORCE_APPIMAGE" = true ]; then
        echo "appimage"
        return 0
    fi
    if [ "$FORCE_DEB" = true ]; then
        echo "deb"
        return 0
    fi

    # Auto-detection: Ubuntu / Debian distros with apt and dpkg
    if [ -f /etc/debian_version ] && command -v apt &>/dev/null && command -v dpkg &>/dev/null; then
        echo "deb"
    else
        echo "appimage"
    fi
}

# ------------------------------------------------------------------------------
# Install Function
# ------------------------------------------------------------------------------
do_install() {
    local target_tag="$1"
    local raw_version="${target_tag#v}"
    local pkg_type="$2"

    log_info "Target Version: ${COLOR_BOLD}v${raw_version}${COLOR_RESET}"
    log_info "Packaging Type: ${COLOR_BOLD}${pkg_type}${COLOR_RESET}"

    # Check architecture
    local arch
    arch=$(uname -m)
    if [ "$arch" != "x86_64" ]; then
        log_error "Unsupported architecture: $arch. SkillManager binaries currently support x86_64 (amd64) only."
        exit 1
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warn "[DRY RUN] Would download and install SkillManager v${raw_version} (${pkg_type})."
        return 0
    fi

    local temp_dir
    temp_dir=$(mktemp -d -t skill-manager-install-XXXXXX)
    trap 'rm -rf "$temp_dir"' EXIT

    if [ "$pkg_type" = "deb" ]; then
        local deb_name="skill-manager_${raw_version}_amd64.deb"
        local deb_url="https://github.com/${REPO}/releases/download/${target_tag}/${deb_name}"
        local deb_path="${temp_dir}/${deb_name}"

        log_info "Downloading ${deb_name}..."
        if ! download_file "$deb_url" "$deb_path"; then
            log_error "Failed to download Debian package from $deb_url."
            log_error "Please verify that release ${target_tag} contains ${deb_name}."
            exit 1
        fi

        log_info "Installing Debian package with dependencies via apt..."
        run_as_root apt-get update -qq || true
        if ! run_as_root apt install -y "$deb_path"; then
            log_warn "apt install failed; attempting dpkg -i with apt-get -f install fallback..."
            run_as_root dpkg -i "$deb_path"
            run_as_root apt-get install -f -y
        fi

        # Clean up any stale user-level desktop overrides or sync them
        local icons_base="$HOME/.local/share/icons/hicolor"
        mkdir -p "$HOME/.local/share/applications" "${icons_base}/scalable/apps" "${icons_base}/256x256/apps" "${icons_base}/128x128/apps" "${icons_base}/64x64/apps"
        if [ -f "/usr/share/applications/skill-manager.desktop" ]; then
            cp -f "/usr/share/applications/skill-manager.desktop" "$HOME/.local/share/applications/skill-manager.desktop" 2>/dev/null || true
            chmod 0755 "$HOME/.local/share/applications/skill-manager.desktop" 2>/dev/null || true
        fi
        # Remove any legacy aliases to maintain single official launcher
        rm -f "$HOME/.local/share/applications/SkillManager.desktop" "$HOME/.local/share/applications/org.dishanagalawatta.SkillManager.desktop" 2>/dev/null || true

        for sz in scalable 256x256 128x128 64x64; do
            if [ -d "/usr/share/icons/hicolor/${sz}/apps" ]; then
                cp -f /usr/share/icons/hicolor/${sz}/apps/skill-manager.* "${icons_base}/${sz}/apps/" 2>/dev/null || true
            fi
        done

    elif [ "$pkg_type" = "appimage" ]; then
        local appimage_name="SkillManager-${raw_version}-x86_64.AppImage"
        local appimage_url="https://github.com/${REPO}/releases/download/${target_tag}/${appimage_name}"
        local install_dir="$HOME/.local/bin"
        local app_dest="${install_dir}/skill-manager"

        mkdir -p "$install_dir"
        log_info "Downloading ${appimage_name} to ${app_dest}..."
        if ! download_file "$appimage_url" "$app_dest"; then
            log_error "Failed to download AppImage from $appimage_url."
            exit 1
        fi
        chmod +x "$app_dest"

        # Desktop entry setup
        local apps_dir="$HOME/.local/share/applications"
        local icons_base="$HOME/.local/share/icons/hicolor"
        mkdir -p "$apps_dir" "${icons_base}/scalable/apps" "${icons_base}/256x256/apps" "${icons_base}/128x128/apps" "${icons_base}/64x64/apps"

        log_info "Configuring desktop launcher and multi-resolution application icons..."
        download_file "https://raw.githubusercontent.com/${REPO}/main/assets/brand/logo.svg" "${icons_base}/scalable/apps/skill-manager.svg" || true
        download_file "https://raw.githubusercontent.com/${REPO}/main/assets/brand/logo.png" "${icons_base}/256x256/apps/skill-manager.png" || true
        download_file "https://raw.githubusercontent.com/${REPO}/main/assets/brand/logo-128.png" "${icons_base}/128x128/apps/skill-manager.png" || true
        download_file "https://raw.githubusercontent.com/${REPO}/main/assets/brand/logo-64.png" "${icons_base}/64x64/apps/skill-manager.png" || true

        # Write single canonical desktop file
        cat > "${apps_dir}/skill-manager.desktop" <<EOF
[Desktop Entry]
Name=SkillManager
Comment=Professional agent skill orchestration desktop system
Exec=${app_dest} %U
Icon=skill-manager
Terminal=false
Type=Application
Categories=Utility;Development;
StartupWMClass=SkillManager
EOF
        chmod 0755 "${apps_dir}/skill-manager.desktop"

        # Remove any legacy aliases to maintain single official launcher
        rm -f "${apps_dir}/SkillManager.desktop" "${apps_dir}/org.dishanagalawatta.SkillManager.desktop" 2>/dev/null || true

        # Check if ~/.local/bin is on PATH
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            log_warn "$HOME/.local/bin is not in your current PATH."
            log_warn "Add it to your ~/.bashrc or ~/.zshrc:"
            echo -e "    ${COLOR_BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${COLOR_RESET}"
        fi
    fi

    # Update desktop database & caches for both system and user directories
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
        if [ "$pkg_type" = "deb" ]; then
            run_as_root update-desktop-database /usr/share/applications 2>/dev/null || true
        fi
    fi
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
        if [ "$pkg_type" = "deb" ]; then
            run_as_root gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
        fi
    fi

    echo ""
    log_success "SkillManager v${raw_version} has been successfully installed!"
    echo -e "You can launch it from your application menu or run: ${COLOR_BOLD}skill-manager${COLOR_RESET}"
    echo ""
}

# ------------------------------------------------------------------------------
# Update Function
# ------------------------------------------------------------------------------
do_update() {
    local target_tag="$1"
    local target_ver="${target_tag#v}"
    local installed_ver
    installed_ver=$(get_installed_version)

    if [ -z "$installed_ver" ]; then
        log_info "No existing SkillManager installation detected. Performing clean install..."
        local pkg_type
        pkg_type=$(determine_package_type)
        do_install "$target_tag" "$pkg_type"
        return 0
    fi

    log_info "Installed version: ${COLOR_BOLD}v${installed_ver}${COLOR_RESET}"
    log_info "Latest version:    ${COLOR_BOLD}v${target_ver}${COLOR_RESET}"

    if [ "$installed_ver" = "$target_ver" ]; then
        log_success "SkillManager is already up to date (v${installed_ver})."
        return 0
    fi

    log_info "Upgrade available: v${installed_ver} -> v${target_ver}"
    local pkg_type
    pkg_type=$(determine_package_type)
    do_install "$target_tag" "$pkg_type"
}

# ------------------------------------------------------------------------------
# Uninstall Function
# ------------------------------------------------------------------------------
do_uninstall() {
    log_info "Preparing to uninstall SkillManager..."

    if [ "$DRY_RUN" = true ]; then
        log_warn "[DRY RUN] Would uninstall SkillManager and remove desktop integration."
        if [ "$PURGE" = true ]; then
            log_warn "[DRY RUN] Would purge user configuration and data (~/.config/SkillManager, ~/.local/share/SkillManager, ~/.cache/SkillManager)."
        fi
        return 0
    fi

    local removed=false

    # 1. Debian Package Uninstall
    if command -v dpkg &>/dev/null && dpkg -s skill-manager &>/dev/null; then
        log_info "Removing Debian package (skill-manager)..."
        run_as_root apt remove -y skill-manager || run_as_root dpkg -r skill-manager
        removed=true
    fi

    # 2. AppImage & User-level Installation Clean up
    local appimage_bin="$HOME/.local/bin/skill-manager"
    local apps_dir="$HOME/.local/share/applications"

    if [ -f "$appimage_bin" ]; then
        log_info "Removing AppImage binary from ${appimage_bin}..."
        rm -f "$appimage_bin"
        removed=true
    fi

    # Remove canonical launcher and any legacy aliases (leaves com.skillmanager.opencode intact)
    for desk in "skill-manager.desktop" "SkillManager.desktop" "org.dishanagalawatta.SkillManager.desktop"; do
        if [ -f "${apps_dir}/${desk}" ]; then
            log_info "Removing desktop entry: ${apps_dir}/${desk}..."
            rm -f "${apps_dir}/${desk}"
            removed=true
        fi
    done

    # Remove user-level application icons
    local icons_base="$HOME/.local/share/icons/hicolor"
    for sz in scalable 256x256 128x128 64x64 48x48 32x32; do
        rm -f "${icons_base}/${sz}/apps/skill-manager."* "${icons_base}/${sz}/apps/SkillManager."* "${icons_base}/${sz}/apps/org.dishanagalawatta.SkillManager."* 2>/dev/null || true
    done

    # System-level AppImage cleanup if present
    if [ -f "/usr/local/bin/skill-manager" ]; then
        log_info "Removing /usr/local/bin/skill-manager..."
        run_as_root rm -f "/usr/local/bin/skill-manager"
        removed=true
    fi

    # 3. Purge User Data (if requested)
    if [ "$PURGE" = true ]; then
        log_warn "Purging user settings, databases, and cache..."
        rm -rf "$HOME/.config/SkillManager"
        rm -rf "$HOME/.local/share/SkillManager"
        rm -rf "$HOME/.cache/SkillManager"
        rm -rf "$HOME/.skill-manager"
        log_success "User data directories purged."
    fi

    # Update desktop database and icon theme caches
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi

    if [ "$removed" = true ]; then
        log_success "SkillManager has been uninstalled successfully."
    else
        log_warn "No active SkillManager installation was found on this system."
    fi
}

# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------
main() {
    parse_args "$@"
    banner
    check_dependencies

    local target_tag
    if [ -n "$SPECIFIC_VERSION" ]; then
        if [[ "$SPECIFIC_VERSION" == v* ]]; then
            target_tag="$SPECIFIC_VERSION"
        else
            target_tag="v${SPECIFIC_VERSION}"
        fi
    else
        target_tag=$(resolve_latest_version)
    fi

    local pkg_type
    pkg_type=$(determine_package_type)

    case "$MODE" in
        install)
            do_install "$target_tag" "$pkg_type"
            ;;
        update)
            do_update "$target_tag"
            ;;
        uninstall)
            do_uninstall
            ;;
    esac
}

main "$@"
