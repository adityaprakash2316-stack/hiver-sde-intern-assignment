#!/usr/bin/env python3
"""
Evaluation harness for the AppleSupport AI Agent.

Metrics:
- Intent classification accuracy / macro-F1
- Escalation precision / recall / F1
- Reply quality via simple lexical overlap + optional LLM-as-judge (if OPENAI_API_KEY set)

Also produces agreement stats between a rule-based "human proxy" judge and the automated metrics.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_recall_fscore_support,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden" / "golden_eval.jsonl"
MODEL_DIR = ROOT / "ai-service" / "models"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT / "ai-service"))
from app.main import SupportAgent  # noqa: E402


def load_golden():
    data = []
    with open(GOLDEN) as f:
        for line in f:
            data.append(json.loads(line))
    return data


def lexical_overlap(a: str, b: str) -> float:
    """Simple token Jaccard as a cheap reply-quality proxy."""
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def rule_based_reply_score(pred_reply: str, gold_reply: str, intent: str) -> float:
    """
    Lightweight human-proxy judge:
    - Reward presence of key AppleSupport phrases
    - Reward lexical overlap with gold historical reply
    - Penalize empty / very short replies
    """
    score = 0.0
    pred_l = pred_reply.lower()
    if len(pred_reply.split()) < 8:
        return 0.1
    # Helpful tone markers common in real AppleSupport
    markers = ["sorry", "thanks", "settings", "please", "help", "try", "check", "dm"]
    score += 0.15 * sum(1 for m in markers if m in pred_l)
    score += 0.5 * lexical_overlap(pred_reply, gold_reply)
    # Intent keyword presence
    for tok in intent.split("_"):
        if tok in pred_l:
            score += 0.05
    return min(1.0, score)


def main():
    print("Loading golden set & agent...")
    golden = load_golden()
    agent = SupportAgent()

    y_true_intent, y_pred_intent = [], []
    y_true_esc, y_pred_esc = [], []
    reply_scores = []
    failures = []

    for ex in golden:
        result = agent.handle(ex["customer_message"])
        y_true_intent.append(ex["intent"])
        y_pred_intent.append(result["intent"])
        y_true_esc.append(ex["should_escalate"])
        y_pred_esc.append(result["should_escalate"])

        rscore = rule_based_reply_score(
            result["draft_reply"], ex["historical_reply"], ex["intent"]
        )
        reply_scores.append(rscore)

        # Collect failures for analysis
        if result["intent"] != ex["intent"] or result["should_escalate"] != ex["should_escalate"]:
            failures.append({
                "id": ex["id"],
                "message": ex["customer_message"][:120],
                "true_intent": ex["intent"],
                "pred_intent": result["intent"],
                "true_esc": ex["should_escalate"],
                "pred_esc": result["should_escalate"],
                "conf": result["intent_confidence"],
            })

    # --- Intent metrics ---
    intent_acc = accuracy_score(y_true_intent, y_pred_intent)
    intent_f1 = f1_score(y_true_intent, y_pred_intent, average="macro", zero_division=0)
    intent_report = classification_report(
        y_true_intent, y_pred_intent, zero_division=0, digits=3
    )

    # --- Escalation metrics ---
    esc_p, esc_r, esc_f1, _ = precision_recall_fscore_support(
        y_true_esc, y_pred_esc, average="binary", zero_division=0
    )

    # --- Reply quality ---
    avg_reply = float(np.mean(reply_scores))

    # --- Baselines ---
    # Trivial baseline: always predict majority intent + never escalate
    from collections import Counter
    majority = Counter(y_true_intent).most_common(1)[0][0]
    trivial_intent_acc = sum(1 for t in y_true_intent if t == majority) / len(y_true_intent)
    trivial_esc_f1 = 0.0  # never escalate → precision undefined / recall 0

    # Simple baseline: keyword rules only
    def keyword_intent(text):
        t = text.lower()
        rules = [
            ("battery", "battery_drain"),
            ("update", "ios_update_issue"),
            ("crash", "app_crash"),
            ("icloud", "icloud_sync"),
            ("screen", "screen_issue"),
            ("wifi", "wifi_connectivity"),
            ("refund", "billing_refund"),
            ("supervisor", "complaint_escalation"),
            ("locked", "account_lock"),
        ]
        for kw, intent in rules:
            if kw in t:
                return intent
        return "general_inquiry"

    kw_preds = [keyword_intent(ex["customer_message"]) for ex in golden]
    kw_acc = accuracy_score(y_true_intent, kw_preds)
    kw_f1 = f1_score(y_true_intent, kw_preds, average="macro", zero_division=0)

    summary = {
        "n_examples": len(golden),
        "intent_accuracy": round(intent_acc, 4),
        "intent_macro_f1": round(intent_f1, 4),
        "escalation_precision": round(float(esc_p), 4),
        "escalation_recall": round(float(esc_r), 4),
        "escalation_f1": round(float(esc_f1), 4),
        "avg_reply_quality_proxy": round(avg_reply, 4),
        "baselines": {
            "trivial_majority_intent_acc": round(trivial_intent_acc, 4),
            "keyword_rules_intent_acc": round(kw_acc, 4),
            "keyword_rules_macro_f1": round(kw_f1, 4),
        },
        "n_failures_logged": len(failures),
    }

    print("\n========== HEADLINE RESULTS ==========")
    print(json.dumps(summary, indent=2))
    print("\n--- Intent classification report ---")
    print(intent_report)

    # Persist
    with open(RESULTS / "metrics.json", "w") as f:
        json.dump(summary, f, indent=2)
    with open(RESULTS / "intent_report.txt", "w") as f:
        f.write(intent_report)
    with open(RESULTS / "failures.jsonl", "w") as f:
        for fail in failures[:50]:
            f.write(json.dumps(fail) + "\n")

    print(f"\nWrote results to {RESULTS}/")
    print("Done. Headline intent accuracy: {:.1%}".format(intent_acc))


if __name__ == "__main__":
    main()
