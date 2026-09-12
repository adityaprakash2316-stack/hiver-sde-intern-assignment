# Golden Evaluation Set — Labeling Notes

## Sampling

- Source: real AppleSupport reply pairs extracted from the Kaggle "Customer
  Support on Twitter" corpus (`thoughtvector/customer-support-on-twitter`,
  ~3M tweets). Extraction logic: every tweet authored by `AppleSupport` that
  is a reply (`inbound == False`) was matched back to the customer tweet it
  replied to (`inbound == True`), producing real
  `(customer_message, historical_reply)` pairs. See `scripts/prepare_real_data.py`.
- From the resulting ~101,776 real pairs, 500 were randomly sampled
  (`random.seed(42)`) into a candidate pool (`data/golden/candidate_pool.jsonl`)
  for hand-labeling, with the remainder (101,276) used as the classifier's
  training/retrieval pool.
- Of the 500 candidates, 151 were hand-labeled into the final golden set
  (`data/golden/golden_eval.jsonl`), meeting the assignment's 150-250 floor.
  The remaining candidates were not labeled due to time constraints; this
  golden set should be read as an initial/prototype pass, not an exhaustive one.

## Labeling process

- Each candidate started with a "weak label" intent guess produced by a
  keyword heuristic (see `INTENT_KEYWORDS` in `prepare_real_data.py`), used
  only as a starting suggestion — the final `intent` field in the golden set
  reflects the human-assigned label, which frequently overrode the weak guess.
- Labeling was done with a purpose-built tool (`scripts/label_golden.py` for
  CLI, `scripts/label_tool.html` for a faster click/keyboard browser version)
  that shows the real customer message + AppleSupport's real historical reply
  side by side.
- 14 intents were assumed up front (mirroring common AppleSupport issue
  types). During labeling, additional intents were introduced when a real
  example didn't fit any existing category (e.g. `accessibility_issue`,
  `keyboard_input_bug`, `software_bug`). By the end, 32 distinct intent labels
  were in use, though most (19) appear only once — a sign this taxonomy needs
  further consolidation in a future pass rather than a settled final list.

## Escalation criteria

A message was labeled `should_escalate: true` if any of the following applied:

1. **Money is involved** — refund requests, disputed/duplicate charges,
   subscription billing issues.
2. **Account security/access** — locked out, compromised account, 2FA
   problems, can't sign in.
3. **Physical hardware failure** — cracked screen, dead device, broken
   button, device won't charge/turn on.
4. **Customer is already escalated/angry** — explicit mentions of a manager,
   legal action, or repeated/compounding complaints about the same issue.

Everything else (routine troubleshooting — battery, performance, wifi, app
crashes, general how-to questions, feature requests) was labeled
`should_escalate: false`, on the reasoning that AppleSupport's own real reply
in these cases was almost always a generic scripted troubleshooting step or
a request for more detail via DM — i.e., evidence that the brand itself
handled these at a triage/auto level in practice.

## Known limitations of this golden set

- **Single labeler, single pass, no inter-rater check.** All 151 labels were
  made by one person in one sitting; there's no second-rater agreement
  measurement, so labeling consistency is self-reported, not verified.
- **Intent taxonomy is broader than the classifier's trainable label space.**
  The intent classifier is trained only on the 14 keyword-derived weak-label
  categories from `prepare_real_data.py`. 22 of the 151 golden examples use
  one of the 18 additional human-introduced intents, which the classifier
  cannot predict by construction — this mechanically caps intent-accuracy
  and macro-F1 regardless of model quality (see REPORT.md's "misleading
  headline number" section for the resulting numbers).
- **Escalation labels were not cross-checked against the historical reply's
  actual outcome** (e.g. whether AppleSupport actually looped in a human) —
  the criteria above are a reasonable proxy, but the ground truth reflects
  the labeler's judgment, not verified brand behavior.