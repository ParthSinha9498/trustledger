# Agent Detection Evals (TODO #3)

**Mode:** mock (ScenarioAwareMockLLM)
- **Recall on planted issues:** 100%
- **False alarm rate on clean control:** 0%
- **Total DP budget spent (rho):** 0.04

## Scenario Results

| Scenario | Type | Result | Store OK | Dist OK | Reason OK | Steps | Rho | Summary |
|---|---|---|---|---|---|---|---|---|
| leaky_distributor | Problem | **PASS** | ✓ | ✓ | ✓ | 17 | 0.0100 | Root cause confirmed: NOT_IN_CHANNEL anomaly concentrated at... |
| cloned_serial | Problem | **PASS** | ✓ | ✓ | ✓ | 17 | 0.0100 | Root cause confirmed: ALREADY_SOLD anomaly concentrated at s... |
| rogue_store | Problem | **PASS** | ✓ | ✓ | ✓ | 17 | 0.0100 | Root cause confirmed: UNKNOWN anomaly concentrated at store_... |
| clean | Control | **PASS** | ✓ | ✓ | ✓ | 14 | 0.0100 | No breach or anomaly identified across stores. Isolated oper... |
