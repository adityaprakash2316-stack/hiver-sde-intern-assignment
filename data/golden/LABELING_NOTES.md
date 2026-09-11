# Golden Evaluation Set Notes

- Size: 200 examples
- Sampling: Stratified across 14 intents (~12 each) + additional edge/ambiguous cases
- Labeling process:
  1. Started from real AppleSupport patterns observed in the Kaggle dataset and public papers.
  2. Manually wrote / curated customer messages to cover typical phrasings, frustration levels, and edge cases.
  3. Assigned ground-truth intent from the taxonomy we defined from the data.
  4. Chose historical-style replies that match real AppleSupport tone (helpful, stepwise, escalate when needed).
  5. Escalation labels decided by rules + human judgment: security/account, hardware service, repeated frustration, explicit escalation requests → escalate; clear self-serve paths → auto-handle.
- Inter-annotator: Single primary labeler (assignment constraint). Ambiguous cases resolved toward "escalate" for safety.
