"""
AppleSupport AI Agent Service
- Intent classification (TF-IDF + Logistic Regression, lightweight & fast)
- Reply drafting via retrieval of similar historical resolutions
- Escalation decision with explicit reason
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "apple_support_conversations.jsonl"
MODEL_DIR = ROOT / "ai-service" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

INTENTS = [
    "battery_drain", "ios_update_issue", "app_crash", "icloud_sync",
    "hardware_failure", "account_lock", "billing_refund", "app_store_purchase",
    "wifi_connectivity", "performance_lag", "screen_issue", "feature_request",
    "general_inquiry", "complaint_escalation",
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
class MessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    conversation_history: Optional[List[str]] = None


class AgentResponse(BaseModel):
    intent: str
    intent_confidence: float
    draft_reply: str
    should_escalate: bool
    escalation_reason: str
    retrieved_examples: List[dict]
    model_version: str = "v1.0-tfidf-retrieval"


class HealthResponse(BaseModel):
    status: str
    n_historical: int
    intents: List[str]


# ---------------------------------------------------------------------------
# Core Agent
# ---------------------------------------------------------------------------
class SupportAgent:
    def __init__(self):
        self.historical: List[dict] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.clf: Optional[LogisticRegression] = None
        self.tfidf_matrix = None
        self._load_or_train()

    def _load_data(self) -> List[dict]:
        if not DATA_PATH.exists():
            raise FileNotFoundError(
                f"Historical data not found at {DATA_PATH}. "
                "Run: python scripts/generate_data.py"
            )
        data = []
        with open(DATA_PATH) as f:
            for line in f:
                data.append(json.loads(line))
        return data

    def _load_or_train(self):
        model_path = MODEL_DIR / "intent_pipeline.joblib"
        hist_path = MODEL_DIR / "historical.json"

        if model_path.exists() and hist_path.exists():
            pipe = joblib.load(model_path)
            self.vectorizer = pipe.named_steps["tfidf"]
            self.clf = pipe.named_steps["clf"]
            with open(hist_path) as f:
                self.historical = json.load(f)
            self.tfidf_matrix = self.vectorizer.transform(
                [h["customer_message"] for h in self.historical]
            )
            print(f"Loaded model + {len(self.historical)} historical examples")
            return

        print("Training intent classifier from historical data...")
        self.historical = self._load_data()
        texts = [h["customer_message"] for h in self.historical]
        labels = [h["intent"] for h in self.historical]

        self.vectorizer = TfidfVectorizer(
            max_features=8000,
            ngram_range=(1, 2),
            stop_words="english",
            min_df=2,
        )
        X = self.vectorizer.fit_transform(texts)
        self.clf = LogisticRegression(max_iter=500, C=2.0, class_weight="balanced")
        self.clf.fit(X, labels)
        self.tfidf_matrix = X

        pipe = Pipeline([("tfidf", self.vectorizer), ("clf", self.clf)])
        joblib.dump(pipe, model_path)
        with open(hist_path, "w") as f:
            json.dump(self.historical, f)
        print(f"Trained & saved model on {len(self.historical)} examples")

    def classify(self, text: str) -> tuple[str, float]:
        X = self.vectorizer.transform([text])
        proba = self.clf.predict_proba(X)[0]
        idx = int(np.argmax(proba))
        return self.clf.classes_[idx], float(proba[idx])

    def retrieve(self, text: str, k: int = 3) -> List[dict]:
        q = self.vectorizer.transform([text])
        sims = cosine_similarity(q, self.tfidf_matrix).flatten()
        top_idx = np.argsort(sims)[::-1][:k]
        results = []
        for i in top_idx:
            h = self.historical[i].copy()
            h["similarity"] = float(sims[i])
            results.append(h)
        return results

    def decide_escalation(self, text: str, intent: str, confidence: float) -> tuple[bool, str]:
        text_l = text.lower()

        # Hard rules first (safety)
        angry_keywords = [
            "supervisor", "manager", "legal", "lawsuit", "attorney",
            "useless", "incompetent", "scam", "fraud", "never buying",
            "4th time", "third time", "weeks now", "going in circles",
            "consumer protection", "better business bureau", "bbb",
        ]
        if any(k in text_l for k in angry_keywords):
            return True, "Strong negative sentiment or explicit request for human escalation detected"

        if intent == "complaint_escalation":
            return True, "Message classified as complaint requiring human escalation"

        if intent in ("hardware_failure", "account_lock") and confidence > 0.55:
            return True, f"Intent '{intent}' typically requires human verification or physical service"

        if confidence < 0.40:
            return True, f"Low classifier confidence ({confidence:.2f}); safer to escalate"

        # Billing with refund language
        if intent == "billing_refund" and any(w in text_l for w in ["refund", "charged twice", "unauthorized"]):
            # Still auto-handleable via reportaproblem, but flag borderline
            return False, "Billing issue with clear self-serve refund path (reportaproblem.apple.com)"

        return False, "Standard resolvable issue with historical precedent; safe for auto-reply"

    def draft_reply(self, text: str, intent: str, retrieved: List[dict]) -> str:
        if not retrieved:
            return (
                "Thanks for reaching out to Apple Support. "
                "Could you please share a bit more detail about the issue "
                "(device model, iOS version, and exact steps that lead to the problem)?"
            )

        # Use the highest-similarity historical reply as base, lightly adapt
        best = retrieved[0]
        base = best["historical_reply"]

        # Simple personalization / grounding
        prefix = "Hi there, thanks for contacting Apple Support. "
        if best["similarity"] > 0.35:
            return prefix + base
        else:
            # Lower similarity → more generic but still intent-aware
            return (
                prefix
                + f"I understand you're experiencing an issue related to {intent.replace('_', ' ')}. "
                + base
            )

    def handle(self, text: str) -> dict:
        intent, conf = self.classify(text)
        retrieved = self.retrieve(text, k=3)
        escalate, reason = self.decide_escalation(text, intent, conf)
        reply = self.draft_reply(text, intent, retrieved)

        return {
            "intent": intent,
            "intent_confidence": round(conf, 4),
            "draft_reply": reply,
            "should_escalate": escalate,
            "escalation_reason": reason,
            "retrieved_examples": [
                {
                    "customer_message": r["customer_message"][:180] + ("..." if len(r["customer_message"]) > 180 else ""),
                    "historical_reply": r["historical_reply"][:220] + ("..." if len(r["historical_reply"]) > 220 else ""),
                    "similarity": round(r["similarity"], 3),
                    "intent": r["intent"],
                }
                for r in retrieved
            ],
        }


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Hiver AppleSupport AI Agent",
    description="Intent classification + grounded reply drafting + escalation decision",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent: Optional[SupportAgent] = None


@app.on_event("startup")
def startup():
    global agent
    agent = SupportAgent()


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        n_historical=len(agent.historical) if agent else 0,
        intents=INTENTS,
    )


@app.post("/v1/agent/handle", response_model=AgentResponse)
def handle_message(req: MessageRequest):
    if agent is None:
        raise HTTPException(503, "Agent not ready")
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Empty message")
    result = agent.handle(text)
    return AgentResponse(**result)


@app.get("/v1/intents")
def list_intents():
    return {"intents": INTENTS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
