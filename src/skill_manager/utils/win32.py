import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

if sys.platform == 'win32':
    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class WINDOWPLACEMENT(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.UINT),
            ("flags", wintypes.UINT),
            ("showCmd", wintypes.UINT),
            ("ptMinPosition", POINT),
            ("ptMaxPosition", POINT),
            ("rcNormalPosition", RECT),
        ]

import pywinstyles

def apply_native_style(window, style_name: str) -> None:
    """
    Applies a native Windows style (mica, acrylic, aero, transparent, win7, inverse, 
    popup, dark, light) to a tkinter window.
    
    Args:
        window: The tkinter window object (Tk or Toplevel).
        style_name: The name of the style to apply.
    """
    if sys.platform != 'win32':
        return

    try:
        # Update the window to ensure HWND is available
        window.update()
        
        # Apply the style using pywinstyles
        # This handles version checks and DwmSetWindowAttribute internally.
        pywinstyles.apply_style(window, style_name)
    except Exception as e:
        print(f"Failed to apply native style {style_name}: {e}")

def get_window_placement(hwnd: int) -> Optional[Tuple]:
    """Returns the placement of the window identified by hwnd."""
    if sys.platform != 'win32':
        return None
        
    placement = WINDOWPLACEMENT()
    placement.length = ctypes.sizeof(WINDOWPLACEMENT)
    if ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
        return (
            placement.flags,
            placement.showCmd,
            (placement.ptMinPosition.x, placement.ptMinPosition.y),
            (placement.ptMaxPosition.x, placement.ptMaxPosition.y),
            (placement.rcNormalPosition.left, placement.rcNormalPosition.top, 
             placement.rcNormalPosition.right, placement.rcNormalPosition.bottom)
        )
    return None

def set_window_placement(hwnd: int, placement_data: Tuple) -> bool:
    """Sets the placement of the window identified by hwnd."""
    if sys.platform != 'win32':
        return False
        
    placement = WINDOWPLACEMENT()
    placement.length = ctypes.sizeof(WINDOWPLACEMENT)
    placement.flags = placement_data[0]
    placement.showCmd = placement_data[1]
    placement.ptMinPosition.x, placement.ptMinPosition.y = placement_data[2]
    placement.ptMaxPosition.x, placement.ptMaxPosition.y = placement_data[3]
    placement.rcNormalPosition.left, placement.rcNormalPosition.top, \
    placement.rcNormalPosition.right, placement.rcNormalPosition.bottom = placement_data[4]
    
    return bool(ctypes.windll.user32.SetWindowPlacement(hwnd, ctypes.byref(placement)))
