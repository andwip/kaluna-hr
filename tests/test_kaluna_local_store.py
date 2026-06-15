import importlib.util
import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("kaluna_local_store", ROOT / "kaluna-local-store.py")
STORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STORE)


class AttendanceEnrichmentTest(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        STORE.init_db(self.con)
        self.insert("locations", "office_jakarta", {
            "id": "office_jakarta",
            "location_id": "office_jakarta",
            "latitude": -6.226203406695065,
            "longitude": 106.83282798220883,
            "radius_meter": 1000,
        })

    def insert(self, collection, doc_id, body):
        self.con.execute(
            "insert into snapshot(collection, doc_id, body, updated_at) values (?, ?, ?, ?)",
            (collection, doc_id, json.dumps(body), STORE.now()),
        )
        self.con.commit()

    def employee(self, employee_id, department):
        self.insert("employees", employee_id, {
            "id": employee_id,
            "employee_id": employee_id,
            "department": department,
            "approved_location_id": "office_jakarta",
        })

    def test_department_matching_is_case_insensitive(self):
        self.assertEqual(STORE.normalize_department("  SALES "), "sales")
        self.assertTrue(STORE.is_sales_employee({"department": " Sales "}))

    def test_inside_office_payload_is_not_modified(self):
        self.employee("EMP_1", "Finance")
        payload = {
            "employee_id": "EMP_1",
            "latitude": -6.226203406695065,
            "longitude": 106.83282798220883,
        }

        result = STORE.enrich_attendance_payload(self.con, "/api/attendance/check-in", payload)

        self.assertEqual(result, payload)

    def test_sales_outside_geofence_requires_purpose(self):
        self.employee("EMP_1", "sales")
        payload = {
            "employee_id": "EMP_1",
            "latitude": -6.1751,
            "longitude": 106.8271,
        }

        with self.assertRaisesRegex(ValueError, "purpose is required"):
            STORE.enrich_attendance_payload(self.con, "/api/attendance/check-in", payload)

    def test_sales_outside_geofence_adds_exception_metadata(self):
        self.employee("EMP_1", "SALES")
        payload = {
            "employee_id": "EMP_1",
            "latitude": -6.1751,
            "longitude": 106.8271,
            "purpose": "Client visit",
        }

        result = STORE.enrich_attendance_payload(self.con, "/api/attendance/check-out", payload)

        self.assertTrue(result["is_outside_geofence"])
        self.assertEqual(result["geofence_exception"], "sales_department")
        self.assertEqual(result["nearest_location_id"], "office_jakarta")

    def test_non_sales_outside_geofence_is_blocked(self):
        self.employee("EMP_1", "Finance")
        payload = {
            "employee_id": "EMP_1",
            "latitude": -6.1751,
            "longitude": 106.8271,
        }

        with self.assertRaisesRegex(ValueError, "only allowed for sales"):
            STORE.enrich_attendance_payload(self.con, "/api/attendance/check-in", payload)


if __name__ == "__main__":
    unittest.main()
