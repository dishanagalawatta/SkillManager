# Installing SkillManager

SkillManager provides fast, automated 1-command installation and update workflows for Linux and Windows.

---

## 1. Linux & Ubuntu (Recommended: 1-Command Script)

No repository cloning or Python dependencies required. The universal installer automatically detects your Linux distribution, resolves required Qt/system dependencies via `apt`, downloads the latest release, and configures application icons and `.desktop` launchers.

```mermaid
flowchart TD
    A["curl -fsSL .../install.sh | bash"] --> B{Detect Linux Distro}
    B -->|Ubuntu / Debian| C[Query GitHub API for latest .deb]
    B -->|Other Linux / --appimage| D[Query GitHub API for latest AppImage]
    C --> E[Download .deb to temporary directory]
    E --> F[sudo apt install -y ./skill-manager_*.deb]
    D --> G[Download to ~/.local/bin/skill-manager]
    G --> H[Install desktop entry & icons to ~/.local/share]
    F --> I[Update desktop database & launch app]
    H --> I
```

### Install / Upgrade to Latest Version

```bash
curl -fsSL https://raw.githubusercontent.com/dishanagalawatta/SkillManager/main/scripts/install.sh | bash
```

*(On Ubuntu and Debian systems, this installs the official `.deb` package. On other Linux distributions, it installs the portable AppImage to `~/.local/bin/skill-manager`).*

### Update SkillManager

Check for the latest release and update seamlessly in one command:

```bash
curl -fsSL https://raw.githubusercontent.com/dishanagalawatta/SkillManager/main/scripts/install.sh | bash -s -- --update
```

### Uninstall

Remove the application and desktop entries cleanly:

```bash
curl -fsSL https://raw.githubusercontent.com/dishanagalawatta/SkillManager/main/scripts/install.sh | bash -s -- --uninstall
```

To also delete all user settings, databases, and cache, append `--purge`:

```bash
curl -fsSL https://raw.githubusercontent.com/dishanagalawatta/SkillManager/main/scripts/install.sh | bash -s -- --uninstall --purge
```

### Advanced Script Options

| Option | Description |
|---|---|
| `--update`, `-u` | Check for updates and install if a newer version exists |
| `--uninstall` | Remove SkillManager and desktop shortcuts |
| `--purge` | With `--uninstall`: removes `~/.config/SkillManager` and user data |
| `--deb` | Force installation via Debian package (`.deb`) |
| `--appimage` | Force installation via portable `AppImage` |
| `-v`, `--version <VER>` | Install a specific version (e.g. `2.0.0` or `v2.0.0`) |
| `--dry-run` | Print actions without making filesystem modifications |
| `-y`, `--yes` | Run non-interactively, accepting all prompts |

---

## 2. Windows (Recommended: winget)

```powershell
winget install --id dishanagalawatta.SkillManager -e --source winget
```

This installs SkillManager via Windows Package Manager. The binary is distributed through Microsoft's package index with verified hashes, so **no SmartScreen warnings appear**.

### Update (Windows)

```powershell
winget upgrade --id dishanagalawatta.SkillManager
```

### Uninstall (Windows)

```powershell
winget uninstall --id dishanagalawatta.SkillManager
```

---

## 3. Manual Downloads (Direct Releases)

Download pre-built packages from [GitHub Releases](https://github.com/dishanagalawatta/SkillManager/releases):

### Windows Installer (.exe)
1. Download `SkillManager_Setup.exe`.
2. Run the installer (if SmartScreen appears, click **More info** → **Run anyway**).
3. Verify file integrity:
   ```powershell
   Get-FileHash .\SkillManager_Setup.exe -Algorithm SHA256
   ```

### Debian / Ubuntu Package (.deb)
```bash
sudo dpkg -i skill-manager_<version>_amd64.deb
sudo apt-get install -f  # resolves any missing dependencies
```

### Standalone Linux AppImage
```bash
chmod +x SkillManager-<version>-x86_64.AppImage
./SkillManager-<version>-x86_64.AppImage
```

*(If FUSE is not installed on your system, run with `./SkillManager-<version>-x86_64.AppImage --appimage-extract-and-run`).*

---

## 4. Developer Setup (From Source)

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone repository
git clone https://github.com/dishanagalawatta/SkillManager.git
cd SkillManager

# Sync dependencies into virtualenv
uv sync

# Run application
uv run skill-manager
```

### Building Installers Locally

- **Linux (`.deb` + `AppImage`)**:
  ```bash
  uv run python scripts/build_linux.py --all
  ```
- **Windows Setup (`SkillManager_Setup.exe`)**:
  ```powershell
  .\packaging\windows\build.ps1 -SkipSign
  ```

---

## 5. Troubleshooting

### "Could not load the Qt platform plugin 'xcb'"
Install the missing XCB cursor library:
```bash
sudo apt install -y libxcb-cursor0
```

### Global hotkey not working on Wayland
Ensure `xdg-desktop-portal` is installed and active on your desktop:
```bash
sudo apt install -y xdg-desktop-portal
```
