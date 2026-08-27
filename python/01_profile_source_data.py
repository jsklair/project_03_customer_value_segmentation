# -*- coding: utf-8 -*-

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "online_retail_II.xlsx"
INTERIM_FILE = PROJECT_ROOT / "data" / "interim" / "online_retail_combined.pkl"

SOURCE_SHEETS = ("Year 2009-2010", "Year 2010-2011")
EXPECTED_COLUMNS = (
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
)
DISPLAY_COLUMNS = list(EXPECTED_COLUMNS)

# Increment this whenever the construction logic for the interim dataset changes.
CACHE_VERSION = 2

BEHAVIOURAL_START = pd.Timestamp("2010-06-01")
VALIDATION_START = pd.Timestamp("2011-06-01")
VALIDATION_END = pd.Timestamp("2011-12-01")


def print_section(title):
    """Print a consistent heading for profiling output."""
    print(f"\n--- {title} ---")


def safe_share(numerator, denominator):
    """Return a proportion while avoiding division-by-zero errors."""
    return numerator / denominator if denominator else float("nan")


def print_top(data, rows=30, index=True):
    """Print a compact preview of a Series or DataFrame."""
    print(data.head(rows).to_string(index=index))


def validate_source_columns(dataframe, source_name):
    """Confirm that a source table contains the expected transaction fields."""
    missing_columns = [
        column for column in EXPECTED_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        raise ValueError(
            f"{source_name} is missing expected columns: {missing_columns}"
        )


def compare_overlap(earlier_sheet, later_sheet):
    """Validate the period shared by the two annual source worksheets."""
    source_columns = list(EXPECTED_COLUMNS)

    earlier_start = earlier_sheet["InvoiceDate"].min()
    earlier_end = earlier_sheet["InvoiceDate"].max()
    later_start = later_sheet["InvoiceDate"].min()
    later_end = later_sheet["InvoiceDate"].max()

    overlap_start = max(earlier_start, later_start)
    overlap_end = min(earlier_end, later_end)
    if overlap_start > overlap_end:
        raise ValueError("The expected source worksheet overlap was not found.")

    earlier_overlap = earlier_sheet.loc[
        earlier_sheet["InvoiceDate"].between(overlap_start, overlap_end),
        source_columns,
    ].copy()
    later_overlap = later_sheet.loc[
        later_sheet["InvoiceDate"].between(overlap_start, overlap_end),
        source_columns,
    ].copy()

    def count_patterns(dataframe, name):
        return (
            dataframe.groupby(source_columns, dropna=False)
            .size()
            .rename(name)
            .reset_index()
        )

    earlier_counts = count_patterns(earlier_overlap, "earlier_count")
    later_counts = count_patterns(later_overlap, "later_count")

    comparison = earlier_counts.merge(
        later_counts,
        on=source_columns,
        how="outer",
    )
    comparison[["earlier_count", "later_count"]] = (
        comparison[["earlier_count", "later_count"]].fillna(0).astype(int)
    )

    same_count = comparison["earlier_count"].eq(comparison["later_count"])
    if not same_count.all():
        raise ValueError(
            "The overlapping source periods are not identical. "
            "Review the workbook before combining the worksheets."
        )

    return {
        "earlier_start": earlier_start,
        "earlier_end": earlier_end,
        "later_start": later_start,
        "later_end": later_end,
        "overlap_start": overlap_start,
        "overlap_end": overlap_end,
        "earlier_overlap_rows": len(earlier_overlap),
        "later_overlap_rows": len(later_overlap),
        "earlier_distinct_patterns": len(earlier_counts),
        "later_distinct_patterns": len(later_counts),
        "shared_patterns": int(
            ((comparison["earlier_count"] > 0) & (comparison["later_count"] > 0)).sum()
        ),
        "identical_count_patterns": int(same_count.sum()),
        "total_comparison_patterns": len(comparison),
        "matched_occurrences": int(
            comparison[["earlier_count", "later_count"]].min(axis=1).sum()
        ),
        "different_count_patterns": int((~same_count).sum()),
        "removed_later_overlap_rows": len(later_overlap),
    }


def build_interim_dataset():
    """Build the combined dataset while removing proven worksheet overlap."""
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Source file not found: {RAW_FILE}")

    print("Creating interim dataset from Excel...")
    source_data = pd.read_excel(RAW_FILE, sheet_name=list(SOURCE_SHEETS))

    earlier_sheet = source_data[SOURCE_SHEETS[0]].copy()
    later_sheet = source_data[SOURCE_SHEETS[1]].copy()

    for sheet_name, dataframe in (
        (SOURCE_SHEETS[0], earlier_sheet),
        (SOURCE_SHEETS[1], later_sheet),
    ):
        validate_source_columns(dataframe, sheet_name)
        dataframe["InvoiceDate"] = pd.to_datetime(dataframe["InvoiceDate"])

    overlap_summary = compare_overlap(earlier_sheet, later_sheet)

    # Keep the earlier worksheet in full, then append only records occurring
    # after it ends. This removes proven duplicate source coverage while
    # preserving repeated rows that genuinely exist inside either worksheet.
    later_non_overlap = later_sheet.loc[
        later_sheet["InvoiceDate"] > overlap_summary["earlier_end"]
    ].copy()

    transactions = pd.concat(
        [earlier_sheet, later_non_overlap],
        ignore_index=True,
    )
    validate_source_columns(transactions, "Combined transactions")

    cache_payload = {
        "cache_version": CACHE_VERSION,
        "transactions": transactions,
        "overlap_summary": overlap_summary,
    }
    INTERIM_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(cache_payload, INTERIM_FILE)
    print(f"Created: {INTERIM_FILE.name}")

    return transactions, overlap_summary


def load_transactions():
    """Load the validated cache where possible, otherwise rebuild from Excel."""
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Source file not found: {RAW_FILE}")

    if INTERIM_FILE.exists():
        print("Checking cached interim dataset...")
        try:
            cached_object = pd.read_pickle(INTERIM_FILE)
        except Exception:
            print("Cached interim dataset could not be read. Rebuilding from Excel.")
        else:
            valid_cache = (
                isinstance(cached_object, dict)
                and cached_object.get("cache_version") == CACHE_VERSION
                and "transactions" in cached_object
                and "overlap_summary" in cached_object
            )
            if valid_cache:
                print("Loading validated cached interim dataset...")
                return (
                    cached_object["transactions"],
                    cached_object["overlap_summary"],
                )
            print("Existing interim cache uses older construction logic. Rebuilding from Excel.")

    return build_interim_dataset()


def build_context(transactions):
    """Create shared masks and measures used across profiling sections."""
    missing_customer = transactions["Customer ID"].isna()
    negative_quantity = transactions["Quantity"] < 0
    zero_quantity = transactions["Quantity"] == 0
    negative_price = transactions["Price"] < 0
    zero_price = transactions["Price"] == 0
    cancelled = transactions["Invoice"].astype("string").str.startswith("C", na=False)
    line_value = transactions["Quantity"] * transactions["Price"]
    positive_sale = (transactions["Quantity"] > 0) & (transactions["Price"] > 0)

    return {
        "missing_customer": missing_customer,
        "negative_quantity": negative_quantity,
        "zero_quantity": zero_quantity,
        "negative_price": negative_price,
        "zero_price": zero_price,
        "cancelled": cancelled,
        "line_value": line_value,
        "positive_sale": positive_sale,
        "total_positive_value": line_value.loc[positive_sale].sum(),
    }


def profile_source_overview(transactions, overlap_summary, context):
    """Report source construction, dimensions and headline quality counts."""
    print_section("Source worksheet overlap")
    print(
        f"Year 2009-2010 date range: {overlap_summary['earlier_start']} "
        f"to {overlap_summary['earlier_end']}"
    )
    print(
        f"Year 2010-2011 date range: {overlap_summary['later_start']} "
        f"to {overlap_summary['later_end']}"
    )
    print(
        f"Overlap period: {overlap_summary['overlap_start']} "
        f"to {overlap_summary['overlap_end']}"
    )
    print(f"Earlier-sheet overlap rows: {overlap_summary['earlier_overlap_rows']:,}")
    print(f"Later-sheet overlap rows: {overlap_summary['later_overlap_rows']:,}")
    print(
        "Distinct row patterns in earlier overlap: "
        f"{overlap_summary['earlier_distinct_patterns']:,}"
    )
    print(
        "Distinct row patterns in later overlap: "
        f"{overlap_summary['later_distinct_patterns']:,}"
    )
    print(f"Exact row patterns present in both sheets: {overlap_summary['shared_patterns']:,}")
    print(
        "Patterns with identical occurrence counts: "
        f"{overlap_summary['identical_count_patterns']:,} of "
        f"{overlap_summary['total_comparison_patterns']:,}"
    )
    print(
        "Matched row occurrences across the two sheets: "
        f"{overlap_summary['matched_occurrences']:,}"
    )
    print(
        "Rows removed from the later worksheet as duplicate source coverage: "
        f"{overlap_summary['removed_later_overlap_rows']:,}"
    )

    print_section("Combined dataset")
    print(f"Rows: {len(transactions):,}")
    print(f"Columns: {transactions.shape[1]}")
    print(
        f"Date range: {transactions['InvoiceDate'].min()} "
        f"to {transactions['InvoiceDate'].max()}"
    )
    print("\nData types:")
    print(transactions.dtypes.to_string())
    print("\nMissing values:")
    print(transactions.isna().sum().to_string())

    print_section("Initial data quality checks")
    metrics = {
        "Duplicate rows": transactions.duplicated().sum(),
        "Negative quantities": context["negative_quantity"].sum(),
        "Zero quantities": context["zero_quantity"].sum(),
        "Negative prices": context["negative_price"].sum(),
        "Zero prices": context["zero_price"].sum(),
        "Cancellation rows": context["cancelled"].sum(),
        "Unique invoices": transactions["Invoice"].nunique(),
        "Identifiable customers": transactions["Customer ID"].nunique(),
        "Countries": transactions["Country"].nunique(),
    }
    for label, value in metrics.items():
        print(f"{label}: {value:,}")


def profile_missing_customers(transactions, context):
    """Quantify how missing customer identifiers affect customer-level analysis."""
    missing_customer = context["missing_customer"]
    positive_sale = context["positive_sale"]
    line_value = context["line_value"]

    missing_positive_value = line_value.loc[missing_customer & positive_sale].sum()

    print_section("Missing Customer ID impact")
    print(f"Rows without Customer ID: {missing_customer.sum():,}")
    print(f"Share of source rows: {missing_customer.mean():.1%}")
    print(
        "Invoices containing rows without Customer ID: "
        f"{transactions.loc[missing_customer, 'Invoice'].nunique():,}"
    )
    print(f"Raw positive transaction value without Customer ID: £{missing_positive_value:,.2f}")
    print(
        "Share of raw positive transaction value: "
        f"{safe_share(missing_positive_value, context['total_positive_value']):.1%}"
    )
    print(
        "\nNote: these are profiling figures before final cleaning rules. "
        "Recalculate the final exclusion impact after cleaning."
    )


def profile_quantities_and_prices(transactions, context):
    """Investigate cancellations, negative quantities and price anomalies."""
    missing_customer = context["missing_customer"]
    negative_quantity = context["negative_quantity"]
    negative_price = context["negative_price"]
    zero_price = context["zero_price"]
    cancelled = context["cancelled"]

    negative_cancelled = negative_quantity & cancelled
    negative_not_cancelled = negative_quantity & ~cancelled
    cancelled_not_negative = cancelled & ~negative_quantity

    print_section("Negative quantity investigation")
    print(f"Negative quantity rows: {negative_quantity.sum():,}")
    print(f"Negative quantity rows on C invoices: {negative_cancelled.sum():,}")
    print(f"Negative quantity rows not on C invoices: {negative_not_cancelled.sum():,}")
    print(f"Cancellation rows without negative quantity: {cancelled_not_negative.sum():,}")

    negative_non_cancel_rows = transactions.loc[
        negative_not_cancelled,
        DISPLAY_COLUMNS,
    ].copy()
    print_section("Non-cancellation negative rows")
    print(f"Rows: {len(negative_non_cancel_rows):,}")
    print(f"Zero-price rows: {(negative_non_cancel_rows['Price'] == 0).sum():,}")
    print(f"Missing Customer ID: {negative_non_cancel_rows['Customer ID'].isna().sum():,}")
    print("\nMost common descriptions:")
    print_top(negative_non_cancel_rows["Description"].value_counts(dropna=False), 30)

    print_section("Cancellation rows without negative quantity")
    print(transactions.loc[cancelled_not_negative, DISPLAY_COLUMNS].to_string(index=False))

    print_section("Price anomaly investigation")
    print(f"Negative-price rows: {negative_price.sum():,}")
    if negative_price.any():
        print("\nNegative-price records:")
        print(transactions.loc[negative_price, DISPLAY_COLUMNS].to_string(index=False))
    print(f"\nZero-price rows with Customer ID: {(zero_price & ~missing_customer).sum():,}")
    print(f"Zero-price rows without Customer ID: {(zero_price & missing_customer).sum():,}")

    zero_price_identified_rows = transactions.loc[
        zero_price & ~missing_customer,
        DISPLAY_COLUMNS,
    ].copy()
    print_section("Zero-price identifiable customer rows")
    print(f"Rows: {len(zero_price_identified_rows):,}")
    print(f"Unique invoices: {zero_price_identified_rows['Invoice'].nunique():,}")
    print(f"Unique customers: {zero_price_identified_rows['Customer ID'].nunique():,}")
    print(f"Positive quantities: {(zero_price_identified_rows['Quantity'] > 0).sum():,}")
    print(f"Negative quantities: {(zero_price_identified_rows['Quantity'] < 0).sum():,}")
    print("\nMost common StockCodes:")
    print_top(zero_price_identified_rows["StockCode"].value_counts(dropna=False), 20)
    print("\nMost common descriptions:")
    print_top(zero_price_identified_rows["Description"].value_counts(dropna=False), 20)


def profile_special_codes(transactions):
    """Surface candidate non-standard StockCodes without treating them as invalid."""
    stock_code_text = (
        transactions["StockCode"].astype("string").str.strip().str.upper()
    )
    standard_product_code = stock_code_text.str.fullmatch(
        r"\d{5}[A-Z]{0,2}",
        na=False,
    )

    special_rows = transactions.loc[~standard_product_code, DISPLAY_COLUMNS].copy()
    special_rows["line_value"] = special_rows["Quantity"] * special_rows["Price"]

    summary = (
        special_rows.groupby("StockCode", dropna=False)
        .agg(
            rows=("Invoice", "size"),
            invoices=("Invoice", "nunique"),
            customers=("Customer ID", "nunique"),
            total_quantity=("Quantity", "sum"),
            total_line_value=("line_value", "sum"),
        )
        .sort_values("rows", ascending=False)
    )

    descriptions = (
        special_rows.groupby(["StockCode", "Description"], dropna=False)
        .size()
        .rename("rows")
        .reset_index()
        .sort_values(["StockCode", "rows"], ascending=[True, False])
    )

    print_section("Potential special or non-product StockCodes")
    print(f"Rows with candidate special StockCodes: {len(special_rows):,}")
    print(f"Distinct candidate StockCodes: {special_rows['StockCode'].nunique():,}")
    print("\nCandidate StockCode summary:")
    print_top(summary, 50)
    print("\nCandidate StockCode-description combinations:")
    print_top(descriptions, 80, index=False)


def profile_manual_transactions(transactions):
    """Test whether manual entries show systematic reversal/correction behaviour."""
    manual_code = (
        transactions["StockCode"].astype("string").str.strip().str.upper().eq("M")
    )
    manual_rows = transactions.loc[manual_code, DISPLAY_COLUMNS].copy()
    manual_rows["line_value"] = manual_rows["Quantity"] * manual_rows["Price"]
    manual_rows["is_cancellation"] = (
        manual_rows["Invoice"].astype("string").str.startswith("C", na=False)
    )
    manual_rows["customer_status"] = manual_rows["Customer ID"].notna().map(
        {True: "Identified customer", False: "Missing Customer ID"}
    )

    print_section("Manual StockCode investigation")
    metrics = {
        "Rows": len(manual_rows),
        "Unique invoices": manual_rows["Invoice"].nunique(),
        "Unique customers": manual_rows["Customer ID"].nunique(),
        "Missing Customer ID": manual_rows["Customer ID"].isna().sum(),
        "Cancellation rows": manual_rows["is_cancellation"].sum(),
        "Positive quantities": (manual_rows["Quantity"] > 0).sum(),
        "Negative quantities": (manual_rows["Quantity"] < 0).sum(),
        "Positive prices": (manual_rows["Price"] > 0).sum(),
        "Zero prices": (manual_rows["Price"] == 0).sum(),
        "Negative prices": (manual_rows["Price"] < 0).sum(),
    }
    for label, value in metrics.items():
        print(f"{label}: {value:,}")
    print(f"Net line value: £{manual_rows['line_value'].sum():,.2f}")

    print("\nLargest manual rows by absolute line value:")
    largest_manual = (
        manual_rows.assign(abs_line_value=manual_rows["line_value"].abs())
        .sort_values("abs_line_value", ascending=False)
        .drop(columns="abs_line_value")
    )
    print_top(largest_manual, 30, index=False)

    print_section("Manual rows by cancellation and customer identification")
    status_summary = (
        manual_rows.groupby(["is_cancellation", "customer_status"], dropna=False)
        .agg(
            rows=("Invoice", "size"),
            invoices=("Invoice", "nunique"),
            customers=("Customer ID", "nunique"),
            total_quantity=("Quantity", "sum"),
            total_line_value=("line_value", "sum"),
        )
    )
    print(status_summary.to_string())

    manual_rows["absolute_quantity"] = manual_rows["Quantity"].abs()
    reversal_summary = (
        manual_rows.groupby(["Price", "absolute_quantity"], dropna=False)
        .agg(
            positive_rows=("Quantity", lambda values: (values > 0).sum()),
            negative_rows=("Quantity", lambda values: (values < 0).sum()),
            rows=("Invoice", "size"),
            total_line_value=("line_value", "sum"),
        )
        .reset_index()
    )
    candidates = reversal_summary.loc[
        (reversal_summary["positive_rows"] > 0)
        & (reversal_summary["negative_rows"] > 0)
    ].copy()

    print_section("Manual value reversal patterns")
    print(f"Price/quantity combinations appearing in both directions: {len(candidates):,}")
    print("\nMost frequent potential reversal combinations:")
    print_top(
        candidates.sort_values(["rows", "Price"], ascending=[False, False]),
        40,
        index=False,
    )

    balanced = candidates.loc[
        candidates["positive_rows"].eq(candidates["negative_rows"])
        & candidates["total_line_value"].abs().lt(0.01)
    ].copy()
    balanced_rows = balanced["rows"].sum()

    print_section("Balanced manual reversal combinations")
    print(f"Perfectly balanced price/quantity combinations: {len(balanced):,}")
    print(
        f"Manual rows in those combinations: {balanced_rows:,} "
        f"({safe_share(balanced_rows, len(manual_rows)):.1%} of manual rows)"
    )
    print("\nLargest perfectly balanced combinations by price:")
    print_top(balanced.sort_values("Price", ascending=False), 30, index=False)


def profile_duplicates(transactions, context):
    """Assess retained exact duplicates without assuming they are erroneous."""
    duplicate_group_mask = transactions.duplicated(keep=False)
    duplicate_rows = transactions.loc[duplicate_group_mask, DISPLAY_COLUMNS].copy()
    duplicate_rows["line_value"] = duplicate_rows["Quantity"] * duplicate_rows["Price"]

    duplicate_groups = (
        transactions.loc[duplicate_group_mask]
        .groupby(list(EXPECTED_COLUMNS), dropna=False)
        .size()
        .rename("group_size")
        .reset_index()
        .sort_values("group_size", ascending=False)
    )
    rows_in_groups = len(duplicate_rows)
    group_count = len(duplicate_groups)
    excess_count = rows_in_groups - group_count

    print_section("Exact duplicate investigation")
    print(f"Rows belonging to duplicate groups: {rows_in_groups:,}")
    print(f"Distinct exact duplicate groups: {group_count:,}")
    print(f"Excess rows beyond one row per group: {excess_count:,}")
    print(
        "Largest exact duplicate group: "
        f"{duplicate_groups['group_size'].max() if group_count else 0:,} rows"
    )
    print("\nDuplicate group-size distribution:")
    print(duplicate_groups["group_size"].value_counts().sort_index().to_string())
    print("\nLargest exact duplicate groups:")
    print_top(duplicate_groups, 30, index=False)

    print_section("Duplicate timing investigation")
    if duplicate_rows.empty:
        print("No exact duplicate groups remain.")
    else:
        overlap_mask = duplicate_rows["InvoiceDate"].between(
            pd.Timestamp("2010-12-01"),
            pd.Timestamp("2010-12-09 23:59:59"),
        )
        duplicate_by_date = (
            duplicate_rows.assign(duplicate_date=duplicate_rows["InvoiceDate"].dt.date)
            .groupby("duplicate_date")
            .size()
            .rename("rows")
            .sort_values(ascending=False)
        )
        print(
            "Duplicate-group rows from 1-9 Dec 2010 after source-overlap removal: "
            f"{overlap_mask.sum():,}"
        )
        print(f"Share of remaining duplicate-group rows: {overlap_mask.mean():.1%}")
        print("\nDates with the most remaining duplicate-group rows:")
        print_top(duplicate_by_date, 30)

    invoice_product_counts = (
        transactions.groupby(["Invoice", "StockCode"], dropna=False)
        .size()
        .rename("rows")
        .reset_index()
    )
    repeated_invoice_products = invoice_product_counts.loc[
        invoice_product_counts["rows"] > 1,
        ["Invoice", "StockCode", "rows"],
    ].copy()
    repeated_keys = transactions.merge(
        repeated_invoice_products[["Invoice", "StockCode"]],
        on=["Invoice", "StockCode"],
        how="inner",
    )
    repeated_summary = (
        repeated_keys.groupby(["Invoice", "StockCode"], dropna=False)
        .agg(
            rows=("InvoiceDate", "size"),
            distinct_quantities=("Quantity", "nunique"),
            distinct_prices=("Price", "nunique"),
            distinct_descriptions=("Description", "nunique"),
        )
        .reset_index()
    )
    varied = repeated_summary.loc[
        (repeated_summary["distinct_quantities"] > 1)
        | (repeated_summary["distinct_prices"] > 1)
        | (repeated_summary["distinct_descriptions"] > 1)
    ]

    print_section("Repeated product lines within invoices")
    print(
        "Invoice/StockCode combinations appearing more than once: "
        f"{len(repeated_invoice_products):,}"
    )
    print(
        "Repeated combinations with differing quantity, price or description: "
        f"{len(varied):,}"
    )
    print("\nExamples of repeated products with differing line details:")
    print_top(varied.sort_values("rows", ascending=False), 30, index=False)

    excess_duplicate = transactions.duplicated(keep="first")
    excess_rows = transactions.loc[excess_duplicate, DISPLAY_COLUMNS].copy()
    excess_rows["line_value"] = excess_rows["Quantity"] * excess_rows["Price"]
    excess_positive_sale = excess_duplicate & context["positive_sale"]
    excess_positive_value = context["line_value"].loc[excess_positive_sale].sum()

    print_section("Exact duplicate commercial impact")
    print(f"Excess exact duplicate rows: {excess_duplicate.sum():,}")
    print(f"Affected invoices: {transactions.loc[excess_duplicate, 'Invoice'].nunique():,}")
    print(
        "Affected identifiable customers: "
        f"{transactions.loc[excess_duplicate & ~context['missing_customer'], 'Customer ID'].nunique():,}"
    )
    print(f"Rows with missing Customer ID: {(excess_duplicate & context['missing_customer']).sum():,}")
    print(f"Cancellation rows: {(excess_duplicate & context['cancelled']).sum():,}")
    print(f"Positive-sale rows: {excess_positive_sale.sum():,}")
    print(f"Net line value of excess duplicate rows: £{excess_rows['line_value'].sum():,.2f}")
    print(
        "Raw positive transaction value represented by excess duplicate rows: "
        f"£{excess_positive_value:,.2f}"
    )
    print(
        "Share of total raw positive transaction value: "
        f"{safe_share(excess_positive_value, context['total_positive_value']):.2%}"
    )

    identified_positive_sale = context["positive_sale"] & ~context["missing_customer"]
    customer_positive_value = (
        transactions.loc[identified_positive_sale]
        .assign(line_value=context["line_value"].loc[identified_positive_sale])
        .groupby("Customer ID")["line_value"]
        .sum()
        .rename("positive_value")
    )
    customer_duplicate_value = (
        transactions.loc[excess_duplicate & identified_positive_sale]
        .assign(
            duplicate_positive_value=context["line_value"].loc[
                excess_duplicate & identified_positive_sale
            ]
        )
        .groupby("Customer ID")["duplicate_positive_value"]
        .sum()
    )
    customer_impact = (
        customer_positive_value.to_frame()
        .join(customer_duplicate_value, how="left")
        .fillna({"duplicate_positive_value": 0})
    )
    customer_impact["duplicate_value_share"] = (
        customer_impact["duplicate_positive_value"] / customer_impact["positive_value"]
    )
    affected = customer_impact.loc[customer_impact["duplicate_positive_value"] > 0].copy()

    print_section("Exact duplicate customer-level impact")
    print(f"Customers with positive duplicate value: {len(affected):,}")
    print(f"Median duplicate share among affected customers: {affected['duplicate_value_share'].median():.2%}")
    print(f"95th percentile duplicate share: {affected['duplicate_value_share'].quantile(0.95):.2%}")
    print(f"Maximum duplicate share: {affected['duplicate_value_share'].max():.2%}")
    for threshold in (0.01, 0.05, 0.10):
        print(
            f"Affected customers with duplicate share above {threshold:.0%}: "
            f"{(affected['duplicate_value_share'] > threshold).sum():,}"
        )
    print("\nCustomers with the largest duplicate-value shares:")
    print_top(affected.sort_values("duplicate_value_share", ascending=False), 20)


def profile_invoice_customer_consistency(transactions):
    """Check whether invoices map cleanly to customer identifiers."""
    invoice_profile = (
        transactions.groupby("Invoice", dropna=False)
        .agg(
            rows=("Invoice", "size"),
            identifiable_customers=("Customer ID", "nunique"),
            missing_customer_rows=("Customer ID", lambda values: values.isna().sum()),
        )
    )
    multi_customer = invoice_profile.loc[invoice_profile["identifiable_customers"] > 1]
    mixed_id = invoice_profile.loc[
        (invoice_profile["identifiable_customers"] > 0)
        & (invoice_profile["missing_customer_rows"] > 0)
    ]
    all_missing = invoice_profile.loc[invoice_profile["identifiable_customers"] == 0]

    print_section("Invoice-to-customer consistency")
    print(f"Total invoices: {len(invoice_profile):,}")
    print(f"Invoices linked to more than one identifiable customer: {len(multi_customer):,}")
    print(f"Invoices containing both identified and missing Customer ID rows: {len(mixed_id):,}")
    print(f"Invoices with no identifiable customer: {len(all_missing):,}")

    return len(multi_customer)


def profile_customer_country_consistency(transactions, context):
    """Check whether customers are associated with more than one country."""
    identified = transactions.loc[~context["missing_customer"]].copy()
    country_counts = identified.groupby("Customer ID")["Country"].nunique()
    multi_country = country_counts.loc[country_counts > 1]

    print_section("Customer-to-country consistency")
    print(f"Identifiable customers: {len(country_counts):,}")
    print(f"Customers associated with more than one country: {len(multi_country):,}")
    print(
        "Share of identifiable customers with multiple countries: "
        f"{safe_share(len(multi_country), len(country_counts)):.2%}"
    )
    print("\nCountry-count distribution by customer:")
    print(country_counts.value_counts().sort_index().to_string())

    if len(multi_country):
        country_examples = identified.groupby("Customer ID")["Country"].agg(
            lambda values: " | ".join(sorted(set(values.dropna().astype(str))))
        )
        detail = (
            multi_country.rename("country_count")
            .to_frame()
            .join(country_examples.rename("countries"))
            .sort_values("country_count", ascending=False)
        )
        print("\nCustomers associated with the most countries:")
        print_top(detail, 30)

    return len(multi_country)


def profile_stock_descriptions(transactions):
    """Assess product-code formatting and description stability."""
    described = transactions.loc[
        transactions["Description"].notna(),
        ["StockCode", "Description"],
    ].copy()
    described["stock_code_normalised"] = (
        described["StockCode"].astype("string").str.strip().str.upper()
    )
    described["description_normalised"] = (
        described["Description"].astype("string").str.strip().str.upper()
    )

    description_counts = (
        described.groupby("stock_code_normalised")["description_normalised"]
        .nunique()
        .rename("distinct_descriptions")
    )
    inconsistent = description_counts.loc[description_counts > 1]
    description_examples = described.groupby("stock_code_normalised")["description_normalised"].agg(
        lambda values: " | ".join(sorted(set(values))[:5])
    )

    print_section("StockCode-to-description consistency")
    print(f"Normalised StockCodes with at least one description: {len(description_counts):,}")
    print(f"StockCodes associated with more than one normalised description: {len(inconsistent):,}")
    print(
        "Share of described StockCodes with multiple descriptions: "
        f"{safe_share(len(inconsistent), len(description_counts)):.2%}"
    )
    if len(inconsistent):
        detail = (
            inconsistent.to_frame()
            .join(description_examples.rename("description_examples"))
            .sort_values("distinct_descriptions", ascending=False)
        )
        print("\nStockCodes with the most distinct descriptions:")
        print_top(detail, 30)

    variants = transactions[["StockCode"]].copy()
    variants["stock_code_normalised"] = (
        variants["StockCode"].astype("string").str.strip().str.upper()
    )
    variant_counts = (
        variants.groupby("stock_code_normalised")["StockCode"]
        .nunique()
        .rename("raw_variant_count")
    )
    multiple_variants = variant_counts.loc[variant_counts > 1]

    print(
        "\nNormalised StockCodes represented by multiple raw code variants: "
        f"{len(multiple_variants):,}"
    )
    if len(multiple_variants):
        raw_examples = variants.groupby("stock_code_normalised")["StockCode"].agg(
            lambda values: " | ".join(
                sorted({str(value).strip() for value in values.dropna()})
            )
        )
        detail = (
            multiple_variants.to_frame()
            .join(raw_examples.rename("raw_variants"))
            .sort_values("raw_variant_count", ascending=False)
        )
        print("\nExamples of StockCode formatting variants:")
        print_top(detail, 30)

    return len(inconsistent)


def profile_outliers(transactions, context):
    """Describe extreme positive customer-identified transactions without deleting them."""
    commercial_rows = transactions.loc[
        context["positive_sale"] & ~context["missing_customer"],
        DISPLAY_COLUMNS,
    ].copy()
    commercial_rows["line_value"] = commercial_rows["Quantity"] * commercial_rows["Price"]

    percentiles = [0.50, 0.95, 0.99, 0.999, 1.00]
    labels = ["50th", "95th", "99th", "99.9th", "Maximum"]
    quantity_percentiles = commercial_rows["Quantity"].quantile(percentiles)
    value_percentiles = commercial_rows["line_value"].quantile(percentiles)

    print_section("Commercial transaction outliers")
    print(f"Identifiable positive-sale rows: {len(commercial_rows):,}")
    print("\nPositive quantity percentiles:")
    for percentile, label in zip(percentiles, labels):
        print(f"{label}: {quantity_percentiles.loc[percentile]:,.0f}")
    print("\nPositive line-value percentiles:")
    for percentile, label in zip(percentiles, labels):
        print(f"{label}: £{value_percentiles.loc[percentile]:,.2f}")
    print("\nLargest identifiable positive-sale rows by line value:")
    print_top(commercial_rows.sort_values("line_value", ascending=False), 30, index=False)
    print("\nLargest identifiable positive-sale rows by quantity:")
    print_top(commercial_rows.sort_values("Quantity", ascending=False), 30, index=False)


def profile_analysis_windows(transactions, context):
    """Profile the raw snapshot and held-out validation populations."""
    behavioural_period = transactions["InvoiceDate"].between(
        BEHAVIOURAL_START,
        VALIDATION_START,
        inclusive="left",
    )
    validation_period = transactions["InvoiceDate"].between(
        VALIDATION_START,
        VALIDATION_END,
        inclusive="left",
    )

    missing_customer = context["missing_customer"]
    positive_sale = context["positive_sale"]
    line_value = context["line_value"]

    behavioural_customers = set(
        transactions.loc[behavioural_period & ~missing_customer, "Customer ID"].unique()
    )
    validation_customers = set(
        transactions.loc[validation_period & ~missing_customer, "Customer ID"].unique()
    )
    behavioural_positive_customers = set(
        transactions.loc[
            behavioural_period & ~missing_customer & positive_sale,
            "Customer ID",
        ].unique()
    )
    validation_positive_customers = set(
        transactions.loc[
            validation_period & ~missing_customer & positive_sale,
            "Customer ID",
        ].unique()
    )

    behavioural_rows = int(behavioural_period.sum())
    behavioural_missing_rows = int((behavioural_period & missing_customer).sum())
    behavioural_positive_value = line_value.loc[behavioural_period & positive_sale].sum()
    behavioural_missing_positive_value = line_value.loc[
        behavioural_period & positive_sale & missing_customer
    ].sum()

    print_section("Raw behavioural and validation populations")
    print("Behavioural window: 1 Jun 2010 to 31 May 2011")
    print(f"Raw transaction rows in behavioural window: {behavioural_rows:,}")
    print(f"Rows without Customer ID in behavioural window: {behavioural_missing_rows:,}")
    print(
        "Share of behavioural rows without Customer ID: "
        f"{safe_share(behavioural_missing_rows, behavioural_rows):.1%}"
    )
    print(f"Raw identifiable customers in behavioural window: {len(behavioural_customers):,}")
    print(
        "Identifiable customers with at least one positive-sale row in behavioural window: "
        f"{len(behavioural_positive_customers):,}"
    )
    print(
        "Raw positive transaction value without Customer ID in behavioural window: "
        f"£{behavioural_missing_positive_value:,.2f}"
    )
    print(
        "Share of behavioural raw positive value without Customer ID: "
        f"{safe_share(behavioural_missing_positive_value, behavioural_positive_value):.1%}"
    )

    print("\nValidation window: 1 Jun 2011 to 30 Nov 2011")
    print(f"Raw transaction rows in validation window: {validation_period.sum():,}")
    print(f"Raw identifiable customers in validation window: {len(validation_customers):,}")
    print(
        "Identifiable customers with at least one positive-sale row in validation window: "
        f"{len(validation_positive_customers):,}"
    )
    print(
        "Behavioural-window customers also observed in validation window: "
        f"{len(behavioural_customers & validation_customers):,}"
    )
    print(
        "Identifiable validation customers not observed in behavioural window: "
        f"{len(validation_customers - behavioural_customers):,}"
    )

    return len(behavioural_customers), len(behavioural_positive_customers)


def print_checkpoint(
    transactions,
    overlap_summary,
    context,
    multi_customer_count,
    multi_country_count,
    inconsistent_description_count,
    behavioural_customer_count,
    behavioural_positive_customer_count,
):
    """Collect the main pre-cleaning diagnostics in one final checkpoint."""
    print_section("Profiling phase checkpoint")
    metrics = {
        "Corrected source rows": len(transactions),
        "Proven overlapping source rows removed": overlap_summary["removed_later_overlap_rows"],
        "Remaining excess exact duplicate rows retained pending sensitivity analysis": transactions.duplicated().sum(),
        "Rows without Customer ID": context["missing_customer"].sum(),
        "Negative quantity rows": context["negative_quantity"].sum(),
        "Zero-price rows": context["zero_price"].sum(),
        "Negative-price rows": context["negative_price"].sum(),
        "Cancellation rows": context["cancelled"].sum(),
        "Invoices linked to multiple identifiable customers": multi_customer_count,
        "Customers associated with multiple countries": multi_country_count,
        "Normalised StockCodes with multiple descriptions": inconsistent_description_count,
        "Raw identifiable behavioural-window customers": behavioural_customer_count,
        "Raw identifiable behavioural-window customers with positive-sale activity": behavioural_positive_customer_count,
    }
    for label, value in metrics.items():
        print(f"{label}: {value:,}")

    print(
        "\nProfiling is descriptive only. Final cleaning rules and the resulting "
        "analytical population should be documented and recalculated separately."
    )


def main():
    transactions, overlap_summary = load_transactions()
    validate_source_columns(transactions, "Combined transactions")
    context = build_context(transactions)

    profile_source_overview(transactions, overlap_summary, context)
    profile_missing_customers(transactions, context)
    profile_quantities_and_prices(transactions, context)
    profile_special_codes(transactions)
    profile_manual_transactions(transactions)
    profile_duplicates(transactions, context)

    multi_customer_count = profile_invoice_customer_consistency(transactions)
    multi_country_count = profile_customer_country_consistency(transactions, context)
    inconsistent_description_count = profile_stock_descriptions(transactions)
    profile_outliers(transactions, context)
    behavioural_customer_count, behavioural_positive_customer_count = (
        profile_analysis_windows(transactions, context)
    )

    print_checkpoint(
        transactions,
        overlap_summary,
        context,
        multi_customer_count,
        multi_country_count,
        inconsistent_description_count,
        behavioural_customer_count,
        behavioural_positive_customer_count,
    )


if __name__ == "__main__":
    main()
