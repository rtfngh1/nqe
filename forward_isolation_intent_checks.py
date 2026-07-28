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
(dev -> prod and prod -> dev) when DIRECTION is "both".

Only the Python standard library is used (no pip installs). Works on Windows
(invoke with `python`), macOS, and Linux.

USAGE
  1. Fill in the CONFIG block below (or override with env vars / CLI flags).
  2. Dry run first (default) to review what would be created:
         python forward_isolation_intent_checks.py hosts.csv
  3. Create the checks:
         python forward_isolation_intent_checks.py hosts.csv --commit
  4. If a long run stops partway, resume by skipping the ones already made:
         python forward_isolation_intent_checks.py hosts.csv --commit --start 2000
"""

import argparse
import base64
import csv
import http.client
import itertools
import json
import os
import random
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ============================================================================
# CONFIG  (edit these, or override with env vars / CLI flags)
# ============================================================================

# --- API credentials & target -------------------------------------------------
BASE_URL   = "https://fwd.app"           # Forward instance base URL (no trailing /api)
API_KEY    = ""                          # API access key  (or username)   [env: FWD_API_KEY]
API_SECRET = ""                          # API secret key  (or password)   [env: FWD_API_SECRET]
NETWORK_ID = "159020"                    # Forward network ID

# Snapshot to attach checks to. Leave None to auto-resolve the latest
# processed snapshot for NETWORK_ID. Checks propagate forward to later
# snapshots when PERSISTENT is True.
SNAPSHOT_ID = None

# --- Where the checks go -------------------------------------------------------
DIRECTORY = "rt-test"                     # intent-check directory; nested allowed, e.g. "rt-test/rt-test-nested"

# --- Environment classification (case-insensitive, exact membership) ----------
DEV_ENVIRONMENTS  = {"dev", "test", "qa"}
PROD_ENVIRONMENTS = {"prod", "production", "prod2"}

# --- Behavior ------------------------------------------------------------------
DIRECTION   = "both"     # "both" (dev->prod and prod->dev) | "dev_to_prod" | "prod_to_dev"

# Route every check "through" this device group (a Forward Device Group ->
# DeviceAliasFilter). Applies to the whole run. Leave "" to omit the through hop.
# Overridable per run with --through <group>.
THROUGH_DEVICE_GROUP = "jfk-campus"

# How to express the destination in the check (in-script constant).
#   "to"      -> destination as a 'to' location (SubnetLocationFilter). RECOMMENDED
#                default: it localizes BOTH source and destination in the topology,
#                which is what an isolation/existence check should verify.
#   "dest-ip" -> destination as an ipv4_dst packet filter on the 'from' clause.
#                This only matches the packet's destination field; it does NOT
#                localize where the destination sits. Only use it when you also set
#                THROUGH_DEVICE_GROUP (or otherwise add enough 'through' hops) so the
#                check represents a full, well-defined flow. See
#                NQE Reference/Forward_Intent_Check_API.md (Best practice).
DEST_MODE   = "to"       # "to" | "dest-ip"

ASYNC       = True       # mirror the UI: submit checks asynchronously
PERSISTENT  = True       # associate checks with later/future snapshots too
VERIFY_TLS  = True       # set False only for self-signed on-prem instances
HTTP_TIMEOUT = 60        # seconds per request

# --- Retry (for momentary instance hiccups: read timeouts, resets, 5xx) --------
MAX_RETRIES       = 5           # extra attempts after the first, per request
RETRY_BACKOFF_SEC = 2.0         # base delay; doubles each attempt (2, 4, 8, ...)
RETRY_MAX_SLEEP   = 30          # cap on any single backoff sleep (seconds)
RETRY_ON_STATUS   = {429, 500, 502, 503, 504}   # HTTP statuses worth retrying

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


# Transient transport errors worth retrying (timeouts, resets, dropped connections).
# Note: HTTPError is caught separately/earlier; it subclasses URLError.
TRANSIENT_EXC = (
    TimeoutError,
    socket.timeout,
    urllib.error.URLError,
    ConnectionError,
    ssl.SSLError,
    http.client.HTTPException,
)


def _backoff_sleep(attempt, reason):
    delay = min(RETRY_BACKOFF_SEC * (2 ** (attempt - 1)), RETRY_MAX_SLEEP)
    delay += random.uniform(0, delay * 0.25)   # jitter to avoid thundering herd
    print(f"    transient failure ({reason}); retry {attempt}/{MAX_RETRIES} in {delay:.1f}s")
    time.sleep(delay)


def http(method, url, auth_header, body=None):
    """
    JSON HTTP helper with retry/backoff. Returns (status_code, text).

    Retries on transient transport errors (read timeouts, connection resets, etc.)
    and on retryable HTTP statuses (RETRY_ON_STATUS), with exponential backoff +
    jitter. Raises the last transport exception only if all attempts are exhausted;
    non-retryable HTTP errors are returned as (code, text) for the caller to handle.
    """
    data = None
    headers = {"Authorization": auth_header, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 2):   # first try + MAX_RETRIES retries
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=HTTP_TIMEOUT) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            code = e.code
            text = e.read().decode("utf-8", "replace")
            if code in RETRY_ON_STATUS and attempt <= MAX_RETRIES:
                _backoff_sleep(attempt, f"HTTP {code}")
                continue
            return code, text
        except TRANSIENT_EXC as e:
            last_exc = e
            if attempt <= MAX_RETRIES:
                _backoff_sleep(attempt, type(e).__name__)
                continue
            raise
    raise last_exc  # pragma: no cover (loop always returns/raises above)


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
            mode, value_c = "ip", ip_c
        elif subnet_c is not None:
            mode, value_c = "subnet", subnet_c
        else:
            raise SystemExit("ERROR: CSV must contain either an 'ip' or a 'subnet' column.")

        rows, skipped = [], 0
        for raw in reader:
            env = _norm(raw.get(env_c))
            value = _norm(raw.get(value_c))
            if not value:
                if mode == "ip" and subnet_c is not None:
                    value = _norm(raw.get(subnet_c))
                if not value:
                    skipped += 1
                    continue
            host = _norm(raw.get(host_c)) if host_c else ""
            rows.append({"env": env, "value": value, "label": host if host else value})
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

    - "to" mode:      from.location = src, to.location = dst  (localizes both ends)
    - "dest-ip" mode: from.location = src, from.headers ipv4_dst = dst
    - THROUGH_DEVICE_GROUP, if set, adds a 'through' chain hop (DeviceAliasFilter).
    """
    name = f"[ISO] {src['label']} ({src['env']}) -x-> {dst['label']} ({dst['env']})"
    note = (f"{src['label']} ({src['env']}) should not be able to reach "
            f"{dst['label']} ({dst['env']})")

    filters = {}
    if THROUGH_DEVICE_GROUP:
        filters["chain"] = [{
            "transitType": "through",
            "location": {"type": "DeviceAliasFilter", "value": THROUGH_DEVICE_GROUP},
        }]

    frm = {"location": {"type": "SubnetLocationFilter", "value": src["value"]}}
    if DEST_MODE == "to":
        filters["from"] = frm
        filters["to"] = {"location": {"type": "SubnetLocationFilter", "value": dst["value"]}}
    else:  # "dest-ip"
        frm["headers"] = [{"type": "PacketFilter", "values": {"ipv4_dst": [dst["value"]]}}]
        filters["from"] = frm

    definition = {
        "checkType": "Isolation",
        "filters": filters,
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
    """
    Create the intent-check directory, one level at a time. Supports nested
    paths like "rt-test/rt-test-nested": each segment is created under its
    parent. Idempotent-ish: a level that already exists is logged and skipped.
    """
    segments = [s for s in directory.strip("/").split("/") if s]
    parent = "/"
    for seg in segments:
        parent_enc = urllib.parse.quote(parent, safe="")   # "/" -> %2F, "/rt-test" -> %2Frt-test
        qs = urllib.parse.urlencode({"action": "addDir", "name": seg})
        url = f"{BASE_URL}/api/networks/{NETWORK_ID}/intent-check-directories/{parent_enc}?{qs}"
        status, text = http("POST", url, auth_header)
        full = "/" + "/".join([p for p in (parent.strip("/"), seg) if p])
        if status in (200, 201, 204):
            print(f"  directory '{full}' created.")
        else:
            print(f"  directory '{full}' create returned {status} (continuing; likely exists): {text[:150]}")
        parent = full


def check_url(snapshot_id, directory):
    params = [("path", "/" + directory.strip("/"))]
    if PERSISTENT:
        params.append(("persistent", "true"))
    qs = urllib.parse.urlencode(params)
    if ASYNC:
        qs = "async&" + qs
    return f"{BASE_URL}/api/snapshots/{snapshot_id}/checks?{qs}"


def create_check(auth_header, url, payload):
    return http("POST", url, auth_header, body=payload)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global DRY_RUN, INPUT_CSV, API_KEY, API_SECRET, THROUGH_DEVICE_GROUP

    ap = argparse.ArgumentParser(description="Bulk-create Forward Isolation intent checks from a CSV.")
    ap.add_argument("csv", nargs="?", default=INPUT_CSV, help="input CSV path")
    ap.add_argument("--commit", action="store_true", help="actually create checks (disables dry run)")
    ap.add_argument("--dry-run", action="store_true", help="force dry run (default)")
    ap.add_argument("--through", default=None, metavar="GROUP",
                    help="device group to route every check 'through' (overrides THROUGH_DEVICE_GROUP; "
                         "use '' to disable)")
    ap.add_argument("--start", type=int, default=0, metavar="N",
                    help="skip the first N planned checks (resume a run that stopped partway)")
    args = ap.parse_args()

    INPUT_CSV = args.csv
    if args.commit:
        DRY_RUN = False
    if args.dry_run:
        DRY_RUN = True
    if args.through is not None:
        THROUGH_DEVICE_GROUP = args.through

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
    print(f"Dest mode : {DEST_MODE}")
    print(f"Through   : {THROUGH_DEVICE_GROUP or '(none)'}")

    if DEST_MODE == "dest-ip" and not THROUGH_DEVICE_GROUP:
        print("\n!! WARNING: DEST_MODE='dest-ip' with no 'through' hop.")
        print("   An ipv4_dst filter matches the packet's destination field but does NOT")
        print("   localize the destination in the network, so the check may not represent a")
        print("   real end-to-end flow. Prefer DEST_MODE='to', or set a 'through' group.")
        print("   See NQE Reference/Forward_Intent_Check_API.md (Best practice).\n")

    print(f"Planned checks: {len(pairs)}")
    if args.start:
        print(f"Resuming    : skipping first {args.start}")
    print("-" * 70)

    if DRY_RUN:
        print("DRY RUN - no API calls will be made.\n")
        dir_disp = "/" + DIRECTORY.strip("/")
        print(f"Would create directory '{dir_disp}' in network {NETWORK_ID} (each level created in turn).")
        sid = SNAPSHOT_ID or "<latest processed snapshot>"
        print(f"Would POST checks to snapshot {sid} at path '{dir_disp}'.\n")
        shown = 0
        for idx, (src, dst) in enumerate(pairs, 1):
            if idx <= args.start:
                continue
            if shown >= 20:
                break
            payload = build_check(src, dst)
            print(f"URL : {check_url(str(sid), DIRECTORY)}")
            print(f"NAME: {payload['name']}")
            print(f"NOTE: {payload['note']}")
            print(f"BODY: {json.dumps(payload['definition'], separators=(',', ':'))}")
            print()
            shown += 1
        remaining = len(pairs) - args.start - shown
        if remaining > 0:
            print(f"... and {remaining} more (showing first {shown}).")
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

    ok = fail = skipped = 0
    total = len(pairs)
    for i, (src, dst) in enumerate(pairs, 1):
        if i <= args.start:
            skipped += 1
            continue
        payload = build_check(src, dst)
        try:
            status, text = create_check(auth, url, payload)
        except Exception as e:
            # All retries exhausted for this one check: record and keep going.
            fail += 1
            print(f"[{i}/{total}] FAIL (after retries) {payload['name']}\n        {type(e).__name__}: {e}")
            continue
        if 200 <= status < 300:
            ok += 1
            print(f"[{i}/{total}] OK   {payload['name']}")
        else:
            fail += 1
            print(f"[{i}/{total}] FAIL {status}  {payload['name']}\n        {text[:300]}")

    print("-" * 70)
    print(f"Done. Created: {ok}   Failed: {fail}   Skipped: {skipped}   Directory: /{DIRECTORY}")
    if fail:
        print("Some checks failed. Fix the cause, then re-run with --start set past the last success "
              "to avoid duplicates (async creation does not dedupe).")


if __name__ == "__main__":
    main()
