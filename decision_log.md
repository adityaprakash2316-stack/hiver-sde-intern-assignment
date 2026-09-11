# Decision Log

Non-obvious decisions made while building the AppleSupport AI Agent (10–15 items).

1. **Brand selection = AppleSupport**  
   Highest volume in the public Kaggle dataset and the brand most frequently studied in academic papers that use this corpus. Clearer, more stable intent clusters than pure retail or ride-sharing.

2. **Synthetic-but-realistic data instead of redistributing the full 3 M-tweet dump**  
   Assignment explicitly encourages a subsample. Generating from observed patterns keeps the repo self-contained, avoids licensing/redistribution issues, and still exercises the full pipeline.

3. **14-intent taxonomy induced bottom-up**  
   Started from frequent complaint themes in AppleSupport literature and the sample data (battery, iOS update, hardware, account lock, billing, etc.). Avoided both an overly coarse (5) and an overly fine (30+) inventory.

4. **TF-IDF + Logistic Regression as the production classifier for the take-home**  
   Extremely fast to train, fully offline, deterministic, and easy to inspect. Sentence-transformers or an LLM classifier would improve accuracy but would hurt the “reproduce in < 15 min” requirement and add heavy dependencies.

5. **Same TF-IDF space for retrieval**  
   Keeps the system consistent and removes the need for a second embedding model at evaluation time. Similarity scores remain interpretable.

6. **Escalation is hybrid (rules + confidence) and biased toward escalate**  
   False auto-handles are more expensive than false escalations for a brand like Apple. Explicit anger / security / hardware rules act as a safety net the linear model might miss.

7. **Reply = highest-similarity historical reply + light prefix**  
   Maximally grounded. Avoided free-form LLM generation so that every draft can be traced to a real (or realistically synthesized) past resolution.

8. **Golden set of 200, stratified**  
   Large enough for stable accuracy/F1 estimates, small enough to hand-curate carefully. Extra hard/ambiguous examples were added deliberately.

9. **Single primary labeler + “escalate on ambiguity” policy**  
   Realistic for a solo take-home. Documented the bias so readers can interpret the escalation metrics correctly.

10. **Spring Boot as API gateway, not as the ML host**  
    Keeps the Java service thin, typed, and easy to evolve (auth, rate limits, logging) while leaving the experimental ML surface in Python where iteration is faster.

11. **React chat UI as the primary “proof” surface**  
    Interactive demonstration is more convincing than metrics alone. Side panel exposes intent, confidence, escalation reason, and retrieved evidence for inspectability.

12. **Evaluation harness ships two baselines (majority + keyword rules)**  
    Satisfies the “at least two baselines” requirement and makes the lift of the learned model immediately visible.

13. **Reply quality measured first with a cheap lexical/tone proxy**  
    Structure left open for an LLM-as-judge. Avoided making the headline number depend on a paid API that the evaluator may not have.

14. **No multi-turn dialogue state in v1**  
    The assignment focuses on per-message classification, grounded reply, and escalation. Multi-turn is explicitly listed under “what we’d do with one more week.”
