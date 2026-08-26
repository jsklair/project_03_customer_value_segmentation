# Project 03 Initial Plan

## Customer Value & Retention Segmentation

## Business problem

A UK online retailer wants to use historical transaction data to identify customer groups that should receive different retention, reactivation and growth treatment.

## Primary stakeholder

Customer Insight / CRM Manager.

## Decision to support

Which customer groups should be prioritised for different retention and growth activity based on their recent purchasing value and behaviour?

## Data source

UCI Machine Learning Repository - Online Retail II.

The dataset contains transaction-level data from a UK-based non-store retailer covering December 2009 to December 2011.

The source is published under a CC BY 4.0 licence.

## Proposed analytical approach

The project will create a customer segmentation at a fixed historical snapshot date using only information available at that time.

Provisional snapshot date:

31 May 2011

Provisional behavioural window:

1 June 2010 to 31 May 2011

A later period will be held back to assess whether the customer segments distinguish subsequent purchasing behaviour.

Provisional validation period:

1 June 2011 to 30 November 2011

## Main analytical questions

1. How concentrated is customer value?
2. What distinct patterns of customer behaviour exist at the snapshot date?
3. Which customers appear most important to retain or reactivate?
4. Which customers show evidence of increasing engagement and growth potential?
5. What characteristics distinguish the customer segments?
6. Do the segments distinguish subsequent purchasing behaviour?
7. What actions should the CRM or Customer Insight Manager consider for each segment?

## Candidate customer measures

Likely measures include:

- recency;
- purchase frequency;
- net sales;
- active months;
- customer tenure;
- recent versus earlier spend momentum;
- product breadth;
- average order value.

Final measures and segment boundaries will be determined after profiling the data.

## Analytical principles

- Do not describe the work as a churn model.
- Do not claim to calculate customer lifetime value.
- Avoid arbitrary segmentation thresholds before inspecting the data.
- Prevent data leakage by excluding future-period behaviour from the original segment definitions.
- Keep the segmentation commercially interpretable.
- Validate whether the segments differ meaningfully in the held-back period.

## Data quality priorities

Initial checks will include:

- missing customer IDs;
- duplicate transaction rows;
- cancellations and negative quantities;
- zero or negative unit prices;
- invoice and customer consistency;
- product-code and description quality;
- unusual non-product transaction codes;
- country consistency;
- the commercial importance of transactions without an identifiable customer.

## Likely tools

- SQL / SQLite
- Python / pandas
- matplotlib
- Git and GitHub
- GitHub Pages

Power BI and Excel are not currently planned because they do not need to be forced into this project.

## Likely deliverables

- reproducible data acquisition and cleaning workflow;
- documented analytical data model;
- SQL validation and analysis;
- customer-level analytical dataset;
- customer segmentation methodology;
- held-out validation analysis;
- selected professional visualisations;
- findings and recommendations;
- README;
- GitHub Pages presentation;
- dependency and reproduction documentation.

## Project scope

Target approximately 5-7 active working days.

The project should remain focused on interpretable customer segmentation and commercial decision support rather than expanding into unnecessary machine learning.

