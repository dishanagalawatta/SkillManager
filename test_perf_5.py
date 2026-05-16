import timeit
tokens = ["creative", "work", "features"]
query = "work"
def test_any():
    return any(query == t for t in tokens)

def test_in():
    return query in tokens

print("any:", timeit.timeit(test_any, number=1000000))
print("in:", timeit.timeit(test_in, number=1000000))
