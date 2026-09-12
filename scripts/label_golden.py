#!/usr/bin/env python3
"""
Interactive hand-labeling tool for building data/golden/golden_eval.jsonl
from data/golden/candidate_pool.jsonl, per the assignment's requirement of
150-250 hand-labelled examples (with a stated should_escalate decision).

Usage:
    python scripts/label_golden.py
    python scripts/label_golden.py --target 200   # stop after 200 labeled (default 200)

Resumable: every accepted label is flushed to disk immediately, and already-
labeled source_tweet_ids are skipped on restart, so you can quit (Ctrl+C or
'q') anytime and pick up later without redoing work.

For each candidate you'll see the real customer message + AppleSupport's
real historical reply, plus the weak keyword-based intent guess. You then:
  1. Confirm or correct the intent (numbered menu, or type a custom one)
  2. Decide should_escalate: y/n
  3. Optionally add a one-line note (e.g. why you overrode the weak label)

Output: data/golden/golden_eval.jsonl, one JSON object per line:
  {
    "customer_message": ...,
    "historical_reply": ...,
    "intent": ...,          # your corrected label
    "weak_intent": ...,     # what the keyword heuristic originally guessed
    "should_escalate": true/false,
    "note": "...",          # optional
    "source_tweet_id": ...
  }
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_POOL = ROOT / "data" / "golden" / "candidate_pool.jsonl"
GOLDEN_EVAL = ROOT / "data" / "golden" / "golden_eval.jsonl"

INTENTS = [
    "battery_drain", "ios_update_issue", "app_crash", "icloud_sync",
    "hardware_failure", "account_lock", "billing_refund", "app_store_purchase",
    "wifi_connectivity", "performance_lag", "screen_issue", "feature_request",
    "general_inquiry", "complaint_escalation",
]


def load_jsonl(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def already_labeled_ids(path):
    return {row["source_tweet_id"] for row in load_jsonl(path)}


def prompt_intent(weak_intent: str) -> str:
    print(f"\nWeak label guessed: {weak_intent}")
    print("Pick a number to confirm/correct, or type a new intent name:")
    for i, intent in enumerate(INTENTS, 1):
        marker = "  <-- weak guess" if intent == weak_intent else ""
        print(f"  {i:2d}. {intent}{marker}")
    while True:
        raw = input("> ").strip()
        if raw == "":
            return weak_intent
        if raw.isdigit() and 1 <= int(raw) <= len(INTENTS):
            return INTENTS[int(raw) - 1]
        if raw.lower() in ("q", "quit"):
            raise KeyboardInterrupt
        # treat anything else as a custom intent name
        return raw.strip()


def prompt_escalate() -> bool:
    while True:
        raw = input("Should this be escalated to a human? [y/n] > ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        if raw in ("q", "quit"):
            raise KeyboardInterrupt
        print("Please answer y or n.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=200,
                         help="Stop once this many total examples are labeled (default 200, range 150-250 per assignment).")
    args = parser.parse_args()

    candidates = load_jsonl(CANDIDATE_POOL)
    if not candidates:
        raise FileNotFoundError(f"No candidates found at {CANDIDATE_POOL}. Run prepare_real_data.py first.")

    done_ids = already_labeled_ids(GOLDEN_EVAL)
    remaining = [c for c in candidates if c["source_tweet_id"] not in done_ids]

    print(f"Golden eval so far: {len(done_ids)} labeled.")
    print(f"Target: {args.target}. Remaining candidates available: {len(remaining)}.")
    print("Commands at any prompt: 's' = skip this example, 'q' = quit and save progress.\n")

    GOLDEN_EVAL.parent.mkdir(parents=True, exist_ok=True)
    labeled_count = len(done_ids)

    try:
        for cand in remaining:
            if labeled_count >= args.target:
                break

            print("\n" + "=" * 80)
            print(f"[{labeled_count}/{args.target} labeled]  tweet_id={cand['source_tweet_id']}")
            print(f"CUSTOMER: {cand['customer_message']}")
            print(f"REPLY:    {cand['historical_reply']}")

            skip_check = input("\nPress Enter to label this, 's' to skip, 'q' to quit > ").strip().lower()
            if skip_check == "q":
                raise KeyboardInterrupt
            if skip_check == "s":
                continue

            intent = prompt_intent(cand["intent"])
            escalate = prompt_escalate()
            note = input("Optional note (why you changed the label, edge case, etc.) > ").strip()

            record = {
                "customer_message": cand["customer_message"],
                "historical_reply": cand["historical_reply"],
                "intent": intent,
                "weak_intent": cand["intent"],
                "should_escalate": escalate,
                "note": note,
                "source_tweet_id": cand["source_tweet_id"],
            }

            with open(GOLDEN_EVAL, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            labeled_count += 1

    except KeyboardInterrupt:
        print("\n\nStopped. Progress saved.")

    print(f"\nTotal labeled so far: {labeled_count} -> {GOLDEN_EVAL}")
    if labeled_count < 150:
        print(f"Need at least 150 total (assignment requires 150-250). Run again to continue.")
    else:
        print("You've hit the minimum required (150+). Run again anytime to add more, up to 250.")


if __name__ == "__main__":
    main()