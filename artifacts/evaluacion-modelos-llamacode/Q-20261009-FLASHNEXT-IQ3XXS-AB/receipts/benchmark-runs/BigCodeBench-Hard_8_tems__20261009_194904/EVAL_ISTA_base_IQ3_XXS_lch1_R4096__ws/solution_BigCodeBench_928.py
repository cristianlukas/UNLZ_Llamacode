from collections import Counter
import itertools
import string


def task_func(word: str) -> dict:
    all_combinations = [''.join(comb) for comb in itertools.product(string.ascii_lowercase, repeat=2)]
    word_combinations = [word[i:i + 2] for i in range(len(word) - 1)]
    counts = Counter(word_combinations)
    return {comb: counts.get(comb, 0) for comb in all_combinations}
