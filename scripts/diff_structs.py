import difflib

with open("orig.txt", encoding="utf-8") as f:
    orig = f.readlines()

with open("curr.txt", encoding="utf-8") as f:
    curr = f.readlines()

diff = difflib.ndiff(orig, curr)
count = 0
for line in diff:
    if line.startswith("-") or line.startswith("+"):
        print(line, end="")
        count += 1
        if count > 100:
            break
