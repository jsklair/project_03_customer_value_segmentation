"""Create final Project 03 segment summaries and portfolio visuals.

The customer segmentation has already been fixed using information available
by 31 May 2011 and validated against the held-out period from 1 June to
30 November 2011.

This script turns the validated analytical layers into recruiter-facing outputs:

* a consolidated segment summary;
* a CRM action table;
* segment-size visualisation;
* held-out future-purchase rates with 95% Wilson intervals;
* snapshot-versus-future customer-value concentration;
* reactivation validation for the historical-only population.

The Wilson intervals are included as descriptive uncertainty guides around
future purchase proportions. They do not turn the validation into a causal
experiment and should not be interpreted as evidence that segment membership
causes later purchasing behaviour.
"""

from math import sqrt
from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "online_retail.db"
)

REPORTS_DIR = PROJECT_ROOT / "reports"
VISUALS_DIR = PROJECT_ROOT / "visuals"

SEGMENT_SUMMARY_FILE = (
    REPORTS_DIR
    / "customer_segment_summary.csv"
)

SEGMENT_ACTIONS_FILE = (
    REPORTS_DIR
    / "customer_segment_actions.csv"
)


EXPECTED_CUSTOMERS = 4_908
EXPECTED_FUTURE_PURCHASERS = 2_549

EXPECTED_SNAPSHOT_VALUE = 7_762_616.79
EXPECTED_FUTURE_VALUE = 4_170_456.73

EXPECTED_SEGMENT_COUNTS = {
    "High-value active": 806,
    "High-value at risk": 59,
    "Core repeat": 321,
    "Recent low-frequency": 1_010,
    "Cooling low-frequency": 551,
    "Drifting": 1_577,
    "High-value lapsed": 117,
    "Lapsed": 467,
}

SEGMENT_ORDER = list(EXPECTED_SEGMENT_COUNTS)

BEHAVIOURAL_SEGMENT_ORDER = [
    "High-value active",
    "High-value at risk",
    "Core repeat",
    "Recent low-frequency",
    "Cooling low-frequency",
    "Drifting",
]

REACTIVATION_SEGMENT_ORDER = [
    "High-value lapsed",
    "Lapsed",
]


# CRM recommendations are deliberately operational rather than predictive
# promises. They describe how a Customer Insight / CRM Manager could use the
# segment distinctions established by the analysis.
SEGMENT_ACTIONS = {
    "High-value active": {
        "priority": "Protect and retain",
        "recommended_action": (
            "Prioritise service, loyalty and relevant cross-sell activity. "
            "Avoid unnecessary blanket discounting of customers who are "
            "already highly valuable and active."
        ),
    },
    "High-value at risk": {
        "priority": "Priority win-back",
        "recommended_action": (
            "Use targeted re-engagement for previously high-value customers "
            "whose latest qualifying purchase is more than six months old. "
            "Their held-out purchasing and value justify disproportionate "
            "attention despite the small segment size."
        ),
    },
    "Core repeat": {
        "priority": "Nurture and grow",
        "recommended_action": (
            "Maintain repeat engagement and test ways to increase customer "
            "value through relevant product breadth, purchase size or "
            "cross-sell rather than simply driving more transactions."
        ),
    },
    "Recent low-frequency": {
        "priority": "Develop the relationship",
        "recommended_action": (
            "Encourage the next purchase while the relationship is still "
            "recent. Focus on progression from occasional to repeat buying "
            "rather than treating these customers as established loyalists."
        ),
    },
    "Cooling low-frequency": {
        "priority": "Timely re-engagement",
        "recommended_action": (
            "Use lower-cost reminders or relevant offers before inactivity "
            "deepens. The held-out purchase rate is weaker than for recent "
            "low-frequency customers but remains commercially meaningful."
        ),
    },
    "Drifting": {
        "priority": "Selective reactivation",
        "recommended_action": (
            "Use inexpensive or automated reactivation activity and avoid "
            "high acquisition-style incentives unless additional customer "
            "evidence supports them."
        ),
    },
    "High-value lapsed": {
        "priority": "Targeted reactivation",
        "recommended_action": (
            "Prioritise lapsed customers with stronger observed earlier "
            "value. Their held-out reactivation rate materially exceeds the "
            "remainder of the historical-only population."
        ),
    },
    "Lapsed": {
        "priority": "Low-cost reactivation",
        "recommended_action": (
            "Use broad, low-cost win-back activity or suppression rules where "
            "contact cost is material. Prior customer value and future "
            "reactivation are both weaker than for high-value lapsed customers."
        ),
    },
}


def wilson_interval(successes, observations, z=1.959963984540054):
    """Return a 95% Wilson interval for a binomial proportion.

    Wilson intervals behave better than a simple normal approximation when
    group sizes are modest or proportions are relatively close to 0 or 1.
    """

    if observations <= 0:
        return float("nan"), float("nan")

    proportion = successes / observations

    denominator = 1 + (z**2 / observations)

    centre = (
        proportion
        + z**2 / (2 * observations)
    ) / denominator

    half_width = (
        z
        * sqrt(
            proportion * (1 - proportion) / observations
            + z**2 / (4 * observations**2)
        )
        / denominator
    )

    return (
        centre - half_width,
        centre + half_width,
    )


def load_validation_data(connection):
    """Load the final snapshot segments and held-out outcomes."""

    query = """
        SELECT
            customer_id_clean,
            customer_segment,

            is_behavioural_purchaser,
            is_historical_only_purchaser,

            recency_days,
            purchase_frequency_12m,
            active_months_12m,
            observed_net_sales_12m,
            product_breadth_12m,

            prior_purchase_invoices,
            prior_active_months,
            prior_observed_net_sales,
            prior_product_breadth,

            average_qualifying_purchase_invoice_value_12m,
            recent_activity_pattern,

            has_validation_purchase,
            validation_purchase_invoices,
            validation_active_months,
            validation_observed_net_sales,
            validation_product_breadth,
            days_to_next_purchase

        FROM customer_segment_validation
    """

    return pd.read_sql_query(
        query,
        connection,
    )


def validate_input(data):
    """Protect final reporting from silent population or value drift."""

    if len(data) != EXPECTED_CUSTOMERS:
        raise ValueError(
            "Unexpected customer population: "
            f"{len(data):,} instead of "
            f"{EXPECTED_CUSTOMERS:,}."
        )

    if data["customer_id_clean"].nunique() != EXPECTED_CUSTOMERS:
        raise ValueError(
            "Customer IDs are not unique in the final validation layer."
        )

    if data["customer_segment"].isna().any():
        raise ValueError(
            "Missing final customer segment assignments."
        )

    actual_counts = (
        data["customer_segment"]
        .value_counts()
        .to_dict()
    )

    if actual_counts != EXPECTED_SEGMENT_COUNTS:
        raise ValueError(
            "Final segment membership has changed unexpectedly.\n"
            f"Expected: {EXPECTED_SEGMENT_COUNTS}\n"
            f"Found: {actual_counts}"
        )

    future_purchasers = int(
        data["has_validation_purchase"].sum()
    )

    if future_purchasers != EXPECTED_FUTURE_PURCHASERS:
        raise ValueError(
            "Unexpected held-out purchaser count: "
            f"{future_purchasers:,} instead of "
            f"{EXPECTED_FUTURE_PURCHASERS:,}."
        )

    snapshot_value = data[
        "observed_net_sales_12m"
    ].sum()

    if abs(snapshot_value - EXPECTED_SNAPSHOT_VALUE) > 0.01:
        raise ValueError(
            "Snapshot customer value no longer reconciles: "
            f"{snapshot_value:,.2f}."
        )

    future_value = data[
        "validation_observed_net_sales"
    ].sum()

    if abs(future_value - EXPECTED_FUTURE_VALUE) > 0.01:
        raise ValueError(
            "Held-out customer value no longer reconciles: "
            f"{future_value:,.2f}."
        )


def build_segment_summary(data):
    """Create a consolidated snapshot and validation summary."""

    working = data.copy()

    working["positive_snapshot_value"] = (
        working["observed_net_sales_12m"]
        .clip(lower=0)
    )

    working["positive_future_value"] = (
        working["validation_observed_net_sales"]
        .clip(lower=0)
    )

    # Earlier customer value is the appropriate commercial reference for the
    # historical-only population. It is deliberately left blank for behavioural
    # customers rather than mixing different measurement periods.
    working["reactivation_prior_value"] = (
        working["prior_observed_net_sales"]
        .where(
            working["is_historical_only_purchaser"].eq(1)
        )
    )

    summary = (
        working
        .groupby(
            "customer_segment",
            observed=False,
        )
        .agg(
            customer_count=(
                "customer_id_clean",
                "size",
            ),
            average_recency_days=(
                "recency_days",
                "mean",
            ),
            average_purchase_frequency=(
                "purchase_frequency_12m",
                "mean",
            ),
            average_active_months=(
                "active_months_12m",
                "mean",
            ),
            average_snapshot_observed_net_sales=(
                "observed_net_sales_12m",
                "mean",
            ),
            total_snapshot_observed_net_sales=(
                "observed_net_sales_12m",
                "sum",
            ),
            average_product_breadth=(
                "product_breadth_12m",
                "mean",
            ),
            average_purchase_invoice_value=(
                "average_qualifying_purchase_invoice_value_12m",
                "mean",
            ),
            average_prior_observed_net_sales=(
                "reactivation_prior_value",
                "mean",
            ),
            future_purchasers=(
                "has_validation_purchase",
                "sum",
            ),
            average_future_purchase_frequency=(
                "validation_purchase_invoices",
                "mean",
            ),
            average_days_to_next_purchase=(
                "days_to_next_purchase",
                "mean",
            ),
            average_future_observed_net_sales=(
                "validation_observed_net_sales",
                "mean",
            ),
            total_future_observed_net_sales=(
                "validation_observed_net_sales",
                "sum",
            ),
            average_future_product_breadth=(
                "validation_product_breadth",
                "mean",
            ),
            positive_snapshot_value=(
                "positive_snapshot_value",
                "sum",
            ),
            positive_future_value=(
                "positive_future_value",
                "sum",
            ),
        )
        .reset_index()
    )

    summary["customer_segment"] = pd.Categorical(
        summary["customer_segment"],
        categories=SEGMENT_ORDER,
        ordered=True,
    )

    summary = summary.sort_values(
        "customer_segment"
    ).reset_index(drop=True)

    summary["customer_share_pct"] = (
        100
        * summary["customer_count"]
        / len(working)
    )

    summary["future_purchase_rate_pct"] = (
        100
        * summary["future_purchasers"]
        / summary["customer_count"]
    )

    overall_future_purchase_rate = (
        working["has_validation_purchase"].mean()
    )

    summary["future_purchase_rate_lift"] = (
        summary["future_purchase_rate_pct"]
        / (100 * overall_future_purchase_rate)
    )

    positive_snapshot_total = (
        working["positive_snapshot_value"].sum()
    )

    positive_future_total = (
        working["positive_future_value"].sum()
    )

    summary["positive_snapshot_value_share_pct"] = (
        100
        * summary["positive_snapshot_value"]
        / positive_snapshot_total
    )

    summary["positive_future_value_share_pct"] = (
        100
        * summary["positive_future_value"]
        / positive_future_total
    )

    lower_bounds = []
    upper_bounds = []

    for row in summary.itertuples(index=False):
        lower, upper = wilson_interval(
            int(row.future_purchasers),
            int(row.customer_count),
        )

        lower_bounds.append(100 * lower)
        upper_bounds.append(100 * upper)

    summary["future_purchase_rate_ci95_lower_pct"] = (
        lower_bounds
    )

    summary["future_purchase_rate_ci95_upper_pct"] = (
        upper_bounds
    )

    rounding = {
        "customer_share_pct": 1,
        "average_recency_days": 1,
        "average_purchase_frequency": 2,
        "average_active_months": 2,
        "average_snapshot_observed_net_sales": 2,
        "total_snapshot_observed_net_sales": 2,
        "average_product_breadth": 1,
        "average_purchase_invoice_value": 2,
        "average_prior_observed_net_sales": 2,
        "future_purchase_rate_pct": 1,
        "future_purchase_rate_lift": 2,
        "future_purchase_rate_ci95_lower_pct": 1,
        "future_purchase_rate_ci95_upper_pct": 1,
        "average_future_purchase_frequency": 2,
        "average_days_to_next_purchase": 1,
        "average_future_observed_net_sales": 2,
        "total_future_observed_net_sales": 2,
        "average_future_product_breadth": 1,
        "positive_snapshot_value": 2,
        "positive_future_value": 2,
        "positive_snapshot_value_share_pct": 1,
        "positive_future_value_share_pct": 1,
    }

    return summary.round(rounding)


def build_actions_table(summary):
    """Attach the stakeholder-facing interpretation to each segment."""

    rows = []

    for segment in SEGMENT_ORDER:
        summary_row = (
            summary.loc[
                summary["customer_segment"]
                .astype("string")
                .eq(segment)
            ]
            .iloc[0]
        )

        action = SEGMENT_ACTIONS[segment]

        rows.append(
            {
                "customer_segment": segment,
                "customer_count": int(
                    summary_row["customer_count"]
                ),
                "customer_share_pct": float(
                    summary_row["customer_share_pct"]
                ),
                "future_purchase_rate_pct": float(
                    summary_row["future_purchase_rate_pct"]
                ),
                "future_purchase_rate_lift": float(
                    summary_row["future_purchase_rate_lift"]
                ),
                "priority": action["priority"],
                "recommended_action": (
                    action["recommended_action"]
                ),
            }
        )

    return pd.DataFrame(rows)


def save_segment_size_chart(summary):
    """Visualise the operational size of the final segments."""

    plot_data = (
        summary
        .set_index("customer_segment")
        .loc[SEGMENT_ORDER]
        .iloc[::-1]
    )

    fig, ax = plt.subplots(
        figsize=(10, 6.5)
    )

    bars = ax.barh(
        plot_data.index,
        plot_data["customer_count"],
    )

    ax.set_title(
        "Customer population by final segment"
    )

    ax.set_xlabel("Customers")
    ax.set_ylabel("")

    ax.grid(
        axis="x",
        alpha=0.2,
    )

    for bar, count, share in zip(
        bars,
        plot_data["customer_count"],
        plot_data["customer_share_pct"],
    ):
        ax.text(
            bar.get_width() + 20,
            bar.get_y() + bar.get_height() / 2,
            f"{int(count):,} ({share:.1f}%)",
            va="center",
            fontsize=9,
        )

    ax.set_xlim(
        0,
        plot_data["customer_count"].max() * 1.22,
    )

    fig.tight_layout()

    output = (
        VISUALS_DIR
        / "01_customer_population_by_segment.png"
    )

    fig.savefig(
        output,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)


def save_future_purchase_chart(summary, overall_rate):
    """Show held-out purchase rates with Wilson uncertainty intervals."""

    plot_data = (
        summary
        .set_index("customer_segment")
        .loc[SEGMENT_ORDER]
        .iloc[::-1]
    )

    rates = plot_data[
        "future_purchase_rate_pct"
    ]

    lower_error = (
        rates
        - plot_data[
            "future_purchase_rate_ci95_lower_pct"
        ]
    )

    upper_error = (
        plot_data[
            "future_purchase_rate_ci95_upper_pct"
        ]
        - rates
    )

    fig, ax = plt.subplots(
        figsize=(10, 6.5)
    )

    bars = ax.barh(
        plot_data.index,
        rates,
        xerr=[lower_error, upper_error],
        capsize=3,
    )

    ax.axvline(
        overall_rate,
        linestyle="--",
        linewidth=1.2,
        label=(
            "Overall held-out purchase rate "
            f"({overall_rate:.1f}%)"
        ),
    )

    ax.set_title(
        "Held-out six-month purchase rate by snapshot segment"
    )

    ax.set_xlabel(
        "Customers making at least one qualifying future purchase (%)"
    )

    ax.set_ylabel("")

    ax.set_xlim(0, 100)

    ax.grid(
        axis="x",
        alpha=0.2,
    )

    # Position labels beyond the upper Wilson bound so they do not
    # overlap the confidence-interval whiskers.
    for bar, rate, upper_bound in zip(
        bars,
        rates,
        plot_data["future_purchase_rate_ci95_upper_pct"],
    ):
        ax.text(
            min(upper_bound + 1.5, 98),
            bar.get_y() + bar.get_height() / 2,
            f"{rate:.1f}%",
            va="center",
            fontsize=9,
        )

    ax.legend(
        loc="lower right",
        frameon=False,
    )

    fig.tight_layout()

    output = (
        VISUALS_DIR
        / "02_future_purchase_rate_by_segment.png"
    )

    fig.savefig(
        output,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)


def save_value_persistence_chart(data):
    """Compare positive customer-value concentration before and after snapshot.

    Restrict this comparison to behavioural purchasers so both periods describe
    the same six behavioural segment populations. Historical-only customers are
    evaluated separately through the reactivation visual.
    """

    behavioural = data.loc[
        data["is_behavioural_purchaser"].eq(1)
    ].copy()

    behavioural["positive_snapshot_value"] = (
        behavioural["observed_net_sales_12m"]
        .clip(lower=0)
    )

    behavioural["positive_future_value"] = (
        behavioural["validation_observed_net_sales"]
        .clip(lower=0)
    )

    grouped = (
        behavioural
        .groupby(
            "customer_segment",
            observed=False,
        )[
            [
                "positive_snapshot_value",
                "positive_future_value",
            ]
        ]
        .sum()
        .loc[BEHAVIOURAL_SEGMENT_ORDER]
    )

    grouped["snapshot_share_pct"] = (
        100
        * grouped["positive_snapshot_value"]
        / grouped["positive_snapshot_value"].sum()
    )

    grouped["future_share_pct"] = (
        100
        * grouped["positive_future_value"]
        / grouped["positive_future_value"].sum()
    )

    positions = list(
        range(len(grouped))
    )

    width = 0.38

    fig, ax = plt.subplots(
        figsize=(11, 6.5)
    )

    ax.bar(
        [position - width / 2 for position in positions],
        grouped["snapshot_share_pct"],
        width=width,
        label="Snapshot positive value share",
    )

    ax.bar(
        [position + width / 2 for position in positions],
        grouped["future_share_pct"],
        width=width,
        label="Held-out positive value share",
    )

    ax.set_xticks(positions)

    ax.set_xticklabels(
        grouped.index,
        rotation=25,
        ha="right",
    )

    ax.set_ylabel(
        "Share of positive observed customer value (%)"
    )

    ax.set_title(
        "High-value concentration persists into held-out behaviour"
    )

    ax.grid(
        axis="y",
        alpha=0.2,
    )

    ax.legend(
        frameon=False,
    )

    fig.tight_layout()

    output = (
        VISUALS_DIR
        / "03_snapshot_vs_future_value_share.png"
    )

    fig.savefig(
        output,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)


def save_reactivation_chart(summary):
    """Compare held-out reactivation within the historical-only population."""

    plot_data = (
        summary
        .set_index("customer_segment")
        .loc[REACTIVATION_SEGMENT_ORDER]
    )

    rates = plot_data[
        "future_purchase_rate_pct"
    ]

    lower_error = (
        rates
        - plot_data[
            "future_purchase_rate_ci95_lower_pct"
        ]
    )

    upper_error = (
        plot_data[
            "future_purchase_rate_ci95_upper_pct"
        ]
        - rates
    )

    fig, ax = plt.subplots(
        figsize=(8, 5.5)
    )

    bars = ax.bar(
        REACTIVATION_SEGMENT_ORDER,
        rates,
        yerr=[lower_error, upper_error],
        capsize=4,
    )

    ax.set_ylim(0, 35)

    ax.set_ylabel(
        "Held-out reactivation rate (%)"
    )

    ax.set_title(
        "High-value lapsed customers show higher held-out reactivation"
    )

    ax.grid(
        axis="y",
        alpha=0.2,
    )

    # Place labels above the upper Wilson bound so the vertical
    # confidence-interval whiskers do not run through the text.
    for bar, rate, upper_bound in zip(
        bars,
        rates,
        plot_data["future_purchase_rate_ci95_upper_pct"],
    ):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            upper_bound + 0.8,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    fig.tight_layout()

    output = (
        VISUALS_DIR
        / "04_lapsed_customer_reactivation.png"
    )

    fig.savefig(
        output,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)


def print_key_results(summary, overall_rate):
    """Print a compact QA and interpretation summary."""

    print("\n--- Final segment reporting QA ---")

    print(
        "Customers:",
        f"{int(summary['customer_count'].sum()):,}",
    )

    print(
        "Segments:",
        len(summary),
    )

    print(
        "Overall held-out purchase rate:",
        f"{overall_rate:.1f}%",
    )

    columns = [
        "customer_segment",
        "customer_count",
        "customer_share_pct",
        "future_purchase_rate_pct",
        "future_purchase_rate_ci95_lower_pct",
        "future_purchase_rate_ci95_upper_pct",
        "future_purchase_rate_lift",
        "positive_future_value_share_pct",
    ]

    print(
        "\n--- Final segment validation summary ---"
    )

    display = summary[columns].copy()

    display["customer_segment"] = (
        display["customer_segment"]
        .astype("string")
    )

    print(
        display.to_string(index=False)
    )

    high_value_lapsed = summary.loc[
        summary["customer_segment"]
        .astype("string")
        .eq("High-value lapsed")
    ].iloc[0]

    lapsed = summary.loc[
        summary["customer_segment"]
        .astype("string")
        .eq("Lapsed")
    ].iloc[0]

    reactivation_difference = (
        high_value_lapsed["future_purchase_rate_pct"]
        - lapsed["future_purchase_rate_pct"]
    )

    reactivation_ratio = (
        high_value_lapsed["future_purchase_rate_pct"]
        / lapsed["future_purchase_rate_pct"]
    )

    print(
        "\nHigh-value lapsed reactivation advantage:",
        f"{reactivation_difference:.1f} percentage points",
    )

    print(
        "High-value lapsed reactivation ratio:",
        f"{reactivation_ratio:.2f}x",
    )


def main():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {DATABASE_PATH}"
        )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    VISUALS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(DATABASE_PATH) as connection:
        data = load_validation_data(connection)

    validate_input(data)

    data["customer_segment"] = pd.Categorical(
        data["customer_segment"],
        categories=SEGMENT_ORDER,
        ordered=True,
    )

    summary = build_segment_summary(data)

    actions = build_actions_table(summary)

    summary.to_csv(
        SEGMENT_SUMMARY_FILE,
        index=False,
    )

    actions.to_csv(
        SEGMENT_ACTIONS_FILE,
        index=False,
    )

    overall_rate = (
        100
        * EXPECTED_FUTURE_PURCHASERS
        / EXPECTED_CUSTOMERS
    )

    save_segment_size_chart(summary)

    save_future_purchase_chart(
        summary,
        overall_rate,
    )

    save_value_persistence_chart(data)

    save_reactivation_chart(summary)

    print_key_results(
        summary,
        overall_rate,
    )

    print(
        "\nCreated report:",
        SEGMENT_SUMMARY_FILE.relative_to(PROJECT_ROOT),
    )

    print(
        "Created report:",
        SEGMENT_ACTIONS_FILE.relative_to(PROJECT_ROOT),
    )

    print(
        "\nCreated visuals:"
    )

    for filename in [
        "01_customer_population_by_segment.png",
        "02_future_purchase_rate_by_segment.png",
        "03_snapshot_vs_future_value_share.png",
        "04_lapsed_customer_reactivation.png",
    ]:
        print(
            " -",
            (VISUALS_DIR / filename)
            .relative_to(PROJECT_ROOT),
        )


if __name__ == "__main__":
    main()