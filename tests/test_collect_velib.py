import unittest
from src.collect_velib import bases, stations_from_payload


class TestCollector(unittest.TestCase):
    def test_station_list(self):
        payload = {"data": {"stations": [{"station_id": 123, "num_bikes_available": 8}]}}
        self.assertEqual(stations_from_payload(payload)[0]["station_id"], 123)

    def test_empty_list_rejected(self):
        with self.assertRaises(ValueError):
            stations_from_payload({"data": {"stations": []}})

    def test_station_id_required(self):
        with self.assertRaises(ValueError):
            stations_from_payload({"data": {"stations": [{"num_bikes_available": 1}]}})

    def test_base_has_official(self):
        self.assertTrue(any("smovengo.cloud" in base for base in bases()))


if __name__ == "__main__":
    unittest.main()
