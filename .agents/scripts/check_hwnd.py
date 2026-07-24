import ctypes, subprocess

hWnd = 199982
pid = ctypes.c_ulong()
ctypes.windll.user32.GetWindowThreadProcessId(hWnd, ctypes.byref(pid))
print(f"HWND {hWnd} PID={pid.value}", flush=True)

# List windows with "Skill" in title
def callback(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
    title = buf.value
    if "skill" in title.lower() or "Skill" in title:
        pid2 = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid2))
        print(f"  HWND={hwnd} PID={pid2.value} Title='{title}'", flush=True)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
print("--- SkillManager windows ---", flush=True)
ctypes.windll.user32.EnumWindows(WNDENUMPROC(callback), 0)
