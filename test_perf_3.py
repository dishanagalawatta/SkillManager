import timeit
import re

from rapidfuzz import fuzz

text1 = "This is a test description with some random words."
text2 = "Another description that is quite different."

def test_fuzz():
    score = fuzz.token_set_ratio("test desc", text1)

print("Fuzz time:", timeit.timeit(test_fuzz, number=10000))
