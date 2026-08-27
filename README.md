# Project 03: Customer Value & Retention Segmentation

A UK online retailer wants to decide which customer groups deserve different retention, reactivation and growth treatment. This project builds that decision from transaction history at a fixed snapshot, then reserves later purchasing behaviour to test whether the resulting segments remain commercially differentiated.

## Business question

Which customer groups should a CRM or Customer Insight Manager prioritise for different retention, reactivation and growth activity based on recent purchasing value and behaviour?

## Analytical design

The analysis uses **Online Retail II** from the UCI Machine Learning Repository.

Customer segments will be defined at a **31 May 2011** snapshot using activity from **1 June 2010 to 31 May 2011**. Transactions from **1 June to 30 November 2011** are held back for subsequent-behaviour validation and cannot influence the original segment definitions.

The project will not be presented as churn modelling or customer lifetime value analysis. The data supports finite-window measures of observed customer value and later purchasing behaviour.

## Data foundation completed

Source profiling is complete.

The workbook contains two annual worksheets with overlapping coverage in early December 2010. Direct comparison confirmed **22,523 rows of duplicate source coverage** across the sheets. The combined source is therefore constructed by retaining the earlier sheet in full and appending only later records after its final timestamp.

After that correction:

- validated combined source: **1,044,848 rows**;
- rows without Customer ID: **235,287**;
- excess exact duplicate rows remaining within the retained source: **11,812**;
- negative-quantity rows: **22,557**;
- zero-price rows: **6,024**;
- negative-price rows: **5**.

The remaining exact duplicates are retained in the primary dataset because the source has no transaction-line identifier that can distinguish an erroneous duplicate from legitimate repeated identical lines. Their impact will be tested later if segment membership proves sensitive to them.

Profiling also established that missing customer identifiers form complete unidentified invoices rather than partly identified orders, that many non-cancellation negative quantities are operational stock adjustments, and that special/manual transaction codes need classification rather than blanket removal.

The evidence and resulting decisions are documented in [`docs/data_quality_and_cleaning_decisions.md`](docs/data_quality_and_cleaning_decisions.md).

## Next stage

The next step is to translate the profiling decisions into an explicit treatment matrix for customer activity, observed net sales and product breadth, then implement the reproducible cleaned transaction layer.

The intended analytical flow is:

```text
validated source
→ cleaned transaction lines
→ SQL/SQLite analytical layer
→ snapshot-valid customer measures
→ interpretable customer segments
→ held-out behavioural validation
→ CRM priorities and recommendations
```

## Tools

- Python / pandas
- SQL / SQLite
- matplotlib
- Git and GitHub
- GitHub Pages

Power BI and Excel are not being forced into this project because those capabilities are already demonstrated elsewhere in the portfolio and do not improve this analytical question.

## Current status

**In progress — source profiling complete; cleaning pipeline next.**

See [`project_plan.md`](project_plan.md) for the initial analytical design and [`data_sources.md`](data_sources.md) for source provenance and licence information.
