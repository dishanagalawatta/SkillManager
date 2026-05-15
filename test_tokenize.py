import shlex
import os

def sanitize_command(command):
    if not command:
        return ""

    try:
        # Use shlex to tokenize the command safely.
        # posix=False preserves backslashes on Windows, but quotes might behave slightly differently.
        tokens = shlex.split(command, posix=(os.name != 'nt'))
    except ValueError:
        return ""

    safe_tokens = []
    allowed_operators = {'&&', '||', '|', '>', '>>', '<'}

    for token in tokens:
        if token in allowed_operators:
            safe_tokens.append(token)
            continue

        if token == ';':
            continue

        # Basic sanitization of the token itself to remove inline subshells
        sanitized = token.replace('`', '').replace('$', '')

        # We don't quote here because we are reconstructing a shell string,
        # but we need to ensure arguments with spaces are quoted again.
        if ' ' in sanitized and not (sanitized.startswith('"') and sanitized.endswith('"')) and not (sanitized.startswith("'") and sanitized.endswith("'")):
            sanitized = f'"{sanitized}"'

        safe_tokens.append(sanitized)

    return " ".join(safe_tokens)

print(sanitize_command("npm --version ; rm -rf /"))
print(sanitize_command("git pull && echo `whoami`"))
# Force os.name check simulation
os.name = 'nt'
print(sanitize_command("test -d C:\\path\\to\\dir"))
