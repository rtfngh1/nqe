#!/usr/bin/env python3
"""
Forward Networks - Posture Matrix first-hop device/VRF discovery (streaming).

PURPOSE
  When you define a Forward "posture" (isolation) resource pool you must ground
  it to specific VRFs and devices rather than "any/any". This script discovers,
  from real path searches, which device(s) and VRF(s) actually own the subnets
  you care about, so you can scope a resource pool to just those.

HOW IT WORKS
  1. Read a CSV that (among other columns) has:  Environment, ip, subnet
     Rows are classified DEV vs PROD by the "Environment" value
     (see DEV_ENVIRONMENTS / PROD_ENVIRONMENTS below - same convention as
     forward_isolation_intent_checks.py).
  2. For every cross-class ordered pair of *subnets* (DEV subnet -> PROD subnet
     AND PROD subnet -> DEV subnet), issue a path search. Because we loop both
     directions, every subnet gets to be the SOURCE against every subnet on the
     other side.
  3. Each path search may return many paths (ECMP / multiple candidates). For
     EVERY returned path we take the FIRST HOP - the device where the source
     subnet's traffic enters the network - and the VRF on that hop's
     subnet-facing interface. The first hop always belongs to the SOURCE subnet
     of that search, so we attribute (first-hop device, first-hop VRF) to the
     source subnet. Across the N returned paths there may be several distinct
     first hops; we tally them all, ranked by how often each appears.
  4. We aggregate the results several ways and write CSVs (see write_outputs).

TRANSPORT (why streaming)
  Uses the streaming bulk endpoint:
      POST /api/networks/{networkId}/paths-bulk-seq
  It returns an RFC 7464 JSON text sequence - one result per query, each framed
  by an ASCII Record Separator (0x1E) and a Line Feed (0x0A), in query order.
  Because results stream back incrementally, the connection keeps sending bytes
  and idle timeouts on intermediary load balancers don't trip (the failure mode
  that closes a long single /paths-bulk response with "Remote end closed
  connection without response"). VRF requires includeNetworkFunctions=true
  (hop.networkFunctions.*.l3.vrf).

RESILIENCE
  - Every completed query is appended to OUTPUT_DIR/checkpoint.jsonl (fsync'd).
  - A dropped/stalled connection is retried with exponential backoff; only the
    queries not yet completed in that batch are re-sent.
  - Re-running RESUMES from the checkpoint (skips already-done queries).
    Use --fresh to ignore/overwrite it, or --rebuild to regenerate the CSVs
    from an existing checkpoint without making any API calls.
  - Aggregate CSVs are rewritten after every batch, so partial results are
    always available.

  Only the Python standard library is used (no pip installs).

USAGE
  1. Fill in the CONFIG block below (or override via env vars / CLI flags).
  2. Dry run first (default) to see the query plan and make no API calls:
         python3 forward_posture_matrix_pathsearch.py hosts.csv
  3. When satisfied, run for real:
         python3 forward_posture_matrix_pathsearch.py hosts.csv --commit
  4. If it stops, just re-run the same command to resume; or rebuild CSVs:
         python3 forward_posture_matrix_pathsearch.py hosts.csv --rebuild
  5. Tune per run:
         --bulk-size 100 --max-results 100 --max-seconds 300 \
         --max-overall-seconds 7200 --max-candidates 10000 --max-retries 5
"""

import argparse
import base64
import csv
import http.client
import ipaddress
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

# ============================================================================
# CONFIG  (edit these, or override with env vars / CLI flags)
# ============================================================================

# --- API credentials & target -----------------------------------------------
BASE_URL   = "https://fwd.app"     # Forward instance base URL (no trailing /api)
API_KEY    = ""                     # API access key  (or username)  [env: FWD_API_KEY]
API_SECRET = ""                     # API secret key  (or password)  [env: FWD_API_SECRET]
NETWORK_ID = "159020"               # Forward network ID              [env: FWD_NETWORK_ID]

# Snapshot to search. Leave None to auto-resolve the latest processed snapshot
# for NETWORK_ID.                                                    [env: FWD_SNAPSHOT_ID]
SNAPSHOT_ID = None

# --- Environment classification (case-insensitive, exact membership) ---------
DEV_ENVIRONMENTS  = {"dev", "test", "qa"}
PROD_ENVIRONMENTS = {"prod", "production", "prod2"}

# --- Path search behavior ----------------------------------------------------
# maxResults: how many paths each search returns. Higher = more distinct first
#   hops captured (ECMP / multiple attachment points). Range 1-maxCandidates.
MAX_RESULTS      = 200
# maxCandidates: results computed before ranking. Range 1-10000.
MAX_CANDIDATES   = 10000
# Per-query timeout (seconds). Range 1-300.
MAX_SECONDS      = 300
# Overall timeout for one bulk request (seconds). Range 1-7200 (7200 = max).
MAX_OVERALL_SECONDS = 7200
# Search intent: PREFER_DELIVERED | PREFER_VIOLATIONS | VIOLATIONS_ONLY
INTENT           = "PREFER_DELIVERED"

# --- Bulk / transport tuning -------------------------------------------------
BULK_SIZE    = 100      # queries per streaming POST (tune if you hit limits)
VERIFY_TLS   = True     # set False only for self-signed on-prem instances
# Per-read (inactivity) socket timeout in seconds. Because results stream in,
# the gap between records is roughly one query's compute budget; a value a bit
# above MAX_SECONDS catches a genuine stall without waiting for the whole run.
# None -> auto (MAX_SECONDS + 60).
HTTP_TIMEOUT = None

# --- Retry on connection drop ------------------------------------------------
MAX_RETRIES  = 5        # attempts per batch before giving up on its remainder
BACKOFF_BASE = 2.0      # seconds; delay = BACKOFF_BASE * 2**(attempt-1)
BACKOFF_MAX  = 60.0     # cap on backoff delay

# --- IO ----------------------------------------------------------------------
INPUT_CSV  = "hosts.csv"            # first CLI arg overrides this
OUTPUT_DIR = "posture_matrix_out"   # CSVs + checkpoint are written here

# Safety: dry run prints the query plan and makes no API calls.
DRY_RUN = True

# ============================================================================
# End of CONFIG
# ============================================================================

# HTTP statuses worth retrying (transient / snapshot-processing / throttling).
RETRYABLE_STATUS = {409, 429, 500, 502, 503, 504}


class StreamError(Exception):
    """Raised when the JSON-seq stream is truncated or a record won't parse;
    treated as a retryable transport failure."""


# Connection-level failures we retry. ConnectionError covers
# RemoteDisconnected / ConnectionReset / ConnectionAborted.
RETRYABLE_EXC = (
    ConnectionError,
    http.client.RemoteDisconnected,
    http.client.IncompleteRead,
    socket.timeout,
    TimeoutError,
    StreamError,
)


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


def http(method, url, auth_header, body=None, timeout=None):
    """Minimal JSON HTTP helper for non-streaming calls (snapshot resolve).
    Returns (status_code, text)."""
    data = None
    headers = {"Authorization": auth_header, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx(),
                                    timeout=timeout or 60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def load_subnets(path):
    """
    Read the CSV and return two lists of dicts (dev, prod), each row:
        {"env": <raw Environment>, "subnet": <CIDR/IP string>}
    The 'subnet' column is used as the search endpoint. Duplicate subnets within
    the same class are de-duplicated, keeping the first Environment label seen.
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
        subnet_c = col("subnet", "cidr")
        if env_c is None:
            raise SystemExit("ERROR: CSV must contain an 'Environment' column.")
        if subnet_c is None:
            raise SystemExit("ERROR: CSV must contain a 'subnet' column.")

        dev, prod = {}, {}
        skipped, ignored = 0, 0
        for raw in reader:
            env = _norm(raw.get(env_c))
            subnet = _norm(raw.get(subnet_c))
            if not subnet:
                skipped += 1
                continue
            cls = classify(env)
            if cls == "dev":
                dev.setdefault(subnet, env)
            elif cls == "prod":
                prod.setdefault(subnet, env)
            else:
                ignored += 1
        if skipped:
            print(f"  (skipped {skipped} row(s) with a blank subnet)")
        if ignored:
            print(f"  (ignored {ignored} row(s) whose Environment was neither "
                  f"dev-class nor prod-class)")

    dev_rows  = [{"env": e, "subnet": s} for s, e in dev.items()]
    prod_rows = [{"env": e, "subnet": s} for s, e in prod.items()]
    return dev_rows, prod_rows


def classify(env):
    e = env.strip().lower()
    if e in {x.lower() for x in DEV_ENVIRONMENTS}:
        return "dev"
    if e in {x.lower() for x in PROD_ENVIRONMENTS}:
        return "prod"
    return None


# ---------------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------------

def build_queries(dev_rows, prod_rows):
    """Yield one meta-record per ordered cross-class subnet pair, both
    directions. The first hop of each search belongs to the SOURCE subnet."""
    out = []
    for d in dev_rows:
        for p in prod_rows:
            if d["subnet"] != p["subnet"]:
                out.append({"src": d["subnet"], "src_env": d["env"], "src_class": "dev",
                            "dst": p["subnet"], "dst_env": p["env"], "dst_class": "prod"})
            if p["subnet"] != d["subnet"]:
                out.append({"src": p["subnet"], "src_env": p["env"], "src_class": "prod",
                            "dst": d["subnet"], "dst_env": d["env"], "dst_class": "dev"})
    return out


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def resolve_snapshot(auth_header):
    if SNAPSHOT_ID:
        return str(SNAPSHOT_ID)
    url = f"{BASE_URL}/api/networks/{NETWORK_ID}/snapshots/latestProcessed"
    status, text = http("GET", url, auth_header, timeout=60)
    if status != 200:
        raise SystemExit(f"ERROR resolving latest snapshot ({status}): {text}")
    sid = json.loads(text).get("id")
    if not sid:
        raise SystemExit(f"ERROR: latestProcessed returned no snapshot id: {text}")
    return str(sid)


def _seq_url(snapshot_id):
    qs = urllib.parse.urlencode({"snapshotId": snapshot_id}) if snapshot_id else ""
    base = f"{BASE_URL}/api/networks/{NETWORK_ID}/paths-bulk-seq"
    return f"{base}?{qs}" if qs else base


def iter_json_seq(resp, chunk_size=65536):
    """Yield parsed JSON objects from an RFC 7464 json-seq HTTP response.
    Each record is framed as: RS (0x1E) <json> LF (0x0A). We split on RS; every
    segment except the trailing (possibly incomplete) one is a complete record.
    A malformed complete record indicates truncation -> StreamError."""
    buf = b""
    while True:
        try:
            piece = resp.read(chunk_size)
        except http.client.IncompleteRead as e:
            piece = e.partial
            if not piece:
                break
        if not piece:
            break
        buf += piece
        parts = buf.split(b"\x1e")
        buf = parts.pop()               # keep trailing (maybe partial) record
        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                yield json.loads(part.decode("utf-8", "replace"))
            except json.JSONDecodeError as e:
                raise StreamError(f"bad record: {e}")
    tail = buf.strip()
    if tail:
        for seg in tail.split(b"\x1e"):
            seg = seg.strip()
            if not seg:
                continue
            try:
                yield json.loads(seg.decode("utf-8", "replace"))
            except json.JSONDecodeError as e:
                raise StreamError(f"bad final record: {e}")


def stream_bulk_seq(auth_header, snapshot_id, queries):
    """Generator yielding (query, result_obj) pairs in order as they stream."""
    body = {
        "queries": [{"srcIp": q["src"], "dstIp": q["dst"]} for q in queries],
        "intent": INTENT,
        "maxResults": MAX_RESULTS,
        "maxCandidates": MAX_CANDIDATES,
        "maxSeconds": MAX_SECONDS,
        "maxOverallSeconds": MAX_OVERALL_SECONDS,
        "includeNetworkFunctions": True,   # required for VRF
    }
    data = json.dumps(body).encode("utf-8")
    headers = {"Authorization": auth_header,
               "Content-Type": "application/json",
               "Accept": "application/json-seq"}
    req = urllib.request.Request(_seq_url(snapshot_id), data=data,
                                 method="POST", headers=headers)
    read_timeout = HTTP_TIMEOUT or (MAX_SECONDS + 60)
    resp = urllib.request.urlopen(req, context=_ssl_ctx(), timeout=read_timeout)
    try:
        for q, obj in zip(queries, iter_json_seq(resp)):
            yield q, obj
    finally:
        try:
            resp.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def first_hop_vrf(hop):
    """VRF on the subnet-facing interface of a first hop: prefer ingress
    (where the source subnet's traffic entered), fall back to egress."""
    nf = (hop or {}).get("networkFunctions") or {}
    for side in ("ingress", "egress"):
        l3 = (nf.get(side) or {}).get("l3") or {}
        vrf = l3.get("vrf")
        if vrf:
            return vrf
    return None


def parse_result(result):
    """Given one PathSearchResponse (or error object), return
    (paths_info, error_text). paths_info: list of per-path first-hop dicts."""
    if isinstance(result, dict) and result.get("error"):
        msg = result.get("message") or result.get("reason") or json.dumps(result)[:200]
        return [], f"query error: {msg}"
    info = (result or {}).get("info") or {}
    paths = info.get("paths") or []
    timed_out = bool((result or {}).get("timedOut"))
    out = []
    for p in paths:
        hops = p.get("hops") or []
        if not hops:
            continue
        fh = hops[0]
        out.append({
            "device": fh.get("deviceName") or "",
            "display": fh.get("displayName") or "",
            "vrf": first_hop_vrf(fh) or "",
            "outcome": p.get("forwardingOutcome") or "",
            "security": p.get("securityOutcome") or "",
            "hop_count": len(hops),
        })
    err = ""
    if not paths:
        err = "timed out (0 paths)" if timed_out else "0 paths"
    return out, err


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class Aggregator:
    """Accumulates first-hop findings keyed by the SOURCE subnet."""

    def __init__(self):
        self.subnets = {}
        self.raw = []   # one row per returned path (audit)

    def _slot(self, subnet, env, cls):
        s = self.subnets.get(subnet)
        if s is None:
            s = {"env": env, "class": cls,
                 "dv": defaultdict(int),     # (device, vrf) -> path count
                 "dev": defaultdict(int),    # device -> path count
                 "vrf": defaultdict(int),    # vrf -> path count
                 "dests": set(), "paths": 0}
            self.subnets[subnet] = s
        return s

    def add(self, q, paths_info):
        s = self._slot(q["src"], q["src_env"], q["src_class"])
        s["dests"].add(q["dst"])
        for idx, p in enumerate(paths_info):
            s["paths"] += 1
            s["dv"][(p["device"], p["vrf"])] += 1
            s["dev"][p["device"]] += 1
            s["vrf"][p["vrf"]] += 1
            self.raw.append({
                "source_subnet": q["src"], "source_env": q["src_env"],
                "source_class": q["src_class"],
                "dest_subnet": q["dst"], "dest_env": q["dst_env"],
                "dest_class": q["dst_class"],
                "path_index": idx,
                "first_hop_device": p["device"],
                "first_hop_display": p["display"],
                "first_hop_vrf": p["vrf"],
                "forwarding_outcome": p["outcome"],
                "security_outcome": p["security"],
                "hop_count": p["hop_count"],
            })


# ---------------------------------------------------------------------------
# Run bookkeeping: checkpoint + retryable batch processing
# ---------------------------------------------------------------------------

class Runner:
    """Feeds streamed results into the aggregator and checkpoints each one."""

    def __init__(self, agg, cp_file, errors=None):
        self.agg = agg
        self.cp = cp_file          # append-mode file handle, or None
        self.errors = list(errors or [])

    def _checkpoint(self, q, paths_info, err):
        if self.cp is None:
            return
        self.cp.write(json.dumps({"q": q, "paths": paths_info, "err": err}) + "\n")
        self.cp.flush()
        try:
            os.fsync(self.cp.fileno())
        except (OSError, ValueError):
            pass

    def handle_result(self, q, result):
        paths_info, err = parse_result(result)
        self.agg.add(q, paths_info)
        if err:
            self.errors.append((q["src"], q["dst"], err))
        self._checkpoint(q, paths_info, err)

    def handle_error(self, q, msg, persist=True):
        self.agg.add(q, [])
        self.errors.append((q["src"], q["dst"], msg))
        if persist:
            self._checkpoint(q, [], msg)


def process_batch(auth, snapshot_id, batch, runner, label=""):
    """Stream one batch, retrying only the not-yet-completed remainder on drop.
    Returns True if every query in the batch was resolved."""
    remaining = list(batch)
    attempt = 0
    while remaining:
        attempt += 1
        consumed = 0
        try:
            for q, result in stream_bulk_seq(auth, snapshot_id, remaining):
                runner.handle_result(q, result)
                consumed += 1
            remaining = remaining[consumed:]
            if not remaining:
                return True
            print(f"    {label} stream ended early ({consumed} this attempt); "
                  f"{len(remaining)} remaining")
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if e.code not in RETRYABLE_STATUS:
                print(f"    {label} HTTP {e.code} (non-retryable): {body}")
                for q in remaining:
                    runner.handle_error(q, f"HTTP {e.code}: {body}")
                return False
            print(f"    {label} HTTP {e.code} (retryable): {body}")
        except RETRYABLE_EXC as e:
            remaining = remaining[consumed:]
            print(f"    {label} connection issue after {consumed} result(s): "
                  f"{type(e).__name__}: {e}")
        except urllib.error.URLError as e:
            remaining = remaining[consumed:]
            print(f"    {label} URL error after {consumed}: {e}")

        if attempt >= MAX_RETRIES:
            print(f"    {label} giving up after {attempt} attempts; "
                  f"{len(remaining)} queries unresolved (will retry on re-run)")
            for q in remaining:
                # don't persist -> a re-run will retry these
                runner.handle_error(q, f"unresolved after {attempt} attempts",
                                    persist=False)
            return False
        delay = min(BACKOFF_BASE * (2 ** (attempt - 1)), BACKOFF_MAX)
        print(f"    {label} retrying in {delay:.0f}s "
              f"(attempt {attempt + 1}/{MAX_RETRIES})")
        time.sleep(delay)
    return True


def load_checkpoint(cp_path, agg):
    """Replay a checkpoint into the aggregator. Returns (done_set, errors)."""
    done = set()
    errors = []
    if not os.path.exists(cp_path):
        return done, errors
    with open(cp_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = rec["q"]
            agg.add(q, rec.get("paths") or [])
            if rec.get("err"):
                errors.append((q["src"], q["dst"], rec["err"]))
            done.add((q["src"], q["dst"]))
    return done, errors


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def _write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def write_outputs(agg, outdir, verbose=True):
    os.makedirs(outdir, exist_ok=True)

    # 1. per-subnet first hops: one row per (subnet, device, vrf)
    rows = []
    for subnet, s in sorted(agg.subnets.items()):
        for (device, vrf), cnt in sorted(s["dv"].items(),
                                         key=lambda kv: (-kv[1], kv[0])):
            share = round(cnt / s["paths"], 4) if s["paths"] else 0
            rows.append([subnet, s["env"], s["class"], device, vrf, cnt,
                         s["paths"], share, len(s["dests"])])
    _write(os.path.join(outdir, "per_subnet_first_hops.csv"),
           ["subnet", "environment", "class", "first_hop_device",
            "first_hop_vrf", "path_count", "subnet_total_paths",
            "share_of_paths", "dest_subnets_searched"], rows)

    # 2. per-class pool aggregates (grounding for a single "all dev" pool etc.)
    for cls in ("dev", "prod"):
        dev_c = defaultdict(int)
        vrf_c = defaultdict(int)
        dev_subnets = defaultdict(set)
        vrf_subnets = defaultdict(set)
        for subnet, s in agg.subnets.items():
            if s["class"] != cls:
                continue
            for d, c in s["dev"].items():
                dev_c[d] += c
                dev_subnets[d].add(subnet)
            for v, c in s["vrf"].items():
                vrf_c[v] += c
                vrf_subnets[v].add(subnet)
        drows = [[d, dev_c[d], len(dev_subnets[d]),
                  ";".join(sorted(dev_subnets[d]))]
                 for d in sorted(dev_c, key=lambda k: (-dev_c[k], k))]
        _write(os.path.join(outdir, f"pool_{cls}_devices.csv"),
               ["first_hop_device", "path_count", "subnet_count", "subnets"], drows)
        vrows = [[v, vrf_c[v], len(vrf_subnets[v]),
                  ";".join(sorted(vrf_subnets[v]))]
                 for v in sorted(vrf_c, key=lambda k: (-vrf_c[k], k))]
        _write(os.path.join(outdir, f"pool_{cls}_vrfs.csv"),
               ["first_hop_vrf", "path_count", "subnet_count", "subnets"], vrows)

    # 3. by-device pivot: device -> subnets, vrfs, classes
    dev_subnets = defaultdict(set)
    dev_vrfs    = defaultdict(set)
    dev_classes = defaultdict(set)
    dev_paths   = defaultdict(int)
    for subnet, s in agg.subnets.items():
        for (device, vrf), cnt in s["dv"].items():
            dev_subnets[device].add(subnet)
            if vrf:
                dev_vrfs[device].add(vrf)
            dev_classes[device].add(s["class"])
            dev_paths[device] += cnt
    rows = [[d, ";".join(sorted(dev_classes[d])), len(dev_subnets[d]),
             len(dev_vrfs[d]), dev_paths[d],
             ";".join(sorted(dev_vrfs[d])), ";".join(sorted(dev_subnets[d]))]
            for d in sorted(dev_subnets, key=lambda k: (-dev_paths[k], k))]
    _write(os.path.join(outdir, "by_device.csv"),
           ["device", "classes", "subnet_count", "vrf_count", "path_count",
            "vrfs", "subnets"], rows)

    # 4. by-vrf pivot: vrf -> subnets, devices, classes
    vrf_subnets = defaultdict(set)
    vrf_devices = defaultdict(set)
    vrf_classes = defaultdict(set)
    vrf_paths   = defaultdict(int)
    for subnet, s in agg.subnets.items():
        for (device, vrf), cnt in s["dv"].items():
            vrf_subnets[vrf].add(subnet)
            vrf_devices[vrf].add(device)
            vrf_classes[vrf].add(s["class"])
            vrf_paths[vrf] += cnt
    rows = [[v or "<none>", ";".join(sorted(vrf_classes[v])),
             len(vrf_subnets[v]), len(vrf_devices[v]), vrf_paths[v],
             ";".join(sorted(vrf_devices[v])), ";".join(sorted(vrf_subnets[v]))]
            for v in sorted(vrf_subnets, key=lambda k: (-vrf_paths[k], str(k)))]
    _write(os.path.join(outdir, "by_vrf.csv"),
           ["vrf", "classes", "subnet_count", "device_count", "path_count",
            "devices", "subnets"], rows)

    # 5. raw audit
    _write(os.path.join(outdir, "raw_first_hops.csv"),
           ["source_subnet", "source_env", "source_class", "dest_subnet",
            "dest_env", "dest_class", "path_index", "first_hop_device",
            "first_hop_display", "first_hop_vrf", "forwarding_outcome",
            "security_outcome", "hop_count"],
           [[r["source_subnet"], r["source_env"], r["source_class"],
             r["dest_subnet"], r["dest_env"], r["dest_class"], r["path_index"],
             r["first_hop_device"], r["first_hop_display"], r["first_hop_vrf"],
             r["forwarding_outcome"], r["security_outcome"], r["hop_count"]]
            for r in agg.raw])
    if verbose:
        print(f"  CSVs updated in ./{outdir}/ "
              f"({len(agg.subnets)} subnets, {len(agg.raw)} first-hop paths)")


def write_errors(errors, outdir):
    os.makedirs(outdir, exist_ok=True)
    _write(os.path.join(outdir, "search_errors.csv"),
           ["source_subnet", "dest_subnet", "detail"],
           [[e[0], e[1], e[2]] for e in errors])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _validate_subnet(v):
    try:
        if "/" in v:
            ipaddress.ip_network(v, strict=False)
        else:
            ipaddress.ip_address(v)
        return True
    except ValueError:
        return False


def main():
    global DRY_RUN, INPUT_CSV, API_KEY, API_SECRET, NETWORK_ID, SNAPSHOT_ID
    global BULK_SIZE, MAX_RESULTS, MAX_CANDIDATES, MAX_SECONDS
    global MAX_OVERALL_SECONDS, MAX_RETRIES, OUTPUT_DIR

    ap = argparse.ArgumentParser(
        description="Discover first-hop devices/VRFs per subnet for posture "
                    "resource-pool grounding, via Forward streaming bulk path "
                    "search (resumable).")
    ap.add_argument("csv", nargs="?", default=INPUT_CSV, help="input CSV path")
    ap.add_argument("--commit", action="store_true",
                    help="actually run path searches (disables dry run)")
    ap.add_argument("--dry-run", action="store_true", help="force dry run (default)")
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild CSVs from an existing checkpoint; no API calls")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore/overwrite any existing checkpoint and start over")
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--bulk-size", type=int, default=None,
                    help=f"queries per streaming POST (default {BULK_SIZE})")
    ap.add_argument("--max-results", type=int, default=None,
                    help=f"paths returned per search (default {MAX_RESULTS})")
    ap.add_argument("--max-candidates", type=int, default=None,
                    help=f"candidates before ranking (default {MAX_CANDIDATES})")
    ap.add_argument("--max-seconds", type=int, default=None,
                    help=f"per-query timeout (default {MAX_SECONDS})")
    ap.add_argument("--max-overall-seconds", type=int, default=None,
                    help=f"per-request timeout (default {MAX_OVERALL_SECONDS})")
    ap.add_argument("--max-retries", type=int, default=None,
                    help=f"retries per batch on drop (default {MAX_RETRIES})")
    ap.add_argument("--snapshot-id", default=None, help="override snapshot id")
    args = ap.parse_args()

    INPUT_CSV = args.csv
    if args.commit:
        DRY_RUN = False
    if args.dry_run:
        DRY_RUN = True
    if args.out is not None:
        OUTPUT_DIR = args.out
    if args.bulk_size is not None:
        BULK_SIZE = args.bulk_size
    if args.max_results is not None:
        MAX_RESULTS = args.max_results
    if args.max_candidates is not None:
        MAX_CANDIDATES = args.max_candidates
    if args.max_seconds is not None:
        MAX_SECONDS = args.max_seconds
    if args.max_overall_seconds is not None:
        MAX_OVERALL_SECONDS = args.max_overall_seconds
    if args.max_retries is not None:
        MAX_RETRIES = args.max_retries

    API_KEY    = os.environ.get("FWD_API_KEY", API_KEY)
    API_SECRET = os.environ.get("FWD_API_SECRET", API_SECRET)
    NETWORK_ID = os.environ.get("FWD_NETWORK_ID", NETWORK_ID)
    SNAPSHOT_ID = args.snapshot_id or os.environ.get("FWD_SNAPSHOT_ID", SNAPSHOT_ID)

    cp_path = os.path.join(OUTPUT_DIR, "checkpoint.jsonl")

    # --- rebuild-only: no CSV read of queries, just replay checkpoint ---
    if args.rebuild:
        agg = Aggregator()
        done, errors = load_checkpoint(cp_path, agg)
        if not done:
            raise SystemExit(f"No checkpoint at {cp_path} to rebuild from.")
        write_outputs(agg, OUTPUT_DIR)
        write_errors(errors, OUTPUT_DIR)
        print(f"Rebuilt CSVs from {len(done)} checkpointed queries.")
        return

    print(f"Input CSV : {INPUT_CSV}")
    dev_rows, prod_rows = load_subnets(INPUT_CSV)
    print(f"DEV subnets: {len(dev_rows)}   PROD subnets: {len(prod_rows)}")
    if not dev_rows or not prod_rows:
        raise SystemExit("Nothing to do: need at least one DEV subnet and one "
                         "PROD subnet.")

    bad = [r["subnet"] for r in (dev_rows + prod_rows)
           if not _validate_subnet(r["subnet"])]
    if bad:
        print(f"  WARNING: {len(bad)} subnet value(s) don't parse as IP/CIDR "
              f"and may be rejected: {bad[:5]}{'...' if len(bad) > 5 else ''}")

    all_queries = build_queries(dev_rows, prod_rows)
    print(f"Planned searches: {len(all_queries)}  "
          f"(both directions across {len(dev_rows)}x{len(prod_rows)} pairs)")
    print(f"Bulk size: {BULK_SIZE}   maxResults={MAX_RESULTS} "
          f"maxCandidates={MAX_CANDIDATES} maxSeconds={MAX_SECONDS} "
          f"maxOverallSeconds={MAX_OVERALL_SECONDS} intent={INTENT}")
    print(f"Endpoint  : {_seq_url(SNAPSHOT_ID or '<latest processed>')}")
    print("-" * 70)

    if DRY_RUN:
        print("DRY RUN - no API calls will be made.\n")
        for q in all_queries[:10]:
            print(f"  {q['src_class']:>4} {q['src']:<20} -> "
                  f"{q['dst_class']:<4} {q['dst']}")
        if len(all_queries) > 10:
            print(f"  ... and {len(all_queries) - 10} more.")
        print(f"\nWould stream to {_seq_url(SNAPSHOT_ID or '<latest processed>')}")
        print(f"Would checkpoint to ./{cp_path} and write CSVs to ./{OUTPUT_DIR}/")
        print("\nRe-run with --commit to execute the searches.")
        return

    # --- Commit path ---
    if not API_KEY or not API_SECRET:
        raise SystemExit("ERROR: API_KEY/API_SECRET are required to commit "
                         "(set in CONFIG or via FWD_API_KEY / FWD_API_SECRET).")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    agg = Aggregator()
    prior_errors = []
    if args.fresh and os.path.exists(cp_path):
        os.remove(cp_path)
        print("Fresh run: removed existing checkpoint.")
    done = set()
    if os.path.exists(cp_path):
        done, prior_errors = load_checkpoint(cp_path, agg)
        print(f"Resuming: {len(done)} queries already in checkpoint "
              f"({len(agg.raw)} first-hop paths replayed).")

    queries = [q for q in all_queries if (q["src"], q["dst"]) not in done]
    print(f"Remaining to search: {len(queries)}")
    if not queries:
        write_outputs(agg, OUTPUT_DIR)
        write_errors(prior_errors, OUTPUT_DIR)
        print("Nothing left to do; CSVs rebuilt from checkpoint.")
        return

    auth = _basic_auth_header(API_KEY, API_SECRET)
    snapshot_id = resolve_snapshot(auth)
    print(f"Snapshot  : {snapshot_id}")
    print("-" * 70)

    cp = open(cp_path, "a", encoding="utf-8")
    runner = Runner(agg, cp, errors=prior_errors)
    batches = list(chunk(queries, BULK_SIZE))
    try:
        for bi, batch in enumerate(batches, 1):
            label = f"[batch {bi}/{len(batches)}]"
            before = len(agg.raw)
            ok = process_batch(auth, snapshot_id, batch, runner, label)
            got = len(agg.raw) - before
            print(f"{label} {'ok' if ok else 'PARTIAL'}: "
                  f"{len(batch)} queries, {got} first-hop paths")
            write_outputs(agg, OUTPUT_DIR)
            write_errors(runner.errors, OUTPUT_DIR)
    finally:
        cp.close()

    print("-" * 70)
    print(f"Done. Subnets with findings: {len(agg.subnets)}   "
          f"Total first-hop paths: {len(agg.raw)}   "
          f"Queries with no/failed result: {len(runner.errors)}")
    print(f"CSVs + checkpoint in ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
