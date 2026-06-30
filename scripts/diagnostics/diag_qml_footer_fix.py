import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

files = [
    'src/skill_manager/SkillManagerComponents/dialogs/CommandCarrySkillsDialog.qml',
    'src/skill_manager/SkillManagerComponents/dialogs/CommandCreateDialog.qml',
    'src/skill_manager/SkillManagerComponents/dialogs/CommandRemovalConfirmDialog.qml',
    'src/skill_manager/SkillManagerComponents/dialogs/MissingSkillsDialog.qml',
    'src/skill_manager/SkillManagerComponents/dialogs/ProjectRenameDialog.qml'
]

for f in files:
    filepath = PROJECT_ROOT / f
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if 'height: 80' in content and 'color: "transparent"' in content:
        lines = content.split('\n')
        new_lines = []
        bracket_count = 0
        in_footer_rect = False
        
        for i, line in enumerate(lines):
            # Find the footer Rectangle
            if 'Rectangle {' in line and i + 2 < len(lines) and 'height: 80' in lines[i+2]:
                in_footer_rect = True
                bracket_count = 1
                continue
                
            if in_footer_rect:
                if 'Layout.fillWidth: true' in line and i < len(lines) and 'height: 80' in lines[i+1]:
                    continue
                if 'height: 80' in line:
                    continue
                if 'color: "transparent"' in line:
                    continue
                
                # Keep tracking brackets to find the end of this Rectangle
                if '{' in line:
                    bracket_count += line.count('{')
                if '}' in line:
                    bracket_count -= line.count('}')
                    
                if bracket_count == 0:
                    in_footer_rect = False
                    continue # Skip the closing bracket of the Rectangle
            
            new_lines.append(line)
            
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write('\n'.join(new_lines))
        print(f'Fixed {f}')
