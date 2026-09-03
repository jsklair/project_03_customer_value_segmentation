# Reproducing Project 03 locally

This guide reproduces **Project 03: Customer Value & Retention Segmentation** from the original UCI Online Retail II workbook through to the final reports and visualisations.

The final reproducibility test used:

- Python 3.13.14
- pandas 3.0.3
- matplotlib 3.11.0
- openpyxl 3.1.5
- SQLite through Python's standard `sqlite3` library

The tested dependency versions are pinned in `requirements.txt`.

## 1. Obtain the source data

Download **Online Retail II** from the UCI Machine Learning Repository:

https://doi.org/10.24432/C5CG6D

Place the original Excel workbook at:

```text
data/raw/online_retail_II.xlsx
```

The raw workbook is not committed to this repository.

The dataset is published under the **CC BY 4.0** licence. See `data_sources.md` for provenance and source-handling details.

## 2. Create a Python environment

Python 3.13 is recommended because this is the version used for the final reproducibility test.

From the repository root:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirm the installed package versions:

```powershell
python -c "import pandas, matplotlib, openpyxl; print('pandas', pandas.__version__); print('matplotlib', matplotlib.__version__); print('openpyxl', openpyxl.__version__)"
```

## 3. Profile and prepare the source

Run:

```powershell
python python\01_profile_source_data.py
```

The corrected source should contain:

```text
1,044,848 rows
```

Then run:

```powershell
python python\02_clean_transactions.py
```

The cleaning gate should report:

```text
Unresolved rows: 0
Unresolved StockCodes: 0
```

## 4. Build the SQLite analytical database

```powershell
python python\03_build_database.py
```

The generated database is:

```text
data/database/online_retail.db
```

The database is rebuilt from scratch on each run so stale analytical objects cannot survive from a previous execution.

Generated intermediate, cleaned and database files are intentionally excluded from version control.

## 5. Build and validate the SQL analytical layers

Run the SQL files in this order:

```powershell
python python\04_run_sql.py sql\01_data_reconciliation.sql
python python\04_run_sql.py sql\02_create_invoice_layer.sql
python python\04_run_sql.py sql\03_investigate_invoice_timestamps.sql
python python\04_run_sql.py sql\04_investigate_customer_population.sql
python python\04_run_sql.py sql\05_create_customer_snapshot_features.sql
python python\04_run_sql.py sql\06_investigate_customer_reconciliation.sql
python python\04_run_sql.py sql\07_profile_customer_features.sql
python python\04_run_sql.py sql\08_investigate_reactivation_features.sql
```

The validated snapshot population should contain:

```text
4,908 eligible customers
4,324 behavioural purchasers
584 historical-only purchasers
```

Behavioural observed customer value should reconcile to:

```text
£7,762,616.79
```

## 6. Assess candidate customer features

```powershell
python python\05_assess_customer_features.py
```

This profiles feature distributions, redundancy, value concentration, recent activity patterns and potential segmentation measures.

## 7. Build the final segmentation

```powershell
python python\04_run_sql.py sql\09_create_segmentation_features.sql
python python\04_run_sql.py sql\11_create_customer_segments.sql
```

`sql/10_prototype_segment_design.sql` is intentionally absent from the final public workflow. The prototype logic was superseded by the final evidence-led segment design and was not retained as production code.

The final segmentation should assign all **4,908 customers uniquely across eight segments**.

## 8. Run held-out validation and sensitivity checks

```powershell
python python\04_run_sql.py sql\12_validate_segments.sql
python python\04_run_sql.py sql\13_segment_sensitivity_checks.sql
```

The held-out validation should reproduce:

```text
2,549 future purchasers
51.9% overall future purchase rate
8,470 future purchase invoices
£4,170,456.73 held-out observed net sales
```

## 9. Generate the final portfolio outputs

```powershell
python python\06_create_segment_outputs.py
```

This recreates:

```text
reports/customer_segment_summary.csv
reports/customer_segment_actions.csv

visuals/01_customer_population_by_segment.png
visuals/02_future_purchase_rate_by_segment.png
visuals/03_snapshot_vs_future_value_share.png
visuals/04_lapsed_customer_reactivation.png
```

The reporting script contains explicit QA gates for:

- the 4,908-customer population;
- exact segment membership;
- held-out purchaser count;
- snapshot observed value;
- held-out observed value.

The script terminates with an error if these established totals drift unexpectedly.

## 10. Final checks

After the complete run:

```powershell
git status --short
git diff --check
```

## Reproducibility note

During final QA, an inefficient SQLite reconciliation join was identified in the customer-snapshot stage.

The original reconciliation joined the behavioural transaction layer to a derived eligible-customer set. SQLite selected an inefficient join strategy, making the check impractically slow despite the underlying customer calculations being fast.

The reconciliation was redesigned to use the already-validated, materialised invoice layer.

The analytical result was unchanged:

```text
£7,762,616.79 = £7,762,616.79
```

The complete customer-snapshot SQL stage then fell from an impractically long runtime to well under one second in the tested environment.

The database was subsequently rebuilt from scratch and the complete database-to-output pipeline passed successfully.

## Analytical scope

The held-out validation is descriptive and predictive, not causal.

It tests whether snapshot-defined customer groups remain commercially differentiated in later behaviour. It does not estimate campaign uplift or demonstrate that segment membership causes later purchasing.
