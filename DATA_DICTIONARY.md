# Data dictionary: joined_32_boroughs.csv

32 rows, one per London borough. The City of London is absent because
ONS does not publish rent figures for it.

Everything is as at **31 March 2026** unless stated.

| Column | Meaning | Source |
|---|---|---|
| `code` | ONS local authority code, E09000002 to E09000033 | Both files. This is the join key |
| `name` | Borough name as written by MHCLG, using `&` | MHCLG |
| `ta_total` | Households in temporary accommodation in this borough | MHCLG TA1, "Households in TA Total" |
| `ta_per_1000` | Households in temporary accommodation per 1,000 households in the borough. The demand measure | MHCLG TA1, "Households in TA Total (per thousand)" |
| `out_broad` | Households owed a temporary accommodation duty in another local authority. **Broader measure, see warning below** | MHCLG TA1, "Households owed a TA duty in another LA Total" |
| `placed_other_la` | Households actually placed in temporary accommodation in another local authority. **This is the numerator used in the analysis** | MHCLG TA9_TATYPE, "Placed in temporary accommodation in another LA, Total" |
| `rent_name` | Borough name as written by ONS, using `and`. Kept to show the join was on code, not name | ONS |
| `rent_1bed_mar26` | Average monthly rent, one bedroom, March 2026, in pounds | ONS PIPR, "Rental price one bed" |
| `rent_1bed_q1avg` | Mean of the January, February and March 2026 one-bedroom rents. Robustness check only | ONS PIPR, derived |
| `out_share` | `placed_other_la ÷ ta_total`. **This is the outcome variable** | Derived |
| `out_share_broad` | `out_broad ÷ ta_total`. Sensitivity check only | Derived |

---

## Warning: `out_broad` and `placed_other_la` are not the same thing

This is the one place where picking the wrong column gives you a wrong
answer that looks right.

**`out_broad`** counts households owed a temporary accommodation duty in
another local authority. MHCLG note 36 states that this "may include
households placed in temporary accommodation by their local authority as
well as those recorded as duty owed but no accommodation secured", and
warns that the total can therefore exceed the total in temporary
accommodation. A share built on it can in principle exceed 1.

**`placed_other_la`** counts only households actually placed in
temporary accommodation in another local authority. It excludes the
no-accommodation-secured cases.

At London level the two reconcile exactly:

```
out_broad         35,460
placed_other_la   35,380
difference            80   (duty owed, no accommodation secured)
```

`placed_other_la` is the one that matches the question "does this
borough place households outside the borough", so it is what the
analysis uses. `out_broad` is kept in the file so the sensitivity check
can be reproduced. Substituting one for the other leaves the correlation
unchanged to three decimal places.

---

## Notes on the sources

MHCLG figures are rounded to the nearest 10, which is why borough totals
do not sum exactly to the published London figure.

ONS treats local authority rent figures as experimental, with much
smaller samples than the national series, and advises reading them as
longer-term trends rather than single months. `rent_1bed_q1avg` exists
for that reason.

MHCLG note 48 records that some out-of-area placements carry incorrect
or non-England local authority codes, so destination totals in TA9 do
not always reconcile with the out-of-area total. That does not affect
any column here, but it will matter for the destination analysis.
