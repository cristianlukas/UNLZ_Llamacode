#!/usr/bin/env python3
"""Paired 2048 probe: state-only LLM vs LLM with explicit one-step predictions.

This is a narrow systems probe, not a general Computer Use benchmark. The game
engine and transition table are deterministic; the LLM must choose one legal
move. A new conversation starts every checkpoint interval with a durable state
receipt to exercise continuation after context reset.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen

SIZE = 4
DIRECTIONS = ("UP", "DOWN", "LEFT", "RIGHT")
VARIANTS = ("state-only", "transition-model",
            "state-only-constrained", "transition-model-constrained",
            "state-only-fallback", "transition-model-fallback")
CHOICE_RE = re.compile(r"\b(UP|DOWN|LEFT|RIGHT)\b", re.I)


def collapse(line: list[int]) -> tuple[list[int], int]:
    packed = [v for v in line if v]
    out: list[int] = []
    reward = 0
    i = 0
    while i < len(packed):
        if i + 1 < len(packed) and packed[i] == packed[i + 1]:
            value = packed[i] * 2
            out.append(value)
            reward += value
            i += 2
        else:
            out.append(packed[i])
            i += 1
    return out + [0] * (SIZE - len(out)), reward


def move(board: list[int], direction: str) -> tuple[list[int], int]:
    grid = [board[i:i + SIZE] for i in range(0, SIZE * SIZE, SIZE)]
    total = 0
    if direction in ("LEFT", "RIGHT"):
        for r in range(SIZE):
            line = grid[r][:]
            if direction == "RIGHT":
                line.reverse()
            collapsed, reward = collapse(line)
            if direction == "RIGHT":
                collapsed.reverse()
            grid[r] = collapsed
            total += reward
    else:
        for c in range(SIZE):
            line = [grid[r][c] for r in range(SIZE)]
            if direction == "DOWN":
                line.reverse()
            collapsed, reward = collapse(line)
            if direction == "DOWN":
                collapsed.reverse()
            for r in range(SIZE):
                grid[r][c] = collapsed[r]
            total += reward
    return [v for row in grid for v in row], total


def legal_moves(board: list[int]) -> dict[str, list[int]]:
    result = {}
    for direction in DIRECTIONS:
        moved, _ = move(board, direction)
        if moved != board:
            result[direction] = moved
    return result


def fallback_move(board: list[int], actions: dict[str, list[int]]) -> str:
    """Pick a legal move using a small deterministic 2048 board evaluator."""
    def evaluate(candidate: list[int]) -> int:
        grid = [candidate[i:i + SIZE] for i in range(0, SIZE * SIZE, SIZE)]
        empty = candidate.count(0)
        reward = sum(v for v in candidate if v)
        log_grid = [[v.bit_length() - 1 if v else 0 for v in row] for row in grid]
        smoothness = 0
        for r in range(SIZE):
            for c in range(SIZE):
                if not grid[r][c]:
                    continue
                if c + 1 < SIZE and grid[r][c + 1]:
                    smoothness += abs(log_grid[r][c] - log_grid[r][c + 1])
                if r + 1 < SIZE and grid[r + 1][c]:
                    smoothness += abs(log_grid[r][c] - log_grid[r + 1][c])
        max_tile = max(candidate)
        corner_bonus = 1 if max_tile in (grid[0][0], grid[0][-1], grid[-1][0], grid[-1][-1]) else 0
        return empty * 1000 + corner_bonus * 100 + reward - smoothness * 25
    return max(actions, key=lambda direction: evaluate(actions[direction]))


def render(board: list[int]) -> str:
    return "\n".join(" ".join(f"{v:4}" if v else "   ." for v in board[r:r + SIZE])
                     for r in range(0, SIZE * SIZE, SIZE))


def spawn(board: list[int], rng: random.Random) -> None:
    empty = [i for i, value in enumerate(board) if value == 0]
    if not empty:
        return
    index = rng.choice(empty)
    board[index] = 4 if rng.random() < 0.1 else 2


def initial(seed: int) -> tuple[list[int], random.Random]:
    rng = random.Random(seed)
    board = [0] * 16
    spawn(board, rng)
    spawn(board, rng)
    return board, rng


def ask(url: str, model: str, messages: list[dict], seed: int,
        allowed: list[str], constrained: bool) -> tuple[str, str, float]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 20,
        "max_tokens": 64 if constrained else 16,
        "seed": seed,
        "stream": False,
    }
    if constrained:
        payload["tools"] = [{"type": "function", "function": {
            "name": "choose_move",
            "description": "Choose exactly one currently legal move.",
            "parameters": {"type": "object",
                           "properties": {"direction": {"type": "string", "enum": allowed}},
                           "required": ["direction"], "additionalProperties": False},
        }}]
        payload["tool_choice"] = "required"
    request = Request(url, data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urlopen(request, timeout=90) as response:
        data = json.loads(response.read())
    message = data["choices"][0]["message"]
    content = str(message.get("content") or "")
    direction = ""
    calls = message.get("tool_calls", []) or []
    if calls:
        arguments = calls[0].get("function", {}).get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        direction = str(arguments.get("direction") or "").upper()
        content = json.dumps(arguments)
    return content, direction, (time.perf_counter() - started) * 1000


def has_moves(board: list[int]) -> bool:
    return bool(legal_moves(board))


def game(url: str, model: str, seed: int, variant: str,
         max_turns: int, checkpoint_every: int) -> dict:
    board, rng = initial(seed)
    score = 0
    rows = []
    history: list[dict] = []
    messages: list[dict] = [
        {"role": "system", "content": (
            "Sos un agente de 2048. Conservá el objetivo de alcanzar la ficha 2048, "
            "elegí sólo movimientos legales. "
            + ("Invocá choose_move con una opción del enum." if variant.endswith("constrained")
               else "Respondé con una sola palabra: UP, DOWN, LEFT o RIGHT.")
            + " No afirmes que el objetivo se cumplió sin ver 2048."
        )},
        {"role": "user", "content": "Objetivo: alcanzar 2048. Empezá con el tablero que recibirás."},
    ]
    invalid = 0
    fallback_count = 0
    restarts = 0
    wall_ms = 0.0
    for turn in range(1, max_turns + 1):
        actions = legal_moves(board)
        if not actions:
            break
        table = "\n".join(f"{direction}: {render(next_board)}"
                          for direction, next_board in actions.items())
        observation = f"Turno {turn}. Score={score}. Mejor ficha={max(board)}.\nTablero:\n{render(board)}\nMovimientos legales: {', '.join(actions)}."
        if variant.startswith("transition-model"):
            observation += f"\nConsecuencias calculadas de cada movimiento legal:\n{table}"
        if turn == 1 or (turn - 1) % checkpoint_every == 0:
            if turn > 1:
                # Simulate a process/context restart using only the durable task receipt.
                messages = [
                    messages[0],
                    {"role": "user", "content": (
                        f"Reanudá el mismo objetivo: alcanzar 2048. Checkpoint verificado: "
                        f"turno {turn}, score {score}, mejor ficha {max(board)}.\n"
                        f"{observation}\nElegí un movimiento legal."
                    )},
                ]
                restarts += 1
            else:
                messages.append({"role": "user", "content": observation})
        else:
            messages.append({"role": "user", "content": observation})
        raw, action, elapsed = ask(url, model, messages, seed + turn,
                                   list(actions), variant.endswith("constrained"))
        wall_ms += elapsed
        if not action:
            match = CHOICE_RE.search(raw.upper())
            action = match.group(1).upper() if match else ""
        proposed_action = action
        valid = action in actions
        if not valid:
            invalid += 1
            if variant.endswith("fallback"):
                action = fallback_move(board, actions)
                fallback_count += 1
            else:
                rows.append({"turn": turn, "raw": raw, "action": action or None,
                             "valid": False, "score": score, "maxTile": max(board),
                             "allowedActions": list(actions),
                             "elapsedMs": round(elapsed, 2)})
                break  # Honest abstention: never silently substitute a move.
        moved, reward = move(board, action)
        score += reward
        board = moved
        spawn(board, rng)
        messages.append({"role": "assistant", "content": action})
        history.append({"turn": turn, "action": action, "score": score, "maxTile": max(board)})
        rows.append({"turn": turn, "action": action, "proposedAction": proposed_action,
                     "fallback": action != proposed_action, "valid": True,
                     "score": score, "maxTile": max(board),
                     "elapsedMs": round(elapsed, 2)})
        if max(board) >= 2048:
            break
    return {
        "seed": seed, "variant": variant, "turns": len(rows), "score": score,
        "maxTile": max(board), "reached2048": max(board) >= 2048,
        "endedNaturally": not has_moves(board), "invalidActions": invalid,
        "fallbackMoves": fallback_count,
        "checkpointRestarts": restarts, "wallMs": round(wall_ms, 2),
        "medianDecisionMs": round(statistics.median(r["elapsedMs"] for r in rows), 2) if rows else None,
        "rows": rows,
    }


def self_test() -> None:
    board = [2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    out, reward = move(board, "LEFT")
    assert out[:4] == [4, 4, 0, 0] and reward == 8
    out, reward = move(board, "RIGHT")
    assert out[:4] == [0, 0, 4, 4] and reward == 8
    board = [2, 0, 0, 0, 2, 0, 0, 0] + [0] * 8
    out, reward = move(board, "UP")
    assert out[0] == 4 and reward == 4
    assert set(legal_moves([0] * 16)) == set()
    assert set(legal_moves([2] * 16)) == set(DIRECTIONS)
    actions = legal_moves([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2])
    assert fallback_move([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2], actions) in actions
    print("self-test: 5 engine invariants passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8095/v1/chat/completions")
    parser.add_argument("--model", default="Qwen3.5-9B-Q4_K_M")
    parser.add_argument("--seeds", default="17,42,91,2026")
    parser.add_argument("--max-turns", type=int, default=128)
    parser.add_argument("--checkpoint-every", type=int, default=16)
    parser.add_argument("--variants", choices=VARIANTS, nargs="+", default=list(VARIANTS))
    parser.add_argument("--out", type=Path,
                        default=Path("/tmp/aura-2048-ab.json"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    seeds = [int(value) for value in args.seeds.split(",") if value]
    results = []
    report = {
        "benchmark": "aura_2048_paired_transition_ab_v1",
        "status": "running",
        "protocol": {"model": args.model, "temperature": 0.0,
                     "seeds": seeds, "maxTurns": args.max_turns,
                     "checkpointEvery": args.checkpoint_every,
                     "invalidActionPolicy": "abstain_and_end unless variant=fallback",
                     "variants": args.variants},
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for seed in seeds:
        for variant in args.variants:
            try:
                result = game(args.url, args.model, seed, variant,
                              args.max_turns, args.checkpoint_every)
            except Exception as exc:
                result = {"seed": seed, "variant": variant,
                          "failureKind": "transport_or_context",
                          "error": f"{type(exc).__name__}: {exc}"}
            results.append(result)
            args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(f"seed={seed} variant={variant} turns={result.get('turns', '-')} "
                  f"max={result.get('maxTile', '-')} score={result.get('score', '-')} "
                  f"invalid={result.get('invalidActions', '-')} restarts={result.get('checkpointRestarts', '-')}",
                  flush=True)
    report["status"] = "complete" if all("failureKind" not in row for row in results) else "incomplete"
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
