import sys

def dump_structure(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    depth = 0
    for i, line in enumerate(lines):
        line = line.split('//')[0].strip()
        if not line: continue
        
        # Count braces
        open_count = line.count('{')
        close_count = line.count('}')
        
        if open_count > 0 or close_count > 0:
            if close_count > open_count:
                depth -= (close_count - open_count)
                print(f"{i+1:3d}: {depth:2d} | {'  ' * depth}{line}")
            else:
                print(f"{i+1:3d}: {depth:2d} | {'  ' * depth}{line}")
                depth += (open_count - close_count)

if len(sys.argv) > 1:
    dump_structure(sys.argv[1])
