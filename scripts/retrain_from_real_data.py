#!/usr/bin/env python3
"""
Force the SupportAgent's TF-IDF + LogisticRegression pipeline to retrain from
the REAL weakly-labeled data (data/processed/apple_support_conversations.jsonl)
instead of loading the stale cached model trained on synthetic data.

Usage:
    python scripts/retrain_from_real_data.py

What it does:
    1. Deletes ai-service/models/intent_pipeline.joblib and historical.json
       if they exist (these are the cache that SupportAgent._load_or_train
       checks first — without deleting them, it will silently keep serving
       the old synthetic-trained model).
    2. Imports SupportAgent, which triggers a fresh train because the cache
       is now gone.
    3. Prints basic sanity info: how many examples it trained on, per-intent
       counts, and how long training took.
"""

import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "ai-service" / "models"
MODEL_PATH = MODEL_DIR / "intent_pipeline.joblib"
HIST_PATH = MODEL_DIR / "historical.json"

sys.path.insert(0, str(ROOT / "ai-service"))


def main():
    for p in (MODEL_PATH, HIST_PATH):
        if p.exists():
            print(f"Deleting stale cached file: {p}")
            p.unlink()

    from app.main import SupportAgent  # import after cache deletion

    print("\nTraining fresh classifier on real data (this may take ~30-90s for ~100k examples)...")
    t0 = time.time()
    agent = SupportAgent()
    elapsed = time.time() - t0

    labels = [h["intent"] for h in agent.historical]
    counts = Counter(labels)

    print(f"\nDone in {elapsed:.1f}s")
    print(f"Trained on {len(agent.historical)} real (customer_message, historical_reply) pairs")
    print("\nWeak-label intent distribution in training data:")
    for intent, n in counts.most_common():
        print(f"  {intent:25s} {n:6d}")

    # Quick smoke test on a couple of made-up-but-plausible inputs
    print("\n--- Smoke test ---")
    for msg in [
        "My battery drains so fast since the update, please help",
        "Someone hacked my apple id and I can't log in",
        "The screen on my iphone is completely cracked after i dropped it",
    ]:
        result = agent.handle(msg)
        print(f"\n  IN:  {msg}")
        print(f"  intent={result['intent']} (conf={result['intent_confidence']:.2f})  escalate={result['should_escalate']}")
        print(f"  reason: {result['escalation_reason']}")


if __name__ == "__main__":
    main()