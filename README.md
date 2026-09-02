# Project 03: Customer Value & Retention Segmentation

A UK online retailer wants to decide which customer groups deserve different retention, reactivation and growth treatment. This project builds that decision from transaction history at a fixed snapshot, then reserves later purchasing behaviour to test whether the resulting segments remain commercially differentiated.

## Business question

Which customer groups should a CRM or Customer Insight Manager prioritise for different retention, reactivation and growth activity based on recent purchasing value and behaviour?

## Analytical design

The analysis uses **Online Retail II** from the UCI Machine Learning Repository.

Customer segments are defined at a **31 May 2011** snapshot. The main behavioural window covers **1 June 2010 to 31 May 2011**, while transactions from **1 June to 30 November 2011** are held back for subsequent-behaviour validation and cannot influence the original segment definitions.

The project is not presented as churn modelling or customer lifetime value analysis. The data supports finite-window measures of observed customer value and later purchasing behaviour.

## Data foundation

The source workbook contains two annual worksheets with overlapping coverage in early December 2010. Direct comparison confirmed **22,523 rows of duplicate source coverage** across the sheets. The combined source is therefore constructed by retaining the earlier sheet in full and appending only later records after its final timestamp.

After that correction:

* validated combined source: **1,044,848 rows**;
* rows without Customer ID: **235,287**;
* excess exact duplicate rows retained within the source: **11,812**;
* negative-quantity rows: **22,557**;
* zero-price rows: **6,024**;
* negative-price rows: **5**.

The remaining exact duplicates are retained in the primary dataset because the source has no transaction-line identifier that can distinguish an erroneous duplicate from legitimate repeated identical lines. Their impact will be tested later if segment membership proves sensitive to them.

The evidence and resulting decisions are documented in [`docs/data_quality_and_cleaning_decisions.md`](docs/data_quality_and_cleaning_decisions.md).

## Transaction cleaning

The profiling decisions have been translated into a reproducible classified transaction layer.

The cleaning pipeline:

* preserves all **1,044,848** rows from the overlap-corrected source;
* retains raw fields alongside normalised analytical fields;
* labels behavioural, validation and out-of-window periods explicitly;
* distinguishes merchandise, cancellations/returns, postage, discounts, Manual entries and administrative/accounting records;
* separates customer activity, observed net sales and product-breadth eligibility rather than applying one blanket valid/invalid transaction rule;
* retains transactions without Customer ID for reconciliation while preventing them from entering customer-level measures;
* preserves within-sheet exact duplicates for the primary analysis;
* ends with **zero unresolved transaction classifications**.

Post-cleaning, **15.0% of positive classified transaction value cannot be attributed to an identifiable customer**.

The full classified dataset is generated locally and excluded from Git. Compact QA outputs remain in the repository.

## SQL and customer snapshot layer

The classified transaction data is loaded reproducibly into a local SQLite database and independently reconciled against the pandas-cleaned layer.

The SQL foundation now includes:

* transaction-level row, period, classification and monetary reconciliation;
* a validated **53,628-invoice** analytical layer;
* investigation of the 83 invoices containing more than one line timestamp;
* explicit customer eligibility rules;
* a settled purchase-frequency definition;
* snapshot-valid customer measures built without validation-period leakage.

The timestamp investigation found that all 83 affected invoices remain on one calendar date, 82 span no more than five minutes and the maximum span is nine minutes. The first recorded timestamp is therefore used consistently at invoice level.

The segmentation population contains **4,908 identifiable customers with evidence of at least one qualifying purchase by the snapshot date**:

* **4,324** made at least one qualifying purchase during the trailing 12-month behavioural window;
* **584** are historical purchasers with no qualifying purchase during that window.

A further 90 identified Customer IDs have no qualifying purchase history and are excluded from segmentation.

Purchase frequency is defined as the **number of distinct qualifying purchase invoices during the trailing 12-month behavioural window**. Returns and other non-purchase records do not create additional purchase frequency.

The initial customer snapshot layer includes:

* recency;
* observed tenure;
* 12-month purchase frequency;
* active months;
* 12-month observed net sales;
* product breadth;
* prior-period purchasing indicators.

Behavioural observed net sales reconcile exactly between the eligible customer feature population and the underlying transaction layer at **£7,762,616.79**.

## Next stage

The next stage is to inspect the customer-feature distributions and determine which measures provide useful, non-redundant evidence for commercially interpretable segmentation.

Segment thresholds and names have **not** yet been fixed.

The intended analytical flow is:

```text
validated source
→ classified transaction layer
→ SQL/SQLite analytical layer
→ snapshot-valid customer measures
→ interpretable customer segments
→ held-out behavioural validation
→ CRM priorities and recommendations
```

## Tools

* Python / pandas
* SQL / SQLite
* matplotlib
* Git and GitHub
* GitHub Pages

Power BI and Excel are not being forced into this project because those capabilities are already demonstrated elsewhere in the portfolio and do not improve this analytical question.

## Current status

**In progress — data foundation and snapshot customer-feature layer complete; feature analysis and segmentation next.**

See [`project_plan.md`](project_plan.md) for the initial analytical design and [`data_sources.md`](data_sources.md) for source provenance and licence information.
