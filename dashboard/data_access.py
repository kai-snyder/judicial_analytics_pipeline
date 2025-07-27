"""
Lightweight wrappers that return tidy DataFrames for the dashboard.
Feel free to add caching decorators (e.g. @st.cache_data) later.
"""
from datetime import date
import pandas as pd
from typing import List
from sqlalchemy import text
from src.utils.db import get_engine

ENG = get_engine()

def filings_agg(
    period: str = "Daily",
    courts: list[str] | None = None,
    start: date | None = None,
    end:   date | None = None,
    codes: list[int] | None = None,
) -> pd.DataFrame:
    """
    Aggregate filings per time bucket. Optional filters:
    - courts : list of court slugs
    - codes  : list of NOS codes
    """
    gran = {"Daily": "day", "Weekly": "week",
            "Monthly": "month", "Yearly": "year"}.get(period, "day")

    q = f"""
        SELECT date_trunc('{gran}', filing_date)::date AS bucket,
               COUNT(*)                                 AS filings
          FROM cases
         WHERE filing_date IS NOT NULL
           {'AND court_slug = ANY(:courts)'           if courts else ''}
           {'AND nature_of_suit_numeric = ANY(:codes)' if codes  else ''}
           {'AND filing_date >= :start'               if start  else ''}
           {'AND filing_date <= :end'                 if end    else ''}
      GROUP BY 1
      ORDER BY 1;
    """
    params = {k: v for k, v in
              dict(courts=courts, codes=codes, start=start, end=end).items()
              if v}
    return pd.read_sql(text(q), ENG, params=params)

def nature_of_suit(courts: list[str] | None = None, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    sql = f"""
        SELECT nature_of_suit_numeric::int AS nos,
               COUNT(*)                    AS cnt
          FROM cases
         WHERE nature_of_suit_numeric IS NOT NULL
           { 'AND court_slug = ANY(:courts)' if courts else '' }
           { 'AND filing_date >= :start' if start else '' }
           { 'AND filing_date <= :end'   if end   else '' }
      GROUP BY nos
    """
    params = {k: v for k, v in dict(courts=courts, start=start, end=end).items() if v}
    return pd.read_sql(text(sql), ENG, params=params)

def geography_counts(
    start:  date | None = None,
    end:    date | None = None,
    courts: List[str] | None = None,
    codes:  List[int] | None = None,
    top_n:  int | None  = None,
) -> pd.DataFrame:
    q = """
        SELECT court_slug,
               COUNT(*) AS filings
          FROM cases
         WHERE filing_date IS NOT NULL
           {start_clause}
           {end_clause}
           {court_clause}
           {code_clause}
      GROUP BY court_slug;
    """.format(
        start_clause = "AND filing_date >= :start"                 if start  else "",
        end_clause   = "AND filing_date <= :end"                   if end    else "",
        court_clause = "AND court_slug = ANY(:courts)"             if courts else "",
        code_clause  = "AND nature_of_suit_numeric = ANY(:codes)"  if codes  else "",
    )

    params = {k: v for k, v in
              dict(start=start, end=end, courts=courts, codes=codes).items()
              if v is not None}

    return pd.read_sql(text(q), ENG, params=params)

def filings_by_nos(
    nos_codes: list[int],
    period: str = "Monthly",
    courts:  list[str]  | None = None,
    start:  date | None = None,
    end:    date | None = None,
) -> pd.DataFrame:
    assert nos_codes, "nos_codes cannot be empty"
    units = {"Daily": ("day",   "1 day"),
             "Weekly": ("week",  "1 week"),
             "Monthly": ("month", "1 month"),
             "Yearly": ("year",  "1 year")}
    gran, step = units[period]
    sql = f"""
    WITH bounds AS (
        SELECT
            date_trunc('{gran}', MIN(filing_date)) AS min_bucket,
            date_trunc('{gran}', MAX(filing_date)) AS max_bucket
        FROM cases
         WHERE filing_date IS NOT NULL
           {'' if not start else 'AND filing_date >= :start'}
           {'' if not end   else 'AND filing_date <= :end'}
    ),
    buckets AS (
        SELECT generate_series(min_bucket, max_bucket, '{step}')::date AS bucket
        FROM   bounds
    ),
    base AS (
        SELECT date_trunc('{gran}', c.filing_date)::date AS bucket,
               c.nature_of_suit_numeric::int        AS nos,
               COUNT(*)                             AS filings
          FROM cases c
         WHERE c.filing_date IS NOT NULL
           AND c.nature_of_suit_numeric::int = ANY(:codes)
           {'' if not courts else 'AND c.court_slug = ANY(:courts)'}
           {'' if not start else 'AND c.filing_date >= :start'}
           {'' if not end   else 'AND c.filing_date <= :end'}
      GROUP BY bucket, nos
    )
    SELECT b.bucket,
           n.nos,
           COALESCE(a.filings, 0) AS filings
      FROM buckets b
     CROSS JOIN UNNEST(:codes) AS n(nos)
      LEFT JOIN base a
        ON b.bucket = a.bucket
       AND n.nos   = a.nos
     ORDER BY b.bucket, n.nos;
    """

    params = {k: v for k, v in
              dict(codes=nos_codes, courts=courts, start=start, end=end).items()
              if v is not None}

    return pd.read_sql(text(sql), ENG, params=params)

def filings_by_court(
    period: str,
    courts: list[str] | None,
    start: date,
    end: date,
    top_n: int | None = None,
    codes: list[int] | None = None,      # NOS filter
) -> pd.DataFrame:
    """
    Return a dataframe with every (time-bucket × selected court) combination.
    Missing combinations are filled with zero filings so the line chart drops
    to the x-axis rather than disappearing.
    """
    # ── granularity helpers ────────────────────────────────────────────
    units = {
        "Daily":   ("day",   "1 day"),
        "Weekly":  ("week",  "1 week"),
        "Monthly": ("month", "1 month"),
        "Yearly":  ("year",  "1 year"),
    }
    gran, step = units[period]

    # ── pick the set of courts to include ──────────────────────────────
    eng   = ENG
    params = {"start": start, "end": end}

    if courts:                                    # explicit list from UI
        court_list = courts
    elif top_n:                                   # derive busiest N courts
        sql_top = f"""
            SELECT court_slug
              FROM cases
             WHERE filing_date BETWEEN :start AND :end
               {'AND nature_of_suit_numeric = ANY(:codes)' if codes else ''}
          GROUP BY court_slug
          ORDER BY COUNT(*) DESC
             LIMIT {top_n};
        """
        if codes:
            params["codes"] = codes
        court_list = pd.read_sql(text(sql_top), eng, params=params)["court_slug"].tolist()
    else:                                         # fall-back: whatever appears in the data
        sql_all = """
            SELECT DISTINCT court_slug
              FROM cases
             WHERE filing_date BETWEEN :start AND :end;
        """
        court_list = pd.read_sql(text(sql_all), eng, params=params)["court_slug"].tolist()

    if not court_list:
        return pd.DataFrame(columns=["bucket", "court_slug", "filings"])

    params["courts"]     = court_list
    if codes:
        params["codes"] = codes

    # ── build the main query ───────────────────────────────────────────
    sql = f"""
    WITH bounds AS (
        SELECT
            date_trunc('{gran}', CAST(:start AS date)) AS min_bucket,
            date_trunc('{gran}', CAST(:end   AS date)) AS max_bucket
    ),
    buckets AS (
        SELECT generate_series(min_bucket, max_bucket, '{step}')::date AS bucket
        FROM   bounds
    ),
    base AS (
        SELECT date_trunc('{gran}', filing_date)::date AS bucket,
               court_slug,
               COUNT(*) AS filings
          FROM cases
         WHERE filing_date BETWEEN :start AND :end
           AND court_slug = ANY(:courts)
           {'' if not codes else 'AND nature_of_suit_numeric = ANY(:codes)'}
      GROUP BY bucket, court_slug
    )
    SELECT b.bucket,
           c.court_slug,
           COALESCE(a.filings, 0) AS filings
      FROM buckets       b
 CROSS JOIN UNNEST(:courts) AS c(court_slug)          -- every bucket × court
 LEFT JOIN base           a
        ON b.bucket     = a.bucket
       AND c.court_slug = a.court_slug
  ORDER BY b.bucket, c.court_slug;
    """

    return pd.read_sql(text(sql), eng, params=params)

def top_courts_by_filings(start: date,
                          end: date,
                          codes: list[int] | None,
                          limit: int = 5) -> list[str]:
    where = ["filing_date BETWEEN :start AND :end"]
    params = {"start": start, "end": end}

    if codes:                                     # NOS filter in sync
        where.append("nature_of_suit_numeric = ANY(:codes)")
        params["codes"] = codes

    where_sql = " AND ".join(where)

    sql = f"""
        SELECT court_slug
          FROM cases
         WHERE {where_sql}
      GROUP BY court_slug
      ORDER BY COUNT(*) DESC
         LIMIT {limit};
    """
    return pd.read_sql(text(sql), ENG, params=params)["court_slug"].tolist()

def days_to_close_df(
    *,
    group_by: str = "court",          # "court"  or "nos"
    courts:   list[str] | None = None,
    codes:    list[int] | None = None,
    start:    date | None = None,
    end:      date | None = None,
) -> pd.DataFrame:
    """
    Return rows:  <group> | days_to_close
    group = court_slug  when group_by="court"
          = nos code    when group_by="nos"
    """
    if group_by not in ("court", "nos"):
        raise ValueError("group_by must be 'court' or 'nos'")

    group_col = "court_slug" if group_by == "court" else "nature_of_suit_numeric::int"

    sql = f"""
        SELECT {group_col}              AS grp,
               (closing_date - filing_date)::int AS days_to_close
          FROM cases
         WHERE closing_date IS NOT NULL
           {{c_and}}
           {{n_and}}
           {{s_and}}
           {{e_and}}
    """.format(
        c_and = "AND court_slug = ANY(:courts)"            if courts else "",
        n_and = "AND nature_of_suit_numeric = ANY(:codes)" if codes  else "",
        s_and = "AND filing_date >= :start"                if start  else "",
        e_and = "AND filing_date <= :end"                  if end    else "",
    )

    params = {k: v for k, v in
              dict(courts=courts, codes=codes,
                   start=start, end=end).items()
              if v is not None}

    df = pd.read_sql(text(sql), ENG, params=params)
    df = df.assign(days_to_close=df["days_to_close"].abs())  # flip negatives
    return df.rename(columns={"grp": "group"})
