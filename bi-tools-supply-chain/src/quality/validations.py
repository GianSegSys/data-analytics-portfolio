from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class ValidationReport:
    total_rows: int
    valid_rows: int
    invalid_rows: int
    invalid_reasons: dict[str, int]


def validate_products(df: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """
    Applies basic data quality rules and returns (valid_df, report).
    Rules:
      - sku not null/empty
      - price_list > 0 (if present)
      - price_sale > 0 (if present)
      - rating in [0,5] (if present)
      - reviews_count >= 0 (if present)
    """
    work = df.copy()

    reasons = {}

    def add_reason(mask: pd.Series, reason: str):
        count = int(mask.sum())
        if count > 0:
            reasons[reason] = reasons.get(reason, 0) + count

    # name
    name_invalid = work["name"].isna() | (work["name"].astype(str).str.strip() == "")
    add_reason(name_invalid, "invalid_name")

    # sku
    sku_invalid = work["sku"].isna() | (work["sku"].astype(str).str.strip() == "")
    add_reason(sku_invalid, "invalid_sku")

    # price_list
    if "price_list" in work.columns:
        price_list_invalid = work["price_list"].notna() & (work["price_list"] <= 0)
        add_reason(price_list_invalid, "invalid_price_list")

    # price_sale
    if "price_sale" in work.columns:
        price_sale_invalid = work["price_sale"].notna() & (work["price_sale"] <= 0)
        add_reason(price_sale_invalid, "invalid_price_sale")

    # rating
    if "rating" in work.columns:
        rating_invalid = work["rating"].notna() & ((work["rating"] < 0) | (work["rating"] > 5))
        add_reason(rating_invalid, "invalid_rating")

    # reviews_count
    if "reviews_count" in work.columns:
        reviews_invalid = work["reviews_count"].notna() & (work["reviews_count"] < 0)
        add_reason(reviews_invalid, "invalid_reviews_count")

    invalid_mask = name_invalid | sku_invalid
    if "price_sale" in work.columns:
        invalid_mask = invalid_mask | price_sale_invalid
    if "price_list" in work.columns:
        invalid_mask = invalid_mask | price_list_invalid
    if "rating" in work.columns:
        invalid_mask = invalid_mask | rating_invalid
    if "reviews_count" in work.columns:
        invalid_mask = invalid_mask | reviews_invalid

    valid_df = work.loc[~invalid_mask].copy()

    report = ValidationReport(
        total_rows=int(len(work)),
        valid_rows=int(len(valid_df)),
        invalid_rows=int(invalid_mask.sum()),
        invalid_reasons=reasons,
    )
    return valid_df, report
