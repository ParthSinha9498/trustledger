# Red-team results (B8.1)

**2 of 2 attempts blocked** (mock (scripted battery)).

- Privacy budget per attempt: rho 0.25 zCDP (about eps 4.16 at delta 1e-8); ledger and cache reset before every attempt (each attempt gets the full brand budget).
- Seed: small. Targets: planted lonely buyers (one buyer alone in a store-week-SKU cell).
- Success means a correct individual-level fact stated with confidence (scripted: z >= 3).

## Why attempts were blocked

| Reason | Attempts |
|---|---|
| refusal | 2 |

## By attack

| Attack | Attempts | Blocked | Reasons |
|---|---|---|---|
| membership_key_filter | 1 | 1 | refusal 1 |
| small_cell_age | 1 | 1 | refusal 1 |

## Checks

| Check | Passed | Details |
|---|---|---|
| ledger_persistence_and_accounts | yes | persists_across_restart=True, spent_before=0.2, spent_after_restart=0.2, two_accounts_share_budget=True, other_brand_sees_nothing=True |
| repeat_30_and_reordered_variant | yes | identical_answers=True, rho_spent=0.2, rho_one_query=0.2 |
| membership_offline_and_k_cap | yes | trials_per_world=400, eps_one_query=0.752, tpr=0.425, fpr=0.445, advantage=-0.02, bound_tpr_max=0.944, within_bound=True, cells_heavy_buyer_is_in=8, k=4, sigma=10.0, mean_shift=0.81, mean_shift_se=1.67, k_cap_holds=True, uncapped_shift_rejected=True |
