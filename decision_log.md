# Decision Log

Non-obvious decisions made while building the AppleSupport AI Agent (10–15 items).

1. **Brand selection = AppleSupport**
   Highest volume in the public Kaggle dataset and the brand most frequently studied in academic papers that use this corpus. Clearer, more stable intent clusters than pure retail or ride-sharing.

2. **Switched from a fully-synthetic data generator to real extracted tweet pairs**
   The initial pipeline (`scripts/generate_data.py`) produced fabricated customer messages and templated replies. This was replaced with `scripts/prepare_real_data.py`, which extracts genuine `(customer_message, historical_reply)` pairs directly from the real AppleSupport reply threads in the Kaggle corpus (~101,776 real pairs found). Chosen over the synthetic approach because a fabricated golden set can't survive being asked to explain how it was built, and real data surfaces real failure modes that synthetic data hides.

3. **14-intent taxonomy induced bottom-up, later expanded during labeling**
   Started from frequent complaint themes in AppleSupport literature and the sample data (battery, iOS update, hardware, account lock, billing, etc.). During hand-labeling of real tweets, additional intents were introduced when examples didn't fit (e.g. `accessibility_issue`, `keyboard_input_bug`). By the end of labeling, 32 distinct intents were in use across the golden set, 19 of them appearing only once — flagged as needing consolidation in a future pass rather than treated as a finished taxonomy (see LABELING_NOTES.md).

4. **TF-IDF + Logistic Regression as the production classifier for the take-home**
   Extremely fast to train, fully offline, deterministic, and easy to inspect. Sentence-transformers or an LLM classifier would improve accuracy but would hurt the "reproduce in < 15 min" requirement and add heavy dependencies. Retrained on the real 101,276-example pool (training takes ~7 seconds).

5. **Same TF-IDF space for retrieval**
   Keeps the system consistent and removes the need for a second embedding model at evaluation time. Similarity scores remain interpretable.

6. **Escalation is hybrid (rules + confidence), keyed off predicted intent — known weakness**
   False auto-handles are more expensive than false escalations for a brand like Apple, so explicit anger/security/hardware keyword rules act as a safety net the linear model might miss. However, real evaluation revealed the confidence-based rules key off the *predicted* intent, not the true one — when the classifier misclassifies a minority class like `account_lock` or `hardware_failure` as a majority class, the corresponding escalation rule never fires. This produced 0.0 escalation precision/recall on the real golden set and is the top item for "what I'd do next" (see REPORT.md).

7. **Reply = highest-similarity historical reply + light prefix**
   Maximally grounded. Avoided free-form LLM generation so that every draft can be traced to a real past resolution.

8. **Golden set of 151 real examples, single labeling pass**
   Meets the assignment's 150-250 floor but was treated as a first/prototype pass rather than an exhaustive one, given time constraints — 500 real candidates were pooled but only 151 hand-labeled. Not stratified by intent; reflects the real (heavily skewed) distribution of AppleSupport traffic in the sample instead of a balanced hand-picked set, which is itself informative about where the classifier will struggle.

9. **Single labeler, documented escalation criteria, no inter-rater check**
   Realistic for a solo take-home. The four escalation criteria (money, account security, hardware, already-escalated customer) are written down in LABELING_NOTES.md precisely so a reader can audit the policy even without a second labeler to check agreement against.

10. **Spring Boot as API gateway, not as the ML host**
    Keeps the Java service thin, typed, and easy to evolve (auth, rate limits, logging) while leaving the experimental ML surface in Python where iteration is faster.

11. **React chat UI as the primary "proof" surface**
    Interactive demonstration is more convincing than metrics alone. Side panel exposes intent, confidence, escalation reason, and retrieved evidence for inspectability.

12. **Evaluation harness ships two baselines (majority + keyword rules)**
    Satisfies the "at least two baselines" requirement. On real data, the learned classifier (71.5% intent accuracy) only modestly beats the keyword-rule baseline (68.2%) — the lift from the trained model is much smaller than the headline number alone suggests, since most of the accuracy comes from the 3 dominant classes both approaches already handle well.

13. **Reply quality: rule-based proxy in place; LLM-as-judge not yet implemented**
    The lexical/tone-marker proxy in `evaluate.py` is a placeholder. An actual LLM-as-judge rubric with human-agreement evidence, as the assignment requires, has not been built yet — flagged explicitly here rather than glossed over, since claiming it exists would misrepresent the current state of the harness.

14. **No multi-turn dialogue state in v1**
    The assignment focuses on per-message classification, grounded reply, and escalation. Multi-turn is explicitly listed under "what we'd do with one more week."