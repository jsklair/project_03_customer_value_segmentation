# Data Quality and Cleaning Decisions

## Status

**Source profiling complete — cleaning implementation next.**

This document records the main data-quality findings from profiling the UCI Online Retail II dataset and the resulting analytical decisions for Project 03.

The aim is to distinguish between:

- confirmed source issues that should be corrected;
- unusual records that should be classified rather than removed automatically;
- limitations that affect the customer-level analytical population;
- issues that should be tested later through sensitivity analysis.

The final cleaned analytical dataset has not yet been created. This document defines the evidence base that the cleaning pipeline must implement and validate.

---

## 1. Source worksheet overlap

The source workbook contains two annual worksheets:

- `Year 2009-2010`
- `Year 2010-2011`

The worksheets overlap between 1 and 9 December 2010.

Direct comparison showed:

- 22,523 rows in the overlap period in each worksheet;
- 22,202 distinct row patterns in each;
- every overlapping row pattern was present in both worksheets;
- occurrence counts matched exactly for every pattern.

### Decision

Keep the earlier worksheet in full and append only records from the later worksheet that occur after the final timestamp in the earlier worksheet.

This removes **22,523 rows of proven duplicate source coverage**.

A general `drop_duplicates()` operation is not used for this correction because repeated lines already exist within the individual source worksheets and may represent legitimate transaction records.

After correcting the overlap, the combined source contains **1,044,848 rows**.

---

## 2. Exact duplicate rows within the retained source

After removing the proven worksheet overlap:

- 11,812 excess exact duplicate rows remain;
- 4,387 invoices are affected;
- 1,594 identifiable customers are affected;
- the excess rows represent approximately 0.28% of raw positive transaction value.

The source also contains 21,234 invoice/StockCode combinations appearing more than once. In 11,160 of these combinations, quantity, price or description differs between lines.

This shows that multiple rows for the same product within an invoice are part of the source structure.

There is no transaction-line identifier that can reliably distinguish an erroneous exact duplicate from two legitimate identical entries.

### Decision

Retain exact duplicate rows within the individual source worksheets in the primary analysis.

Do not apply a blanket `drop_duplicates()` rule.

If duplicate treatment could materially affect final customer segments, compare results with a deduplicated version as a sensitivity check.

---

## 3. Missing Customer ID

After correcting the worksheet overlap:

- 235,287 rows have no Customer ID.

Within the behavioural window from 1 June 2010 to 31 May 2011:

- 494,905 transaction rows are present;
- 111,777 rows have no Customer ID;
- this represents 22.6% of behavioural-window rows;
- approximately £1.52 million of raw positive transaction value cannot be assigned to a customer;
- this represents 15.6% of raw positive transaction value in the behavioural window.

No invoice contains a mixture of identified and unidentified customer rows.

### Decision

Transactions without a Customer ID cannot contribute to customer-level segmentation.

They should be excluded from the customer analytical population, while the scale of the excluded activity should be reported transparently as a project limitation.

The final excluded value share should be recalculated after transaction-cleaning rules have been applied.

---

## 4. Invoice-to-customer consistency

No invoice is linked to more than one identifiable Customer ID.

No invoice contains both identified and missing Customer ID rows.

### Decision

Invoice-level measures can safely be attributed to a single customer where a Customer ID is available.

---

## 5. Cancellations and negative quantities

The source uses invoice numbers beginning with `C` to identify cancellations.

Most negative-quantity rows correspond to cancellation invoices, but a smaller group of negative-quantity rows does not.

Profiling showed that the non-cancellation negative rows:

- have zero price;
- have no Customer ID;
- frequently contain operational descriptions such as stock losses, damage or adjustments.

These appear to represent inventory or operational adjustments rather than customer transactions.

### Decision

Cancellation transactions should be retained where needed to calculate net customer purchasing value.

Negative-quantity rows that do not represent customer cancellations should not contribute to customer purchasing behaviour.

The cleaning pipeline must explicitly distinguish customer returns/cancellations from operational stock adjustments.

---

## 6. Negative prices

Five negative-price rows were identified.

They use StockCode `B`, description `Adjust bad debt`, have no Customer ID and contain large negative values.

### Decision

Treat these as accounting adjustments rather than customer purchases.

They should not contribute to customer purchasing behaviour or customer value measures.

---

## 7. Zero-price transactions

6,024 zero-price rows remain after correcting the source overlap.

Some identifiable zero-price transactions appear to represent genuine products, while others include test or administrative activity.

Examples include:

- ordinary merchandise codes;
- `TEST001`;
- manual transactions.

### Decision

Do not remove zero-price rows solely because their price is zero.

A legitimate zero-price product may represent customer activity while contributing £0 to observed sales.

Test or administrative records should be excluded where their purpose can be identified reliably.

---

## 8. Manual transactions (`M` / `m`)

Manual transactions are commercially material and include both positive and negative records.

Profiling found strong evidence of reversal and correction activity:

- many matching positive and negative price/quantity combinations;
- 172 perfectly balanced combinations;
- 422 manual rows in those combinations, representing 30.1% of manual rows after correcting the worksheet overlap.

Large manual entries frequently form exact-value reversals or adjustments.

### Decision

Manual transactions should not be treated as ordinary merchandise and should not contribute to product-breadth measures.

Their treatment in customer net-sales calculations must be defined explicitly in the cleaning and feature logic.

They should not be classified automatically as ordinary customer purchases.

---

## 9. Special and non-product transaction codes

Profiling identified transaction codes representing several different concepts, including:

- postage and carriage;
- discounts;
- bank charges;
- Amazon fees;
- bad-debt adjustments;
- commission;
- administrative adjustments;
- test records;
- samples;
- gift vouchers;
- manual entries.

It also showed that non-standard StockCode formatting does not necessarily imply a non-product record. Several genuine merchandise codes do not follow a simple five-digit pattern.

### Decision

Do not classify transaction validity using StockCode format alone.

Special transaction codes should be classified according to their known business meaning and treated appropriately for:

- customer activity;
- observed net sales;
- product breadth.

The exact classification must be implemented explicitly in the cleaning pipeline.

---

## 10. StockCode standardisation

The same product code sometimes appears with differences in letter case.

Profiling identified 174 normalised StockCodes represented by multiple raw variants.

Examples include:

- `15056BL` and `15056bl`;
- `15056N` and `15056n`;
- similar case differences across many other product codes.

### Decision

Strip surrounding whitespace and standardise StockCode case before using StockCode in customer-level feature calculations.

---

## 11. Product descriptions

Descriptions are not stable identifiers.

Among 4,778 normalised StockCodes with a description, 1,190 are associated with more than one normalised description.

Some differences reflect:

- wording changes;
- spelling variations;
- operational notes;
- damage or adjustment annotations;
- incorrect coding.

### Decision

Use normalised StockCode rather than Description as the primary identifier for product-breadth measures.

Description remains useful for interpretation and data-quality investigation.

---

## 12. Customer country

Of 5,942 identifiable customers:

- 5,929 are associated with one country;
- 13 are associated with two countries.

Multi-country customers therefore represent approximately 0.22% of identifiable customers.

### Decision

Do not assume Country is inherently unique at customer level.

If a single customer country is required later, define an explicit assignment rule rather than relying on arbitrary row order.

Country is not currently expected to be a core segmentation feature.

---

## 13. Commercial outliers

The positive customer-identified transaction data is strongly right-skewed.

For positive-sale rows:

- median quantity is 5;
- 99th percentile quantity is 128;
- 99.9th percentile quantity is 576;
- maximum quantity is 80,995.

Positive line value ranges from a median of £11.90 to a maximum of £168,469.60.

Several extreme observations appear to represent genuine high-volume transactions rather than obvious data-entry errors.

### Decision

Do not remove observations purely because they are extreme.

Outliers should be retained unless there is evidence that they are invalid.

Customer-level feature distributions should be reviewed after aggregation, and sensitivity or robust segmentation methods should be considered if individual extreme customers dominate the results.

---

## 14. Behavioural and validation populations

The behavioural window is:

**1 June 2010 to 31 May 2011**

The held-out validation window is:

**1 June 2011 to 30 November 2011**

Before final cleaning:

- 4,376 identifiable customers appear in the behavioural window;
- 4,338 have at least one positive-sale row;
- 3,499 identifiable customers appear in the validation window;
- 2,500 behavioural-window customers are also observed during validation;
- 999 validation customers were not observed in the behavioural window.

### Decision

The final segmentation population will be defined from information available at the 31 May 2011 snapshot only.

Validation-period behaviour must not be used to construct the segments.

The validation period will be used only to assess whether snapshot-defined segments distinguish subsequent customer behaviour.

---

## Overall cleaning principle

The cleaning approach is evidence-led rather than based on blanket rules.

The guiding process is:

> profile → investigate → classify → clean → validate

Confirmed source errors are corrected.

Unusual records are not removed simply because they are inconvenient, extreme or duplicated.

Where the source does not provide enough evidence to make a definitive distinction, the assumption will be documented and, where material, tested through sensitivity analysis.

The next implementation step is to translate these decisions into an explicit transaction-treatment matrix and then into the reproducible cleaning pipeline.
