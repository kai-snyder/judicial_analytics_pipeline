import plotly.express as px
import geopandas as gpd
import pandas as pd
from pathlib import Path
import matplotlib.colors as mcolors
from dashboard import data_access as da
from src.data.nos_map import NOS_MAP
import numpy as np

DISTRICTS_GJ = Path(__file__).parent / "shapefiles" / "district_courts" / "districts_simplified.geojson"
DISTRICTS    = gpd.read_file(DISTRICTS_GJ)[["NAME", "geometry"]].rename(columns={"NAME": "district"})

LKUP_CSV = Path(__file__).parent / "court_to_district.csv"
COURTS_LKUP = pd.read_csv(LKUP_CSV)

_GRAD = mcolors.LinearSegmentedColormap.from_list(
    "court_orange",
    ["#ffffff", "#ff8a25", "#7a1d00"],    # 0 %  50 %  100 %
)

# ── Nature-of-Suit → chapter lookup ────────────────────────────────
_CHAPTER: dict[int, str] = {

    # Contract (110-199)
    **{k: "Contract" for k in (
        110, 120, 130, 140, 150, 151, 152, 153,
        160, 190, 195, 196)},

    # Real Property (210-299)
    **{k: "Real Property" for k in (210, 220, 230, 240, 245, 290)},

    # Torts – Personal Injury (310-368, 375)
    **{k: "Torts · Pers Injury" for k in (
        310, 315, 320, 330, 340, 345,
        350, 355, 360, 362, 365, 367, 368, 375)},

    # Torts – Personal Property (370-385)
    **{k: "Torts · Pers Property" for k in (370, 371, 380, 385)},

    # Bankruptcy (422-423)
    **{k: "Bankruptcy" for k in (422, 423)},

    # Civil Rights (440-448)
    **{k: "Civil Rights" for k in (
        440, 441, 442, 443, 444, 445, 446, 448)},

    # Immigration (462-465)
    **{k: "Immigration" for k in (462, 463, 465)},

    # Prisoner / Habeas (510-560)
    **{k: "Prisoner / Habeas" for k in (
        510, 530, 535, 540, 550, 555, 560)},

    # Forfeiture / Penalty (610-690)
    **{k: "Forfeiture / Penalty" for k in (
        610, 620, 625, 630, 640, 650, 660, 690)},

    # Labor (710-799)
    **{k: "Labor" for k in (
        710, 720, 730, 740, 751, 790, 791)},

    # Intellectual Property & related (820-840)
    **{k: "Property Rights" for k in (820, 830, 840)},

    # Social Security (861-865)
    **{k: "Social Security" for k in (861, 862, 863, 864, 865)},

    # Federal Tax Suits (870-871)
    **{k: "Federal Tax" for k in (870, 871)},

    # Other Statutes / Misc. Federal Civil
    **{k: "Other Statutes" for k in (
        400, 410, 430, 450, 460, 470, 480, 490,
        810, 850, 875,
        890, 891, 892, 893, 894, 895, 896, 899, 900, 950)},
}

def bar_filings(
    df: pd.DataFrame,
    title: str = "",
    x_col: str = "bucket",
    y_col: str = "filings",
    height: int = 460,
) -> px.bar:
    """Vertical bar chart of filing volume."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        template="plotly_white",
        height=height,
    )
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="Filings",
        margin=dict(t=40, r=20, l=0, b=0),
    )
    fig.update_traces(
        marker_color="black"
    )
    return fig

def line_filings(df: pd.DataFrame, *,
                 x_col: str = "bucket",
                 y_col: str = "filings",
                 title: str = "Filings over time"):
    fig = px.line(df, x=x_col, y=y_col,
                  template="plotly_white", markers=True)
    fig.update_layout(title=title,
                      xaxis_title=x_col.capitalize(),
                      yaxis_title=y_col)
    fig.update_traces(
        line   = dict(color="black", width=4),
        marker = dict(color="black")          # dots the same colour
    )
    return fig

def line_filings_by_court(df: pd.DataFrame, *, period: str) -> px.line:
    """Multi-series line: one per district court."""
    if df.empty:
        return px.line(title="No data for selected courts")

    fig = px.line(
        df,
        x="bucket",
        y="filings",
        color="court_slug",
        markers=True,
        template="plotly_white",
        title=f"{period} Filings by District Courts",
        height=460,
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Filings",
        legend_title="Court",
        margin=dict(t=40, l=0, r=0, b=0),
    )
    return fig

def _single_hue(series: pd.Series) -> list[str]:
    """
    Map numeric series to the custom single-hue ramp.
    """
    norm = mcolors.Normalize(vmin=series.min(), vmax=series.max())
    return [mcolors.to_hex(_GRAD(norm(v))) for v in series]

def map_density(df_counts: pd.DataFrame):
    """
    df_counts columns: ['court_slug', 'filings']
    Produces a true district-court map coloured by filings.
    """
    # join counts → geometries
    gdf = (pd.merge(df_counts, COURTS_LKUP, on="court_slug")  # add 'district'
             .merge(DISTRICTS, on="district")                 # add geometry
             .fillna({"filings": 0}))
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")

    # colour ramp
    gdf["color"] = _single_hue(gdf["filings"])

    fig = px.choropleth_mapbox(
        gdf,
        geojson=gdf.__geo_interface__,
        locations=gdf.index,
        color=gdf["filings"],                        # numeric → legend
        color_continuous_scale=["#ffffff", "#ff8a25", "#7a1d00"],
        range_color=(gdf["filings"].min(), gdf["filings"].max()),
        hover_name="court_slug",
        hover_data={"filings": True},
        mapbox_style="carto-positron",
        zoom=2.7, center={"lat": 39.8, "lon": -98.6},
        opacity=0.83
    )

    # tidy the tooltip
    fig.update_traces(
        # bring two columns into the tooltip
        customdata=gdf[["district", "filings"]].values,
        # format it and suppress the default “index” field
        hovertemplate="<b>%{customdata[0]}</b><br>Filings: %{customdata[1]:,}<extra></extra>"
    )

    # thin black outlines so small districts pop
    fig.update_traces(marker_line_width=0.4, marker_line_color="black")

    # nicer colour-bar title
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        title="Cumulative Filings by District Court",
        coloraxis_colorbar=dict(title="Filings")
    )
    return fig

def _add_chapter_cols(df: pd.DataFrame) -> pd.DataFrame:
    # assumes df["nos"] looks like "365 Personal injury – Product liability"
    chapter_code    = df["nos"].str.extract(r"^(\d{2})")[0]
    chapter_title   = chapter_code + "x " + df["nos"].str.split(" ").str[1]
    return df.assign(chapter_code=chapter_code,
                     chapter_title=chapter_title)

def treemap_nos(
    *,
    count_min: int = 50,
    courts: list[str] | None = None,
    codes:  list[int] | None = None,
) -> px.treemap:
    # ── fetch + basic cleaning ──────────────────────────────────────────
    raw = (
        da.nature_of_suit(courts=courts)         # scoped to courts
          .rename(columns={"nos": "nos_raw"})
    )

    # pull leading 3‑digit code (keep float → drop NaNs)
    if pd.api.types.is_numeric_dtype(raw["nos_raw"]):
        raw["nos"] = raw["nos_raw"].astype(int)
    else:
        raw["nos"] = (
            raw["nos_raw"]
                .str.extract(r"^(\d{3})", expand=False)
                .astype("float")
        )
        raw = raw.dropna(subset=["nos"]).copy()
        raw["nos"] = raw["nos"].astype(int)

    # ── apply NOS code filter, if any ───────────────────────────────────
    if codes:                                  # (None or [] ⇒ no filter)
        raw = raw[raw["nos"].isin(codes)].copy()
    if raw.empty:
        return px.treemap(title="No data for selected NOS")

    raw["nos_raw"] = raw["nos_raw"].astype("string")
    raw["chapter"] = raw["nos"].map(_CHAPTER)
    raw = raw.dropna(subset=["chapter"])

    # ── map the official NOS title ──────────────────────────────────────
    raw["short"] = (
        raw["nos"]
            .map(NOS_MAP)
            .fillna(
                raw["nos_raw"]
                    .str.replace(r"^\d{3}\s*[-·]?\s*", "", regex=True)
                    .str.replace(r"\s*[-–]\s*",      " ", regex=True)
                    .str.strip()
                    .str.title()
            )
    )

    # ── aggregate once per (chapter, nos) ──────────────────────────────
    df = (
        raw.groupby(["chapter", "nos"], as_index=False)
           .agg(cnt=("cnt", "sum"), short=("short", "first"))
    )
    total = df["cnt"].sum()
    cutoff = max(1, total * 0.0001)        # never drop the only case in tiny sets
    df = df[df["cnt"] >= cutoff]
    df["child_lb"] = df["nos"].astype(str) + " · " + df["short"]

    # ── build the treemap ───────────────────────────────────────────────
    fig = px.treemap(
        df,
        path=["chapter", "child_lb"],
        values="cnt",
        color="cnt",
        color_continuous_scale=px.colors.sequential.Oranges,
        template="plotly_white", 
        title="Cumulative Filings by NOS Code"
    ).update_coloraxes(
        cmin=0, cmax=df["cnt"].max(), colorbar_title="Filings"
    )

    # ── polish ─────────────────────────────────────────────────────────
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>"
                      "Parent: %{parent}<br>"
                      "Cases: %{value:,}"
                      "<extra></extra>",
        tiling=dict(pad=2),
        marker_line_width=0,
        selector=dict(type="treemap"),
        root_color="rgba(0,0,0,0)"
    )
    fig.update_layout(
        margin=dict(t=40, l=0, r=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=460
    )
    return fig

def line_nos(
    df: pd.DataFrame,
    *,
    period: str = "Daily",        # ← pass “Daily / Weekly / Monthly / Yearly”
    title: str | None = None,     # ← optional manual override
) -> px.line:
    """Multi‑series line chart for NOS filings."""
    if df.empty:
        return px.line(title="No data for selected NOS")

    # auto‑generate a heading unless the caller supplies one
    if title is None:
        title = f"{period} Filings by NOS Codes"

    fig = px.line(
        df,
        x="bucket",
        y="filings",
        color="nos",
        markers=True,
        template="plotly_white",
        height=460,
        title=title,
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Filings",
        legend_title="NOS",
        showlegend=not df.empty,
        margin=dict(t=40, l=0, r=0, b=0),
    )
    return fig

def violin_days_to_close(
    df: pd.DataFrame,
    *,
    group_label: str = "Group",
    height: int = 380,
    sort_by: str = "median",
    ascending: bool = False,
) -> px.violin:
    if df.empty:
        return px.violin(title="No closed cases in current filter")

    df["group"] = df["group"].astype("string")
    df, order = _order_by_stat(df, stat=sort_by, ascending=ascending)

    fig = px.violin(
        df,
        x="group",
        y="days_to_close",
        points=False,
        box=True,
        template="plotly_white",
        height=height,
        labels={"group": group_label, "days_to_close": "Days to Close"},
        title=f"Distribution of Days to Close by {group_label}",
        category_orders={"group": order},
    )
    fig.update_traces(meanline_visible=True)
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
    return fig

def _order_by_stat(df: pd.DataFrame,
                   stat: str = "median",
                   ascending: bool = False) -> tuple[pd.DataFrame, list[str]]:
    stats = {
        "mean"  : df.groupby("group")["days_to_close"].mean(),
        "median": df.groupby("group")["days_to_close"].median(),
        "q1"    : df.groupby("group")["days_to_close"].quantile(0.25),
        "q3"    : df.groupby("group")["days_to_close"].quantile(0.75),
        "min"   : df.groupby("group")["days_to_close"].min(),
        "max"   : df.groupby("group")["days_to_close"].max(),
    }
    order = (
        stats[stat]
        .sort_values(ascending=ascending)
        .index.astype(str)
        .tolist()
    )
    df["group"] = pd.Categorical(df["group"].astype(str),
                                 categories=order,
                                 ordered=True)
    return df, order
