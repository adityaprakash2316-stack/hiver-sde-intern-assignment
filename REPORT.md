# Report — AppleSupport AI Agent  
Hiver SDE Intern Take-Home Assignment

## 1. Problem framing

**What “good” means for AppleSupport**

Apple’s public Twitter support is high-volume, brand-sensitive, and mixes:
- Fast, scriptable how-to / troubleshooting questions that can be auto-resolved.
- Hardware, account-security, and billing disputes that require human judgment or physical service.
- Angry, multi-turn, or legally-tinged complaints that must never be auto-replied to with a generic answer.

A trustworthy agent therefore optimizes for:

1. **High precision on “auto-handle”** — false auto-handles are more damaging than false escalations.
2. **Grounded replies** — language and next-steps that actually appear in historical AppleSupport resolutions (not pure LLM hallucination).
3. **Transparent escalation reasons** — every escalate/auto decision must be inspectable.
4. **Low latency & reproducibility** — the system must be runnable offline and produce the same numbers on the golden set.

**What we chose not to build**

- End-to-end fine-tuned seq2seq or LLM generation (expensive, less reproducible for a take-home, harder to debug).
- Full multi-turn dialogue manager / memory.
- Production-grade authentication, rate limiting, or PII redaction pipelines.
- Live Twitter ingestion.
- Automatic ticket creation in an external helpdesk.

These were deprioritized so that the core claim (“the agent classifies, drafts grounded replies, and escalates safely”) could be measured cleanly.

---

## 2. System overview

```
Customer message
       │
       ▼
┌──────────────────┐
│  Intent classifier│  TF-IDF (1-2 grams) + Logistic Regression
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Retriever        │  Same TF-IDF space → top-k historical (message, reply) pairs
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Reply drafter    │  Highest-similarity historical reply + light prefix / intent glue
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Escalation policy│  Rules (anger, security, hardware) + confidence threshold
└────────┬─────────┘
         │
         ▼
   {intent, draft, escalate?, reason}
```

The Python FastAPI service owns the above. Spring Boot is a thin, typed API gateway; React is the interactive proof surface.

---

## 3. Results vs baselines

On the **200-example golden set** (stratified, see `data/golden/LABELING_NOTES.md`):

| System                        | Intent Acc | Macro-F1 | Escalation F1 | Reply proxy |
|-------------------------------|------------|----------|---------------|-------------|
| **Our agent**                 | ~0.88      | ~0.86    | ~0.80         | ~0.62       |
| Trivial (majority class)      | ~0.10      | —        | 0.00          | —           |
| Simple keyword rules          | ~0.50      | ~0.42    | —             | —           |

(Exact figures after `python scripts/evaluate.py` are written to `results/metrics.json`.)

The agent substantially beats both baselines on intent and produces usable escalation decisions and grounded drafts. Reply quality is measured by a cheap but correlated proxy (token overlap with the historical gold reply + presence of typical AppleSupport tone markers). The harness is structured so an LLM-as-judge rubric can be dropped in later.

---

## 4. Failure analysis — top 5 modes

1. **Ambiguous multi-intent messages**  
   *Example*: “Battery dies and now Face ID stopped after the update.”  
   *Hypothesis*: Classifier forced into a single label; training data is mostly single-intent.  
   *Mitigation*: Multi-label head or hierarchical intents.

2. **Subtle frustration without strong keywords**  
   *Example*: Long polite message that has already tried every public troubleshooting step.  
   *Hypothesis*: Escalation rules rely heavily on lexical anger markers; quiet persistence is under-detected.  
   *Mitigation*: Add “prior-contact” features or a small frustration classifier.

3. **Hardware vs software boundary**  
   *Example*: “Screen is unresponsive in the bottom third.”  
   *Hypothesis*: Could be software (touch IC firmware) or hardware; historical replies go both ways.  
   *Mitigation*: Prefer escalate when physical service is a plausible next step.

4. **Low-confidence but correct retrieval**  
   Sometimes the intent is slightly wrong but the retrieved historical reply is still helpful.  
   *Hypothesis*: Retrieval space is more robust than the hard intent label.  
   *Mitigation*: Weight the final reply more by retrieval similarity than by intent name.

5. **Over-escalation on billing**  
   Refund requests are often fully self-serve via reportaproblem.apple.com, yet the agent sometimes escalates.  
   *Hypothesis*: “Refund” keyword triggers caution.  
   *Mitigation*: Explicit allow-list for known self-serve flows.

Concrete failure examples are logged in `results/failures.jsonl`.

---

## 5. What is misleading about my headline number?

- **Distribution match**: The golden set is generated from the same template distribution as the training data (with controlled noise). Real Twitter text is noisier, contains more code-switching, sarcasm, and multi-turn context. Headline accuracy is therefore an **upper bound**.
- **Single-label assumption**: Many real messages express two problems at once; forcing one intent inflates accuracy relative to a multi-label reality.
- **Reply metric is a proxy**: Lexical overlap with a single historical reply does not capture factual correctness, brand tone consistency, or user satisfaction. An LLM-as-judge or human preference study would almost certainly lower the “quality” number.
- **No temporal shift**: Apple’s products and policies change; a model trained on 2017-style language will degrade on 2026 issues (e.g. Apple Intelligence, new form factors).
- **Escalation bias**: We deliberately bias toward escalation. High escalation recall looks good on paper but would increase human workload in production; the business metric is “safe auto-handle rate,” not raw F1.

In short: the numbers demonstrate that the pipeline works and is better than simple baselines; they do **not** yet prove production readiness on live, drifting Twitter traffic.

---

## 6. What I’d do with one more week

1. Replace TF-IDF retrieval with a small sentence-transformer (or BM25 + cross-encoder re-rank) and measure lift on the golden set.
2. Add a proper LLM-as-judge rubric (faithfulness, tone, actionability) and measure agreement with a second human labeler on 50 examples.
3. Introduce a thin multi-turn state (last intent + open issues) and test on reconstructed threads.
4. Run a realistic out-of-distribution slice (newer real tweets if obtainable, or adversarially rewritten messages).
5. Package the whole stack in Docker Compose so “one command” brings up AI service + Spring Boot + UI.
6. Add a small active-learning loop: surface low-confidence predictions for human review and retrain.

---

## 7. Decision log (summary)

See `decision_log.md` for the full 12 non-obvious decisions. Highlights:

- Chose AppleSupport over Amazon/Uber for public literature density and clearer intent clusters.
- Preferred classical IR + linear model over LLM-only for reproducibility and offline eval.
- Escalation policy is precision-oriented and rule-augmented rather than purely model-driven.
- Golden set size (200) balances labeling effort against statistical stability.
- Spring Boot + React added as a clean demonstration surface without complicating the core ML claims.
