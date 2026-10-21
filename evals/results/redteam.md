# Red-team results (B8.1)

**11 of 11 attempts blocked** (mock (scripted battery)).

- Privacy budget per attempt: rho 0.25 zCDP (about eps 4.16 at delta 1e-8); ledger and cache reset before every attempt (each attempt gets the full brand budget).
- Seed: small. Targets: planted lonely buyers (one buyer alone in a store-week-SKU cell).
- Success means a correct individual-level fact stated with confidence (scripted: z >= 3).
- Unconfident best guesses were right 60% of the time over 5 guesses (chance is 20% for age band, 33% for gender).

## Why attempts were blocked

| Reason | Attempts |
|---|---|
| budget | 1 |
| cache | 1 |
| noise | 3 |
| refusal | 1 |
| suppression | 5 |

## By attack

| Attack | Attempts | Blocked | Reasons |
|---|---|---|---|
| membership_key_filter | 1 | 1 | refusal 1 |
| small_cell_age | 1 | 1 | suppression 1 |
| small_cell_age_gender | 1 | 1 | suppression 1 |
| small_cell_spend | 1 | 1 | suppression 1 |
| cross_node_linkage | 1 | 1 | suppression 1 |
| difference_weeks | 1 | 1 | noise 1 |
| tracker_region_store | 1 | 1 | noise 1 |
| average_30_repeats | 1 | 1 | cache 1 |
| semantic_variants | 1 | 1 | noise 1 |
| budget_exhaustion | 1 | 1 | budget 1 |
| disallowed_dims_cells | 1 | 1 | suppression 1 |

## Checks

| Check | Passed | Details |
|---|---|---|
| ledger_persistence_and_accounts | yes | persists_across_restart=True, spent_before=0.03, spent_after_restart=0.03, two_accounts_share_budget=True, other_brand_sees_nothing=True |
| repeat_30_and_reordered_variant | yes | identical_answers=True, rho_spent=0.01, rho_one_query=0.01 |
| membership_offline_and_k_cap | yes | trials_per_world=40, eps_one_query=0.752, tpr=0.4, fpr=0.55, advantage=-0.15, bound_tpr_max=1.0, within_bound=True, cells_heavy_buyer_is_in=8, k=4, sigma=14.14, mean_shift=4.77, mean_shift_se=11.35, k_cap_holds=True, uncapped_shift_rejected=False |
