"""Sauvegarde un instantané GBFS Vélib' compressé à chaque exécution.

Usage : python -m src.collect_velib
Données ouvertes publiques ; aucune clé API requise.
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOG = logging.getLogger("velib-collector")
DATA_DIR = Path(os.environ.get("VELIB_DATA_DIR", "data"))
OFFICIAL_BASE = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"
# Domaine alternatif utilisé par des applications tierces : secours seulement.
ALTERNATE_BASE = "https://velib-metropole-opendata.smovengo.fr/opendata/Velib_Metropole"


def bases() -> list[str]:
    custom = os.environ.get("VELIB_BASE_URL", "").rstrip("/")
    return list(dict.fromkeys([v for v in [custom, OFFICIAL_BASE, ALTERNATE_BASE] if v]))


def http_session() -> requests.Session:
    retry = Retry(
        total=2,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session = requests.Session()
    session.headers.update({"User-Agent": "TelecomParis-KitDataScience-Velib/1.0 (academic project)"})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_json(session: requests.Session, base: str, filename: str) -> dict:
    url = f"{base}/{filename}"
    response = session.get(url, timeout=(7, 25))
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError(f"Réponse JSON inattendue : {url}")
    return result


def stations_from_payload(payload: dict) -> list[dict]:
    stations = payload.get("data", {}).get("stations")
    if not isinstance(stations, list) or not stations:
        raise ValueError("Flux GBFS sans liste de stations valide")
    if not all(isinstance(item, dict) and "station_id" in item for item in stations):
        raise ValueError("Stations mal formées ou sans station_id")
    return stations


def save_gzip_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Temporaire local puis renommage atomique, pour éviter les fichiers tronqués.
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(obj, handle, ensure_ascii=False, separators=(",", ":"))
    temporary.replace(path)


def station_quality(stations: list[dict], collected_at: datetime) -> dict:
    """Indicateurs fiables sur la couverture/fraîcheur, sans retirer de lignes."""
    ids = [str(station["station_id"]) for station in stations]
    duplicates = len(ids) - len(set(ids))
    ages = []
    for station in stations:
        ts = station.get("last_reported")
        if isinstance(ts, (int, float)) and ts > 0:
            ages.append(max(0, collected_at.timestamp() - float(ts)))
    return {
        "station_count": len(stations),
        "unique_station_count": len(set(ids)),
        "duplicate_ids": duplicates,
        "reported_count": len(ages),
        "stations_stale_over_15m": sum(age > 900 for age in ages),
        "stations_stale_over_60m": sum(age > 3600 for age in ages),
        "empty_open_stations": sum(
            station.get("is_renting") in (1, True, "1")
            and station.get("num_bikes_available", station.get("numBikesAvailable")) == 0
            for station in stations
        ),
    }


def save_quality_row(day: str, row: dict) -> None:
    destination = DATA_DIR / "quality" / f"{day}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    exists = destination.exists() and destination.stat().st_size > 0
    with destination.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def collect(now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("L'horodatage doit avoir un fuseau")
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    output = DATA_DIR / "raw" / day / f"{stamp}.json.gz"
    ref_output = DATA_DIR / "reference" / f"station_information_{day}.json.gz"

    errors = []
    with http_session() as session:
        for base in bases():
            try:
                payload = fetch_json(session, base, "station_status.json")
                stations = stations_from_payload(payload)
                quality = station_quality(stations, now)
                min_stations = int(os.environ.get("VELIB_MIN_STATIONS", "1000"))
                if quality["station_count"] < min_stations or quality["duplicate_ids"]:
                    raise ValueError(
                        "Instantané incomplet/incohérent: "
                        f"{quality['station_count']} stations, "
                        f"{quality['duplicate_ids']} identifiants dupliqués"
                    )
                saved = {
                    "collected_at_utc": now.isoformat(timespec="seconds"),
                    "source_url": f"{base}/station_status.json",
                    "source_last_updated": payload.get("lastUpdatedOther", payload.get("last_updated")),
                    "quality": quality,
                    "stations": stations,
                }
                save_gzip_json(output, saved)
                LOG.info("Sauvegardé %s : %s stations", output, len(stations))
                save_quality_row(day, {
                    "collected_at_utc": now.isoformat(timespec="seconds"),
                    "source_url": f"{base}/station_status.json",
                    "source_last_updated": payload.get("lastUpdatedOther", payload.get("last_updated")),
                    **quality,
                })
                if not ref_output.exists():
                    try:
                        info = fetch_json(session, base, "station_information.json")
                        info_stations = stations_from_payload(info)
                        save_gzip_json(ref_output, {
                            "collected_at_utc": now.isoformat(timespec="seconds"),
                            "source_url": f"{base}/station_information.json",
                            "stations": info_stations,
                        })
                        LOG.info("Référentiel sauvegardé : %s stations", len(info_stations))
                    except (requests.RequestException, ValueError, KeyError) as exc:
                        # La collecte du statut reste exploitable si le référentiel est HS.
                        LOG.warning("Référentiel inaccessible : %s", exc)
                return output
            except (requests.RequestException, ValueError, KeyError) as exc:
                errors.append(f"{base}: {exc}")
                LOG.warning("Échec du flux %s : %s", base, exc)

    raise RuntimeError("Aucun endpoint accessible. " + " | ".join(errors))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    path = collect()
    print(f"Collecte OK : {path}")
