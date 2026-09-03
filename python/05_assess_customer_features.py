"""Assess candidate customer features before Project 03 segment design.

The snapshot SQL layer already contains the core customer measures. This script
focuses on behavioural-window purchasers and asks whether the current features
are overly redundant and whether two possible additions add useful information:

1. average value per qualifying purchase invoice;
2. recent-versus-previous purchasing momentum.

The held-out validation period is deliberately excluded. These calculations are
for feature selection only and must not use future customer behaviour.
"""

from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "online_retail.db"

EXPECTED_ELIGIBLE_CUSTOMERS = 4_908
EXPECTED_BEHAVIOURAL_PURCHASERS = 4_324


def load_snapshot_features(connection: sqlite3.Connection) -> pd.DataFrame:
    """Load the existing snapshot-valid customer feature layer."""

    query = """
        SELECT *
        FROM customer_snapshot_features
    """

    return pd.read_sql_query(query, connection)


def load_candidate_purchase_features(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Build purchase-value and short-term momentum candidates.

    Average purchase value is based only on invoices containing qualifying
    purchasing activity. Standalone returns and financial adjustments therefore
    do not create a purchase occasion or distort its denominator.

    Momentum compares two equal three-month periods immediately before the
    snapshot:

        previous period: 1 Dec 2010 to 28 Feb 2011
        recent period:   1 Mar 2011 to 31 May 2011

    Equal windows avoid creating an artificial difference purely because one
    comparison period is longer than the other.
    """

    query = """
        SELECT
            customer_id_clean,

            SUM(
                CASE
                    WHEN analysis_period = 'behavioural'
                         AND has_qualifying_activity = 1
                    THEN 1
                    ELSE 0
                END
            ) AS qualifying_purchase_invoices_12m,

            SUM(
                CASE
                    WHEN analysis_period = 'behavioural'
                         AND has_qualifying_activity = 1
                    THEN observed_invoice_value
                    ELSE 0
                END
            ) AS qualifying_purchase_invoice_value_12m,

            SUM(
                CASE
                    WHEN analysis_period = 'behavioural'
                         AND has_qualifying_activity = 1
                         AND DATE(invoice_timestamp)
                             BETWEEN '2010-12-01' AND '2011-02-28'
                    THEN 1
                    ELSE 0
                END
            ) AS previous_3m_purchase_frequency,

            SUM(
                CASE
                    WHEN analysis_period = 'behavioural'
                         AND has_qualifying_activity = 1
                         AND DATE(invoice_timestamp)
                             BETWEEN '2011-03-01' AND '2011-05-31'
                    THEN 1
                    ELSE 0
                END
            ) AS recent_3m_purchase_frequency,

            SUM(
                CASE
                    WHEN analysis_period = 'behavioural'
                         AND has_qualifying_activity = 1
                         AND DATE(invoice_timestamp)
                             BETWEEN '2010-12-01' AND '2011-02-28'
                    THEN observed_invoice_value
                    ELSE 0
                END
            ) AS previous_3m_purchase_value,

            SUM(
                CASE
                    WHEN analysis_period = 'behavioural'
                         AND has_qualifying_activity = 1
                         AND DATE(invoice_timestamp)
                             BETWEEN '2011-03-01' AND '2011-05-31'
                    THEN observed_invoice_value
                    ELSE 0
                END
            ) AS recent_3m_purchase_value

        FROM invoice_summary

        WHERE
            has_customer_id = 1
            AND analysis_period = 'behavioural'

        GROUP BY customer_id_clean
    """

    return pd.read_sql_query(query, connection)


def validate_population(
    features: pd.DataFrame,
    behavioural: pd.DataFrame,
) -> None:
    """Stop early if the analytical population has drifted unexpectedly."""

    if len(features) != EXPECTED_ELIGIBLE_CUSTOMERS:
        raise ValueError(
            "Unexpected eligible-customer count: "
            f"{len(features):,} instead of "
            f"{EXPECTED_ELIGIBLE_CUSTOMERS:,}."
        )

    if len(behavioural) != EXPECTED_BEHAVIOURAL_PURCHASERS:
        raise ValueError(
            "Unexpected behavioural-purchaser count: "
            f"{len(behavioural):,} instead of "
            f"{EXPECTED_BEHAVIOURAL_PURCHASERS:,}."
        )


def add_candidate_features(
    behavioural: pd.DataFrame,
) -> pd.DataFrame:
    """Create interpretable candidate features for assessment."""

    result = behavioural.copy()

    # Purchase frequency in this candidate table must reconcile to the settled
    # snapshot definition before average purchase value is calculated.
    frequency_matches = (
        result["purchase_frequency_12m"]
        == result["qualifying_purchase_invoices_12m"]
    )

    if not frequency_matches.all():
        mismatch_count = int((~frequency_matches).sum())
        raise ValueError(
            "Candidate purchase frequency does not reconcile to the "
            f"snapshot feature layer for {mismatch_count:,} customers."
        )

    result["average_purchase_invoice_value_12m"] = (
        result["qualifying_purchase_invoice_value_12m"]
        / result["purchase_frequency_12m"]
    )

    # Absolute momentum is easier to interpret than a percentage change when
    # many customers have zero purchases in one of the comparison periods.
    result["purchase_value_change_3m"] = (
        result["recent_3m_purchase_value"]
        - result["previous_3m_purchase_value"]
    )

    result["purchase_frequency_change_3m"] = (
        result["recent_3m_purchase_frequency"]
        - result["previous_3m_purchase_frequency"]
    )

    result["momentum_coverage"] = "neither period"

    result.loc[
        (result["previous_3m_purchase_frequency"] > 0)
        & (result["recent_3m_purchase_frequency"] == 0),
        "momentum_coverage",
    ] = "previous only"

    result.loc[
        (result["previous_3m_purchase_frequency"] == 0)
        & (result["recent_3m_purchase_frequency"] > 0),
        "momentum_coverage",
    ] = "recent only"

    result.loc[
        (result["previous_3m_purchase_frequency"] > 0)
        & (result["recent_3m_purchase_frequency"] > 0),
        "momentum_coverage",
    ] = "both periods"

    return result


def print_candidate_summary(behavioural: pd.DataFrame) -> None:
    """Print coverage and distribution information for proposed additions."""

    print("\n--- Candidate feature coverage ---")

    coverage = (
        behavioural["momentum_coverage"]
        .value_counts()
        .rename_axis("coverage")
        .reset_index(name="customers")
    )

    coverage["share_pct"] = (
        100.0 * coverage["customers"] / len(behavioural)
    ).round(1)

    print(coverage.to_string(index=False))

    candidate_columns = [
        "average_purchase_invoice_value_12m",
        "previous_3m_purchase_frequency",
        "recent_3m_purchase_frequency",
        "previous_3m_purchase_value",
        "recent_3m_purchase_value",
        "purchase_frequency_change_3m",
        "purchase_value_change_3m",
    ]

    print("\n--- Candidate feature distributions ---")

    summary = behavioural[candidate_columns].describe(
        percentiles=[0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    ).T

    summary = summary[
        [
            "min",
            "10%",
            "25%",
            "50%",
            "mean",
            "75%",
            "90%",
            "95%",
            "99%",
            "max",
        ]
    ].round(2)

    print(summary.to_string())


def print_correlations(behavioural: pd.DataFrame) -> None:
    """Assess monotonic feature redundancy with Spearman correlations.

    Spearman correlation is preferred here because the customer measures are
    strongly skewed and several have extreme values. It assesses whether
    customers tend to rank similarly across two features without assuming a
    linear relationship or normally distributed measures.
    """

    correlation_columns = [
        "recency_days",
        "purchase_frequency_12m",
        "active_months_12m",
        "observed_net_sales_12m",
        "product_breadth_12m",
        "observed_tenure_days",
        "average_purchase_invoice_value_12m",
        "purchase_frequency_change_3m",
        "purchase_value_change_3m",
    ]

    correlations = behavioural[correlation_columns].corr(
        method="spearman"
    ).round(3)

    print("\n--- Spearman feature correlations ---")
    print(correlations.to_string())

    # Surface only relatively strong relationships so the feature-selection
    # discussion is not buried in the full correlation matrix.
    strong_pairs = []

    for left_index, left_feature in enumerate(correlation_columns):
        for right_feature in correlation_columns[left_index + 1 :]:
            correlation = correlations.loc[left_feature, right_feature]

            if abs(correlation) >= 0.70:
                strong_pairs.append(
                    {
                        "feature_1": left_feature,
                        "feature_2": right_feature,
                        "spearman_correlation": correlation,
                    }
                )

    strong_pairs_df = pd.DataFrame(strong_pairs)

    print("\n--- Strong absolute correlations (>= 0.70) ---")

    if strong_pairs_df.empty:
        print("None")
    else:
        strong_pairs_df["absolute_correlation"] = (
            strong_pairs_df["spearman_correlation"].abs()
        )

        strong_pairs_df = strong_pairs_df.sort_values(
            "absolute_correlation",
            ascending=False,
        ).drop(columns="absolute_correlation")

        print(strong_pairs_df.to_string(index=False))


def print_extreme_average_orders(behavioural: pd.DataFrame) -> None:
    """Inspect customers with unusually large average purchase invoices."""

    columns = [
        "customer_id_clean",
        "recency_days",
        "purchase_frequency_12m",
        "active_months_12m",
        "observed_net_sales_12m",
        "average_purchase_invoice_value_12m",
        "product_breadth_12m",
    ]

    largest = behavioural.nlargest(
        10,
        "average_purchase_invoice_value_12m",
    )[columns].copy()

    money_columns = [
        "observed_net_sales_12m",
        "average_purchase_invoice_value_12m",
    ]

    largest[money_columns] = largest[money_columns].round(2)

    print("\n--- Highest average purchase-invoice values ---")
    print(largest.to_string(index=False))


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {DATABASE_PATH}"
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        snapshot_features = load_snapshot_features(connection)
        candidate_features = load_candidate_purchase_features(connection)

    behavioural = snapshot_features.loc[
        snapshot_features["is_behavioural_purchaser"] == 1
    ].copy()

    behavioural = behavioural.merge(
        candidate_features,
        on="customer_id_clean",
        how="left",
        validate="one_to_one",
    )

    validate_population(snapshot_features, behavioural)

    behavioural = add_candidate_features(behavioural)

    print(
        "Eligible snapshot customers:",
        f"{len(snapshot_features):,}",
    )

    print(
        "Behavioural purchasers assessed:",
        f"{len(behavioural):,}",
    )

    print_candidate_summary(behavioural)
    print_correlations(behavioural)
    print_extreme_average_orders(behavioural)


if __name__ == "__main__":
    main()