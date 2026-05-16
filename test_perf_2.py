import timeit
import re

# original tokenize
def tokenize_uncompiled(text):
    if not text: return []
    tokens = re.findall(r'\b\w+\b', text.lower())
    return [t for t in tokens if len(t) > 1]

TOKEN_REGEX = re.compile(r'\b\w+\b')

def tokenize_compiled(text):
    if not text: return []
    tokens = TOKEN_REGEX.findall(text.lower())
    return [t for t in tokens if len(t) > 1]

# What about memory?
class SkillIndexer1:
    def tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        tokens = re.findall(r'\b\w+\b', text.lower())
        return [t for t in tokens if len(t) > 1]

class SkillIndexer2:
    TOKEN_REGEX = re.compile(r'\b\w+\b')
    def tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        tokens = self.TOKEN_REGEX.findall(text.lower())
        return [t for t in tokens if len(t) > 1]

text = "This is a test of the emergency broadcast system. " * 10
indexer1 = SkillIndexer1()
indexer2 = SkillIndexer2()

print("Indexer 1 (Uncompiled):", timeit.timeit(lambda: indexer1.tokenize(text), number=10000))
print("Indexer 2 (Compiled):", timeit.timeit(lambda: indexer2.tokenize(text), number=10000))
