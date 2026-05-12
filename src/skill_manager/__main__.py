import os
import sys
from pathlib import Path

# Add 'src' to sys.path to allow running as a module without installation
root_dir = Path(__file__).parent.parent.parent.resolve()
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

def apply_customtkinter_patch():
    """
    Apply monkey-patches to CustomTkinter to resolve issues on Python 3.14.
    1. Fix KeyError in CTkCanvas when radius is a float.
    2. Ensure coordinates are integers to avoid Tcl issues.
    """
    try:
        import customtkinter as ctk
        from customtkinter.windows.widgets.core_rendering.ctk_canvas import CTkCanvas
        
        # 1. Patch _get_char_from_radius to handle float radii (prevents KeyError)
        original_get_char = CTkCanvas._get_char_from_radius
        
        def patched_get_char(self, radius):
            if radius >= 20:
                return "A"
            try:
                # Try exact lookup (fast path)
                return self.radius_to_char_fine[radius]
            except KeyError:
                # Fallback to rounded integer (handles floats from scaling)
                try:
                    return self.radius_to_char_fine[int(round(radius))]
                except (KeyError, TypeError):
                    return "A" # Final fallback
                    
        CTkCanvas._get_char_from_radius = patched_get_char
        
        # 2. Patch coords to be more robust (ensures integer coordinates for Tcl 9.0)
        original_coords = CTkCanvas.coords
        
        def patched_coords(self, tag_or_id, *args):
            try:
                # Convert coordinate args to int to avoid potential Tcl 9.0 float issues
                new_args = []
                for arg in args:
                    if isinstance(arg, (int, float)):
                        new_args.append(int(round(arg)))
                    elif isinstance(arg, (list, tuple)):
                        new_args.append([int(round(x)) if isinstance(x, (int, float)) else x for x in arg])
                    else:
                        new_args.append(arg)
                
                return original_coords(self, tag_or_id, *new_args)
            except Exception:
                # Fallback to original if conversion fails
                return original_coords(self, tag_or_id, *args)
                    
        CTkCanvas.coords = patched_coords
        
    except Exception:
        # Silently fail if patching is not possible
        pass

from skill_manager.app import SkillManagerApp

def main():
    apply_customtkinter_patch()
    app = SkillManagerApp()
    app.mainloop()

if __name__ == "__main__":
    main()
