import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import text
from dashboard import data_access as da
from dashboard import charts as ch
from dashboard.data_access import days_to_close_df

st.set_page_config(page_title="Case Landscape Dashboard",
                   layout="wide",
                   page_icon="⚖️",
                   initial_sidebar_state="expanded")

# ── Sidebar filters ───────────────────────────────────
min_dt = pd.to_datetime(
    pd.read_sql("SELECT MIN(filing_date) FROM cases", da.ENG).iat[0, 0]
).date()
max_dt = pd.to_datetime(
    pd.read_sql("SELECT MAX(filing_date) FROM cases", da.ENG).iat[0, 0]
).date()

start_dt, end_dt = st.sidebar.date_input(
    "Date Range",
    value=(min_dt, max_dt),
    min_value=min_dt,
    max_value=max_dt,
)

courts_all = sorted(
    pd.read_sql("SELECT DISTINCT court_slug FROM cases ORDER BY 1", da.ENG)
      .court_slug.tolist()
)
court_options = ["All", "Top 5 (by count)"] + courts_all

court_raw = st.sidebar.multiselect("District Court", court_options, default=[])

if not court_raw or "All" in court_raw:
    courts_sel = None        # include every court
    top5_flag  = False
elif "Top 5 (by count)" in court_raw:
    courts_sel = None        # derive busiest 5 in the query
    top5_flag  = True
else:
    courts_sel = court_raw   # explicit list
    top5_flag  = False

nos_df = da.nature_of_suit(courts_sel, start_dt, end_dt)  # ← was global
top5   = nos_df.nlargest(5, "cnt")["nos"].astype(int).tolist()

all_nos = sorted(nos_df["nos"].astype(int).tolist())
options = ["All", "Top 5 (by count)"] + [str(n) for n in all_nos]

nos_raw = st.sidebar.multiselect("NOS Codes", options, default=[])

if "All" in nos_raw:
    nos_codes      = []          # no NOS filter
    show_nos_chart = False
elif "Top 5 (by count)" in nos_raw:
    nos_codes      = top5        # ← now tailored to selected courts
    show_nos_chart = True
else:
    nos_codes      = [int(x) for x in nos_raw]
    show_nos_chart = bool(nos_codes)

agg = st.sidebar.selectbox("Time Bucket",
                           ["Daily", "Weekly", "Monthly", "Yearly"], index=0)

group_option = st.sidebar.radio(
    "Violin Group",
    ["District Courts", "NOS Codes"],
    index=0,
    help="Show latency distribution by court or by NOS code"
)

group_flag = "court" if group_option == "District Courts" else "nos"

sort_options = {
    "Mean":   "mean",
    "Median": "median",
    "Q1":     "q1",
    "Q3":     "q3",
    "Min":    "min",
    "Max":    "max",
}
sort_choice = st.sidebar.selectbox("Violin Sorting Metric", list(sort_options.keys()), index=0)
sort_stat = sort_options[sort_choice]
sort_dir  = st.sidebar.selectbox(
    "Violin Sorting Direction",
    ["Descending", "Ascending"],
    index=0
)
asc_flag = (sort_dir == "Ascending")

# ── KPI row ──────────────────────────────────────────────────────────
# 1. build param dict & WHERE pieces
kpi_params = {"start": start_dt, "end": end_dt}
extra_clauses = []

if courts_sel:                                   # list[str]
    kpi_params["courts"] = courts_sel
    extra_clauses.append("AND court_slug = ANY(:courts)")

if nos_codes:                                    # list[int]
    kpi_params["codes"] = nos_codes
    extra_clauses.append("AND nature_of_suit_numeric = ANY(:codes)")

kpi_extra = "\n           ".join(extra_clauses)   # joined into one string

# 2. queries that share the same params / extra WHERE
total_cases = pd.read_sql(
    text(f"""
        SELECT COUNT(*) AS n
          FROM cases
         WHERE filing_date BETWEEN :start AND :end
           {kpi_extra}
    """),
    da.ENG, params=kpi_params,
).iat[0, 0]

closed = pd.read_sql(
    text(f"""
        SELECT COUNT(*) AS n
          FROM cases
         WHERE closing_date IS NOT NULL
           AND filing_date BETWEEN :start AND :end
           {kpi_extra}
    """),
    da.ENG, params=kpi_params,
).iat[0, 0]

avg_time = pd.read_sql(
    text(f"""
        SELECT AVG(ABS(closing_date - filing_date)) AS days
          FROM cases
         WHERE closing_date IS NOT NULL
           AND filing_date BETWEEN :start AND :end
           {kpi_extra}
    """),
    da.ENG, params=kpi_params,
).iat[0, 0]

open_rate = 1 - closed / total_cases if total_cases else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Dockets",       f"{total_cases:,}")
c2.metric("Closed",              f"{closed:,}")
c3.metric("Open Rate",           f"{open_rate:.1%}")
c4.metric("Avg Days to Close",   f"{avg_time:.0f}")

st.markdown("---")

# ── Layout: three rows ──────────────────────────────────
row1 = st.columns((2,2))
row2 = st.columns((2,2))
row3 = st.columns(1)

# 1-A Geography map
if top5_flag:
    # derive the busiest 5 courts for the current date & NOS slice
    map_courts = da.top_courts_by_filings(start_dt, end_dt, nos_codes, limit=5)
else:
    map_courts = courts_sel
df_geo  = da.geography_counts(start_dt, end_dt, map_courts, nos_codes)
row1[0].plotly_chart(ch.map_density(df_geo), use_container_width=True)

# 1-B Filing volume line
if courts_sel is None and not top5_flag:
    # ― Case: "All" courts → composite line
    df_line = da.filings_agg(
        period=agg,
        courts=None,          # include every court
        start=start_dt,
        end=end_dt,
        codes=nos_codes
    )
    fig_line = ch.line_filings(          # single-series helper
        df_line,
        title=f"{agg} Filings by District Courts",
        x_col="bucket"
    )
else:
    # ― Case: explicit courts or "Top 5" → one line per court
    df_line = da.filings_by_court(
        period=agg,
        courts=courts_sel,
        start=start_dt,
        end=end_dt,
        top_n=5 if top5_flag else None,
        codes=nos_codes
    )
    fig_line = ch.line_filings_by_court(df_line, period=agg)

row1[1].plotly_chart(fig_line, use_container_width=True)

# 2-A Nature of Suit treemap
if top5_flag:
    treemap_courts = da.top_courts_by_filings(
        start_dt, end_dt, nos_codes, limit=5
    )
else:
    treemap_courts = courts_sel   # None or explicit list
row2[0].plotly_chart(
    ch.treemap_nos(
        count_min=100,
        courts=treemap_courts,
        codes=nos_codes
    ),
    use_container_width=True
)

# 2-B Nature of Suit line chart
show_nos_chart = True          # default

if "All" in nos_raw:
    nos_codes = []             # empty => chart suppressed
    show_nos_chart = False
elif "Top 5 (by count)" in nos_raw:
    nos_codes = top5
else:
    nos_codes = [int(x) for x in nos_raw]

if show_nos_chart and nos_codes:
    df_nos_freq = da.filings_by_nos(
        nos_codes=nos_codes,
        period=agg,
        courts=courts_sel,
        start=start_dt,
        end=end_dt,
    )
    fig_nos_line = ch.line_nos(
        df_nos_freq, 
        period=agg
    )
else:
    fig_nos_line = None

if fig_nos_line is not None:
    row2[1].plotly_chart(fig_nos_line, use_container_width=True)
else:
    row2[1].info("Select one or more NOS codes\nfrom the sidebar to see trends.")

# 3-A Days-to-Close violin plot
df_latency = days_to_close_df(
    group_by=group_flag,
    courts=courts_sel if not top5_flag else da.top_courts_by_filings(
        start_dt, end_dt, nos_codes, limit=5),
    codes=nos_codes,
    start=start_dt,
    end=end_dt,
)

if df_latency["group"].nunique() <= 20 and not df_latency.empty:
    row3[0].plotly_chart(
        ch.violin_days_to_close(
            df_latency,
            group_label=("District Court(s)" if group_flag == "court" else "NOS Code(s)"),
            sort_by=sort_stat,
            ascending=asc_flag,
        ),
        use_container_width=True
    )
else:
    row3[0].info("Too many groups selected; refine filters to ≤ 20 to view the violin plot.")

# ── Completeness disclaimer ───────────────────────────────────────────
nos_gap = pd.read_sql(
    text(f"""
        SELECT
            COUNT(*) FILTER (WHERE nature_of_suit_numeric IS NULL) AS missing,
            COUNT(*)                                            AS total
          FROM cases
         WHERE filing_date BETWEEN :start AND :end
           {kpi_extra}                -- re-use the same court / NOS filters
    """),
    da.ENG,
    params=kpi_params,
).iloc[0]

missing_nos = int(nos_gap.missing)
total_slice = int(nos_gap.total)

st.caption(
    f"ℹ️ **Data Completeness:** Of the **{total_slice:,}** dockets in the "
    f"current filters, **{missing_nos:,}** "
    f"({missing_nos/total_slice:.1%}) have no Nature of Suit (NOS) code."
)
