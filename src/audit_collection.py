"""Mesure la couverture réelle des instantanés enregistrés.

Exemple : python -m src.audit_collection --hours 48
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Horodatage sans fuseau")
    return result.astimezone(timezone.utc)


def audit(data_dir: Path, hours: int = 48, interval_min: int = 5) -> dict:
    items = []
    for file in sorted((data_dir / "raw").glob("*/*.json.gz")):
        try:
            with gzip.open(file, "rt", encoding="utf-8") as handle:
                record = json.load(handle)
            timestamp = parse_time(record["collected_at_utc"])
            stations = record.get("stations")
            if not isinstance(stations, list):
                continue
            items.append((timestamp, len(stations)))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
    items.sort(key=lambda it: it[0])
    expected = math.ceil(hours * 60 / interval_min)
    if not items:
        return {"window_hours": hours, "expected_snapshots": expected,
                "snapshots": 0, "coverage_percent": 0, "complete_48h": False}
    # Fenêtre glissante de 48 heures basée sur le dernier instantané enregistré.
    end = items[-1][0]
    start = end - timedelta(hours=hours)
    selected = [(t, n) for t, n in items if start < t <= end]
    longest_gap = max(
        ((b[0] - a[0]).total_seconds() / 60 for a, b in zip(selected, selected[1:])),
        default=0,
    )
    real_span = (items[-1][0] - items[0][0]).total_seconds() / 3600
    counts = [n for _, n in selected]
    return {
        "window_hours": hours,
        "expected_snapshots": expected,
        "snapshots": len(selected),
        "coverage_percent": round(min(100, len(selected) / expected * 100), 2),
        "history_span_hours": round(real_span, 2),
        "first_snapshot_utc": items[0][0].isoformat(),
        "last_snapshot_utc": end.isoformat(),
        "max_gap_minutes": round(longest_gap, 2),
        "min_stations_per_snapshot": min(counts),
        "max_stations_per_snapshot": max(counts),
        "mean_stations_per_snapshot": round(sum(counts) / len(counts), 2),
        # Objectif opérationnel : 48h + >=95% des créneaux + aucun trou >15min.
        "complete_48h": real_span >= hours and
                        len(selected) / expected >= 0.95 and longest_gap <= 15,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditer la couverture temporelle Vélib")
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--interval-min", type=int, default=5)
    args = parser.parse_args()
    result = audit(Path(os.environ.get("VELIB_DATA_DIR", "data")),
                   args.hours, args.interval_min)
    print(json.dumps(result, ensure_ascii=False, indent=2))
