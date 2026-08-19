import os
import urllib.request

base = r"c:\Users\DIKKA\Documents\01-Projects\20-AiSupportTools\SkillManager\assets\ui"

# icon-id : [list of filenames to save to]
mappings = {
    "solar:widget-add-bold-duotone": ["layout-grid-add-icon.svg"],
    "solar:alt-arrow-down-bold-duotone": [
        "expand-arrow-icon.svg",
        "expand-arrow-icon-dark.svg",
        "expand-arrow-icon-light.svg",
        "collapse-arrow-icon.svg",
        "collapse-arrow-icon-dark.svg",
        "collapse-arrow-icon-light.svg",
    ],
    "solar:copy-bold-duotone": ["copy-icon.svg"],
    "solar:star-broken": ["star-unstarred-icon.svg"],
    "solar:star-bold-duotone": ["star-icon.svg"],
    "solar:camera-add-bold": ["screenshot-icon.svg"],
    "solar:refresh-bold-duotone": ["refresh-icon.svg"],
    "solar:cat-bold": ["lightning-icon.svg"],
    "solar:folder-2-bold-duotone": ["folder-sync-icon.svg", "collection-icon.svg"],
    "solar:settings-minimalistic-bold": ["settings-icon.svg"],
    "solar:close-circle-bold-duotone": ["close-icon.svg"],
    "solar:maximize-square-3-bold-duotone": ["maximize-icon.svg"],
    "solar:minimize-square-3-bold-duotone": ["restore-icon.svg"],
    "solar:minus-circle-bold-duotone": ["minimize-icon.svg"],
    "solar:sun-2-broken": ["sun-icon.svg"],
    "solar:moon-broken": ["moon-icon.svg"],
    "solar:add-circle-broken": ["check-icon.svg"],
    "solar:trash-bin-trash-bold-duotone": ["delete-icon.svg"],
    "solar:bolt-bold-duotone": ["command-icon.svg"],
    "solar:notebook-minimalistic-bold-duotone": ["library-icon.svg"],
}

for icon, filenames in mappings.items():
    prefix, name = icon.split(":")
    url = f"https://api.iconify.design/{prefix}/{name}.svg"
    print(f"Downloading {icon}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req).read().decode("utf-8")
        for fname in filenames:
            with open(os.path.join(base, fname), "w", encoding="utf-8") as f:
                f.write(data)
            print(f"  -> {fname}")
    except Exception as e:
        print(f"  FAILED: {e}")

print("\nDone!")
