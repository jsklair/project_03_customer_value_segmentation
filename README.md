# Project 03: Customer Value & Retention Segmentation

Analysis of real UK online-retail transaction data to identify commercially meaningful customer groups for retention, reactivation and growth activity.

The project uses a fixed historical snapshot to describe customers from their purchasing behaviour, then assesses whether those segments distinguish subsequent activity in a held-out future period.

## Business question

Which customer groups should a CRM or Customer Insight Manager prioritise for different retention, reactivation and growth activity?

## Data

The analysis uses **Online Retail II** from the UCI Machine Learning Repository.

The dataset contains approximately 1.07 million transaction lines from a UK-based non-store retailer between December 2009 and December 2011.

The segmentation snapshot is **31 May 2011**, using customer behaviour from **1 June 2010 to 31 May 2011**. The period from **1 June to 30 November 2011** is held back for subsequent-behaviour validation.

Detailed source provenance and raw-data handling are documented in [`data_sources.md`](data_sources.md).

## Analytical approach

The project will:

- profile the transaction data and investigate material quality issues before setting cleaning rules;
- create a reproducible cleaned analytical dataset;
- use SQL and Python to derive snapshot-valid customer measures;
- design commercially interpretable customer segments;
- assess whether those segments distinguish subsequent purchasing behaviour;
- translate the findings into practical CRM priorities and recommendations.

The analysis will not be presented as churn modelling or customer lifetime value analysis. The available data supports finite-window measures of observed customer value and subsequent purchasing behaviour.

## Tools

- SQL / SQLite
- Python / pandas
- matplotlib
- Git and GitHub
- GitHub Pages

## Status

**In progress - data foundation and source profiling.**

Current work is focused on understanding missing customer identifiers, cancellations and negative quantities, zero/negative prices, duplicate records and non-product transaction codes before final cleaning rules are set.