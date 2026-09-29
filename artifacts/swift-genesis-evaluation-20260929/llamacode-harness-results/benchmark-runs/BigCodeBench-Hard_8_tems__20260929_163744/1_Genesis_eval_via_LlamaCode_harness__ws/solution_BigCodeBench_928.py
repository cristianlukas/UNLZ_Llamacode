from collections import Counter
import itertools
import string

def task_func(word: str) -> dict:
    word = word.lower()
    result = {a + b: 0 for a, b in itertools.product(string.ascii_lowercase, repeat=2)}
    for i in range(len(word) - 1):
        pair = word[i] + word[i + 1]
        if pair in result:
            result[pair] += 1
    return result
