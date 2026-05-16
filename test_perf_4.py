import timeit
import re
from rapidfuzz import fuzz

text1 = "This is a test description with some random words."
text2 = "Another description that is quite different."

def test_fuzz():
    score = fuzz.token_set_ratio("test desc", text1)

# What if we move compiled regex to class level?
TOKEN_REGEX = re.compile(r'\b\w+\b')
def tokenize_compiled(text):
    if not text: return []
    tokens = TOKEN_REGEX.findall(text.lower())
    return [t for t in tokens if len(t) > 1]

print("Fuzz token_set_ratio time (10k calls):", timeit.timeit(test_fuzz, number=10000))
