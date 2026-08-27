# Data Sources

## Primary dataset

**Dataset:** Online Retail II  
**Provider:** UCI Machine Learning Repository  
**Creator:** Daqing Chen  
**DOI:** https://doi.org/10.24432/C5CG6D  
**Source page:** https://archive.ics.uci.edu/dataset/502/online+retail+ii

## Coverage

The source contains transaction-level records for a UK-based registered non-store retailer from **1 December 2009 to 9 December 2011**.

The retailer mainly sells giftware and includes both consumer and wholesale customers.

The workbook contains two annual worksheets:

```text
Year 2009-2010
Year 2010-2011
```

A naïve concatenation of the two worksheets produces **1,067,371 rows**, but the sheets overlap in early December 2010.

Direct row-pattern comparison confirmed **22,523 rows of duplicate source coverage** across the overlapping period. The reproducible combined source therefore keeps the earlier worksheet in full and appends only records from the later worksheet after the earlier worksheet's final timestamp.

The validated combined source contains **1,044,848 rows**.

This correction is a source-construction rule. It is deliberately separate from the remaining exact duplicate rows that occur within the retained source and cannot be assumed to be errors.

Detailed evidence and decisions are recorded in [`docs/data_quality_and_cleaning_decisions.md`](docs/data_quality_and_cleaning_decisions.md).

## Main fields

The source includes:

- invoice number;
- stock code;
- product description;
- quantity;
- invoice date and time;
- unit price;
- customer ID;
- country.

The UCI dataset documentation states that invoice numbers beginning with `C` indicate cancellations.

## Licence

The dataset is published under the **Creative Commons Attribution 4.0 International licence (CC BY 4.0)**.

This permits sharing and adaptation with appropriate attribution.

## Raw-data handling

The original Excel workbook is retained unchanged locally at:

```text
data/raw/online_retail_II.xlsx
```

The raw workbook is not committed to the public GitHub repository.

The combined interim cache at:

```text
data/interim/online_retail_combined.pkl
```

is generated for performance only, is ignored by Git, and is not an authoritative source dataset.

All source construction, cleaning and transformation must remain reproducible from the unchanged original workbook.

## Attribution

Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D
