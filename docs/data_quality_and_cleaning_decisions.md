# Data Quality and Cleaning Decisions

## Status

**Source profiling and transaction-treatment methodology complete — cleaning implementation next.**

This document records the main data-quality findings from profiling the UCI Online Retail II dataset and the resulting analytical decisions for Project 03.

The aim is to distinguish between:

* confirmed source issues that should be corrected;
* unusual records that should be classified rather than removed automatically;
* limitations that affect the customer-level analytical population;
* issues that should be tested later through sensitivity analysis.

The final cleaned analytical dataset has not yet been created. This document defines the evidence base and transaction-treatment rules that the cleaning pipeline must implement and validate.

---

## 1. Source worksheet overlap

The source workbook contains two annual worksheets:

* `Year 2009-2010`
* `Year 2010-2011`

The worksheets overlap between 1 and 9 December 2010.

Direct comparison showed:

* 22,523 rows in the overlap period in each worksheet;
* 22,202 distinct row patterns in each;
* every overlapping row pattern was present in both worksheets;
* occurrence counts matched exactly for every pattern.

### Decision

Keep the earlier worksheet in full and append only records from the later worksheet that occur after the final timestamp in the earlier worksheet.

This removes **22,523 rows of proven duplicate source coverage**.

A general `drop_duplicates()` operation is not used for this correction because repeated lines already exist within the individual source worksheets and may represent legitimate transaction records.

After correcting the overlap, the combined source contains **1,044,848 rows**.

---

## 2. Exact duplicate rows within the retained source

After removing the proven worksheet overlap:

* 11,812 excess exact duplicate rows remain;
* 4,387 invoices are affected;
* 1,594 identifiable customers are affected;
* the excess rows represent approximately 0.28% of raw positive transaction value.

The source also contains 21,234 invoice/StockCode combinations appearing more than once. In 11,160 of these combinations, quantity, price or description differs between lines.

This shows that multiple rows for the same product within an invoice are part of the source structure.

There is no transaction-line identifier that can reliably distinguish an erroneous exact duplicate from two legitimate identical entries.

### Decision

Retain exact duplicate rows within the individual source worksheets in the primary analysis.

Do not apply a blanket `drop_duplicates()` rule.

The retained rows should receive the same transaction treatment as any other row of their underlying transaction class.

If duplicate treatment could materially affect final customer segments, compare results with a deduplicated version as a sensitivity check.

---

## 3. Missing Customer ID

After correcting the worksheet overlap:

* 235,287 rows have no Customer ID.

Within the behavioural window from 1 June 2010 to 31 May 2011:

* 494,905 transaction rows are present;
* 111,777 rows have no Customer ID;
* this represents 22.6% of behavioural-window rows;
* approximately £1.52 million of raw positive transaction value cannot be assigned to a customer;
* this represents 15.6% of raw positive transaction value in the behavioural window.

No invoice contains a mixture of identified and unidentified customer rows.

### Decision

Transactions without a Customer ID cannot contribute to customer-level segmentation.

They should be excluded from customer-level activity, observed-value and product-breadth measures, while remaining available for source-level reconciliation and limitation reporting.

The scale of the excluded activity should be reported transparently as a project limitation.

The final excluded value share should be recalculated after transaction-cleaning rules have been applied rather than reusing the raw 15.6% figure.

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

* have zero price;
* have no Customer ID;
* frequently contain operational descriptions such as stock losses, damage or adjustments.

These appear to represent inventory or operational adjustments rather than customer transactions.

### Decision

Customer cancellation and return transactions should be retained where needed to calculate observed net customer value.

Their signed negative value should reduce observed net sales, but the return itself should not make a customer appear more recently or frequently active and should not contribute to product breadth.

Negative-quantity rows that do not represent customer cancellations should not contribute to customer purchasing behaviour, observed customer value or product breadth.

The cleaning pipeline must explicitly distinguish customer returns/cancellations from operational stock adjustments.

---

## 6. Negative prices

Five negative-price rows were identified.

They use StockCode `B`, description `Adjust bad debt`, have no Customer ID and contain large negative values.

### Decision

Treat these as accounting adjustments rather than customer purchases.

They should not contribute to customer purchasing behaviour, observed customer value or product-breadth measures.

---

## 7. Zero-price transactions

6,024 zero-price rows remain after correcting the source overlap.

Some identifiable zero-price transactions appear to represent genuine products, while others include test or administrative activity.

Examples include:

* ordinary merchandise codes;
* `TEST001`;
* manual transactions.

### Decision

Do not remove zero-price rows solely because their price is zero.

A legitimate zero-price product may represent genuine customer and product activity while contributing £0 to observed net sales.

Explicit test, administrative, sample or other non-purchase records should be treated according to their business meaning rather than being retained merely because a Customer ID is present.

---

## 8. Manual transactions (`M` / `m`)

Manual transactions are commercially material and include both positive and negative records.

Profiling found strong evidence of reversal and correction activity:

* many matching positive and negative price/quantity combinations;
* 172 perfectly balanced combinations;
* 422 manual rows in those combinations, representing 30.1% of manual rows after correcting the worksheet overlap.

Large manual entries frequently form exact-value reversals or adjustments.

### Decision

Manual transactions should not be treated as ordinary merchandise.

They should:

* not independently create customer purchasing activity;
* not contribute to product-breadth measures;
* contribute to observed net sales using their signed line value.

Including their signed monetary effect preserves correction and reversal behaviour already represented in the transaction ledger without treating the records as ordinary product purchases.

If Manual entries materially influence customer-value distributions or final segment membership, rerun the relevant analysis with Manual entries excluded as a sensitivity check.

---

## 9. Special and non-product transaction codes

Profiling identified transaction codes representing several different concepts, including:

* postage and carriage;
* discounts;
* bank charges;
* Amazon fees;
* bad-debt adjustments;
* commission;
* administrative adjustments;
* test records;
* samples;
* gift vouchers;
* manual entries.

It also showed that non-standard StockCode formatting does not necessarily imply a non-product record. Several genuine merchandise codes do not follow a simple five-digit pattern.

### Decision

Do not classify transaction validity using StockCode format alone.

Known special transaction codes should be classified according to their business meaning and treated separately for:

* customer activity;
* observed net sales;
* product breadth.

The agreed treatments are defined explicitly in Section 15.

An unfamiliar or ambiguous StockCode should not be silently classified as either merchandise or administrative activity. Material unresolved cases should be surfaced for investigation.

---

## 10. StockCode standardisation

The same product code sometimes appears with differences in letter case.

Profiling identified 174 normalised StockCodes represented by multiple raw variants.

Examples include:

* `15056BL` and `15056bl`;
* `15056N` and `15056n`;
* similar case differences across many other product codes.

### Decision

Before transaction classification and product-breadth calculation:

1. strip surrounding whitespace from StockCode;
2. standardise StockCode to uppercase;
3. use the normalised StockCode as the primary product identifier.

This prevents casing differences from creating artificial product distinctions.

---

## 11. Product descriptions

Descriptions are not stable identifiers.

Among 4,778 normalised StockCodes with a description, 1,190 are associated with more than one normalised description.

Some differences reflect:

* wording changes;
* spelling variations;
* operational notes;
* damage or adjustment annotations;
* incorrect coding.

### Decision

Use normalised StockCode rather than Description as the primary identifier for product-breadth measures.

Description remains useful for interpretation, transaction classification and data-quality investigation.

---

## 12. Customer country

Of 5,942 identifiable customers:

* 5,929 are associated with one country;
* 13 are associated with two countries.

Multi-country customers therefore represent approximately 0.22% of identifiable customers.

### Decision

Do not assume Country is inherently unique at customer level.

If a single customer country is required later, define an explicit assignment rule rather than relying on arbitrary row order.

Country is not currently expected to be a core segmentation feature.

---

## 13. Commercial outliers

The positive customer-identified transaction data is strongly right-skewed.

For positive-sale rows:

* median quantity is 5;
* 99th percentile quantity is 128;
* 99.9th percentile quantity is 576;
* maximum quantity is 80,995.

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

* 4,376 identifiable customers appear in the behavioural window;
* 4,338 have at least one positive-sale row;
* 3,499 identifiable customers appear in the validation window;
* 2,500 behavioural-window customers are also observed during validation;
* 999 validation customers were not observed in the behavioural window.

### Decision

The final segmentation population will be defined from information available at the 31 May 2011 snapshot only.

Validation-period behaviour must not be used to construct the segments.

The validation period will be used only to assess whether snapshot-defined segments distinguish subsequent customer behaviour.

---

## 15. Transaction treatment matrix

The customer-level analysis separates three concepts that should not automatically be treated in the same way:

* **customer activity** — evidence of genuine customer purchasing activity;
* **observed net sales** — the signed monetary contribution used when measuring observed customer value;
* **product breadth** — whether the normalised StockCode counts as a distinct product purchased by the customer.

A transaction can therefore contribute to one measure without contributing to the others.

| Transaction class                                               | Customer activity      | Observed net sales                         | Product breadth | Treatment rationale                                                                                                                                                                       |
| --------------------------------------------------------------- | ---------------------- | ------------------------------------------ | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ordinary positive merchandise sale                              | Yes                    | Include signed `Quantity × Price`          | Yes             | Genuine merchandise purchase.                                                                                                                                                             |
| Customer cancellation / return                                  | No                     | Include negative signed `Quantity × Price` | No              | Returns reduce observed customer value but should not make a customer appear more recently or frequently active.                                                                          |
| Non-cancellation negative-quantity stock/inventory adjustment   | No                     | Exclude                                    | No              | Operational stock activity rather than customer behaviour.                                                                                                                                |
| Bad-debt accounting adjustment                                  | No                     | Exclude                                    | No              | Accounting adjustment rather than customer purchasing behaviour.                                                                                                                          |
| Genuine zero-price merchandise                                  | Yes                    | Include at £0                              | Yes             | Can represent genuine customer/product activity even though it contributes no sales value.                                                                                                |
| Customer-facing postage / carriage                              | No additional activity | Include signed line value                  | No              | A genuine customer charge, but not another purchase event or product.                                                                                                                     |
| Explicit discount                                               | No additional activity | Include signed line value                  | No              | Reduces observed customer value but is not a product or additional purchasing event.                                                                                                      |
| Bank charge                                                     | No                     | Exclude                                    | No              | Accounting or merchant-cost activity rather than customer purchasing behaviour.                                                                                                           |
| Amazon/platform fee                                             | No                     | Exclude                                    | No              | Retailer/platform cost rather than customer purchasing behaviour.                                                                                                                         |
| Commission / `CRUK`-type entry                                  | No                     | Exclude                                    | No              | Non-merchandise accounting or commission activity.                                                                                                                                        |
| Administrative adjustment, including `ADJUST` / `ADJUST2`       | No                     | Exclude                                    | No              | Back-office adjustment rather than genuine customer activity.                                                                                                                             |
| Explicit test record, including `TEST001` / `TEST002`           | No                     | Exclude                                    | No              | Test activity should not enter customer measures.                                                                                                                                         |
| Sample, including `S`                                           | No                     | Exclude                                    | No              | Marketing/sample activity is not evidence that the customer purchased the item.                                                                                                           |
| Gift-voucher sale                                               | Yes                    | Include signed line value                  | No              | Represents observed customer spend/activity, but not merchandise breadth. This is an analytical transaction-value definition rather than statutory revenue recognition.                   |
| Manual `M` / `m` entry                                          | No additional activity | Include signed line value                  | No              | Manual entries show substantial correction/reversal behaviour. Retaining their signed financial effect preserves those corrections while avoiding interpretation as ordinary merchandise. |
| Unusual StockCode that otherwise represents genuine merchandise | Yes                    | Include signed `Quantity × Price`          | Yes             | Non-standard code format alone is not evidence that a row is non-product.                                                                                                                 |
| Unresolved or ambiguous special code                            | Investigate            | Investigate                                | Investigate     | Do not silently classify an unresolved code. Surface it for review before final customer features are produced.                                                                           |

### 15.1 Missing Customer ID

Transactions without an identifiable Customer ID remain part of source-level reconciliation and limitation reporting but cannot contribute to customer-level activity, observed-value or product-breadth measures.

After the cleaned transaction layer is created, recalculate the proportion of commercial activity excluded because Customer ID is missing.

### 15.2 Exact duplicates within retained source sheets

Exact duplicates remaining after removal of the proven cross-sheet overlap are retained in the primary analytical dataset.

There is no transaction-line identifier that allows an apparently duplicated row to be distinguished reliably from two legitimate identical entries.

The transaction treatment therefore follows the row's underlying transaction class.

If final segment membership appears materially sensitive to these duplicates, compare the primary result with a deduplicated sensitivity version.

### 15.3 StockCode standardisation

Before transaction classification and product-breadth calculation:

1. strip surrounding whitespace from StockCode;
2. standardise StockCode to uppercase;
3. use the normalised StockCode as the primary product identifier.

Description remains useful for interpretation but is not sufficiently stable to act as the product key.

### 15.4 Returns and behavioural measures

Customer cancellations and returns reduce observed net sales but do not independently contribute to:

* recency;
* purchase frequency;
* active months;
* product breadth.

This prevents a recent return from making an otherwise inactive customer appear recently active.

### 15.5 Postage, discounts and other non-product charges

Customer-facing postage/carriage and explicit discounts affect observed net sales using their signed monetary value.

They do not independently contribute to purchasing activity or product breadth.

This prevents administrative or invoice-level financial lines from artificially increasing behavioural frequency or the apparent number of products purchased.

### 15.6 Gift vouchers

A gift-voucher sale to an identifiable customer is treated as genuine customer activity and contributes its signed transaction value to observed customer value.

It does not count towards merchandise product breadth.

This is an analytical definition of observed customer transaction value. It should not be interpreted as a statement about statutory revenue-recognition treatment.

### 15.7 Manual-entry sensitivity

Manual entries are included in observed net sales at their signed value because profiling found substantial correction/reversal behaviour.

They do not count as ordinary purchase activity or product breadth.

If Manual entries materially influence customer-value distributions or final segment membership, rerun the relevant analysis excluding them as a sensitivity check.

### 15.8 Unresolved classifications

The cleaning process must not silently default an unfamiliar special StockCode to either merchandise or administrative activity.

Any unresolved transaction class should be surfaced explicitly for investigation before the customer-feature layer is considered final.

### 15.9 Classification precedence and diagnostic flags

Some rows can satisfy more than one descriptive condition. Transaction classification must therefore follow a deterministic precedence rather than depend on the order in which implementation code happens to run.

The first implementation and subsequent classification QA showed that a specific known transaction code can provide more useful business meaning than the generic `C`-invoice cancellation indicator. For example, a `D` discount line may itself appear on a cancellation invoice.

The final precedence is therefore:

1. **Known hard exclusions**
   Bad-debt adjustments, bank charges, Amazon/platform fees, commission/`CRUK`-type entries, administrative adjustments, tests and samples.

2. **Explicit administrative records identified from row context**
   Records whose description and other characteristics establish an administrative purpose despite an otherwise genuine-looking StockCode.

3. **Operational non-customer stock adjustments**
   Non-cancellation negative-quantity records representing losses, damage, shortages or other inventory adjustments.

4. **Manual `M` / `m` transactions**
   Manual entries retain their signed financial effect but do not independently contribute to purchasing activity or product breadth.

5. **Recognised non-product customer financial lines**
   Postage/carriage, explicit discounts and gift vouchers receive their individually defined treatments from the transaction-treatment matrix.

6. **Customer cancellations / returns**
   Remaining `C`-prefixed customer transactions retain their signed financial effect but do not independently contribute to purchasing activity or product breadth.

7. **Genuine merchandise**
   This includes ordinary positive-price merchandise, genuine zero-price merchandise and genuine products whose StockCodes use unusual but reviewed and valid formats.

8. **Unresolved or ambiguous records**
   Records that still cannot be classified confidently are surfaced for investigation rather than silently defaulted to merchandise or administrative activity.

The cleaned transaction layer preserves useful diagnostic characteristics separately from the primary transaction class.

Useful row-level fields include:

* `has_customer_id`;
* `is_cancellation`;
* `is_manual`;
* `is_zero_price`;
* `transaction_class`;
* `counts_as_activity`;
* `counts_in_net_sales`;
* `counts_in_product_breadth`.

This means, for example, that assigning a `D` row to the `discount` transaction class does not erase the fact that the transaction was also recorded on a cancellation invoice.

The purpose of the primary class is to provide the most specific reproducible business interpretation available for each row. Supporting flags preserve overlapping source characteristics needed for validation, reconciliation and sensitivity analysis.

### 15.10 Retention of classified source rows

The cleaned transaction layer should retain all rows from the corrected 1,044,848-row source rather than physically removing records that do not contribute to customer analysis.

Excluded transaction classes should remain available with explicit classification and treatment flags showing that they do not contribute to the relevant customer measures.

This preserves:

* traceability back to the corrected source;
* reconciliation between source and cleaned data;
* visibility of excluded activity;
* the ability to review or revise a classification without reconstructing discarded rows.

Rows without Customer ID should also remain in this classified transaction layer even though they cannot enter customer-level segmentation.

### 15.11 Analytical-period labelling

The cleaned transaction layer should retain the complete corrected source date range rather than restricting the stored data to the behavioural and validation windows.

Each transaction should be assigned an explicit analytical-period label.

The principal periods are:

* **pre-behavioural** — before 1 June 2010;
* **behavioural** — 1 June 2010 to 31 May 2011;
* **validation** — 1 June 2011 to 30 November 2011;
* **outside analysis** — records after the validation window.

This allows downstream SQL and feature calculations to apply time-window filters explicitly and makes leakage controls easier to inspect.

The segmentation itself must use behavioural-period information available at the 31 May 2011 snapshot only.

### 15.12 Preservation of raw and cleaned fields

Source fields should be preserved wherever practical rather than overwritten during cleaning.

Normalised or analytical versions should be created as additional fields.

For example:

* retain the original `StockCode`;
* create a normalised StockCode with surrounding whitespace removed and case standardised;
* retain the source Description while allowing a cleaned Description field where useful;
* preserve original transaction quantities, prices and dates.

Valid Customer IDs should use an integer-compatible representation that also supports missing values.

This approach preserves source provenance while providing consistent analytical fields for downstream processing.

### 15.13 Row-level monetary measures

The cleaned transaction layer should contain both an unadjusted line-value calculation and the treatment-adjusted value used in customer analysis.

Define:

`raw_line_value = Quantity × Price`

for every transaction row.

Also create an `observed_net_sales` measure.

`observed_net_sales` should contain the signed line value where the transaction-treatment matrix says the row contributes to observed customer value and zero where the row is excluded from that measure.

Examples include:

* ordinary merchandise sale: signed line value included;
* cancellation/return: negative signed line value included;
* postage/carriage: signed line value included;
* explicit discount: signed line value included;
* Manual transaction: signed line value included;
* bank charge: zero;
* test transaction: zero;
* operational stock adjustment: zero.

Keeping both measures makes the effect of the analytical treatment explicit and supports reconciliation and validation.

### 15.14 Purchase-frequency definition deferred to customer-feature design

The transaction-cleaning stage should identify whether a row represents qualifying customer purchasing activity but should not itself define the final customer-level purchase-frequency measure.

A row-level activity indicator should therefore be created during cleaning.

The later customer-feature stage will define the appropriate aggregation, likely using distinct qualifying purchase invoices rather than transaction-line counts.

This prevents transaction cleaning from silently fixing a customer-level behavioural definition that should instead be assessed alongside the other segmentation features.

### 15.15 Unresolved-classification validation gate

The initial cleaning run may expose transactions that cannot yet be classified confidently.

Such rows should be reported explicitly rather than causing the first investigative run to fail or being silently assigned to a default category.

The workflow should be:

1. run transaction classification;
2. summarise unresolved records;
3. investigate any unresolved classes;
4. update and document the treatment where necessary;
5. rerun and validate the classification.

The customer-feature layer should not be considered ready to proceed while **material unresolved transaction classifications** remain.

This provides an explicit quality gate between transaction cleaning and customer-feature construction.

### 15.16 Generated cleaned-data artefact

The full classified transaction dataset is a generated analytical artefact rather than a source file that needs to be stored in the public Git repository.

The cleaned transaction dataset should therefore:

* be generated reproducibly by the cleaning pipeline;
* remain available locally for subsequent analysis and SQLite construction;
* be excluded from Git where its size makes repository storage inappropriate;
* be reproducible from the documented source data and tracked cleaning code.

The public repository should instead contain the cleaning logic, analytical documentation and appropriately sized validation or summary outputs required to understand and reproduce the process.

The storage format should be selected for practical analytical value rather than novelty. A new dependency such as Parquet support should only be introduced if it provides a material advantage for this project.

---

## 16. Overall cleaning principle

The cleaning approach is evidence-led rather than based on blanket rules.

The guiding process is:

> profile → question → investigate → decide → document → validate

Confirmed source errors are corrected.

Unusual records are not removed simply because they are inconvenient, extreme, duplicated or difficult to classify.

Different analytical measures are allowed to use different aspects of the same transaction where that reflects the business meaning of the record. For example, a return can reduce observed customer value without being treated as new purchasing activity.

Where the source does not provide enough evidence to make a definitive distinction, the assumption should be documented and, where material, tested through sensitivity analysis.

The transaction-treatment matrix is now settled.

The transaction-treatment methodology, classification precedence and cleaned-layer design are now settled. The next implementation step is to translate these decisions into the reproducible cleaning pipeline:

`python/02_clean_transactions.py`