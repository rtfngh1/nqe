#!/usr/bin/env python3
"""
nqe_csv_regression_diff.py

Compare two NQE query CSV exports -- a baseline and a candidate -- and report what
changed, without printing any cell value that could identify a device.

Intended use: you are refactoring an NQE query and need to prove the refactor did
not change the result. Export the CSV before, export it after, run this.

WHY NOT `sort | diff`
---------------------
An NQE comprehension evaluates to a Bag, which is explicitly unordered, so two runs
of the same query emit rows in a different order and a line-based diff is all noise.
Column order and quoting can also vary between exports. This script canonicalises
both files (columns sorted by name, uniform quoting, whitespace trimmed) and then
compares them as multisets, so ordering is irrelevant.

WHAT IT REPORTS
---------------
  1. Row counts, and identical / only-in-baseline / only-in-candidate counts.
  2. Per column, how many paired rows differ in that column. This is the useful
     one: it localises a regression to a single field in one line.
  3. An optional value-level breakdown for columns you nominate as safe to print.

It also distinguishes the two failure modes that are easy to confuse:
  - rows that CHANGED VALUE  -> keys present in both, columns listed as differing
  - rows that DISAPPEARED    -> keys only in baseline, zero columns differing

PRIVACY
-------
Row keys are hashed and never printed. Cell values are printed ONLY for columns you
explicitly list in SAFE_BREAKDOWN_COLUMNS. Choose low-cardinality, non-identifying
columns for that list. The output is intended to be safe to paste into a ticket or
a chat; the input CSVs never need to leave the machine.

REQUIREMENTS
------------
Python 3.8+. Standard library only -- no pip install, no virtualenv.

USAGE
-----
Edit the CONFIG block below, then:

    python nqe_csv_regression_diff.py

Exit codes: 0 = exports equivalent, 1 = differences found, 2 = could not run.
"""

import csv
import hashlib
import os
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# CONFIG -- edit these
# ---------------------------------------------------------------------------

# The two CSV exports to compare. Use a raw string on Windows so backslashes are
# taken literally, e.g. r"C:\exports\baseline.csv".
BASELINE_CSV = r"baseline.csv"
CANDIDATE_CSV = r"candidate.csv"

# Column(s) that uniquely identify a row. Used to PAIR rows between the two files
# so per-column differences can be counted. Values are hashed, never printed.
# Set to [] to skip the per-column analysis and do multiset counts only.
KEY_COLUMNS = ["_id"]

# Columns whose values are safe to PRINT in the summary. Pick low-cardinality
# columns that cannot identify anything -- enum-like fields, flags, prefix
# lengths, record types.
#
# Do NOT list columns holding hostnames, device names, IP addresses, subnets,
# MAC addresses, serial numbers or any composite key built from them.
SAFE_BREAKDOWN_COLUMNS = []

# The per-column analysis holds one entry per row in memory. At around a million
# rows expect a few hundred MB. Lower this to cap memory; the multiset counts in
# section 1 are unaffected and always cover the whole file.
MAX_ROWS_FOR_COLUMN_ANALYSIS = 2_000_000

# Some NQE columns hold long list values, which exceed the csv module default.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# ---------------------------------------------------------------------------

def _h(text):
    """Short stable hash. Used so row identity never has to be held in memory."""
    return int.from_bytes(
        hashlib.blake2b(text.encode("utf-8", "replace"), digest_size=8).digest(),
        "big",
    )


def read_csv(path):
    if not os.path.exists(path):
        raise SystemExit(f"ERROR: file not found: {path}")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.reader(fh)
        try:
            header = next(rdr)
        except StopIteration:
            raise SystemExit(f"ERROR: {path} is empty")
        header = [h.strip() for h in header]
        for row in rdr:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            yield header, row


def canonical(header, row, order):
    """Row as a tuple ordered by sorted column name, whitespace-normalised."""
    lookup = dict(zip(header, row))
    return tuple((lookup.get(c, "") or "").strip() for c in order)


def scan(path):
    """Return (header, column_order, row_hash_multiset, {key_hash: col_hashes}, n)."""
    gen = read_csv(path)
    header, first = next(gen)
    order = sorted(header)
    key_idx = [order.index(c) for c in KEY_COLUMNS if c in order]

    multiset = Counter()
    per_key = {}
    n = 0

    def handle(row):
        nonlocal n
        vals = canonical(header, row, order)
        multiset[_h("\x1f".join(vals))] += 1
        if key_idx and n < MAX_ROWS_FOR_COLUMN_ANALYSIS:
            per_key[_h("\x1f".join(vals[i] for i in key_idx))] = tuple(
                _h(v) for v in vals
            )
        n += 1

    handle(first)
    for _, row in gen:
        handle(row)
    return header, order, multiset, per_key, n


def safe_value_counts(path, columns):
    """value -> count, for the nominated printable columns only."""
    gen = read_csv(path)
    header, first = next(gen)
    idx = {c: header.index(c) for c in columns if c in header}
    out = {c: Counter() for c in idx}

    def handle(row):
        for c, i in idx.items():
            out[c][(row[i] or "").strip()] += 1

    handle(first)
    for _, row in gen:
        handle(row)
    return out


def main():
    print("=" * 74)
    print("NQE CSV regression diff")
    print("=" * 74)
    print(f"baseline : {BASELINE_CSV}")
    print(f"candidate: {CANDIDATE_CSV}\n")

    h1, o1, m1, k1, n1 = scan(BASELINE_CSV)
    h2, o2, m2, k2, n2 = scan(CANDIDATE_CSV)

    if o1 != o2:
        print("COLUMN SET DIFFERS -- everything below is unreliable until this is fixed")
        only1 = [c for c in o1 if c not in o2]
        only2 = [c for c in o2 if c not in o1]
        if only1:
            print(f"  only in baseline : {only1}")
        if only2:
            print(f"  only in candidate: {only2}")
        print()
        return 1

    print(f"columns  : {len(o1)}")
    print(f"rows     : baseline {n1:,}   candidate {n2:,}   delta {n2 - n1:+,}\n")

    removed = m1 - m2
    added = m2 - m1
    n_removed = sum(removed.values())
    n_added = sum(added.values())
    identical = sum((m1 & m2).values())

    print("-" * 74)
    print("1. WHOLE-ROW COMPARISON (order-independent)")
    print("-" * 74)
    print(f"  identical rows        : {identical:,}")
    print(f"  only in baseline      : {n_removed:,}")
    print(f"  only in candidate     : {n_added:,}")
    if n_removed == 0 and n_added == 0:
        print("\n  >>> EXPORTS ARE EQUIVALENT (same rows, any order) <<<")

    if k1 and k2:
        common = k1.keys() & k2.keys()
        gone = len(k1.keys() - k2.keys())
        new = len(k2.keys() - k1.keys())

        col_diffs = Counter()
        changed_rows = 0
        for kh in common:
            a, b = k1[kh], k2[kh]
            if a == b:
                continue
            changed_rows += 1
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    col_diffs[o1[i]] += 1

        print()
        print("-" * 74)
        print(f"2. PAIRED BY {KEY_COLUMNS} (key values hashed, never printed)")
        print("-" * 74)
        print(f"  keys in both          : {len(common):,}")
        print(f"  keys only in baseline : {gone:,}   (rows that DISAPPEARED)")
        print(f"  keys only in candidate: {new:,}   (rows that APPEARED)")
        print(f"  paired rows differing in >=1 column: {changed_rows:,}")
        if col_diffs:
            print("\n  columns that changed, most affected first:")
            width = max(len(c) for c in col_diffs)
            for col, cnt in col_diffs.most_common():
                pct = 100.0 * cnt / max(1, len(common))
                print(f"    {col:<{width}}  {cnt:>10,}  ({pct:5.2f}% of paired rows)")
        elif changed_rows == 0:
            print("\n  no paired row changed in any column")
        if len(k1) >= MAX_ROWS_FOR_COLUMN_ANALYSIS:
            print(f"\n  NOTE: capped at MAX_ROWS_FOR_COLUMN_ANALYSIS "
                  f"({MAX_ROWS_FOR_COLUMN_ANALYSIS:,}); this section is partial.")
    elif KEY_COLUMNS:
        print(f"\n  (section 2 skipped: none of {KEY_COLUMNS} are columns in these files)")

    cols = [c for c in SAFE_BREAKDOWN_COLUMNS if c in o1]
    if cols:
        print()
        print("-" * 74)
        print("3. VALUE BREAKDOWN for the columns you nominated as printable")
        print("-" * 74)
        b1 = safe_value_counts(BASELINE_CSV, cols)
        b2 = safe_value_counts(CANDIDATE_CSV, cols)
        for c in cols:
            keys = sorted(
                set(b1[c]) | set(b2[c]),
                key=lambda v: (-max(b1[c].get(v, 0), b2[c].get(v, 0)), v),
            )
            print(f"\n  {c}")
            print(f"    {'value':<24}{'baseline':>12}{'candidate':>12}{'delta':>12}")
            shown = 0
            for v in keys:
                x, y = b1[c].get(v, 0), b2[c].get(v, 0)
                if x == y and shown >= 12:
                    continue
                flag = "" if x == y else "   <-- moved"
                label = (v if v != "" else "(empty)")[:24]
                print(f"    {label:<24}{x:>12,}{y:>12,}{y - x:>+12,}{flag}")
                shown += 1
            if len(keys) > shown:
                print(f"    ... {len(keys) - shown} unchanged value(s) omitted")
    skipped = [c for c in SAFE_BREAKDOWN_COLUMNS if c not in o1]
    if skipped:
        print(f"\n  (not columns in these files, skipped: {skipped})")

    print()
    print("=" * 74)
    equivalent = n_removed == 0 and n_added == 0
    print("VERDICT: identical" if equivalent else "VERDICT: differences found")
    print("No row keys or unnominated cell values were printed above.")
    print("=" * 74)
    return 0 if equivalent else 1


if __name__ == "__main__":
    sys.exit(main())
