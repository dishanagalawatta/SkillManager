# Installing SkillManager

## Recommended: winget (no SmartScreen warning)

```powershell
winget install --id dishanagalawatta.SkillManager -e --source winget
```

This installs SkillManager via Windows Package Manager. The binary is
distributed through Microsoft's package index, so Windows trusts the
install path and **no SmartScreen warning appears**.

To update:

```powershell
winget upgrade --id dishanagalawatta.SkillManager
```

To uninstall:

```powershell
winget uninstall --id dishanagalawatta.SkillManager
```

## Direct Download

Download `SkillManager_Setup.exe` from
[Releases](https://github.com/dishanagalawatta/SkillManager/releases).

### Bypassing SmartScreen

If Windows shows "Windows protected your PC" (SmartScreen warning):

1. Click **More info**.
2. Click **Run anyway**.

This happens because the installer is signed with a self-signed certificate.
The binary is safe — you can verify by checking the SHA256 hash against the
one published in the Release notes.

### Verifying the installer

After download, verify the installer integrity:

```powershell
Get-FileHash .\SkillManager_Setup.exe -Algorithm SHA256
```

Compare the output hash with the SHA256 listed on the
[Release page](https://github.com/dishanagalawatta/SkillManager/releases).

## Linux

### Option A: .deb (Ubuntu/Debian)

Download `skill-manager_<version>_amd64.deb` from
[Releases](https://github.com/dishanagalawatta/SkillManager/releases), then:

```bash
sudo dpkg -i skill-manager_<version>_amd64.deb
```

If dpkg reports missing dependencies, fix them with:

```bash
sudo apt-get install -f
```

Supported on Ubuntu 22.04+ (amd64). The package installs to `/opt/SkillManager`
with a `/usr/bin/skill-manager` symlink and a launcher entry.

To uninstall:

```bash
sudo dpkg -r skill-manager
```

### Option B: AppImage (any distro)

Download `SkillManager-<version>-x86_64.AppImage` from
[Releases](https://github.com/dishanagalawatta/SkillManager/releases), then:

```bash
chmod +x SkillManager-<version>-x86_64.AppImage
./SkillManager-<version>-x86_64.AppImage
```

You can also double-click the file in your file manager. If FUSE2 is not
available, run with `--appimage-extract-and-run` instead:

```bash
./SkillManager-<version>-x86_64.AppImage --appimage-extract-and-run
```

Optionally, move the AppImage into a directory on your `PATH` (for example
`~/.local/bin`) and create a desktop entry so it appears in your application
menu.

### Updates

The in-app Updates view links to the GitHub Releases page; there is no in-app
installer. To update:

- **.deb users**: download the new `skill-manager_<version>_amd64.deb` and
  reinstall it with `sudo dpkg -i`.
- **AppImage users**: download the new `SkillManager-<version>-x86_64.AppImage`
  and replace the old file.

### Troubleshooting

#### "Could not load the Qt platform plugin 'xcb'"

Install the missing XCB library:

```bash
sudo apt install -y libxcb-cursor0
```

#### Global hotkey not working on Wayland

Make sure `xdg-desktop-portal` is present:

```bash
sudo apt install -y xdg-desktop-portal
```

## Developer Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/dishanagalawatta/SkillManager.git
cd SkillManager
uv sync
uv run skill-manager
```

## Environment Configuration

For tiered environment overrides (dev, staging, prod), see
[`environments/README.md`](../environments/README.md). Copy the
appropriate `.env.*.example` to `.env` in the project root.

## Building the Installer Locally

Requires: Python 3.12+, uv, [Inno Setup](https://jrsoftware.org/isinfo.php).

```powershell
# Build without signing (no cert needed)
.\packaging\windows\build.ps1 -SkipSign

# Build with signing (cert must be in packaging\windows\certs\)
$env:WIN_PFX_PASS = "SkillManager2026!"
.\packaging\windows\build.ps1
```

Output: `dist/SkillManager_Setup.exe`

## Troubleshooting

### "Unknown Publisher" warning

The installer uses a self-signed certificate. This is expected. Use winget
for the cleanest install experience, or click "Run anyway" for direct download.

### winget: "No manifest found"

The winget package may not be published yet. Check the
[microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) repo
for `dishanagalawatta.SkillManager`.

### Installation fails silently

Run the installer from an elevated command prompt:

```powershell
& ".\SkillManager_Setup.exe" /SILENT
```
