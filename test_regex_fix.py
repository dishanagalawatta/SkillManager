import re

def sanitize(text):
    # This token pattern matches a sequence of:
    # 1. Unquoted characters
    # 2. Single quoted string
    # 3. Double quoted string
    token_pattern = r"(?:[^;\r\n\s'\"]|'[^']*'|\"(?:\\.|[^\"\\])*\")+"

    # We replace everything after echo password= that matches this token with ***
    pattern = r"(echo password=)(" + token_pattern + r")"

    if "echo password=" in text:
        text = re.sub(pattern, r"\1***", text)
    return text

print("1:", sanitize("echo password='secret'\"'\"'more'"))
print("2:", sanitize("echo password='secret\\'"))
print("3:", sanitize("echo password='secret\nmore'"))
print("4:", sanitize('echo password="secret\nmore"'))
print("5:", sanitize("echo password=secret && echo hello"))
print("6:", sanitize('echo password="my\\"secret" && echo hello'))
