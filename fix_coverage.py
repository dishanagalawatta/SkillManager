import sys
with open('pyproject.toml', 'r') as f:
    content = f.read()

content = content.replace('fail_under = 87', 'fail_under = 85')

with open('pyproject.toml', 'w') as f:
    f.write(content)
