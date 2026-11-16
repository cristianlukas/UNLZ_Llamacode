#!/usr/bin/env python3
"""CPU-only regression check for exact token-count prompt generation."""
import sys
from pathlib import Path
profile=Path(__file__).resolve().parent
sys.path.insert(0,str(profile))
from run_seeded_benchy_exact import PromptGenerator
from llama_benchy.corpus import TokenizedCorpus
import numpy as np
url="https://www.gutenberg.org/files/1661/1661-0.txt"
tokenizer="/media/cristian/HDD extra/Modelos-eval/Q208-UD31-Qwen38/tokenizer"
corpus=TokenizedCorpus(url,tokenizer,"Qwen3.8-27B-UD-Q4_K_XL.gguf")
np.random.seed(42)
gen=PromptGenerator(corpus)
expected=8180
counts=[]; prompts=[]
for _ in range(3):
    context,prompt=gen.generate(expected,0,True)
    count=len(gen.tokenizer.encode(prompt,add_special_tokens=False))
    counts.append(count); prompts.append(prompt)
assert counts==[expected]*3, counts
assert len(set(prompts))==3, "no-cache prompts must remain unique"
print({"status":"PASS","target":expected,"counts":counts,"unique":len(set(prompts))})
