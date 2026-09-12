#!/usr/bin/env python3
"""
Build a REAL AppleSupport conversation dataset from the Kaggle
"Customer Support on Twitter" corpus (thoughtvector/customer-support-on-twitter).

This replaces the fully-synthetic scripts/generate_data.py pipeline with one that
uses actual customer messages and actual AppleSupport replies, subsampled from
the ~3M-tweet dump (a subsample is explicitly expected by the assignment).

Usage:
    python scripts/prepare_real_data.py

Requires:
    data/raw/twcs.csv   (downloaded via: kaggle datasets download -d thoughtvector/customer-support-on-twitter)

Outputs:
    data/processed/apple_support_conversations.jsonl   (weakly-labeled training pool)
    data/golden/candidate_pool.jsonl                    (larger pool for YOU to hand-label 150-250 from)
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "twcs.csv"
OUT_PROCESSED = ROOT / "data" / "processed" / "apple_support_conversations.jsonl"
OUT_CANDIDATE_POOL = ROOT / "data" / "golden" / "candidate_pool.jsonl"

BRAND_HANDLE = "AppleSupport"

# ---------------------------------------------------------------------------
# Same 14-intent taxonomy as before, now used as WEAK LABELS via keyword
# matching over REAL text (bootstrap only — golden set must be hand-verified).
# ---------------------------------------------------------------------------
INTENT_KEYWORDS = {
    "battery_drain": ["battery", "drain", "charge", "charging", "dies fast", "dead by"],
    "ios_update_issue": ["update", "ios 1", "ios update", "software update", "installing"],
    "app_crash": ["crash", "crashing", "freeze", "freezing", "force close"],
    "icloud_sync": ["icloud", "sync", "syncing", "backup", "photos not"],
    "hardware_failure": ["screen crack", "speaker", "camera broken", "button stuck", "won't turn on", "hardware"],
    "account_lock": ["locked out", "apple id", "2fa", "two-factor", "can't sign in", "password reset"],
    "billing_refund": ["refund", "charged", "billing", "subscription", "unauthorized charge"],
    "app_store_purchase": ["app store", "purchase failed", "can't download", "in-app purchase"],
    "wifi_connectivity": ["wifi", "wi-fi", "cellular", "no signal", "can't connect"],
    "performance_lag": ["slow", "lag", "laggy", "overheating", "sluggish"],
    "screen_issue": ["screen", "display", "touch not working", "unresponsive", "burn-in"],
    "feature_request": ["please add", "feature request", "wish you", "would be nice if"],
    "general_inquiry": ["how do i", "how to", "question about", "does anyone know"],
    "complaint_escalation": ["manager", "lawsuit", "legal", "worst support", "never buying", "escalate"],
}


def clean_text(t: str) -> str:
    t = re.sub(r"@\w+", "", t)          # strip @mentions
    t = re.sub(r"http\S+", "", t)       # strip URLs
    t = re.sub(r"\s+", " ", t).strip()
    return t


def weak_label(text: str) -> str:
    text_l = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(k in text_l for k in keywords):
            return intent
    return "general_inquiry"  # fallback bucket


def main():
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"{RAW_CSV} not found. Download it first:\n"
            f"  kaggle datasets download -d thoughtvector/customer-support-on-twitter\n"
            f"  Expand-Archive customer-support-on-twitter.zip -DestinationPath data\\raw"
        )

    print("Loading twcs.csv (this file is large, may take ~30-60s)...")
    df = pd.read_csv(RAW_CSV, dtype=str)

    # Index tweets by id for fast lookup
    tweets_by_id = df.set_index("tweet_id", drop=False)

    # AppleSupport's own outbound replies
    apple_replies = df[(df["author_id"] == BRAND_HANDLE) & (df["inbound"] == "False")]
    print(f"Found {len(apple_replies)} raw AppleSupport reply tweets.")

    pairs = []
    for _, reply_row in apple_replies.iterrows():
        in_response_to = reply_row.get("in_response_to_tweet_id")
        if pd.isna(in_response_to):
            continue
        try:
            customer_row = tweets_by_id.loc[str(int(float(in_response_to)))]
        except (KeyError, ValueError):
            continue
        if isinstance(customer_row, pd.DataFrame):  # duplicate ids, take first
            customer_row = customer_row.iloc[0]
        if str(customer_row.get("inbound")) != "True":
            continue

        customer_msg = clean_text(str(customer_row["text"]))
        reply_msg = clean_text(str(reply_row["text"]))
        if len(customer_msg) < 15 or len(reply_msg) < 10:
            continue

        pairs.append({
            "customer_message": customer_msg,
            "historical_reply": reply_msg,
            "intent": weak_label(customer_msg),
            "source_tweet_id": str(customer_row["tweet_id"]),
        })

    print(f"Built {len(pairs)} real (customer_message, historical_reply) pairs.")

    # Split: most goes to the training/retrieval pool, a larger slice becomes
    # the candidate pool for YOU to manually review and hand-label 150-250
    # examples from (per the assignment's "hand-labelled" requirement).
    import random
    random.seed(42)
    random.shuffle(pairs)

    candidate_pool_size = min(500, max(300, len(pairs) // 10))
    candidate_pool = pairs[:candidate_pool_size]
    training_pool = pairs[candidate_pool_size:]

    OUT_PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PROCESSED, "w", encoding="utf-8") as f:
        for p in training_pool:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    OUT_CANDIDATE_POOL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CANDIDATE_POOL, "w", encoding="utf-8") as f:
        for p in candidate_pool:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(training_pool)} examples -> {OUT_PROCESSED}")
    print(f"Wrote {len(candidate_pool)} candidates -> {OUT_CANDIDATE_POOL}")
    print(
        "\nNEXT STEP (manual, required by the assignment):\n"
        f"  Open {OUT_CANDIDATE_POOL.relative_to(ROOT)} and hand-pick/relabel 150-250\n"
        "  examples into data/golden/golden_eval.jsonl, correcting the weak 'intent'\n"
        "  label where the keyword heuristic got it wrong, and adding a 'should_escalate'\n"
        "  boolean based on your own judgment. Document your process in\n"
        "  data/golden/LABELING_NOTES.md (this is required, not optional)."
    )


if __name__ == "__main__":
    main()