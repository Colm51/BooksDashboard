"""Streamlit dashboard for a personal book library."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from book_data import (
    author_summary,
    collection_summary,
    decade_counts,
    dewey_summary,
    filter_books,
    load_book_data,
    membership_values,
    split_memberships,
    year_counts,
)


WORKBOOK_PATH = Path(__file__).parent / "Books_Sept2.xlsx"
ACCENT = "#8B5E4B"
NEUTRAL = "#D9D1CB"
TOP_CATEGORIES = 15

st.set_page_config(page_title="My Book Library", page_icon="▤", layout="wide")
st.markdown(
    """
    <style>
        .block-container {max-width: 1240px; padding-top: 2.6rem; padding-bottom: 4rem;}
        h1, h2, h3 {letter-spacing: -0.025em;}
        h2 {margin-top: 2.8rem;}
        [data-testid="stMetric"] {padding: 0.25rem 0;}
        [data-testid="stMetricValue"] {font-size: clamp(1.55rem, 3vw, 2.25rem);}
        .quiet {color: color-mix(in srgb, currentColor 65%, transparent); max-width: 800px;}
        .section-rule {border-top: 1px solid rgba(128,128,128,.22); margin: 2.4rem 0 0;}
        @media (max-width: 700px) {.block-container {padding: 1.4rem 1rem 3rem;}}

        /* Short landscape phones need their own treatment: their width can exceed
           the ordinary phone breakpoint even though vertical space is scarce. */
        @media (orientation: landscape) and (max-height: 500px) {
            header[data-testid="stHeader"],
            header[data-testid="stHeader"] > div[data-testid="stToolbar"] {
                display: none !important;
            }
            section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
                padding-top: 0 !important;
            }
            .block-container {
                max-width: 100%;
                padding-right: 1rem;
                padding-bottom: 1.4rem;
                padding-left: 1rem;
            }
            h1 {
                font-size: 1.65rem;
                margin: 0 0 0.15rem;
            }
            h2 {
                font-size: 1.3rem;
                margin: 0.45rem 0 0.15rem;
            }
            h3 {
                font-size: 1.1rem;
                margin-block: 0.35rem 0.1rem;
            }
            p {margin-block: 0.2rem;}
            .quiet {line-height: 1.25; margin-block: 0.1rem 0.25rem;}
            .section-rule {margin: 0.75rem 0 0;}
            [data-testid="stVerticalBlock"] {gap: 0.45rem;}
            [data-testid="stMetric"] {padding: 0;}
            [data-testid="stMetricValue"] {
                font-size: 1.45rem;
                line-height: 1.1;
            }
            [data-testid="stMetricLabel"] {line-height: 1.1;}
            [data-testid="stCaptionContainer"] p {line-height: 1.2;}
            [data-testid="stPlotlyChart"] {
                height: clamp(220px, 58vh, 280px) !important;
                margin-block: -0.15rem;
            }

            /* Touch gestures still work; hide the hover-oriented toolbar only in
               this constrained viewport. Desktop and portrait controls remain. */
            [data-testid="stPlotlyChart"] .modebar-container,
            [data-testid="stPlotlyChart"] .modebar {
                display: none !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_data(path: Path) -> pd.DataFrame:
    return load_book_data(path)


def section_intro(title: str, text: str | None = None) -> None:
    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.header(title)
    if text:
        st.markdown(f'<p class="quiet">{text}</p>', unsafe_allow_html=True)


def horizontal_bar(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str = ACCENT,
    custom_data: list[str] | None = None,
    hovertemplate: str | None = None,
    height: int | None = None,
):
    figure = px.bar(
        data,
        x=x,
        y=y,
        orientation="h",
        title=title,
        color_discrete_sequence=[color],
        custom_data=custom_data,
    )
    figure.update_traces(marker_line_width=0, hovertemplate=hovertemplate)
    figure.update_layout(
        height=height or max(360, 34 * len(data)),
        showlegend=False,
        margin=dict(l=10, r=10, t=65, b=10),
        title_x=0,
    )
    figure.update_xaxes(fixedrange=False)
    figure.update_yaxes(title=None)
    return figure


def short_label(value: str, length: int = 68) -> str:
    return value if len(value) <= length else value[: length - 1].rstrip() + "…"


try:
    books = get_data(WORKBOOK_PATH)
except (FileNotFoundError, ValueError, ImportError) as error:
    st.error(f"The books workbook could not be loaded: {error}")
    st.stop()

st.title("My Book Collection")
st.markdown(
    '<p class="quiet">The subjects, languages, and publication dates of books in my personal library.</p>',
    unsafe_allow_html=True,
)

all_years = books["Publication Year"].dropna().astype(int)
year_limits = (int(all_years.min()), int(all_years.max())) if not all_years.empty else None

with st.expander("Filters", expanded=True):
    filter_columns = st.columns(3)
    selected_collections = filter_columns[0].multiselect(
        "Collection",
        membership_values(books, "Collections", "Collection"),
        placeholder="All collections",
    )
    selected_dewey = filter_columns[1].multiselect(
        "Dewey Wording",
        sorted(books["Dewey Wording"].dropna().unique(), key=str.casefold),
        placeholder="All Dewey subjects",
    )
    selected_authors = filter_columns[2].multiselect(
        "Author",
        sorted(books["Author"].dropna().unique(), key=str.casefold),
        placeholder="All authors",
    )

    lower_columns = st.columns([1, 1, 1])
    selected_languages = lower_columns[0].multiselect(
        "Language",
        membership_values(books, "Languages", "Language"),
        placeholder="All languages",
    )
    if year_limits:
        selected_years = lower_columns[1].slider(
            "Publication year",
            min_value=year_limits[0],
            max_value=year_limits[1],
            value=year_limits,
        )
        include_unknown = lower_columns[2].checkbox(
            "Include unknown publication years", value=True
        )
    else:
        selected_years = None
        include_unknown = True

filtered = filter_books(
    books,
    collections=selected_collections,
    dewey_wordings=selected_dewey,
    authors=selected_authors,
    languages=selected_languages,
    year_range=selected_years,
    include_unknown_years=include_unknown,
)

if filtered.empty:
    st.warning("No books match the current filters. Adjust a selection to continue.")
    st.stop()

total_pages = int(filtered["Page Count"].sum())
median_pages = filtered["Page Count"].median()
collection_count = len(split_memberships(filtered, "Collections", "Collection")["Collection"].unique())
language_count = len(split_memberships(filtered, "Languages", "Language")["Language"].unique())

headline_columns = st.columns(4)
headline_values = [
    ("Books", len(filtered)),
    ("Authors", filtered["Author"].nunique(dropna=True)),
    ("Total pages", total_pages),
    ("Median pages", median_pages),
]
for column, (label, value) in zip(headline_columns, headline_values):
    column.metric(label, "—" if pd.isna(value) else f"{value:,.0f}")

detail_columns = st.columns([1, 1, 1, 1])
detail_columns[0].metric("Collections", collection_count)
detail_columns[1].metric(
    "Dewey subjects", filtered["Dewey Wording"].nunique(dropna=True)
)
detail_columns[2].metric("Languages", language_count)
detail_columns[3].metric("Books with a known year", f"{filtered['Publication Year'].notna().sum():,}")

missing_years = int(filtered["Publication Year"].isna().sum())
missing_pages = int(filtered["Page Count"].isna().sum())
st.caption(
    f"Showing {len(filtered):,} of {len(books):,} books · "
    f"{missing_years:,} without a usable year · {missing_pages:,} without a plain numeric page count"
)

section_intro(
    "Publication Years",
    "This may not represent the initial date of release! For example for Greek texts. Missing or invalid dates are excluded.",
)
year_data = year_counts(filtered)
decade_data = decade_counts(filtered)
if year_data.empty:
    st.info("No usable publication years are available for the current selection.")
else:
    year_plot = year_data.copy()
    year_plot["Year Label"] = year_plot["Publication Year"].astype(str)
    year_figure = px.bar(
        year_plot,
        x="Year Label",
        y="Books",
        title="Books by publication year",
        color_discrete_sequence=[ACCENT],
    )
    year_figure.update_traces(
        marker_line_width=0,
        customdata=year_plot[["Publication Year"]],
        hovertemplate="Year %{customdata[0]}<br>%{y:,.0f} books<extra></extra>",
    )
    year_figure.update_layout(
        height=440,
        bargap=0.08,
        showlegend=False,
        margin=dict(l=10, r=10, t=65, b=10),
        title_x=0,
    )
    year_figure.update_xaxes(title="Publication Year", nticks=18, fixedrange=False)
    st.plotly_chart(year_figure, width="stretch", config={"displaylogo": False})

    decade_figure = px.bar(
        decade_data,
        x="Decade",
        y="Books",
        title="Books by decade",
        color_discrete_sequence=[NEUTRAL],
    )
    decade_figure.update_traces(
        marker_color=NEUTRAL,
        marker_line_width=0,
        hovertemplate="%{x}<br>%{y:,.0f} books<extra></extra>",
    )
    decade_figure.update_layout(
        height=390,
        bargap=0.12,
        showlegend=False,
        margin=dict(l=10, r=10, t=65, b=10),
        title_x=0,
    )
    decade_figure.update_xaxes(title=None, tickangle=-35, fixedrange=False)
    st.plotly_chart(decade_figure, width="stretch", config={"displaylogo": False})

section_intro(
    "Collections",
    "Collections can overlap. Each book counts once within a collection, while the headline book total always counts each selected row once.",
)
collection_stats = collection_summary(filtered)
if collection_stats.empty:
    st.info("No Collection values are available for the current selection.")
else:
    collection_chart = collection_stats.loc[
        collection_stats["Collection"].ne("Your library")
    ].head(TOP_CATEGORIES)
    if collection_chart.empty:
        collection_chart = collection_stats.head(TOP_CATEGORIES)
    else:
        st.markdown(
            '<p class="quiet">I have not assigned most books to a collection.</p>',
            unsafe_allow_html=True,
        )
    collection_chart = collection_chart.sort_values("Books", ascending=True)
    st.plotly_chart(
        horizontal_bar(
            collection_chart,
            x="Books",
            y="Collection",
            title="Collection sizes",
            hovertemplate="%{y}<br>%{x:,.0f} books<extra></extra>",
        ),
        width="stretch",
        config={"displaylogo": False},
    )
    st.subheader("Collection Summary")
    st.dataframe(
        collection_stats,
        hide_index=True,
        width="stretch",
        column_config={
            "Books": st.column_config.NumberColumn(format="%,d"),
            "Authors": st.column_config.NumberColumn(format="%,d"),
            "Total Pages": st.column_config.NumberColumn(format="%,d"),
        },
    )

section_intro(
    "Authors",
    "The authors with the most books in the current selection. Missing or blank author values are excluded.",
)
author_stats = author_summary(filtered)
if author_stats.empty:
    st.info("No Author values are available for the current selection.")
else:
    top_authors = author_stats.head(20).copy()
    author_chart = top_authors.sort_values(
        ["Books", "Author"], ascending=[True, False]
    )
    author_figure = horizontal_bar(
        author_chart,
        x="Books",
        y="Author",
        title="Top 20 authors by number of books",
        hovertemplate="%{y}<br>%{x:,.0f} books<extra></extra>",
        height=max(440, 31 * len(author_chart)),
    )
    author_figure.update_xaxes(title="Number of books")
    st.plotly_chart(
        author_figure,
        width="stretch",
        config={"displaylogo": False},
    )
    st.dataframe(
        top_authors[["Author", "Books"]],
        hide_index=True,
        width="stretch",
        height=300,
        column_config={
            "Author": st.column_config.TextColumn(width="large"),
            "Books": st.column_config.NumberColumn(format="%,d"),
        },
    )

section_intro(
    "Dewey Subjects",
    f"The chart shows the {TOP_CATEGORIES} largest exact Dewey Wording groups. The table retains every represented group; raw Dewey Decimal values remain in the detailed book table.",
)
dewey_stats = dewey_summary(filtered)
if dewey_stats.empty:
    st.info("No Dewey Wording values are available for the current selection.")
else:
    dewey_chart = dewey_stats.head(TOP_CATEGORIES).copy()
    dewey_chart["Subject"] = dewey_chart["Dewey Wording"].map(short_label)
    dewey_chart = dewey_chart.sort_values("Books", ascending=True)
    st.plotly_chart(
        horizontal_bar(
            dewey_chart,
            x="Books",
            y="Subject",
            title="Largest Dewey subject groups",
            custom_data=["Dewey Wording"],
            hovertemplate="%{customdata[0]}<br>%{x:,.0f} books<extra></extra>",
            height=max(440, 36 * len(dewey_chart)),
        ),
        width="stretch",
        config={"displaylogo": False},
    )
    st.subheader("Dewey Summary")
    st.dataframe(
        dewey_stats,
        hide_index=True,
        width="stretch",
        height=430,
        column_config={
            "Books": st.column_config.NumberColumn(format="%,d"),
            "Authors": st.column_config.NumberColumn(format="%,d"),
            "Total Pages": st.column_config.NumberColumn(format="%,d"),
        },
    )

section_intro(
    "Languages",
    "Language fields are kept compact because English accounts for most of the collection. Multi-language books count once in each listed language. Original language would be another interesting field",
)
language_columns = st.columns(2)
language_specs = [
    ("Languages", "Language", "Books by language", ACCENT),
    ("Original Languages", "Original Language", "Books by original language", NEUTRAL),
]
for column, (source, label, title, color) in zip(language_columns, language_specs):
    language_data = split_memberships(filtered, source, label)
    counts = (
        language_data[label]
        .value_counts()
        .rename_axis(label)
        .rename("Books")
        .reset_index()
        .head(12)
        .sort_values("Books", ascending=True)
    )
    if counts.empty:
        column.info(f"No {label.lower()} values are available.")
    else:
        column.plotly_chart(
            horizontal_bar(
                counts,
                x="Books",
                y=label,
                title=title,
                color=color,
                hovertemplate="%{y}<br>%{x:,.0f} books<extra></extra>",
                height=max(360, 31 * len(counts)),
            ),
            width="stretch",
            config={"displaylogo": False},
        )

section_intro(
    "Books",
    "The detailed source values for the current selection. Use a column header to sort the table.",
)
detail_table = (
    filtered[
        [
            "Title",
            "Author",
            "Date",
            "Publication Year",
            "Page Count",
            "Collections",
            "Languages",
            "Original Languages",
            "Dewey Decimal",
            "Dewey Wording",
        ]
    ]
    .sort_values(["Title", "Author"], na_position="last")
    .reset_index(drop=True)
)
st.dataframe(
    detail_table,
    hide_index=True,
    width="stretch",
    height=560,
    column_config={
        "Title": st.column_config.TextColumn(width="large"),
        "Author": st.column_config.TextColumn(width="medium"),
        "Date": st.column_config.NumberColumn("Source Date", format="%d"),
        "Publication Year": st.column_config.NumberColumn(format="%d"),
        "Page Count": st.column_config.NumberColumn(format="%,d"),
        "Collections": st.column_config.TextColumn(width="medium"),
        "Dewey Wording": st.column_config.TextColumn(width="large"),
    },
)

st.caption(
    "Source: Books_Sept2.xlsx · Collection membership is manually curated and may overlap · The workbook is read-only"
)
