# Project 03 Initial Plan

## Customer Value & Retention Segmentation

## Business problem

A UK online retailer wants to use historical transaction data to identify customer groups that should receive different retention, reactivation and growth treatment.

The aim is not simply to produce customer segments. The analysis should identify groups that are commercially meaningful, explain how their purchasing behaviour differs, and test whether those differences remain useful when compared with subsequent customer activity.

## Primary stakeholder

Customer Insight / CRM Manager.

## Decision to support

Which customer groups should be prioritised for different retention, reactivation and growth activity based on their recent purchasing value and behaviour?

## Data source

UCI Machine Learning Repository - Online Retail II.

The dataset contains transaction-level data from a UK-based non-store retailer covering December 2009 to December 2011.

The source is published under a CC BY 4.0 licence.

Detailed provenance and raw-data handling are recorded in `data_sources.md`.

## Analytical time design

The segmentation will be created at a fixed historical snapshot using only information that would have been available at that point.

**Snapshot date:** 31 May 2011

**Behavioural window:** 1 June 2010 to 31 May 2011

**Held-out validation window:** 1 June 2011 to 30 November 2011

The validation period uses six complete calendar months. The partial December 2011 period is excluded.

Customer measures and segment definitions must not use information from the held-out period. Subsequent purchasing behaviour will then be used to assess whether the original segments distinguish meaningful future outcomes.

This validation can show whether the segmentation has useful descriptive or predictive differentiation. It will not establish that segment membership, or any proposed CRM action, caused later behaviour.

## Main analytical questions

1. How concentrated is observed customer value?
2. What distinct patterns of customer behaviour exist at the snapshot date?
3. Which customers appear most important to retain or reactivate?
4. Which customers show evidence of increasing engagement and growth potential?
5. What characteristics distinguish the customer segments?
6. Do the segments distinguish subsequent purchasing behaviour?
7. What actions should the CRM or Customer Insight Manager consider for each segment?

## Candidate customer measures

Potential snapshot measures include:

- recency;
- purchase frequency;
- net sales;
- active months;
- customer tenure;
- recent-versus-earlier spend momentum;
- product breadth;
- average order value.

These are candidate measures rather than a fixed feature list.

Final measures should be chosen after the source data and customer-level distributions have been investigated. Measures should be retained because they improve the commercial interpretation of the segmentation, not simply because they are available.

## Segmentation success criteria

The final segmentation should be:

- **mutually exclusive** - each eligible customer belongs to one segment;
- **collectively exhaustive** - every eligible customer can be classified;
- **snapshot-valid** - future-period information does not enter the segment definition;
- **interpretable** - a CRM stakeholder can understand why a customer belongs to a segment;
- **commercially differentiated** - segments differ meaningfully in value or purchasing behaviour;
- **actionable** - the groups imply genuinely different retention, reactivation or growth priorities;
- **reproducible** - another analyst can recreate the result from the documented workflow;
- **validated** - the groups show useful differences in subsequent customer behaviour.

Segment names and thresholds will not be fixed before the underlying behavioural distributions have been assessed.

## Analytical principles

- Do not describe the work as a churn model because the dataset contains no true subscription-cancellation or churn event.
- Do not claim to calculate customer lifetime value. The available data supports finite-window revenue measures rather than lifetime profit economics.
- Use terms such as `observed customer value` where a finite historical value measure is intended.
- Avoid arbitrary RFM-style thresholds simply because they are conventional.
- Prevent data leakage by excluding held-out future behaviour from the original segment definitions.
- Distinguish observed data from analytical interpretation.
- Keep the segmentation commercially understandable rather than optimising for technical complexity.
- Validate segment usefulness against the held-out period without making causal claims.
- Do not introduce machine learning unless it solves a genuine analytical problem that cannot be addressed more clearly with an interpretable approach.

## Data quality priorities

The source will be profiled before final cleaning rules are imposed.

Important areas include:

- missing customer IDs;
- duplicate transaction rows;
- cancellations and negative quantities;
- zero or negative unit prices;
- invoice-to-customer consistency;
- customer-to-country consistency;
- product-code and description consistency;
- unusual non-product or administrative transaction codes;
- extreme quantities or customer values;
- the commercial importance of transactions without an identifiable customer.

Cleaning decisions should distinguish genuine data problems from unusual but legitimate commercial activity.

Where records are excluded, the reason and impact should be quantified where practical rather than hidden inside the cleaning code.

## Planned analytical workflow

The intended workflow is:

**source acquisition and profiling → evidence-based cleaning rules → reproducible cleaned transaction data → SQL/SQLite analytical layer → snapshot-valid customer measures → interpretable customer segmentation → held-out future-period validation → commercial interpretation and recommendations → employer-facing publication**

Profiling should be completed before segment thresholds or final cleaning rules are fixed.

## Planned tool roles

### Python / pandas

Likely uses include:

- source ingestion and profiling;
- data-quality investigation;
- reproducible cleaning where pandas is the clearer tool;
- exploratory analysis of customer measures;
- segmentation design;
- selected validation calculations;
- professional visualisation.

### SQL / SQLite

SQL should have a substantial analytical role, likely including:

- clean-layer validation;
- customer and invoice aggregation;
- conditional aggregation;
- snapshot-window calculations;
- customer feature views;
- segment summaries;
- held-out outcome calculations;
- reconciliation checks.

CTEs and window functions should be used where they genuinely improve the analysis rather than simply to demonstrate syntax.

### Visualisation

Matplotlib will be used for selected analytical and employer-facing charts.

Power BI and Excel are not currently planned because the portfolio already demonstrates them and they do not need to be forced into this project.

## Planned deliverables

The completed project should include:

- documented source provenance and raw-data handling;
- reproducible source profiling and cleaning;
- documented data-quality decisions;
- cleaned analytical transaction data;
- an appropriate SQLite analytical layer;
- SQL validation and analysis;
- customer-level snapshot measures;
- a documented segmentation methodology;
- held-out validation analysis;
- selected professional visualisations;
- findings, recommendations and limitations;
- a concise employer-facing README;
- a GitHub Pages presentation;
- dependency and reproduction instructions.

## Anticipated limitations

Important limitations to consider throughout the analysis include:

- a substantial proportion of transactions do not contain an identifiable Customer ID;
- the available history covers a finite period and cannot represent true customer lifetime value;
- the dataset contains cancellations, adjustments, administrative records and other transaction anomalies that require interpretation;
- product margin and profitability are unavailable, so customer value measures will primarily be revenue-based;
- the retailer and transaction period are historical, so the project demonstrates analytical method and judgement rather than current commercial conditions;
- held-out validation can test differentiation in later behaviour but cannot establish the causal effectiveness of a CRM intervention.

These limitations should be refined as the analysis develops rather than copied mechanically into the final conclusions.

## Completion standard

Project 03 should not be marked complete until the following have been addressed.

### Analysis and data

- the business question has been answered;
- final cleaning rules and analytical metrics have been validated;
- customer eligibility and exclusions are documented;
- SQL and Python outputs reconcile where appropriate;
- segment definitions are reproducible and use no future information;
- held-out validation has been completed;
- conclusions and recommendations are proportionate to the evidence;
- important limitations are explicit.

### Code and reproducibility

- Python and SQL files are complete and readable;
- comments explain analytical intent, assumptions and non-obvious logic without becoming tutorial narration;
- dependencies are recorded;
- source and generated data are handled consistently;
- reproduction instructions are complete;
- the project has been run through its documented workflow where practical;
- UTF-8 and general text hygiene have been checked.

### Public presentation

- README is complete, concise and written in a natural experienced-analyst voice;
- selected visuals have been manually reviewed;
- GitHub Pages is complete and visually checked;
- public documents use consistent metrics, terminology, findings and recommendations;
- the distinction between this initial plan and the final implemented state is clear;
- no private working material or accidental prompt/assistant residue is present.

### GitHub closure

- final project changes have been reviewed through the planned pull-request workflow;
- completed milestone branches have been merged appropriately;
- local `main` has been synchronised and checked;
- obsolete local and remote feature branches have been cleaned up;
- repository About description, website and topics have been completed;
- GitHub profile README and pinning have been reconsidered;
- the profile website has been reconsidered against the strongest published project;
- relevant Data Career Rebuild Project Sources have been updated.

The final review should verify these standards rather than requiring a major rescue or rewrite.

## Project scope

Target approximately 5-7 active working days, while allowing the work to take longer if genuine analytical investigation requires it.

The project should remain focused on interpretable customer segmentation and commercial decision support rather than expanding into unnecessary machine learning or adding tools simply for portfolio coverage.