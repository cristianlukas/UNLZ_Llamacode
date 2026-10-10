from collections import Counter
import itertools
import string

def task_func(word: str) -> dict:
    all_combos = [''.join(c) for c in itertools.product(string.ascii_lowercase, repeat=2)]
    counts = Counter(word[i:i+2] for i in range(len(word) - 1))
    return {combo: counts.get(combo, 0) for combo in all_combos}
