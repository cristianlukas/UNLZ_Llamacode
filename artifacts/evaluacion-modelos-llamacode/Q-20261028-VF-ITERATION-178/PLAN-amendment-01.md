# Q178 amendment 01 — rebuild the Flash-Next NInfer v3 artifacts

## Why this amendment exists

Q178 attempt 01 stopped before readiness. The Q171-era NInfer v3 artifact lacks the
`ple_layers` field required by the Q174 NInfer-all runtime. The receipt has no smoke,
samples, or inference PID; both GPUs and the port were clean after exit. Do not rerun
that artifact or treat the attempt as a hardware, memory, or quality failure.

## Preregistered recovery

Use the existing IQ2_XS GGUF source shards. Do not download, delete, replace, or modify
the ASTRA, SOL, PeritoSoft, source GGUF, Q171 artifact, or production profile. Rebuild
only isolated NInfer v3 evaluation artifacts with Q174's pinned converter commit
`3d882fc116941d9233c40bf30f4d66dbaa3d24bd`.

1. Create an isolated CPU-only conversion environment on `Disco local`, with PyTorch
   `2.14.1` from the official CPU wheel index. Keep its environment and package cache
   off `/` (which had 6.4 GiB free at preregistration). Verify that `torch.cuda.is_available()`
   is false; conversion must not initialize a GPU.
   The first source-preparation invocation stopped at Python import time because the
   conversion module imports `safetensors.torch` transitively. It did not read/write
   any GGUF or create the source-config directory. Amendment 01 now pins the additional
   import dependencies `safetensors==0.8.0` and `gguf==0.19.0` into the same isolated
   venv before retrying. The second import attempt found that `gguf_source.py` imports
   the official `gguf` package transitively; it also stopped before any GGUF read/write.
2. Run `scripts/prepare_q178_v3_source.py` (SHA-256
   `6ebbb720c3c226c4017780af9312793dddbc6d08706533810d8bfaa5541bbf83`). It reconstructs
   the HF-style config from the prior conversion's exact normalized config, restores the
   current raw fields including `ple_layer_ids=[2]`, extracts the four frontend resources
   from the same prior artifact, runs the current `text_config` adapter, and validates
   every model tensor/header against the local GGUF before writing the source directory.
   The script records source/config/resource hashes. If validation fails, stop before
   conversion and preserve the output.
3. Convert the text-only model to a new path on HDD extra, and the shared n-gram table
   to a separate new path on Disco local. Use the same `qwen3_8_flash_next_gguf` recipe,
   CPU, 65,536 rows/chunk, and `--max-file-bytes 32000000000` for the text artifact.
   The local model and table shards are the only weight inputs. No data is written to
   the existing Q171 artifact.
4. Run the NInfer artifact inspector on both outputs. Verify text/PLE config, resource
   presence, file lengths, component types, and that the model's table digest names the
   independently generated n-gram artifact. Hash every output. If the pair does not
   validate, do not start the server.
5. Inference attempt 02 requires a second amendment that pins the generated artifact
   hashes and wrapper hash before any GPU use. It will retain Q178's preregistered dual
   RTX 3090 pipeline, `/health` cold/hot starts, 8K×3 and 32K/64K/128K/261888 ladder,
   128 exact output tokens, existing stop guards, and no new 512K/1M run. It writes to
   fresh attempt-02 receipts; attempt 01 is immutable.

## Storage estimate and guards

At preregistration, Disco local had 194.3 GiB free and HDD extra 67.9 GiB free. The
expected text artifact is about 39.2 GB on HDD extra; the n-gram artifact is about
29 GB on Disco local. No cleanup or overwrite is permitted. If free space drops below
50 GB on HDD extra or 100 GB on Disco local before conversion, stop and reassess.
Conversion is serialized, CPU-only, and limited to these pinned inputs.

## Exact conversion commands

From `/tmp/q174-d/ninfer-src`, with `PYTHONPATH` pointing to that checkout and the
isolated CPU environment active:

```bash
python -m tools.convert \
  --model "/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/source-config" \
  --recipe qwen3_8_flash_next_gguf --components text \
  --source gguf="/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf" \
  --source ngram="/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf" \
  --device cpu --rows-per-chunk 65536 --max-file-bytes 32000000000 \
  --name qwen3.8-flash-next-iq2-xs-q178-v3 \
  --out "/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/text/qwen4exp.ninfer"

python -m tools.convert \
  --model "/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/source-config" \
  --recipe qwen3_8_flash_next_gguf --components ngram \
  --source ngram="/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf" \
  --device cpu --rows-per-chunk 65536 \
  --out "/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/ngram/qwen4exp-ngram.ninfer"
```

## State

Preregistered under the Q146 umbrella lock. The failed initial attempt remains at
`runs/context-ladder.json`; the first preparer import failure is preserved as
`receipts/prepare-source-v3-attempt01.log`. No conversion or GPU retry has run under
this amendment yet.
