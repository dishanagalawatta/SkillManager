import re

def print_tree(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    depth = 0
    in_comment = False
    
    for i, line in enumerate(lines):
        orig_line = line
        line = line.strip()
        
        # very basic comment removal for same line
        if '//' in line:
            line = line[:line.find('//')].strip()
            
        open_count = line.count('{')
        close_count = line.count('}')
        
        if open_count > 0 or close_count > 0:
            if close_count > open_count:
                depth -= (close_count - open_count)
                print(f"{i+1:3d}: {depth:2d} | {'  ' * depth}{line}")
            else:
                print(f"{i+1:3d}: {depth:2d} | {'  ' * depth}{line}")
                depth += (open_count - close_count)

print_tree("src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml")
