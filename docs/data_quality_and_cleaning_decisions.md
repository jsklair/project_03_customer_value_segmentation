# Data Quality and Cleaning Decisions

## Status

**Source profiling, transaction cleaning, SQL feature engineering, final segmentation, held-out validation and sensitivity testing are complete.**

This document records the main data-quality findings from profiling the UCI Online Retail II dataset and the resulting analytical decisions for Project 03.

The aim is to distinguish between:

* confirmed source issues that should be corrected;
* unusual records that should be classified rather than removed automatically;
* limitations that affect the customer-level analytical population;
* assumptions whose materiality should be tested through sensitivity analysis.

The evidence-led transaction-treatment rules have been implemented and validated in the classified transaction layer. The downstream SQL, customer-population and sensitivity decisions that depend directly on those rules are also recorded here.

For the final feature-selection, segmentation and held-out validation methodology, see [`segmentation_and_validation_methodology.md`](segmentation_and_validation_methodology.md).

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

The retained rows receive the same transaction treatment as any other row of their underlying transaction class.

### Sensitivity result

A complete alternative scenario removing all **11,812** excess exact duplicate rows was tested after the final segmentation was designed.

The alternative treatment:

* reduces behavioural observed net sales by **0.34%**;
* changes final segment membership for only **6 of 4,908 customers (0.12%)**;
* moves the behavioural high-value boundary from **£1,898.51 to £1,884.36**;
* moves the historical-only high-value boundary from **£552.40 to £542.89**.

The primary decision to retain the ambiguous duplicate rows is therefore **not material to the final segmentation**.

---

## 3. Missing Customer ID

After correcting the worksheet overlap:

* 235,287 rows have no Customer ID.

Within the behavioural window from 1 June 2010 to 31 May 2011:

* 494,905 transaction rows are present;
* 111,777 rows have no Customer ID;
* this represents 22.6% of behavioural-window rows;
* approximately £1.52 million of raw positive transaction value cannot be assigned to a customer;
* this represents 15.6% of raw positive transaction value before final transaction classification.

No invoice contains a mixture of identified and unidentified customer rows.

### Decision

Transactions without a Customer ID cannot contribute to customer-level segmentation.

They are excluded from customer-level:

* activity;
* observed value;
* product breadth.

They remain in the classified transaction layer for reconciliation and limitation reporting.

After the final transaction-classification rules are applied, **15.0% of positive classified transaction value cannot be attributed to an identifiable customer**.

This is retained as an important limitation of the project.

---

## 4. Invoice-to-customer consistency

No invoice is linked to more than one identifiable Customer ID.

No invoice contains both identified and missing Customer ID rows.

### Decision

Invoice-level measures can safely be attributed to a single customer where a Customer ID is available.

---

## 5. Cancellations and negative quantities

The source uses invoice numbers beginning with `C` to identify cancellations.

Most negative-quantity rows correspond to cancellation invoices, but a smaller group does not.

Profiling showed that the non-cancellation negative rows:

* have zero price;
* have no Customer ID;
* frequently contain operational descriptions such as stock losses, damage or adjustments.

These appear to represent inventory or operational adjustments rather than customer transactions.

### Decision

Customer cancellation and return transactions are retained where needed to calculate observed net customer value.

Their signed negative value reduces observed net sales, but the return itself does not make a customer appear more recently or frequently active and does not contribute to product breadth.

Negative-quantity rows representing non-customer stock adjustments do not contribute to:

* customer purchasing behaviour;
* observed customer value;
* product breadth.

The cleaning pipeline explicitly distinguishes customer returns/cancellations from operational stock adjustments.

---

## 6. Negative prices

Five negative-price rows were identified.

They use StockCode `B`, description `Adjust bad debt`, have no Customer ID and contain large negative values.

### Decision

Treat these as accounting adjustments rather than customer purchases.

They do not contribute to:

* customer purchasing behaviour;
* observed customer value;
* product breadth.

---

## 7. Zero-price transactions

6,024 zero-price rows remain after correcting the source overlap.

Some identifiable zero-price transactions appear to represent genuine products, while others include test or administrative activity.

Examples include:

* ordinary merchandise codes;
* `TEST001`;
* Manual transactions.

### Decision

Do not remove zero-price rows solely because their price is zero.

A legitimate zero-price product may represent genuine customer and product activity while contributing £0 to observed net sales.

Explicit test, administrative, sample or other non-purchase records are treated according to their business meaning rather than being retained merely because a Customer ID is present.

---

## 8. Manual transactions (`M` / `m`)

Manual transactions are commercially material and include both positive and negative records.

Profiling found strong evidence of reversal and correction activity:

* many matching positive and negative price/quantity combinations;
* 172 perfectly balanced combinations;
* 422 Manual rows in those combinations, representing 30.1% of Manual rows after correcting the worksheet overlap.

Large Manual entries frequently form exact-value reversals or adjustments.

### Decision

Manual transactions are not treated as ordinary merchandise.

They:

* do not independently create customer purchasing activity;
* do not contribute to product breadth;
* contribute to observed net sales using their signed line value.

Including their signed monetary effect preserves correction and reversal behaviour already represented in the transaction ledger without treating the records as ordinary product purchases.

### Sensitivity result

The final segmentation was rerun with Manual entries excluded from observed customer value.

This alternative treatment:

* increases behavioural observed net sales by **0.60%** because Manual entries are net negative;
* changes final segment membership for only **4 of 4,908 customers (0.08%)**;
* moves the behavioural high-value boundary from **£1,898.51 to £1,902.84**;
* moves the historical-only high-value boundary from **£552.40 to £544.41**.

Manual-entry treatment is therefore **not material to the final segmentation**.

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
* Manual entries.

It also showed that non-standard StockCode formatting does not necessarily imply a non-product record. Several genuine merchandise codes do not follow a simple five-digit pattern.

### Decision

Do not classify transaction validity using StockCode format alone.

Known special transaction codes are classified according to their business meaning and treated separately for:

* customer activity;
* observed net sales;
* product breadth.

The agreed treatments are defined explicitly in Section 15.

An unfamiliar or ambiguous StockCode is not silently classified as either merchandise or administrative activity.

Material unresolved cases must be surfaced for investigation.

The final cleaning pipeline ends with **zero unresolved transaction classifications**.

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

If a single customer country is required, define an explicit assignment rule rather than relying on arbitrary row order.

Country is not used as a core segmentation feature in the final analysis.

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

Customer-level value is also highly concentrated:

* the largest customer accounts for 3.22% of positive observed behavioural value;
* the highest approximately 1% account for 28.92%;
* the top 5% account for 49.30%;
* the top 10% account for 61.57%;
* the top 20% account for 75.65%.

### Decision

Do not remove observations purely because they are extreme.

Outliers are retained unless there is evidence that they are invalid.

Because individual customers contribute substantial value, the final segment validation is also tested after removing the highest 1% of behavioural customers by snapshot observed value.

### Sensitivity result

After excluding the highest 1% of behavioural customers, the main held-out future-purchase ordering remains intact:

* High-value active: **91.9%**
* Core repeat: **81.3%**
* Recent low-frequency: **60.0%**
* High-value at risk: **55.9%**
* Cooling low-frequency: **49.2%**
* Drifting: **35.1%**

High-value active customers still account for **58.7% of positive held-out customer value** after the highest 1% are removed.

Extreme customers therefore contribute materially to commercial value concentration but **do not create the main behavioural differentiation between the segments**.

---

## 14. Behavioural and validation populations

The behavioural window is:

**1 June 2010 to 31 May 2011**

The held-out validation window is:

**1 June 2011 to 30 November 2011**

Initial source profiling found:

* 4,376 identifiable customers in the behavioural window;
* 4,338 with at least one positive-sale row;
* 3,499 identifiable customers in the validation window.

These raw-profile counts are superseded for segmentation by the cleaned qualifying-purchase definition.

### Final population decision

The segmentation population is defined solely from information available by the **31 May 2011 snapshot**.

The final eligible population contains **4,908 customers**:

* **4,324 behavioural purchasers** with at least one qualifying purchase during the trailing 12 months;
* **584 historical-only purchasers** with earlier qualifying purchase history but no qualifying purchase during the behavioural window.

A further **90 identified Customer IDs** have no qualifying purchase history in the available pre-snapshot data and are excluded.

Validation-period behaviour is not used to construct the segments.

### Final validation result

Across all 4,908 snapshot customers:

* **2,549** make at least one qualifying purchase during the six-month held-out period;
* overall future purchase rate: **51.9%**;
* future qualifying purchase invoices: **8,470**;
* held-out observed net sales: **£4,170,456.73**.

Segment-level future purchase rates range from:

* **91.8%** for High-value active customers;
* to **12.6%** for Lapsed customers.

Full validation results and interpretation are recorded in [`segmentation_and_validation_methodology.md`](segmentation_and_validation_methodology.md).

The validation is descriptive/predictive rather than causal.

---

## 15. Transaction treatment matrix

The customer-level analysis separates three concepts that should not automatically be treated in the same way:

* **customer activity** — evidence of genuine customer purchasing activity;
* **observed net sales** — the signed monetary contribution used when measuring observed customer value;
* **product breadth** — whether the normalised StockCode counts as a distinct product purchased by the customer.

A transaction can therefore contribute to one measure without contributing to the others.

| Transaction class                                             | Customer activity      | Observed net sales                         | Product breadth | Treatment rationale                                                                                              |
| ------------------------------------------------------------- | ---------------------- | ------------------------------------------ | --------------- | ---------------------------------------------------------------------------------------------------------------- |
| Ordinary positive merchandise sale                            | Yes                    | Include signed `Quantity × Price`          | Yes             | Genuine merchandise purchase.                                                                                    |
| Customer cancellation / return                                | No                     | Include negative signed `Quantity × Price` | No              | Returns reduce observed customer value but should not make a customer appear more recently or frequently active. |
| Non-cancellation negative-quantity stock/inventory adjustment | No                     | Exclude                                    | No              | Operational stock activity rather than customer behaviour.                                                       |
| Bad-debt accounting adjustment                                | No                     | Exclude                                    | No              | Accounting adjustment rather than customer purchasing behaviour.                                                 |
| Genuine zero-price merchandise                                | Yes                    | Include at £0                              | Yes             | Can represent genuine customer/product activity even though it contributes no sales value.                       |
| Customer-facing postage / carriage                            | No additional activity | Include signed line value                  | No              | Genuine customer financial effect, but not another purchase event or product.                                    |
| Explicit discount                                             | No additional activity | Include signed line value                  | No              | Reduces observed customer value but is not a product or additional purchasing event.                             |
| Bank charge                                                   | No                     | Exclude                                    | No              | Accounting or merchant-cost activity rather than customer behaviour.                                             |
| Amazon/platform fee                                           | No                     | Exclude                                    | No              | Retailer/platform cost rather than customer behaviour.                                                           |
| Commission / `CRUK` entry                                     | No                     | Exclude                                    | No              | Non-merchandise accounting or commission activity.                                                               |
| Administrative adjustment, including `ADJUST` / `ADJUST2`     | No                     | Exclude                                    | No              | Back-office adjustment rather than genuine customer activity.                                                    |
| Explicit test record, including `TEST001` / `TEST002`         | No                     | Exclude                                    | No              | Test activity should not enter customer measures.                                                                |
| Sample, including `S`                                         | No                     | Exclude                                    | No              | Marketing/sample activity is not evidence that the customer purchased the item.                                  |
| Gift-voucher sale                                             | Yes                    | Include signed line value                  | No              | Represents observed customer spend/activity but not merchandise breadth.                                         |
| Manual `M` / `m` entry                                        | No additional activity | Include signed line value                  | No              | Preserves correction/reversal effects while avoiding interpretation as ordinary merchandise.                     |
| Unusual StockCode representing genuine merchandise            | Yes                    | Include signed `Quantity × Price`          | Yes             | Non-standard code format alone is not evidence that a row is non-product.                                        |
| Unresolved or ambiguous special code                          | Investigate            | Investigate                                | Investigate     | Do not silently classify an unresolved code.                                                                     |

### 15.1 Missing Customer ID

Transactions without an identifiable Customer ID remain part of source-level reconciliation and limitation reporting but cannot contribute to customer-level:

* activity;
* observed value;
* product breadth.

After final classification, **15.0% of positive classified transaction value cannot be attributed to an identifiable customer**.

### 15.2 Exact duplicates within retained source sheets

Exact duplicates remaining after removal of the proven cross-sheet overlap are retained in the primary analytical dataset.

There is no transaction-line identifier that allows an apparently duplicated row to be distinguished reliably from two legitimate identical entries.

The transaction treatment therefore follows the row's underlying transaction class.

The completed deduplication sensitivity test changes only **6 of 4,908 segment assignments (0.12%)**, so this treatment is not material to the final segmentation.

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

This prevents invoice-level financial lines from artificially increasing behavioural frequency or the apparent number of products purchased.

### 15.6 Gift vouchers

A gift-voucher sale to an identifiable customer is treated as genuine customer activity and contributes its signed transaction value to observed customer value.

It does not count towards merchandise product breadth.

This is an analytical definition of observed transaction value and should not be interpreted as a statement about statutory revenue-recognition treatment.

### 15.7 Manual-entry sensitivity

Manual entries are included in observed net sales at their signed value because profiling found substantial correction/reversal behaviour.

They do not count as ordinary purchase activity or product breadth.

The completed sensitivity analysis excluding Manual monetary effects changes only **4 of 4,908 segment assignments (0.08%)**.

The Manual-entry treatment is therefore not material to the final segmentation.

### 15.8 Unresolved classifications

The cleaning process must not silently default an unfamiliar special StockCode to either merchandise or administrative activity.

Any unresolved transaction class is surfaced explicitly for investigation.

The final classified transaction layer contains **zero unresolved classifications**.

### 15.9 Classification precedence and diagnostic flags

Some rows can satisfy more than one descriptive condition. Transaction classification therefore follows a deterministic precedence rather than depending on the implementation order of individual rules.

The final precedence is:

1. **Known hard exclusions**
   Bad-debt adjustments, bank charges, Amazon/platform fees, commission/`CRUK` entries, administrative adjustments, tests and samples.

2. **Explicit administrative records identified from row context**
   Records whose description and other characteristics establish an administrative purpose despite an otherwise genuine-looking StockCode.

3. **Operational non-customer stock adjustments**
   Non-cancellation negative-quantity records representing losses, damage, shortages or other inventory adjustments.

4. **Manual `M` / `m` transactions**
   Manual entries retain their signed financial effect but do not independently contribute to purchasing activity or product breadth.

5. **Recognised non-product customer financial lines**
   Postage/carriage, explicit discounts and gift vouchers receive their individually defined treatments.

6. **Customer cancellations / returns**
   Remaining `C`-prefixed customer transactions retain their signed financial effect but do not independently contribute to purchasing activity or breadth.

7. **Genuine merchandise**
   Ordinary positive-price merchandise, genuine zero-price merchandise and reviewed genuine products with unusual StockCodes.

8. **Unresolved or ambiguous records**
   Surfaced for investigation rather than silently defaulted to another category.

The cleaned transaction layer preserves diagnostic characteristics separately from the primary transaction class.

Useful row-level fields include:

* `has_customer_id`;
* `is_cancellation`;
* `is_manual`;
* `is_zero_price`;
* `transaction_class`;
* `counts_as_activity`;
* `counts_in_net_sales`;
* `counts_in_product_breadth`.

This means, for example, that assigning a `D` row to the `discount` transaction class does not erase the fact that the source invoice may also be a cancellation invoice.

### 15.10 Retention of classified source rows

The cleaned transaction layer retains all rows from the corrected **1,044,848-row source** rather than physically deleting records that do not contribute to customer analysis.

Excluded transaction classes remain available with explicit classification and treatment flags.

This preserves:

* source traceability;
* reconciliation;
* visibility of excluded activity;
* the ability to review or revise classifications.

Rows without Customer ID also remain in this layer.

### 15.11 Analytical-period labelling

The classified transaction layer retains the complete corrected source date range.

Each transaction receives an explicit analytical-period label:

* **pre-behavioural** — before 1 June 2010;
* **behavioural** — 1 June 2010 to 31 May 2011;
* **validation** — 1 June 2011 to 30 November 2011;
* **outside analysis** — records after the validation window.

This makes downstream filters and leakage controls explicit.

Segment construction uses only information available by the 31 May 2011 snapshot.

### 15.12 Preservation of raw and cleaned fields

Source fields are preserved wherever practical rather than overwritten.

Normalised or analytical versions are created alongside them.

For example:

* original `StockCode` is retained;
* normalised StockCode strips whitespace and standardises case;
* source Description is retained alongside cleaned Description;
* original quantities, prices and dates remain available.

Valid Customer IDs use an integer-compatible representation supporting missing values.

### 15.13 Row-level monetary measures

The cleaned transaction layer contains both an unadjusted line-value calculation and treatment-adjusted monetary measures.

Define:

`raw_line_value = Quantity × Price`

for every transaction row.

`observed_net_sales` then contains the signed line value where the transaction-treatment matrix says the row contributes to customer value, and zero where it is excluded.

Examples:

* merchandise sale: signed line value included;
* cancellation/return: signed negative line value included;
* postage/carriage: signed line value included;
* discount: signed line value included;
* Manual entry: signed line value included;
* bank charge: zero;
* test transaction: zero;
* operational stock adjustment: zero.

Keeping both measures makes the analytical treatment transparent and supports reconciliation.

### 15.14 Purchase-frequency definition

Transaction cleaning identifies whether a row represents qualifying purchasing activity but does not use transaction-line counts as customer frequency.

The customer-feature stage settles purchase frequency as:

> **the number of distinct qualifying purchase invoices during the behavioural window from 1 June 2010 to 31 May 2011**

Returns, cancellations and non-purchase financial adjustments do not create additional frequency.

Historical-only eligible customers therefore have behavioural purchase frequency equal to zero.

### 15.15 Unresolved-classification validation gate

The cleaning workflow is:

1. run transaction classification;
2. summarise unresolved records;
3. investigate unresolved classes;
4. update and document treatments;
5. rerun and validate classification.

The customer-feature layer cannot proceed while material unresolved classifications remain.

The final cleaning run passes this gate with **zero unresolved transaction classifications**.

### 15.16 Generated cleaned-data artefact

The full classified transaction dataset is a generated analytical artefact rather than a source file stored in the public repository.

It is:

* generated reproducibly by the cleaning pipeline;
* retained locally for downstream analysis and SQLite construction;
* excluded from Git because of its size;
* reproducible from the documented source and tracked cleaning code.

The public repository contains the cleaning logic, methodology and appropriately sized validation/summary outputs instead.

---

## 16. Overall cleaning principle

The cleaning approach is evidence-led rather than based on blanket rules.

The guiding process is:

> profile → question → investigate → decide → document → validate

Confirmed source errors are corrected.

Unusual records are not removed simply because they are inconvenient, extreme, duplicated or difficult to classify.

Different analytical measures are allowed to use different aspects of the same transaction where that reflects its business meaning.

For example, a return can reduce observed customer value without being treated as new purchasing activity.

Where the source does not provide enough evidence for a definitive distinction, the assumption is documented and, where material, tested through sensitivity analysis.

The transaction-treatment methodology, classification precedence, cleaned-layer design and material sensitivity checks are now implemented and validated.

---

## 17. SQL/SQLite analytical foundation

The classified transaction layer is loaded reproducibly into a local SQLite database.

The SQL stage provides a second analytical layer rather than merely repeating the pandas work.

### 17.1 Database construction

`python/03_build_database.py` loads the complete classified transaction dataset into SQLite as `classified_transactions`.

The database build validates the expected:

* **1,044,848 rows**;
* analytical-period counts;
* schema;
* transaction classifications.

Indexes support the main invoice, customer, period and class lookups.

The generated database remains local and is excluded from Git.

### 17.2 Invoice layer

`sql/02_create_invoice_layer.sql` creates one analytical row per source invoice.

The validated invoice layer contains:

**53,628 invoices**

No invoice:

* contains more than one identifiable customer;
* mixes identified and unidentified customer rows;
* spans more than one analytical period.

### 17.3 Multiple invoice timestamps

83 invoices contain transaction lines recorded at more than one timestamp.

Investigation found:

* 82 span no more than five minutes;
* the maximum span is nine minutes;
* every affected invoice remains on a single calendar date.

### Decision

Use the **first recorded invoice timestamp** consistently for invoice-level timing.

This does not materially alter day-level recency.

### 17.4 Customer eligibility

A Customer ID alone is not enough for segmentation eligibility.

The customer must have evidence of at least one **qualifying purchase on or before the snapshot date**.

The final eligible population contains:

* **4,908 customers**;
* **4,324 behavioural purchasers**;
* **584 historical-only purchasers**.

A further:

**90 identified Customer IDs**

have no qualifying purchase history and are excluded.

Historical-only customers remain in scope because the business question includes **reactivation**.

### 17.5 Purchase frequency

Purchase frequency is defined as:

> **distinct qualifying purchase invoices during the trailing 12-month behavioural window**

Because the invoice layer contains one row per invoice, qualifying invoice rows represent purchase occasions directly.

Returns and non-purchase adjustments do not create frequency.

Historical-only customers have frequency equal to zero.

### 17.6 Snapshot customer measures

The validated base customer snapshot layer contains:

* recency;
* observed tenure;
* pre-behavioural purchase invoices;
* 12-month purchase frequency;
* active months;
* 12-month observed net sales;
* product breadth;
* behavioural/historical-only population flags.

Recency is based on the most recent **qualifying purchase**, not the most recent return or adjustment.

Product breadth uses distinct normalised StockCodes across qualifying merchandise lines.

Observed tenure describes only the period visible in the source and is not treated as true lifetime tenure.

### 17.7 Enriched segmentation features

Feature analysis led to a second segmentation-oriented layer adding:

* prior purchase invoices;
* prior active months;
* prior observed net sales;
* prior product breadth;
* average qualifying purchase-invoice value;
* previous three-month purchase frequency/value;
* recent three-month purchase frequency/value;
* recent activity pattern.

Historical-only customers require prior observed value because their trailing-12-month purchasing measures are structurally zero.

### 17.8 Monetary reconciliation

Behavioural observed net sales for the final eligible segmentation population reconcile exactly between the customer feature layer and transaction layer at:

**£7,762,616.79**

The 90 identified but ineligible Customer IDs account for the difference between this eligible-population total and the broader identified-customer total.

### 17.9 Final segmentation

The final segmentation contains eight mutually exclusive and collectively exhaustive groups:

* High-value active;
* High-value at risk;
* Core repeat;
* Recent low-frequency;
* Cooling low-frequency;
* Drifting;
* High-value lapsed;
* Lapsed.

Behavioural high value is defined as the highest fifth of observed 12-month net sales.

The empirical behavioural boundary is:

**£1,898.51**

Historical-only high value is defined independently using prior observed net sales.

The empirical boundary is:

**£552.40**

The complete segment-design rationale is documented in [`segmentation_and_validation_methodology.md`](segmentation_and_validation_methodology.md).

### 17.10 Held-out validation

Segment definitions are frozen before examining validation-period outcomes.

During the six-month held-out period:

* **2,549 of 4,908 customers (51.9%)** make a qualifying purchase;
* the population generates **8,470 qualifying purchase invoices**;
* held-out observed net sales total **£4,170,456.73**.

Future purchase rates range from:

* High-value active: **91.8%**;
* Core repeat: **81.3%**;
* Recent low-frequency: **60.0%**;
* High-value at risk: **55.9%**;
* Cooling low-frequency: **49.2%**;
* Drifting: **35.1%**;
* High-value lapsed: **21.4%**;
* Lapsed: **12.6%**.

The results demonstrate useful subsequent-behaviour differentiation but are **not interpreted causally**.

### 17.11 Sensitivity conclusion

The three principal robustness questions have been resolved:

* exact-deduplication changes **0.12%** of segment assignments;
* excluding Manual monetary effects changes **0.08%**;
* excluding the highest 1% of behavioural customers does not change the main future-purchase ordering.

The final segmentation is therefore not dependent on a single ambiguous cleaning decision or on a handful of exceptionally large customers.

---

## 18. Final data-quality conclusion

The project does not attempt to create an artificially pristine retail dataset.

Instead, it preserves the commercial complexity of the source while making explicit distinctions between:

* genuine purchasing activity;
* customer financial effects;
* product activity;
* operational adjustments;
* accounting records;
* unidentified activity;
* genuinely ambiguous records.

The most material uncertain treatment decisions were carried through to the completed segmentation and tested directly.

The resulting customer groups remain stable under those alternatives and show substantial differentiation in held-out purchasing behaviour.

The remaining limitations — particularly missing Customer IDs, finite historical coverage and highly concentrated customer value — are therefore documented as limitations rather than hidden through aggressive data removal.
