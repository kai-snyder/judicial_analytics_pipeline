#!/usr/bin/env python3
"""
Case Prediction Pipeline – unified CLI
======================================

Run any step like so:

    # 1. Pull raw dockets
    python -m src.cli fetch --start 2024-01-01 --end 2024-01-07 --court dcd

    # 2. Transform -> parquet
    python -m src.cli transform

    # 3. Ingest parquet into Postgres
    python -m src.cli ingest

    # 4. Build feature matrix
    python -m src.cli features

    # 5. Train models
    python -m src.cli train

    # 6. Evaluate & plot calibration
    python -m src.cli evaluate
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Callable, Mapping

# ---------------------------------------------------------------------------
# 0.  Make project root import-safe regardless of $PWD
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# 1.  Registry helpers
# ---------------------------------------------------------------------------

# Each CLI sub-command maps to "module_path:function_name"
COMMAND_TABLE: Mapping[str, str] = {
    "fetch": "src.data.fetch_courtlistener:main",
    "transform": "src.data.transform:main",
    "ingest": "src.data.ingest_sql:main",
    "features": "src.features.build_features:main",
    "train": "src.models.train:main",
    "evaluate": "src.models.evaluate:main",
}


def _resolve_callable(dotted: str) -> Callable[..., None]:
    """Import the `module:function` specified in dotted path and return it."""
    module_path, func_name = dotted.split(":")
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


# ---------------------------------------------------------------------------
# 2.  Argparse scaffold
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="case_prediction_pipeline",
        description="End-to-end pipeline wrapper for Case Prediction.",
    )
    subs = parser.add_subparsers(dest="command", required=True, metavar="<step>")

    # ── fetch ────────────────────────────────────────────────────────────────
    fetch = subs.add_parser("fetch", help="Download raw docket JSONL from CourtListener")
    fetch.add_argument("--start", required=True, help="YYYY-MM-DD (filed_after)")
    fetch.add_argument("--end", required=True, help="YYYY-MM-DD (filed_before)")
    fetch.add_argument("--court", required=True, help="Court slug, e.g. dcd")
    fetch.set_defaults(_entry=COMMAND_TABLE["fetch"])

    # ── transform ────────────────────────────────────────────────────────────
    transform = subs.add_parser("transform", help="Raw JSONL ➜ processed parquet")
    transform.set_defaults(_entry=COMMAND_TABLE["transform"])

    # ── ingest ───────────────────────────────────────────────────────────────
    ingest = subs.add_parser("ingest", help="Load processed parquet into Postgres")
    ingest.set_defaults(_entry=COMMAND_TABLE["ingest"])

    # ── features ─────────────────────────────────────────────────────────────
    feat = subs.add_parser("features", help="Build design matrix for modelling")
    feat.set_defaults(_entry=COMMAND_TABLE["features"])

    # ── train ────────────────────────────────────────────────────────────────
    train = subs.add_parser("train", help="Train logistic & LightGBM models")
    train.set_defaults(_entry=COMMAND_TABLE["train"])

    # ── evaluate ─────────────────────────────────────────────────────────────
    evl = subs.add_parser("evaluate", help="Compute AUC / PR-AUC and plot calibration")
    evl.set_defaults(_entry=COMMAND_TABLE["evaluate"])

    return parser


# ---------------------------------------------------------------------------
# 3.  Top-level dispatcher
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None):
    args = build_parser().parse_args(argv)

    # Pull out the target callable from the CLI metadata
    dotted = getattr(args, "_entry")
    target_fn = _resolve_callable(dotted)

    # Forward the *remaining* Namespace entries to the target
    kwargs = {
        k: v
        for k, v in vars(args).items()
        if k not in {"command", "_entry"} and v is not None
    }
    target_fn(**kwargs)


if __name__ == "__main__":
    main()
