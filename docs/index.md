# Customer Value & Retention Segmentation

**Turning historical retail transactions into practical retention, growth and reactivation priorities**

This project analyses customer purchasing behaviour for a UK online retailer and asks a practical CRM question:

> **Which customer groups should receive different retention, reactivation and growth treatment based on their recent purchasing value and behaviour?**

Rather than defining segments and judging them on the same data, the analysis fixes the customer view at **31 May 2011** and reserves the following six months of transactions to see whether the resulting groups actually behave differently afterwards.

[View the GitHub repository](https://github.com/jsklair/project_03_customer_value_segmentation)

---

## What the analysis found

The final segmentation covers **4,908 customers across eight mutually exclusive groups**.

Several differences persist strongly into the six-month held-out period:

* **High-value active customers** represent 16.4% of the eligible population but account for **71.7% of positive held-out customer value**. **91.8%** purchase again.
* **Core repeat customers** have an **81.3%** future purchase rate.
* Among lower-frequency behavioural customers, future purchase rates decline from **60.0% for Recent low-frequency**, to **49.2% for Cooling low-frequency**, to **35.1% for Drifting**.
* **High-value lapsed customers** show **21.4% observed reactivation**, compared with **12.6%** for other lapsed customers.

These results support differentiated CRM treatment rather than a single retention strategy for the entire customer base.

![Held-out purchase rate by customer segment](https://raw.githubusercontent.com/jsklair/project_03_customer_value_segmentation/main/visuals/02_future_purchase_rate_by_segment.png)

---

## The segmentation

The design is deliberately transparent rather than based on an opaque clustering model or generic additive RFM score.

Behavioural customers are differentiated using:

* **recency** since the latest qualifying purchase;
* **purchase frequency** over the trailing 12 months;
* **observed net customer value** over that period.

Historical-only customers are treated separately because their trailing-12-month purchasing measures are structurally zero. Their earlier observed value is therefore used to distinguish higher-priority reactivation candidates.

| Segment               | Customers | Share | Suggested CRM priority   |
| --------------------- | --------: | ----: | ------------------------ |
| High-value active     |       806 | 16.4% | Protect and retain       |
| High-value at risk    |        59 |  1.2% | Priority win-back        |
| Core repeat           |       321 |  6.5% | Nurture and grow         |
| Recent low-frequency  |     1,010 | 20.6% | Develop the relationship |
| Cooling low-frequency |       551 | 11.2% | Timely re-engagement     |
| Drifting              |     1,577 | 32.1% | Selective reactivation   |
| High-value lapsed     |       117 |  2.4% | Targeted reactivation    |
| Lapsed                |       467 |  9.5% | Low-cost reactivation    |

Behavioural high value is defined as the highest fifth of 12-month observed net sales, beginning at **£1,898.51**.

Historical-only customers are ranked separately using the earlier observed history available in the dataset. The high-value-lapsed boundary is **£552.40**.

---

## Why the segments are useful

The strongest test is what happens after the snapshot.

Across all 4,908 customers:

* **2,549** make at least one qualifying purchase during the next six months;
* the overall future purchase rate is **51.9%**;
* those customers generate **8,470 qualifying purchase invoices**;
* held-out observed net customer value totals **£4.17 million**.

The segment-level future purchase rates are:

| Segment               | Future purchase rate |
| --------------------- | -------------------: |
| High-value active     |            **91.8%** |
| Core repeat           |            **81.3%** |
| Recent low-frequency  |            **60.0%** |
| High-value at risk    |            **55.9%** |
| Cooling low-frequency |            **49.2%** |
| Drifting              |            **35.1%** |
| High-value lapsed     |            **21.4%** |
| Lapsed                |            **12.6%** |

The chart above includes **95% Wilson intervals** around these proportions. The smaller High-value at risk and High-value lapsed groups naturally have wider uncertainty than the larger segments.

The validation is descriptive and predictive, **not causal**. It shows that the snapshot groups distinguish later purchasing behaviour; it does not show that membership of a segment causes that behaviour or that a particular CRM campaign would generate uplift.

---

## High customer value persists

The concentration of customer value is not confined to the historical period used to create the segments.

High-value active customers generated:

* **70.2% of positive behavioural customer value** before the snapshot;
* **71.7% of positive held-out customer value** afterwards.

![Snapshot versus held-out positive value share](https://raw.githubusercontent.com/jsklair/project_03_customer_value_segmentation/main/visuals/03_snapshot_vs_future_value_share.png)

That concentration is partly driven by genuinely very large customers, but not entirely. After removing the highest 1% of behavioural customers by snapshot value, High-value active customers still have a **91.9%** future purchase rate and account for **58.7%** of positive held-out value.

This makes them an obvious retention priority, while also showing why blanket discounting across already-active high-value customers would be difficult to justify from this analysis alone.

---

## A separate reactivation opportunity

Customers with no qualifying purchase during the trailing 12 months are not all equally attractive reactivation targets.

The historical-only population was therefore split using earlier observed customer value.

![Held-out reactivation among lapsed customers](https://raw.githubusercontent.com/jsklair/project_03_customer_value_segmentation/main/visuals/04_lapsed_customer_reactivation.png)

Observed six-month reactivation is:

* **21.4% for High-value lapsed customers**
* **12.6% for other Lapsed customers**

That is an **8.8 percentage-point difference**, or approximately **1.70×** the observed reactivation rate.

The groups are relatively small, so this result should be treated as useful prioritisation evidence rather than a guarantee that a particular win-back campaign will succeed.

---

## From messy transactions to customer decisions

The project uses the **Online Retail II** dataset from the UCI Machine Learning Repository, covering transactions for a UK-based non-store retailer.

The source is useful precisely because it requires analytical judgement before customer segmentation can begin.

Key issues included:

* two annual worksheets containing **22,523 rows of proven duplicate source coverage**;
* **235,287 rows without Customer ID**;
* cancellations and returns that should reduce observed customer value without creating new purchasing activity;
* Manual and administrative entries that require different treatment from merchandise;
* ambiguous exact duplicates within the retained source;
* highly concentrated customer value;
* customer histories constrained by the start of the available data.

After transaction classification, **15.0% of positive classified transaction value cannot be attributed to an identifiable customer**. This activity remains part of reconciliation but cannot enter customer-level segmentation.

The analytical pipeline is:

```text
source profiling
→ evidence-led transaction classification
→ SQLite invoice and customer layers
→ snapshot-valid feature assessment
→ customer segmentation
→ held-out validation
→ sensitivity analysis
→ CRM priorities
```

The final behavioural customer value reconciles exactly between the transaction and customer layers at **£7,762,616.79**.

---

## Feature choices were evidence-led

The project deliberately avoids using every available customer measure as a segmentation dimension.

For example:

* purchase frequency and active months have a **Spearman correlation of 0.959**, so using both would largely count the same behaviour twice;
* observed tenure is affected by the beginning of the source history and is therefore descriptive rather than a primary segment rule;
* product breadth is useful for describing customers but is also strongly related to frequency and value;
* average qualifying purchase-invoice value adds context about purchase size without needing to become another segmentation axis.

The result is a smaller set of rules that a CRM stakeholder could understand, reproduce and act on.

[Read the full segmentation and validation methodology](https://github.com/jsklair/project_03_customer_value_segmentation/blob/main/docs/segmentation_and_validation_methodology.md)

---

## Robustness checks

The main segmentation was tested against the data-treatment decisions most likely to affect customer value.

### Exact duplicates

Removing all **11,812** ambiguous exact duplicate rows:

* changes behavioural observed value by **-0.34%**;
* changes only **6 of 4,908 customer segment assignments (0.12%)**.

### Manual financial entries

Removing the monetary effect of Manual entries:

* changes behavioural observed value by **+0.60%**;
* changes only **4 customer assignments (0.08%)**.

### Extreme customers

Removing the highest 1% of behavioural customers by snapshot value leaves the main future-purchase ordering intact.

The final segmentation is therefore not dependent on a single ambiguous cleaning decision or a handful of exceptionally large customers.

[Read the data-quality and cleaning decisions](https://github.com/jsklair/project_03_customer_value_segmentation/blob/main/docs/data_quality_and_cleaning_decisions.md)

---

## CRM implications

The analysis suggests different levels and types of attention rather than treating every inactive customer as equally valuable.

**High-value active**
Protect the relationship and service experience. Relevant loyalty or cross-sell activity may be appropriate, but the analysis does not support unnecessary blanket discounting.

**High-value at risk**
Treat as a small priority win-back group. Their purchasing is less recent, but their historical value and held-out behaviour justify disproportionate attention.

**Core repeat**
Nurture a strong repeat relationship and look for sensible opportunities to grow customer value.

**Recent low-frequency**
Encourage another purchase while the relationship remains recent, with the aim of developing occasional customers rather than assuming established loyalty.

**Cooling low-frequency**
Use timely, relatively low-cost re-engagement before inactivity deepens.

**Drifting**
Favour selective or automated reactivation rather than expensive intervention across a large lower-propensity population.

**High-value lapsed**
Prioritise within the long-lapsed population because earlier value identifies a group with higher observed reactivation.

**Lapsed**
Use lower-cost win-back activity or suppression rules where contact economics make more intensive treatment unattractive.

These are **CRM prioritisation hypotheses**, not estimates of campaign uplift. Testing actual interventions would require campaign-treatment and cost data that this dataset does not contain.

---

## Limitations

The most important limitations are:

* **15.0% of positive classified transaction value lacks an identifiable Customer ID** and cannot enter customer-level analysis.
* The source begins in December 2009, so observed customer histories may be shorter than the real relationship.
* Historical-only value represents available earlier history, not lifetime customer value.
* Customer value is strongly concentrated even though sensitivity testing shows that the main segment differentiation survives removal of the largest customers.
* Segment thresholds are specific to this retailer and snapshot and would need recalibration in another business or period.
* The held-out horizon is six months.
* The analysis contains no randomised CRM treatment and therefore cannot establish causal campaign effects.

---

## Tools used

* **Python / pandas** for source profiling, cleaning, feature assessment and final reporting
* **SQL / SQLite** for invoice-level modelling, customer features, segmentation, validation and sensitivity analysis
* **matplotlib** for final analytical visualisation
* **Git and GitHub** for version-controlled project development and review
* **GitHub Pages** for the employer-facing presentation

Power BI and Excel were not added simply for tool coverage. Both are demonstrated elsewhere in the portfolio, while this project benefits more from deeper SQL, Python and longitudinal customer analysis.

---

## Technical detail

For readers who want to inspect the implementation:

* [Repository](https://github.com/jsklair/project_03_customer_value_segmentation)
* [README](https://github.com/jsklair/project_03_customer_value_segmentation#readme)
* [Segmentation and validation methodology](https://github.com/jsklair/project_03_customer_value_segmentation/blob/main/docs/segmentation_and_validation_methodology.md)
* [Data-quality and cleaning decisions](https://github.com/jsklair/project_03_customer_value_segmentation/blob/main/docs/data_quality_and_cleaning_decisions.md)
* [Reproduce the analysis locally](https://github.com/jsklair/project_03_customer_value_segmentation/blob/main/docs/run_project_locally.md)
* [Final segment summary](https://github.com/jsklair/project_03_customer_value_segmentation/blob/main/reports/customer_segment_summary.csv)
* [CRM action summary](https://github.com/jsklair/project_03_customer_value_segmentation/blob/main/reports/customer_segment_actions.csv)

---

*Historical portfolio analysis using the UCI Online Retail II dataset. Results describe the supplied dataset and should not be interpreted as current performance for a real retailer.*
