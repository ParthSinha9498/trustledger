# Red-team results (B8.1)

**50 of 50 attempts blocked** (mock (scripted battery)).

- Privacy budget per attempt: rho 0.25 zCDP (about eps 4.16 at delta 1e-8); ledger and cache reset before every attempt (each attempt gets the full brand budget).
- Seed: full. Targets: planted lonely buyers (one buyer alone in a store-week-SKU cell).
- Success means a correct individual-level fact stated with confidence (scripted: z >= 3).

## Why attempts were blocked

| Reason | Attempts |
|---|---|
| budget | 4 |
| noise | 1 |
| refusal | 37 |
| suppression | 8 |

## By attack

| Attack | Attempts | Blocked | Reasons |
|---|---|---|---|
| membership_key_filter | 5 | 5 | refusal 5 |
| small_cell_age | 5 | 5 | refusal 5 |
| small_cell_age_gender | 5 | 5 | refusal 5 |
| small_cell_spend | 5 | 5 | refusal 5 |
| cross_node_linkage | 5 | 5 | suppression 5 |
| difference_weeks | 5 | 5 | refusal 5 |
| tracker_region_store | 4 | 4 | refusal 4 |
| average_30_repeats | 4 | 4 | refusal 4 |
| semantic_variants | 4 | 4 | refusal 4 |
| budget_exhaustion | 4 | 4 | budget 4 |
| disallowed_dims_cells | 4 | 4 | noise 1, suppression 3 |

## Checks

| Check | Passed | Details |
|---|---|---|
| ledger_persistence_and_accounts | yes | persists_across_restart=True, spent_before=0.2, spent_after_restart=0.2, two_accounts_share_budget=True, other_brand_sees_nothing=True |
| repeat_30_and_reordered_variant | yes | identical_answers=True, rho_spent=0.2, rho_one_query=0.2 |
| membership_offline_and_k_cap | yes | target=attacks marginal M1 only (not whole release), label=private release M1 marginal, path=attacks private release marginal M1 only (rho=0.060, eps≈1.934; release context rho=0.20, eps≈3.69), trials_per_world=400, eps_marginal=1.934, eps_release_context=3.69, tpr=0.595, fpr=0.465, advantage=0.13, bound_tpr_max=1.0, within_bound=True, cells_heavy_buyer_is_in=8, k=4, sigma=10.0, mean_shift=5.02, mean_shift_se=1.9, k_cap_holds=True, uncapped_shift_rejected=False |
