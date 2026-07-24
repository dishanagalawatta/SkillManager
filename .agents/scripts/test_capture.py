import sys, os, base64
from skill_manager.mcp.bridge import capture_app_window, get_window_info, _is_minimized

info = get_window_info()
hwnd = info.get("hwnd")
minimized = _is_minimized(hwnd) if hwnd else None
print(f"Window HWND={hwnd} minimised={minimized}", flush=True)

b64, w, h = capture_app_window()
size_kb = len(b64) / 1024 if b64 else 0
print(f"Capture: {w}x{h} data={b64 is not None} size={size_kb:.1f}KB", flush=True)

if b64:
    path = r".agents\screenshots\test_fix.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    print(f"Saved: {path}", flush=True)

sys.exit(0)
