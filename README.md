# Hiver SDE Intern — AppleSupport AI Agent

**Take-home assignment submission**

> Turn a messy real-world customer-support dataset into a working AI system and *prove* it works.

This repo implements an end-to-end AI support agent for **AppleSupport** — chosen as the highest-volume brand in the public [Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter) dataset, and the brand most frequently studied in papers that use this corpus.

The agent, given a customer message:

1. **Classifies** it into an intent taxonomy derived from real AppleSupport reply threads (14 base categories, expanded to a richer human-labeled set during golden-set curation — see below).
2. **Retrieves** similar historical resolutions and **drafts a grounded reply** from them.
3. **Decides** auto-handle vs. escalate-to-human, with an explicit, inspectable reason.

**Stack:** a lightweight Python (FastAPI + scikit-learn) service owns the ML logic; a **Spring Boot** backend exposes it as a typed REST API; a **React** frontend provides an interactive demo.

```
Customer message
       │
       ▼
┌────────────────────┐
│  Intent classifier  │  TF-IDF (1-2 grams) + Logistic Regression, trained on
└─────────┬───────────┘  101,276 REAL (customer_message, historical_reply) pairs
          ▼
┌────────────────────┐
│  Retriever          │  Same TF-IDF space → top-k historical (message, reply) pairs
└─────────┬───────────┘
          ▼
┌────────────────────┐
│  Reply drafter      │  Highest-similarity historical reply + light intent-aware framing
└─────────┬───────────┘
          ▼
┌────────────────────┐
│  Escalation policy  │  Rules (anger / security / hardware) + confidence threshold
└─────────┬───────────┘  (known limitation: keyed off predicted intent — see REPORT.md §4)
          ▼
   { intent, draft_reply, should_escalate, escalation_reason, retrieved_examples }
```

---

## Quick start — reproduce headline results in under 15 minutes

### Prerequisites
- Python 3.10+
- Java 17+ and Maven 3.8+ (a Maven Wrapper is not bundled — install Maven directly, or use Docker, see below)
- Node.js 18+ (only needed for the UI demo, optional for metrics)

### Fast path (recommended — uses real data already included in this repo)

The real, already-extracted training pool (`data/processed/apple_support_conversations.jsonl`, 101,276 real AppleSupport reply pairs) and the hand-labeled golden evaluation set (`data/golden/golden_eval.jsonl`, 151 real examples) ship directly in this repo, so you don't need Kaggle credentials to reproduce the headline numbers.

```bash
cd hiver_sde_intern
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ai-service/requirements.txt

# Train the classifier fresh on the real data (~7 seconds)
python scripts/retrain_from_real_data.py

# Run the evaluation harness against the real, hand-labeled golden set
python scripts/evaluate.py
# → results/metrics.json      (intent accuracy, macro-F1, escalation F1, baselines)
# → results/failures.jsonl    (misclassified examples for failure analysis)
# → results/intent_report.txt (per-class precision/recall)
```

This is the ~7-second training + a few-second evaluation — the whole fast path completes in well under a minute of actual compute, plus dependency install time.

### Full pipeline (optional — rebuilds real data from scratch via Kaggle)

Only needed if you want to regenerate `data/processed/` and `data/golden/candidate_pool.jsonl` from the raw Kaggle corpus yourself, rather than using the already-extracted files above.

```bash
pip install kaggle --break-system-packages
# requires a Kaggle account + API token at ~/.kaggle/kaggle.json — see kaggle.com/settings
kaggle datasets download -d thoughtvector/customer-support-on-twitter
# unzip to data/raw/twcs.csv, then:
python scripts/prepare_real_data.py
```

This extracts real `(customer_message, historical_reply)` pairs from every AppleSupport reply thread in the ~3M-tweet corpus (no full dump is redistributed — only the derived, Apple-specific subsample is committed to this repo, consistent with the assignment's guidance to subsample). Hand-labeling the golden set from the resulting candidate pool is manual and not part of the reproducible pipeline — use `scripts/label_golden.py` (CLI) or `scripts/label_tool.html` (browser-based, faster) if you want to relabel or extend it.

### Start the full stack

**Terminal A — AI service (port 8000)**
```bash
cd ai-service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Terminal B — Spring Boot backend (port 8080)**
```bash
cd backend
mvn spring-boot:run
```

**Terminal C — React UI (port 3000)**
```bash
cd frontend
npm install
npm start
```

Open **http://localhost:3000** and try the example messages, or hit the API directly:

```bash
curl http://localhost:8080/api/v1/health
curl -X POST http://localhost:8080/api/v1/support \
  -H "Content-Type: application/json" \
  -d '{"text": "My iPhone 13 battery is draining insanely fast after the latest update."}'
```

### Alternative: Docker Compose

```bash
docker-compose up --build
```
Brings up all three services together (see `docker-compose.yml`, and each service's `Dockerfile`).

---

## Repository layout

```
├── ai-service/                  # FastAPI + scikit-learn TF-IDF intent classifier + retrieval + escalation logic
│   └── app/main.py              # SupportAgent: classify(), retrieve(), decide_escalation(), draft_reply()
├── backend/                     # Spring Boot 3 API gateway (WebClient → AI service)
│   └── src/.../dto/             # AgentResponse (camelCase, → frontend) / AiServiceResponse (snake_case, ← AI service)
├── frontend/                    # React chat UI + "Last Decision" panel
├── data/
│   ├── processed/               # 101,276 REAL (customer_message, historical_reply) pairs, weak-labeled
│   ├── raw/                     # twcs.csv (only present if you ran the full Kaggle pipeline; not committed)
│   └── golden/
│       ├── candidate_pool.jsonl # 500 real candidates sampled for hand-labeling
│       ├── golden_eval.jsonl    # 151 real, hand-labeled examples (the actual ground truth)
│       └── LABELING_NOTES.md    # sampling method, escalation criteria, known limitations
├── scripts/
│   ├── prepare_real_data.py     # extracts real pairs from twcs.csv (full pipeline only)
│   ├── retrain_from_real_data.py# forces a fresh classifier retrain on the real data
│   ├── label_golden.py          # CLI hand-labeling tool
│   ├── label_tool.html          # browser-based hand-labeling tool (faster)
│   ├── llm_judge.py             # LLM-as-judge + human-agreement harness (built, not yet run to completion — see REPORT.md)
│   ├── generate_data.py         # LEGACY — original fully-synthetic generator, superseded by prepare_real_data.py
│   └── evaluate.py              # automated metrics + baselines + failure logging
├── results/                     # metrics.json, intent_report.txt, failures.jsonl
├── docs/
├── REPORT.md                    # Full write-up: problem framing, results, failure analysis, limitations
├── decision_log.md              # 14 non-obvious design decisions
└── README.md
```

---

## Headline results (151-example real, hand-labeled golden set)

| System                      | Intent Acc | Macro-F1 | Escalation F1 | Reply proxy |
|------------------------------|-----------|----------|----------------|-------------|
| **Our agent**                | 0.728     | 0.174    | 0.000          | 0.408       |
| Trivial baseline (majority)  | 0.411     | —        | 0.000          | —           |
| Simple keyword-rules         | 0.695     | 0.153    | —              | —           |

Full numbers in `results/metrics.json` after running `scripts/evaluate.py`. **These numbers need context to interpret correctly** — see [§ What is misleading about the headline number](#what-is-misleading-about-the-headline-number) below and the full discussion in `REPORT.md` §5. In short: the model barely beats simple keyword rules on accuracy, and the low macro-F1 combined with 0.000 escalation F1 reveals the model is failing completely on several real, important intent categories (`account_lock`, `billing_refund`, `app_store_purchase`, `feature_request`) despite the headline accuracy looking reasonable.

---

## Golden evaluation set

- **Size:** 151 examples (assignment floor is 150) · **Location:** `data/golden/golden_eval.jsonl`
- Sourced from 500 real candidates randomly sampled from ~101,776 real AppleSupport reply pairs extracted from the Kaggle corpus — **not** synthetic, **not** stratified by intent; reflects the real (heavily skewed) distribution of the sample.
- Full labeling methodology, escalation criteria, and known limitations documented in `data/golden/LABELING_NOTES.md`, including:
  - Single labeler, single pass, no inter-rater agreement check (documented as a limitation, not hidden)
  - 14 intents assumed up front, expanded to 32 during labeling as real examples surfaced categories that didn't fit (19 of the 32 appear only once — flagged as needing consolidation in a future pass)
  - Explicit 4-point escalation criteria: money involved, account security, physical hardware, already-escalated customer

---

## Evaluation harness

```bash
python scripts/evaluate.py
```

Produces:
- Intent accuracy, macro-F1, and per-class precision/recall (`results/intent_report.txt`)
- Escalation precision / recall / F1
- A lightweight reply-quality proxy (token overlap + tone-marker presence vs. the historical gold reply)
- Comparison against two baselines: majority-class and keyword-rules
- Misclassified examples logged to `results/failures.jsonl` for failure analysis

**LLM-as-judge status:** `scripts/llm_judge.py` implements a full LLM-as-judge rubric (relevance/helpfulness/tone/groundedness/overall scoring) plus a blind human-rating sample and agreement computation (Pearson correlation, exact-match rate, MAE), built against a free-tier LLM API (Groq). It was **not run to completion** in the time available for this submission — see `REPORT.md` §6 for why this is the top item for "one more week," and `decision_log.md` for why this gap is documented explicitly rather than omitted.

---

## Report

The full write-up lives in **[`REPORT.md`](./REPORT.md)** and covers, per the assignment spec:

1. **Problem framing** — what "good" means for AppleSupport, and what we deliberately did *not* build
2. **System overview** — architecture diagram and component responsibilities
3. **Results vs. two baselines** — table + discussion
4. **Failure analysis** — top 5 failure modes with real examples and hypotheses
5. **What is misleading about the headline number** — mandatory section, see below
6. **What I'd do with one more week**
7. **Decision log summary** (full version in `decision_log.md`)

### What is misleading about the headline number?

(Full version in `REPORT.md` §5 — short version:)

- **72.8% accuracy barely beats a keyword-rules baseline (69.5%)** — most of the model's apparent skill is just correctly handling the 3 dominant classes that simple string matching already catches.
- **Macro-F1 (0.174) tells a very different story than accuracy (0.728).** The model scores 0.000 F1 on `account_lock`, `billing_refund`, `app_store_purchase`, and `feature_request` — real, trainable classes it simply fails on, hidden by accuracy's bias toward large classes.
- **Escalation F1 is 0.000** — invisible if you only look at intent accuracy, but this is arguably the most safety-critical part of the whole system.
- **~15% of the golden set uses intents outside the classifier's trainable label space** (added during human labeling but never fed back into training), mechanically capping accuracy regardless of model quality.
- **The reply-quality proxy (0.408) is a weak lexical heuristic**, not a validated measure of helpfulness — the LLM-as-judge that would make this credible wasn't completed (see above).

---

## Design choices (short version — see `decision_log.md` for all 14)

- **Brand:** AppleSupport — highest volume + richest public literature in the source dataset.
- **Data:** switched mid-project from a fully-synthetic generator to real extracted tweet pairs, after recognizing a synthetic golden set can't survive being asked to explain how it was built.
- **Model:** TF-IDF + Logistic Regression, chosen for speed, full offline reproducibility, and zero external API dependency during evaluation — not for maximum possible accuracy. Retrains on 101,276 real examples in ~7 seconds.
- **Retrieval:** same TF-IDF space as classification, keeping similarity scores interpretable without a second embedding model.
- **Escalation:** hybrid rules + classifier confidence, deliberately biased toward escalating when uncertain — but currently keyed off the *predicted* intent, which causes a documented compounding-failure mode when the classifier misclassifies a minority class (see REPORT.md §4, finding #1).

---

## Known issues found & fixed during development

Documented here for transparency since they weren't obvious from the code alone:

1. **Windows `UnicodeDecodeError` on real tweet data.** Real tweets contain emoji, curly quotes, and other non-ASCII characters; opening files without `encoding="utf-8"` falls back to Windows' `cp1252` codec and crashes. Fixed in `ai-service/app/main.py` and `scripts/evaluate.py` by adding explicit `encoding="utf-8"` to every file open.
2. **Golden-set field mismatch.** `scripts/evaluate.py` originally expected an `id` field on golden examples; the real, hand-labeled golden set uses `source_tweet_id` instead. Fixed.
3. **Stale cached model after switching to real data.** `SupportAgent._load_or_train()` only retrains if `ai-service/models/*.joblib` is missing — after regenerating `data/processed/`, you must delete the cached model files (or run `scripts/retrain_from_real_data.py`, which does this for you) or the service will silently keep serving the old model.
4. **Escalation policy missed a hardware case.** Smoke-testing surfaced that a cracked-screen message (classified correctly as `screen_issue`) did not escalate, since the original rule only checked `hardware_failure`/`account_lock`. Patched by adding `screen_issue` to the confidence-based escalation rule — see `decision_log.md` item 6 for the accepted trade-off (slight over-escalation of software-only touch bugs).
5. **No bundled Maven Wrapper.** `backend/` ships `pom.xml` but no `mvnw`/`mvnw.cmd`. Install Maven 3.8+ directly, or use `docker-compose up` to avoid a local Maven install entirely.
6. **Backend DTO field-naming mismatch** (carried over from initial integration testing) — the Python AI service returns snake_case JSON (`intent_confidence`, `escalation_reason`, ...); the original `AgentResponse` Java DTO used camelCase with no naming-strategy annotation, so Jackson silently defaulted confidence/reason/retrieved-examples while `intent` (no underscore) happened to still match. Fixed via two DTOs: `AiServiceResponse` (snake_case, deserializes the AI service) and `AgentResponse` (camelCase, serves the frontend), with explicit mapping in `AgentController`.

---

## Citation / data provenance

- Data source: [Customer Support on Twitter (Kaggle)](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter), licensed CC-BY-NC-SA-4.0.
- This repo commits only a **derived, Apple-specific subsample** (101,276 real reply pairs out of ~3M total tweets in the corpus) — not the full raw dataset — consistent with the assignment's explicit guidance that a subsample is expected and encouraged.

## What we deliberately did not build

- Full multi-turn dialogue state tracking
- Fine-tuned LLM generation (cost / reproducibility trade-off for a take-home)
- Real-time Twitter streaming ingestion
- Production-grade auth, rate-limiting, or observability beyond basic health checks
- A completed LLM-as-judge run with human-agreement evidence (built, not finished — see `REPORT.md` §6)

See `REPORT.md` §1 for the reasoning behind each.