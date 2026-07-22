#!/usr/bin/env python3
"""
Forward Networks - bulk Isolation intent-check creator.

Reads a CSV of hosts/subnets tagged with an "Environment", then creates
Forward "Isolation" intent checks verifying that DEV-class endpoints and
PROD-class endpoints cannot reach each other. Checks are placed in a named
intent-check directory.

Two input shapes are supported (columns are matched case-insensitively):
  1. Granular:  "Host Name", "Environment", "ip", "subnet"   -> checks per IP
  2. Subnet:    "Environment", "Subnet"                       -> checks per subnet

For every DEV row x every PROD row a pair of Isolation checks is created
(dev -> prod and prod -> dev), because DIRECTION defaults to "both".

Only the Python standard library is used (no pip installs).

USAGE
  1. Fill in the CONFIG block below (or override via env vars / CLI flags).
  2. Run a dry run first (default) to review what would be created:
         python3 forward_isolation_intent_checks.py hosts.csv
  3. When satisfied, actually create the checks:
         python3 forward_isolation_intent_checks.py hosts.csv --commit
"""

import argparse
import base64
import csv
import itertools
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

# ============================================================================
# CONFIG  (edit these, or override with env vars / CLI flags)
# ============================================================================

# --- API credentials & target -------------------------------------------------
BASE_URL   = "https://fwd.app"          # Forward instance base URL (no trailing /api)
API_KEY    = ""                          # API access key  (or username)   [env: FWD_API_KEY]
API_SECRET = ""                          # API secret key  (or password)   [env: FWD_API_SECRET]
NETWORK_ID = "159020"                    # Forward network ID

# Snapshot to attach checks to. Leave None to auto-resolve the latest
# processed snapshot for NETWORK_ID. Checks propagate forward to later
# snapshots when PERSISTENT is True.
SNAPSHOT_ID = None

# --- Where the checks go -------------------------------------------------------
DIRECTORY = "rt-test"                     # intent-check directory (single level, under root)

# --- Environment classification (case-insensitive, exact membership) ----------
DEV_ENVIRONMENTS  = {"dev", "test", "qa"}
PROD_ENVIRONMENTS = {"prod", "production", "prod2"}

# --- Behavior ------------------------------------------------------------------
DIRECTION   = "both"     # "both" (dev->prod and prod->dev) | "dev_to_prod" | "prod_to_dev"
ASYNC       = True       # mirror the UI: submit checks asynchronously
PERSISTENT  = True       # associate checks with later/future snapshots too
VERIFY_TLS  = True       # set False only for self-signed on-prem instances
HTTP_TIMEOUT = 60        # seconds per request

# Input CSV (can also be passed as the first CLI argument)
INPUT_CSV = "hosts.csv"

# Safety: dry run prints what WOULD happen and makes no API calls.
# Override with --commit on the command line.
DRY_RUN = True

# ============================================================================
# End of CONFIG
# ============================================================================


def _norm(s):
    return (s or "").strip()


def _basic_auth_header(key, secret):
    token = base64.b64encode(f"{key}:{secret}".encode("utf-8")).decode("ascii")
    return "Basic " + token


def _ssl_ctx():
    ctx = ssl.create_default_context()
    if not VERIFY_TLS:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def http(method, url, auth_header, body=None):
    """Minimal JSON HTTP helper. Returns (status_code, text). Raises on transport error."""
    data = None
    headers = {"Authorization": auth_header, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=HTTP_TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def load_rows(path):
    """
    Returns (mode, rows) where mode is "ip" or "subnet" and rows is a list of
    dicts: {"env": str, "value": str, "label": str}.
    """
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise SystemExit(f"ERROR: {path} has no header row.")
        # Map normalized header -> actual header
        hmap = {h.strip().lower(): h for h in reader.fieldnames}

        def col(*names):
            for n in names:
                if n in hmap:
                    return hmap[n]
            return None

        env_c    = col("environment", "env")
        ip_c     = col("ip", "ip address", "ipaddress")
        subnet_c = col("subnet", "cidr")
        host_c   = col("host name", "hostname", "host")

        if env_c is None:
            raise SystemExit("ERROR: CSV must contain an 'Environment' column.")
        if ip_c is not None:
            mode = "ip"
            value_c = ip_c
        elif subnet_c is not None:
            mode = "subnet"
            value_c = subnet_c
        else:
            raise SystemExit("ERROR: CSV must contain either an 'ip' or a 'subnet' column.")

        rows = []
        skipped = 0
        for raw in reader:
            env = _norm(raw.get(env_c))
            value = _norm(raw.get(value_c))
            if not value:
                # In ip mode, fall back to subnet if the ip cell is blank.
                if mode == "ip" and subnet_c is not None:
                    value = _norm(raw.get(subnet_c))
                if not value:
                    skipped += 1
                    continue
            host = _norm(raw.get(host_c)) if host_c else ""
            label = host if host else value
            rows.append({"env": env, "value": value, "label": label})
        if skipped:
            print(f"  (skipped {skipped} row(s) with no usable {mode} value)")
    return mode, rows


def classify(env):
    e = env.strip().lower()
    if e in {x.lower() for x in DEV_ENVIRONMENTS}:
        return "dev"
    if e in {x.lower() for x in PROD_ENVIRONMENTS}:
        return "prod"
    return None


# ---------------------------------------------------------------------------
# Check construction
# ---------------------------------------------------------------------------

def build_check(src, dst):
    """
    Build the NewNetworkCheck payload for 'src should NOT reach dst'.
    Shape mirrors exactly what the Forward UI posts for an Isolation check:
    source is the 'from' location; destination is an ipv4_dst packet filter.
    """
    name = f"[ISO] {src['label']} ({src['env']}) -x-> {dst['label']} ({dst['env']})"
    note = (f"{src['label']} ({src['env']}) should not be able to reach "
            f"{dst['label']} ({dst['env']})")
    definition = {
        "checkType": "Isolation",
        "filters": {
            "from": {
                "location": {"type": "SubnetLocationFilter", "value": src["value"]},
                "headers": [
                    {"type": "PacketFilter", "values": {"ipv4_dst": [dst["value"]]}}
                ],
            }
        },
        "noiseTypes": ["NETWORK_OR_BROADCAST_ADDRESS"],
        "headerFieldsWithDefaults": ["url"],
    }
    return {
        "definition": definition,
        "name": name,
        "note": note,
        "tags": [],
        "priority": "NOT_SET",
        "enabled": True,
    }


def plan_pairs(dev_rows, prod_rows):
    """Yield (src, dst) tuples honoring DIRECTION, de-duplicated, skipping self-pairs."""
    seen = set()
    directed = []
    for d, p in itertools.product(dev_rows, prod_rows):
        if DIRECTION in ("both", "dev_to_prod"):
            directed.append((d, p))
        if DIRECTION in ("both", "prod_to_dev"):
            directed.append((p, d))
    for src, dst in directed:
        if src["value"] == dst["value"]:
            continue
        key = (src["value"], dst["value"])
        if key in seen:
            continue
        seen.add(key)
        yield src, dst


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def resolve_snapshot(auth_header):
    if SNAPSHOT_ID:
        return str(SNAPSHOT_ID)
    url = f"{BASE_URL}/api/networks/{NETWORK_ID}/snapshots/latestProcessed"
    status, text = http("GET", url, auth_header)
    if status != 200:
        raise SystemExit(f"ERROR resolving latest snapshot ({status}): {text}")
    sid = json.loads(text).get("id")
    if not sid:
        raise SystemExit(f"ERROR: latestProcessed returned no snapshot id: {text}")
    return str(sid)


def ensure_directory(auth_header, directory):
    """Create the intent-check directory under root. Idempotent-ish: tolerate 'exists'."""
    parent = urllib.parse.quote("/", safe="")   # %2F
    qs = urllib.parse.urlencode({"action": "addDir", "name": directory})
    url = f"{BASE_URL}/api/networks/{NETWORK_ID}/intent-check-directories/{parent}?{qs}"
    status, text = http("POST", url, auth_header)
    if status in (200, 201, 204):
        print(f"  directory '/{directory}' created.")
    else:
        # Most likely already exists; log and continue.
        print(f"  directory create returned {status} (continuing; likely already exists): {text[:200]}")


def check_url(snapshot_id, directory):
    params = [("path", "/" + directory)]
    if PERSISTENT:
        params.append(("persistent", "true"))
    qs = urllib.parse.urlencode(params)
    if ASYNC:
        qs = "async&" + qs
    return f"{BASE_URL}/api/snapshots/{snapshot_id}/checks?{qs}"


def create_check(auth_header, url, payload):
    status, text = http("POST", url, auth_header, body=payload)
    return status, text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global DRY_RUN, INPUT_CSV, API_KEY, API_SECRET

    ap = argparse.ArgumentParser(description="Bulk-create Forward Isolation intent checks from a CSV.")
    ap.add_argument("csv", nargs="?", default=INPUT_CSV, help="input CSV path")
    ap.add_argument("--commit", action="store_true", help="actually create checks (disables dry run)")
    ap.add_argument("--dry-run", action="store_true", help="force dry run (default)")
    args = ap.parse_args()

    INPUT_CSV = args.csv
    if args.commit:
        DRY_RUN = False
    if args.dry_run:
        DRY_RUN = True

    API_KEY = os.environ.get("FWD_API_KEY", API_KEY)
    API_SECRET = os.environ.get("FWD_API_SECRET", API_SECRET)

    print(f"Input CSV : {INPUT_CSV}")
    mode, rows = load_rows(INPUT_CSV)
    print(f"Mode      : {mode}  ({'per-IP' if mode == 'ip' else 'per-subnet'})")

    dev_rows, prod_rows, ignored = [], [], 0
    for r in rows:
        c = classify(r["env"])
        if c == "dev":
            dev_rows.append(r)
        elif c == "prod":
            prod_rows.append(r)
        else:
            ignored += 1

    print(f"DEV rows  : {len(dev_rows)}   PROD rows: {len(prod_rows)}   ignored: {ignored}")
    if not dev_rows or not prod_rows:
        raise SystemExit("Nothing to do: need at least one DEV row and one PROD row.")

    pairs = list(plan_pairs(dev_rows, prod_rows))
    print(f"Direction : {DIRECTION}")
    print(f"Planned checks: {len(pairs)}")
    print("-" * 70)

    if DRY_RUN:
        print("DRY RUN - no API calls will be made.\n")
        print(f"Would create directory '/{DIRECTORY}' in network {NETWORK_ID}.")
        sid = SNAPSHOT_ID or "<latest processed snapshot>"
        print(f"Would POST checks to snapshot {sid} at path '/{DIRECTORY}'.\n")
        preview = pairs if len(pairs) <= 20 else pairs[:20]
        for src, dst in preview:
            payload = build_check(src, dst)
            print(f"URL : {check_url(str(sid), DIRECTORY)}")
            print(f"NAME: {payload['name']}")
            print(f"NOTE: {payload['note']}")
            print(f"BODY: {json.dumps(payload['definition'], separators=(',', ':'))}")
            print()
        if len(pairs) > len(preview):
            print(f"... and {len(pairs) - len(preview)} more (showing first {len(preview)}).")
        print("\nRe-run with --commit to create these checks.")
        return

    # --- Commit path ---
    if not API_KEY or not API_SECRET:
        raise SystemExit("ERROR: API_KEY/API_SECRET are required to commit "
                         "(set in CONFIG or via FWD_API_KEY / FWD_API_SECRET).")
    auth = _basic_auth_header(API_KEY, API_SECRET)

    snapshot_id = resolve_snapshot(auth)
    print(f"Snapshot  : {snapshot_id}")
    ensure_directory(auth, DIRECTORY)
    url = check_url(snapshot_id, DIRECTORY)

    ok, fail = 0, 0
    for i, (src, dst) in enumerate(pairs, 1):
        payload = build_check(src, dst)
        status, text = create_check(auth, url, payload)
        if 200 <= status < 300:
            ok += 1
            print(f"[{i}/{len(pairs)}] OK   {payload['name']}")
        else:
            fail += 1
            print(f"[{i}/{len(pairs)}] FAIL {status}  {payload['name']}\n        {text[:300]}")

    print("-" * 70)
    print(f"Done. Created: {ok}   Failed: {fail}   Directory: /{DIRECTORY}")


if __name__ == "__main__":
    main()
