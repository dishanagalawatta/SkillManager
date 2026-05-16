import timeit
import re

def tokenize_uncompiled(text):
    if not text: return []
    tokens = re.findall(r'\b\w+\b', text.lower())
    return [t for t in tokens if len(t) > 1]

TOKEN_REGEX = re.compile(r'\b\w+\b')
def tokenize_compiled(text):
    if not text: return []
    tokens = TOKEN_REGEX.findall(text.lower())
    return [t for t in tokens if len(t) > 1]

text = "This is a test of the emergency broadcast system. " * 10

print("Uncompiled:", timeit.timeit(lambda: tokenize_uncompiled(text), number=10000))
print("Compiled:", timeit.timeit(lambda: tokenize_compiled(text), number=10000))
