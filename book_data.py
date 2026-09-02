"""Data loading and calculations for the personal books dashboard."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd


ADMIN_COLLECTIONS = frozenset({"archive", "Box1", "Box2", "Box3"})

SOURCE_COLUMNS = [
    "Book ID",
    "Title",
    "Primary Author",
    "Date",
    "Page Count",
    "Collections",
    "Languages",
    "Original Languages",
    "Dewey Decimal",
    "Dewey Wording",
]

TEXT_COLUMNS = [
    "Title",
    "Primary Author",
    "Collections",
    "Languages",
    "Original Languages",
    "Dewey Decimal",
    "Dewey Wording",
]


def _clean_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    return cleaned if cleaned else pd.NA


def load_book_data(workbook_path: Path | str) -> pd.DataFrame:
    """Read and conservatively normalize the source workbook without writing to it."""
    workbook_path = Path(workbook_path)
    workbook = pd.ExcelFile(workbook_path, engine="openpyxl")
    if "Simple" not in workbook.sheet_names:
        raise ValueError("Books_Sept2.xlsx does not contain the expected 'Simple' worksheet.")

    source = pd.read_excel(workbook_path, sheet_name="Simple", engine="openpyxl")
    missing = [column for column in SOURCE_COLUMNS if column not in source.columns]
    if missing:
        raise ValueError(
            "Books_Sept2.xlsx is missing required columns: " + ", ".join(missing)
        )

    data = source[SOURCE_COLUMNS].copy().reset_index(drop=True)
    data.insert(0, "_Book Row", data.index)
    for column in TEXT_COLUMNS:
        data[column] = data[column].apply(_clean_text)

    # Keep Date untouched and add a conservative year field. Excel dates or ranges
    # are not guessed: only whole numbers in a plausible publication-year range pass.
    numeric_dates = pd.to_numeric(data["Date"], errors="coerce")
    valid_year = numeric_dates.mod(1).eq(0) & numeric_dates.between(1000, 2100)
    data["Publication Year"] = numeric_dates.where(valid_year).astype("Int64")

    # Preserve the exact source text for inspection and table display. Only plain
    # numeric page counts contribute to calculations (for example, "xvi; 304" does not).
    data["Page Count Source"] = data["Page Count"]
    page_text = data["Page Count"].astype("string").str.strip()
    plain_pages = page_text.str.fullmatch(r"\d+(?:\.0+)?", na=False)
    data["Page Count"] = pd.to_numeric(
        page_text.where(plain_pages), errors="coerce"
    ).astype("Int64")

    # The source calls this field Primary Author; expose the dashboard-friendly label
    # without altering the source workbook or discarding the original column.
    data["Author"] = data["Primary Author"]
    return data


def split_memberships(data: pd.DataFrame, source_column: str, label: str) -> pd.DataFrame:
    """Return one row per book/category membership for comma-separated fields."""
    memberships = data[["_Book Row", source_column]].copy()
    memberships[label] = memberships[source_column].astype("string").str.split(
        r"\s*,\s*"
    )
    memberships = memberships.explode(label)
    memberships[label] = memberships[label].str.strip()
    memberships = memberships.loc[
        memberships[label].notna() & memberships[label].ne(""),
        ["_Book Row", label],
    ]
    if source_column == "Collections":
        memberships = memberships.loc[~memberships[label].isin(ADMIN_COLLECTIONS)]
    return memberships.drop_duplicates(["_Book Row", label])


def membership_values(data: pd.DataFrame, source_column: str, label: str) -> list[str]:
    """Return sorted distinct values from a comma-separated membership field."""
    values = split_memberships(data, source_column, label)[label].unique().tolist()
    return sorted(values, key=str.casefold)


def _selected_row_ids(
    data: pd.DataFrame, source_column: str, label: str, selected: Iterable[str]
) -> set[int]:
    selected_set = set(selected)
    if not selected_set:
        return set(data["_Book Row"])
    memberships = split_memberships(data, source_column, label)
    return set(memberships.loc[memberships[label].isin(selected_set), "_Book Row"])


def filter_books(
    data: pd.DataFrame,
    collections: Iterable[str] = (),
    dewey_wordings: Iterable[str] = (),
    authors: Iterable[str] = (),
    languages: Iterable[str] = (),
    year_range: tuple[int, int] | None = None,
    include_unknown_years: bool = True,
) -> pd.DataFrame:
    """Apply dashboard filters; multiple selections within a filter use OR logic."""
    mask = pd.Series(True, index=data.index)

    if collections:
        row_ids = _selected_row_ids(data, "Collections", "Collection", collections)
        mask &= data["_Book Row"].isin(row_ids)
    if dewey_wordings:
        mask &= data["Dewey Wording"].isin(dewey_wordings)
    if authors:
        mask &= data["Author"].isin(authors)
    if languages:
        row_ids = _selected_row_ids(data, "Languages", "Language", languages)
        mask &= data["_Book Row"].isin(row_ids)
    if year_range is not None:
        start, end = year_range
        in_range = data["Publication Year"].between(start, end)
        if include_unknown_years:
            in_range |= data["Publication Year"].isna()
        mask &= in_range

    return data.loc[mask].copy()


def collection_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Summarize overlapping collection memberships without double-counting books."""
    memberships = split_memberships(data, "Collections", "Collection")
    joined = memberships.merge(
        data[["_Book Row", "Author", "Page Count"]], on="_Book Row", how="left"
    )
    if joined.empty:
        return pd.DataFrame(columns=["Collection", "Books", "Authors", "Total Pages"])
    summary = (
        joined.groupby("Collection", as_index=False)
        .agg(
            Books=("_Book Row", "nunique"),
            Authors=("Author", "nunique"),
            **{"Total Pages": ("Page Count", "sum")},
        )
        .sort_values(["Books", "Collection"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return summary


def dewey_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Summarize books by their exact Dewey Wording value."""
    known = data.loc[data["Dewey Wording"].notna()]
    if known.empty:
        return pd.DataFrame(
            columns=["Dewey Wording", "Books", "Authors", "Total Pages"]
        )
    return (
        known.groupby("Dewey Wording", as_index=False)
        .agg(
            Books=("_Book Row", "nunique"),
            Authors=("Author", "nunique"),
            **{"Total Pages": ("Page Count", "sum")},
        )
        .sort_values(["Books", "Dewey Wording"], ascending=[False, True])
        .reset_index(drop=True)
    )


def year_counts(data: pd.DataFrame) -> pd.DataFrame:
    """Count books for each represented publication year."""
    years = data["Publication Year"].dropna().astype(int)
    return (
        years.value_counts()
        .sort_index()
        .rename_axis("Publication Year")
        .rename("Books")
        .reset_index()
    )


def decade_counts(data: pd.DataFrame) -> pd.DataFrame:
    """Count books by decade with explicit, readable labels."""
    years = data["Publication Year"].dropna().astype(int)
    starts = years.floordiv(10).mul(10)
    counts = starts.value_counts().sort_index()
    result = counts.rename_axis("Decade Start").rename("Books").reset_index()
    result["Decade"] = result["Decade Start"].map(
        lambda start: f"{start}–{start + 9}"
    )
    return result[["Decade Start", "Decade", "Books"]]
