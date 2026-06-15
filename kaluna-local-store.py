#!/usr/bin/env python3
import argparse
import datetime
import json
import math
import os
import sqlite3
import subprocess
import sys
import uuid

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data", "kaluna-local.db")
COLLECTIONS = [
    "employees",
    "attendance",
    "leave_requests",
    "locations",
    "policy",
    "channel_pair_tickets",
    "onboarding_tasks",
    "offboarding_tasks",
    "audit_logs",
    "agent",
]
ATTENDANCE_ENDPOINTS = {
    "/api/attendance/check-in",
    "/api/attendance/check-out",
}


def now():
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db(con):
    con.executescript("""
    create table if not exists snapshot (
      collection text not null,
      doc_id text not null,
      body text not null,
      updated_at text not null,
      primary key (collection, doc_id)
    );
    create table if not exists outbox (
      id text primary key,
      action text not null,
      endpoint text not null,
      payload text not null,
      status text not null default 'pending',
      attempts integer not null default 0,
      last_error text,
      created_at text not null,
      updated_at text not null
    );
    """)
    con.commit()


def doc_id(collection, doc, idx):
    for key in ("id", "employee_id", "attendance_id", "request_id", "code"):
        if isinstance(doc, dict) and doc.get(key):
            return str(doc[key])
    return f"{collection}_{idx}"


def import_snapshot(args):
    con = connect()
    init_db(con)
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = 0
    for collection in COLLECTIONS:
        items = data.get(collection, [])
        if isinstance(items, dict):
            items = [
                {"id": k, **v} if isinstance(v, dict) else {"id": k, "value": v}
                for k, v in items.items()
            ]
        if not isinstance(items, list):
            continue
        for idx, doc in enumerate(items):
            did = doc_id(collection, doc, idx)
            con.execute(
                "insert or replace into snapshot(collection, doc_id, body, updated_at) values (?, ?, ?, ?)",
                (collection, did, json.dumps(doc, separators=(",", ":")), now()),
            )
            total += 1
    con.commit()
    print(f"imported {total} documents into {DB}")


def import_collection(args):
    con = connect()
    init_db(con)
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("data", data)
    if isinstance(items, dict):
        items = [
            {"id": k, **v} if isinstance(v, dict) else {"id": k, "value": v}
            for k, v in items.items()
        ]
    if not isinstance(items, list):
        print("collection import file must contain an array or a JSON object with a data array", file=sys.stderr)
        sys.exit(1)

    for idx, doc in enumerate(items):
        did = doc_id(args.collection, doc, idx)
        con.execute(
            "insert or replace into snapshot(collection, doc_id, body, updated_at) values (?, ?, ?, ?)",
            (args.collection, did, json.dumps(doc, separators=(",", ":")), now()),
        )
    con.commit()
    print(f"imported {len(items)} {args.collection} documents into {DB}")


def list_docs(args):
    con = connect()
    init_db(con)
    rows = con.execute(
        "select doc_id, body from snapshot where collection=? order by doc_id limit ?",
        (args.collection, args.limit),
    ).fetchall()
    print(json.dumps([json.loads(r["body"]) for r in rows], indent=2))


def get_doc(args):
    con = connect()
    init_db(con)
    row = con.execute(
        "select body from snapshot where collection=? and doc_id=?",
        (args.collection, args.id),
    ).fetchone()
    if not row:
        print("not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(json.loads(row["body"]), indent=2))


def resolve_channel(args):
    con = connect()
    init_db(con)
    rows = con.execute(
        "select body from snapshot where collection='employees'"
    ).fetchall()

    for row in rows:
        employee = json.loads(row["body"])
        channel_ids = [
            str(employee.get("channel_user_id") or ""),
            str(employee.get("telegram_user_id") or ""),
        ]
        if str(args.channel_user_id) not in channel_ids:
            continue

        status = (
            employee.get("channel_auth_status")
            or employee.get("telegram_auth_status")
            or "unlinked"
        )
        linked = status in ("verified", "active")
        print(json.dumps({
            "success": True,
            "linked": linked,
            "binding_status": "active" if linked else status,
            "employee_id": employee.get("employee_id") or employee.get("id"),
            "email": employee.get("email"),
            "full_name": employee.get("full_name"),
            "bot_role": employee.get("bot_role") or employee.get("role"),
            "department": employee.get("department"),
            "channel_user_id": employee.get("channel_user_id") or employee.get("telegram_user_id"),
            "channel_username": employee.get("channel_username") or employee.get("telegram_username"),
            "channel_type": employee.get("channel_type") or "telegram",
        }, indent=2))
        return

    print(json.dumps({
        "success": True,
        "linked": False,
        "binding_status": "unlinked",
        "channel_user_id": str(args.channel_user_id),
    }, indent=2))


def snapshot_docs(con, collection):
    rows = con.execute(
        "select body from snapshot where collection=?",
        (collection,),
    ).fetchall()
    return [json.loads(row["body"]) for row in rows]


def find_employee(con, employee_id):
    for employee in snapshot_docs(con, "employees"):
        ids = [
            str(employee.get("employee_id") or ""),
            str(employee.get("id") or ""),
        ]
        if str(employee_id) in ids:
            return employee
    return None


def normalize_department(value):
    return " ".join(str(value or "").strip().lower().split())


def is_sales_employee(employee):
    return normalize_department((employee or {}).get("department")) == "sales"


def to_float(value, field):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number")


def haversine_meter(lat1, lon1, lat2, lon2):
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def candidate_locations(con, employee, payload):
    locations = snapshot_docs(con, "locations")
    requested_id = payload.get("location_id")
    approved_id = (
        requested_id
        or (employee or {}).get("approved_location_id")
        or (employee or {}).get("location")
    )
    if approved_id:
        scoped = [
            location for location in locations
            if str(location.get("location_id") or location.get("id") or "") == str(approved_id)
        ]
        if scoped:
            return scoped
    return locations


def nearest_geofence(con, employee, payload):
    latitude = to_float(payload.get("latitude"), "latitude")
    longitude = to_float(payload.get("longitude"), "longitude")
    nearest = None

    for location in candidate_locations(con, employee, payload):
        if location.get("latitude") is None or location.get("longitude") is None:
            continue
        distance = haversine_meter(
            latitude,
            longitude,
            to_float(location.get("latitude"), "location.latitude"),
            to_float(location.get("longitude"), "location.longitude"),
        )
        radius = to_float(location.get("radius_meter") or location.get("radius_meters") or 0, "radius_meter")
        current = {
            "location_id": location.get("location_id") or location.get("id"),
            "distance_meter": round(distance, 2),
            "radius_meter": radius,
            "inside": distance <= radius,
        }
        if nearest is None or current["distance_meter"] < nearest["distance_meter"]:
            nearest = current

    return nearest


def enrich_attendance_payload(con, endpoint, payload):
    if endpoint not in ATTENDANCE_ENDPOINTS:
        return payload
    if "latitude" not in payload or "longitude" not in payload:
        return payload

    employee_id = payload.get("employee_id")
    employee = find_employee(con, employee_id)
    if not employee:
        raise ValueError("employee not found in local snapshot")

    geofence = nearest_geofence(con, employee, payload)
    if not geofence:
        raise ValueError("office geofence not found in local snapshot")
    if geofence["inside"]:
        return payload

    payload = dict(payload)
    payload["is_outside_geofence"] = True
    payload["nearest_location_id"] = geofence["location_id"]
    payload["nearest_location_distance_meter"] = geofence["distance_meter"]
    payload["nearest_location_radius_meter"] = geofence["radius_meter"]

    if is_sales_employee(employee):
        if not str(payload.get("purpose") or "").strip():
            raise ValueError("purpose is required for sales outside geofence attendance")
        payload["geofence_exception"] = "sales_department"
        return payload

    raise ValueError("outside geofence attendance is only allowed for sales employees")


def enqueue(args):
    con = connect()
    init_db(con)
    try:
        payload_obj = json.loads(args.payload)
        if not isinstance(payload_obj, dict):
            raise ValueError("payload must be a JSON object")
        payload_obj = enrich_attendance_payload(con, args.endpoint, payload_obj)
        payload = json.dumps(payload_obj, separators=(",", ":"))
    except ValueError as exc:
        print(json.dumps({"queued": False, "error": str(exc)}, indent=2), file=sys.stderr)
        sys.exit(1)

    oid = str(uuid.uuid4())
    con.execute(
        """insert into outbox(id, action, endpoint, payload, status, created_at, updated_at)
           values (?, ?, ?, ?, 'pending', ?, ?)""",
        (oid, args.action, args.endpoint, payload, now(), now()),
    )
    con.commit()
    print(json.dumps({"queued": True, "id": oid}, indent=2))


def status(args):
    con = connect()
    init_db(con)
    rows = con.execute(
        "select status, count(*) as count from outbox group by status order by status"
    ).fetchall()
    print(json.dumps({r["status"]: r["count"] for r in rows}, indent=2))


def sync(args):
    con = connect()
    init_db(con)

    rows = con.execute(
        """select id, action, endpoint, payload, attempts
           from outbox
           where status in ('pending', 'failed')
           order by created_at
           limit ?""",
        (args.limit,),
    ).fetchall()

    synced = 0
    failed = 0

    for row in rows:
        oid = row["id"]
        endpoint = row["endpoint"]
        payload = row["payload"]

        try:
            result = subprocess.run(
                [os.path.join(BASE, "kaluna-api-post.sh"), endpoint, payload],
                cwd=BASE,
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=True,
            )

            con.execute(
                """update outbox
                   set status='synced',
                       attempts=attempts+1,
                       last_error=null,
                       updated_at=?
                   where id=?""",
                (now(), oid),
            )
            synced += 1

            if args.verbose:
                print(json.dumps({
                    "id": oid,
                    "status": "synced",
                    "response": result.stdout.strip(),
                }, indent=2))

        except Exception as exc:
            error = str(exc)

            if isinstance(exc, subprocess.CalledProcessError):
                error = (exc.stderr or exc.stdout or str(exc)).strip()

            con.execute(
                """update outbox
                   set status='failed',
                       attempts=attempts+1,
                       last_error=?,
                       updated_at=?
                   where id=?""",
                (error, now(), oid),
            )
            failed += 1

            if args.verbose:
                print(json.dumps({
                    "id": oid,
                    "status": "failed",
                    "error": error,
                }, indent=2))

    con.commit()
    print(json.dumps({"synced": synced, "failed": failed}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Kaluna local SQLite snapshot and async outbox")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("import-snapshot")
    p.add_argument("file")
    p.set_defaults(func=import_snapshot)

    p = sub.add_parser("import-collection")
    p.add_argument("collection", choices=COLLECTIONS)
    p.add_argument("file")
    p.set_defaults(func=import_collection)

    p = sub.add_parser("list")
    p.add_argument("collection", choices=COLLECTIONS)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=list_docs)

    p = sub.add_parser("get")
    p.add_argument("collection", choices=COLLECTIONS)
    p.add_argument("id")
    p.set_defaults(func=get_doc)

    p = sub.add_parser("resolve-channel")
    p.add_argument("channel_user_id")
    p.set_defaults(func=resolve_channel)

    p = sub.add_parser("enqueue")
    p.add_argument("action")
    p.add_argument("endpoint")
    p.add_argument("payload")
    p.set_defaults(func=enqueue)

    p = sub.add_parser("status")
    p.set_defaults(func=status)

    p = sub.add_parser("sync")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
