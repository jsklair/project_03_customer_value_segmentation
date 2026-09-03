# Segmentation and Validation Methodology

## Purpose

This document records how the final customer segments for Project 03 were designed, tested and validated.

The business question is:

> Which customer groups should a CRM or Customer Insight Manager prioritise for different retention, reactivation and growth activity based on recent purchasing value and behaviour?

Segments are defined at a fixed **31 May 2011 snapshot**. Transactions from **1 June to 30 November 2011** are held out until after segment assignment and are used only to assess whether the snapshot-defined groups distinguish subsequent customer behaviour.

The validation is descriptive and predictive rather than causal. Differences in later purchasing behaviour do not show that segment membership caused those differences.

---

## 1. Final analytical population

The segmentation population contains **4,908 identifiable customers with evidence of at least one qualifying purchase by 31 May 2011**:

* **4,324 behavioural purchasers** made at least one qualifying purchase during the trailing 12-month behavioural window from 1 June 2010 to 31 May 2011.
* **584 historical-only purchasers** had qualifying purchase history before the behavioural window but made no qualifying purchase during it.

A further **90 identified Customer IDs** have no qualifying purchase history in the available pre-snapshot data and are excluded.

Behavioural observed net sales for the final eligible population reconcile to the transaction layer at:

**£7,762,616.79**

---

## 2. Candidate feature assessment

The initial customer snapshot layer contained:

* recency;
* 12-month purchase frequency;
* active months;
* 12-month observed net sales;
* product breadth;
* observed tenure.

Additional candidates investigated included:

* average qualifying purchase-invoice value;
* recent-versus-previous three-month purchasing activity;
* earlier observed value and purchasing behaviour for historical-only customers.

### 2.1 Distribution and concentration

Customer behaviour is strongly right-skewed.

Among all eligible customers:

* median 12-month purchase frequency: **2**;
* median observed net sales: **£526.50**;
* median product breadth: **28** products.

Among behavioural purchasers:

* median purchase frequency: **2**;
* median observed net sales: **£634.20**;
* median product breadth: **35** products.

Observed value is highly concentrated:

* largest customer: **3.22%** of positive observed value;
* top approximately 1%: **28.92%**;
* top 5%: **49.30%**;
* top 10%: **61.57%**;
* top 20%: **75.65%**.

This makes mean-based or arbitrary raw-value thresholds vulnerable to a relatively small number of very large customers.

### 2.2 Feature redundancy

Spearman rank correlations were used because the customer measures are strongly skewed and contain genuine extreme observations.

Important correlations among behavioural purchasers were:

| Feature pair                             | Spearman correlation |
| ---------------------------------------- | -------------------: |
| Purchase frequency vs active months      |                0.959 |
| Purchase frequency vs observed net sales |                0.813 |
| Active months vs observed net sales      |                0.801 |
| Observed net sales vs product breadth    |                0.738 |
| Purchase frequency vs product breadth    |                0.653 |

Purchase frequency and active months are therefore too similar to justify using both as independent segmentation axes.

**Decision:** use purchase frequency as the primary engagement measure because its business definition is simpler and more directly actionable. Retain active months as a descriptive characteristic.

Product breadth is also retained as a segment descriptor rather than an independent segmentation dimension.

### 2.3 Observed tenure

Observed tenure is constrained by the left boundary of the dataset:

* **19.4%** of eligible customers are first observed during December 2009, the first source month;
* **34.5%** are first observed within the first three months.

Customers already trading with the retailer before the dataset begins can therefore appear artificially new.

**Decision:** retain observed tenure as descriptive context but do not use it to assign segments.

### 2.4 Average purchase-invoice value

Average qualifying purchase-invoice value has a Spearman correlation of only **0.165** with purchase frequency, but **0.668** with total observed net sales.

It therefore adds useful descriptive information about whether customer value comes from many purchases or large individual purchases.

However, it is deliberately different from observed net sales. Standalone returns and financial adjustments belong in net customer value but do not create a qualifying purchase occasion.

**Decision:** retain average qualifying purchase-invoice value as a segment descriptor rather than a segmentation axis.

### 2.5 Recent activity pattern

Purchasing activity was compared across two equal three-month windows immediately before the snapshot:

* previous period: 1 December 2010 to 28 February 2011;
* recent period: 1 March to 31 May 2011.

Among behavioural purchasers:

| Activity pattern | Customers | Share |
| ---------------- | --------: | ----: |
| Both periods     |       955 | 22.1% |
| Recent only      |     1,036 | 24.0% |
| Previous only    |       725 | 16.8% |
| Neither period   |     1,608 | 37.2% |

The categorical activity pattern provides useful interpretation, but it is strongly related to recency and is not required as another independent segmentation dimension.

**Decision:** retain it as supporting evidence when interpreting segments.

---

## 3. Historical-only reactivation features

The 584 historical-only customers have structurally zero behavioural-window:

* purchase frequency;
* active months;
* product breadth.

Their behavioural-period observed net sales are also not a useful representation of previous customer importance. Collectively they record **-£26,881.42** during the behavioural window, largely because of later Manual adjustments, cancellations/returns and postage effects rather than new purchasing.

Earlier observed history was therefore assessed separately.

All **584** historical-only customers have a qualifying earlier purchase and:

* **578** have positive prior observed net sales;
* 3 have zero prior value;
* 3 have negative prior value.

Prior observed net sales range from **-£450.04** to **£30,411.26**, with:

* median: **£277.81**;
* p90: **£1,011.82**;
* p99: **£8,421.47**.

Previous value is also concentrated: the highest-value 5% account for **46.17%** of positive prior observed value.

Prior purchase frequency and active months offer less separation because the available earlier history is relatively short:

* median prior purchase invoices: **1**;
* median prior active months: **1**.

**Decision:** use prior observed net sales to distinguish higher-priority historical-only reactivation customers. Retain prior frequency and breadth as supporting descriptors.

These measures describe only the customer history available in the source and should not be interpreted as lifetime customer value.

---

## 4. Final segmentation design

The final design is hierarchical rather than a conventional additive RFM score.

This makes each rule directly interpretable and allows historical-only customers to be treated according to measures that are meaningful for them.

### 4.1 Behavioural high-value boundary

Behavioural purchasers are ranked by 12-month observed net sales.

The highest-value fifth contains **865 customers**.

The empirical boundary is:

* minimum top-fifth value: **£1,898.51**;
* maximum value outside the top fifth: **£1,895.00**.

The top-fifth rule is used as a commercial prioritisation tier. It is not combined with arbitrary RFM scores.

### 4.2 Historical-only high-value boundary

Historical-only customers are independently ranked by prior observed net sales.

The highest-value fifth contains **117 customers**.

The empirical boundary is:

* minimum high-value lapsed prior value: **£552.40**;
* maximum other lapsed prior value: **£544.41**.

### 4.3 Recency and frequency rules

The remaining behavioural segmentation uses simple CRM decision horizons:

* **90 days**: approximately a three-month recent-customer horizon;
* **180 days**: approximately a six-month deterioration/risk horizon;
* **5+ qualifying purchases**: repeat-purchase threshold above the observed p75 boundary of 4 purchases.

### 4.4 Final rules

Rules are applied in the following order:

| Segment               | Final rule                                                        |
| --------------------- | ----------------------------------------------------------------- |
| High-value lapsed     | Historical-only customer in the top fifth of prior observed value |
| Lapsed                | Other historical-only customer                                    |
| High-value active     | Behavioural top-value-fifth customer with recency ≤180 days       |
| High-value at risk    | Behavioural top-value-fifth customer with recency >180 days       |
| Core repeat           | Not already high value; frequency ≥5 and recency ≤180 days        |
| Recent low-frequency  | Remaining behavioural customer with recency ≤90 days              |
| Cooling low-frequency | Remaining behavioural customer with recency 91–180 days           |
| Drifting              | Remaining behavioural customer with recency >180 days             |

The hierarchy is **mutually exclusive and collectively exhaustive** across all 4,908 eligible customers.

---

## 5. Final snapshot segment profile

| Segment               | Customers | Population share | Avg recency | Avg frequency | Avg observed net sales |
| --------------------- | --------: | ---------------: | ----------: | ------------: | ---------------------: |
| High-value active     |       806 |            16.4% |   39.6 days |         11.85 |              £6,785.59 |
| High-value at risk    |        59 |             1.2% |  230.7 days |          3.58 |              £3,497.38 |
| Core repeat           |       321 |             6.5% |   54.7 days |          6.59 |              £1,285.41 |
| Recent low-frequency  |     1,010 |            20.6% |   41.5 days |          2.20 |                £643.87 |
| Cooling low-frequency |       551 |            11.2% |  135.6 days |          2.06 |                £567.61 |
| Drifting              |     1,577 |            32.1% |  242.4 days |          1.64 |                £468.16 |
| High-value lapsed     |       117 |             2.4% |  427.0 days |             0 |                      - |
| Lapsed                |       467 |             9.5% |  453.4 days |             0 |                      - |

For historical-only customers, earlier observed history is more informative than behavioural-window value:

| Segment           | Avg prior invoices | Avg prior observed value | Avg prior product breadth |
| ----------------- | -----------------: | -----------------------: | ------------------------: |
| High-value lapsed |               2.59 |                £2,010.81 |                      51.7 |
| Lapsed            |               1.21 |                  £235.20 |                      18.0 |

---

## 6. Held-out validation

Segment definitions are frozen before validation.

The validation period covers **1 June to 30 November 2011**.

Across the complete snapshot population:

* customers: **4,908**;
* customers making a future qualifying purchase: **2,549**;
* overall future purchase rate: **51.9%**;
* future qualifying purchase invoices: **8,470**;
* future observed net sales: **£4,170,456.73**.

### 6.1 Future purchase behaviour

| Segment               | Future purchasers | Future purchase rate | 95% Wilson interval | Rate vs overall |
| --------------------- | ----------------: | -------------------: | ------------------: | --------------: |
| High-value active     |         740 / 806 |            **91.8%** |         89.7%–93.5% |           1.77× |
| Core repeat           |         261 / 321 |            **81.3%** |         76.7%–85.2% |           1.57× |
| Recent low-frequency  |       606 / 1,010 |            **60.0%** |         56.9%–63.0% |           1.16× |
| High-value at risk    |           33 / 59 |            **55.9%** |         43.3%–67.8% |           1.08× |
| Cooling low-frequency |         271 / 551 |            **49.2%** |         45.0%–53.3% |           0.95× |
| Drifting              |       554 / 1,577 |            **35.1%** |         32.8%–37.5% |           0.68× |
| High-value lapsed     |          25 / 117 |            **21.4%** |         14.9%–29.6% |           0.41× |
| Lapsed                |          59 / 467 |            **12.6%** |          9.9%–16.0% |           0.24× |

The behavioural groups exhibit a coherent deterioration in subsequent purchasing as snapshot engagement weakens.

### 6.2 Persistence of high customer value

`High-value active` contains **16.4% of all eligible customers**.

At the snapshot it accounts for:

**70.2% of positive behavioural observed customer value**

During the held-out period it accounts for:

**71.7% of positive future observed customer value**

This persistence shows that the historical high-value/active designation identifies a commercially important customer population rather than only describing an isolated historical period.

### 6.3 Reactivation differentiation

Among historical-only customers:

* High-value lapsed future purchase rate: **21.4%**
* Other lapsed future purchase rate: **12.6%**

The observed difference is:

**8.8 percentage points**

The high-value lapsed rate is approximately:

**1.70×** the other lapsed rate.

The uncertainty intervals are wider for these smaller populations, so this should be described as an observed validation difference rather than a guaranteed or causal effect.

---

## 7. Sensitivity analysis

Three material robustness questions were tested.

### 7.1 Exact duplicate rows

The primary analysis retains **11,812 exact duplicate rows** because the source has no transaction-line identifier proving that they are erroneous.

A full exact-deduplication sensitivity scenario:

* removes all 11,812 rows;
* changes behavioural observed value by only **-0.34%**;
* changes final segment membership for **6 of 4,908 customers (0.12%)**.

The behavioural high-value boundary moves from:

**£1,898.51 → £1,884.36**

The historical high-value boundary moves from:

**£552.40 → £542.89**

**Conclusion:** retaining the exact duplicate rows does not materially affect the segmentation.

### 7.2 Manual financial entries

Manual entries are included in observed net sales at their signed value but do not create purchasing activity or product breadth.

Excluding their monetary effect:

* changes behavioural observed value by **+0.60%**;
* changes segment membership for only **4 customers (0.08%)**.

The behavioural high-value boundary becomes **£1,902.84**.

**Conclusion:** the documented Manual-entry treatment is not driving the final segmentation.

### 7.3 Extreme customer influence

The behavioural population is highly concentrated, so validation was repeated after excluding the highest 1% of behavioural customers by snapshot observed value.

The main future-purchase ordering remains:

* High-value active: **91.9%**
* Core repeat: **81.3%**
* Recent low-frequency: **60.0%**
* High-value at risk: **55.9%**
* Cooling low-frequency: **49.2%**
* Drifting: **35.1%**

High-value active still accounts for **58.7% of positive future value** after the highest 1% of snapshot-value customers are removed.

**Conclusion:** extreme customers materially contribute to commercial value concentration, but they do not create the main behavioural differentiation between the segments.

---

## 8. CRM interpretation

The segmentation is designed to support different treatment rather than merely label customers.

| Segment               | Suggested CRM priority          |
| --------------------- | ------------------------------- |
| High-value active     | Protect and retain              |
| High-value at risk    | Priority win-back               |
| Core repeat           | Nurture and grow                |
| Recent low-frequency  | Develop the relationship        |
| Cooling low-frequency | Timely re-engagement            |
| Drifting              | Selective/low-cost reactivation |
| High-value lapsed     | Targeted reactivation           |
| Lapsed                | Low-cost reactivation           |

These recommendations are prioritisation hypotheses based on observed behaviour. The dataset contains no campaign-treatment or contact-cost information, so it cannot establish the incremental return from a particular intervention.

---

## 9. Why a transparent rule-based segmentation was retained

Clustering and more complex predictive modelling were considered unnecessary for the final analytical question.

The final segmentation already provides:

* transparent rules;
* mutually exclusive and collectively exhaustive groups;
* direct business interpretation;
* reproducible SQL implementation;
* meaningful held-out behavioural differentiation;
* clear CRM actions;
* robustness to material data-treatment decisions.

Adding an opaque clustering solution would increase methodological complexity without resolving a demonstrated weakness in the final decision framework.

Likewise, the project is not presented as a churn or customer-lifetime-value model. The available data supports observed customer value, behavioural segmentation and held-out subsequent-behaviour validation.

---

## 10. Key limitations

The final analysis should be interpreted with the following limitations:

1. **Missing customer identity:** 15.0% of positive classified transaction value cannot be attributed to an identifiable customer and cannot enter customer-level segmentation.
2. **Finite source history:** observed tenure and prior customer history may understate relationships that began before December 2009.
3. **Historical-only history is limited:** earlier-value measures use only the pre-behavioural history available in the dataset, not true lifetime value.
4. **Customer-value concentration:** a relatively small number of customers account for a large proportion of observed value, although the sensitivity analysis shows the main segment differentiation persists after extreme-customer exclusion.
5. **Source-specific thresholds:** the empirical value boundaries arise from this retailer and snapshot and should be recalibrated for another population or date.
6. **Six-month validation horizon:** later behaviour is observed only through 30 November 2011.
7. **No causal campaign evidence:** the validation shows association and predictive differentiation, not the incremental effect of CRM treatment.
8. **Exact duplicates:** ambiguous within-sheet duplicates remain in the primary source, although removing all of them changes only 0.12% of segment assignments.
9. **Manual entries:** their signed value is retained as a customer financial effect, but excluding them changes only 0.08% of segment assignments.

---

## 11. Reproducible analytical flow

```text
validated source
→ classified transaction layer
→ SQLite invoice layer
→ snapshot customer features
→ feature assessment
→ enriched segmentation features
→ final customer segments
→ held-out validation
→ sensitivity analysis
→ CRM recommendations and portfolio visuals
```

The final segmentation is therefore based on pre-snapshot evidence, tested against future customer behaviour and checked against the material data-quality decisions most likely to affect customer value.
