import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.audit_collection import audit
from src.collect_velib import station_quality


class TestAuditCollection(unittest.TestCase):
    def test_all_stations_preserved_and_quality(self):
        rows = [
            {"station_id": str(i), "num_bikes_available": i % 3,
             "last_reported": 1600000000, "is_renting": 1}
            for i in range(1500)
        ]
        result = station_quality(rows, datetime.fromtimestamp(1600000000, tz=timezone.utc))
        self.assertEqual(result["station_count"], 1500)
        self.assertEqual(result["unique_station_count"], 1500)
        self.assertEqual(result["duplicate_ids"], 0)
        self.assertEqual(result["empty_open_stations"], 500)

    def test_48_hour_window_is_recognized(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            begin = datetime(2026, 10, 24, tzinfo=timezone.utc)
            # 577 instants = 48h révolues, aucun trou > 5min.
            for k in range(577):
                t = begin + timedelta(minutes=k*5)
                file = base / "raw" / t.strftime("%Y-%m-%d") / (t.strftime("%H%M") + ".json.gz")
                file.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(file, "wt", encoding="utf-8") as handle:
                    json.dump({"collected_at_utc": t.isoformat(),
                               "stations": [{"station_id": 1}]}, handle)
            status = audit(base)
            self.assertTrue(status["complete_48h"])
            self.assertEqual(status["snapshots"], 576)
            self.assertEqual(status["min_stations_per_snapshot"], 1)

    def test_empty_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            result = audit(Path(temp))
            self.assertEqual(result["snapshots"], 0)
            self.assertFalse(result["complete_48h"])


if __name__ == "__main__":
    unittest.main()
