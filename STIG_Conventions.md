# STIG Project Conventions

Living document — refined as the project evolves. Sections marked **(provisional)**
have not yet been exercised in production and may change; sections marked
**(settled)** have been confirmed by code that runs or by direct user verification.

When this document conflicts with an earlier conversation handover, this document
wins for forward-looking work. The handover briefs (`STIG_Findings_Handover.md`
and its delta) remain the authoritative record of *why* decisions were made.

---

## 1. Scope and intent (settled)

The project forks Forward's stock `STIG Findings` NQE query down to a small set
of STIG rules (initial: V228860, V228877, V228658 — all Palo Alto Networks),
adds per-device exemptions, per-rule logic overrides, and a chassis-level
rollup. The fork lives in the org repo, not the Forward Library.

**Fork vs. import-and-wrap is a settled decision — do not re-litigate.** It is
tempting to suggest importing `@fwd/Security/STIGs/STIG Findings` and calling
its exported `deviceStigResults(device)` to inherit all 1,929 stock rules in
one line. That approach is rejected because the stock query does its own
bare-path imports of every per-rule module, so per-rule logic overrides
(`Overrides/...`) would be bypassed for any rule that's been overridden. The
explicit-listing fork is the price of having a working override mechanism.

Juniper is out of scope. The four Junos override flags accepted by
`deviceStigResultsInternal` are hard-coded to `false` at the call site in the
forked main query.

---

## 2. File layout (settled)

```
Projects/STIGs/
├── Custom STIG Findings           Main executable query (the fork).
├── Configuration                  Exemption DATA only. No logic.
├── Utils                          Exemption HELPERS (isExempt, exemptionReason).
└── Overrides/                     Per-rule logic overrides. Mirrors the
    └── {VendorPath}/{RuleName}    Forward Library tree file-for-file.
```

For the three current STIGs, the override paths are:

```
Overrides/Palo Alto Networks/PAN_OS Application Layer Gateway/PANW-AG-000102 V-228860
Overrides/Palo Alto Networks/PAN_OS Application Layer Gateway/PANW-AG-000143 V-228877
Overrides/Palo Alto Networks/PAN_OS NDM/PANW-NM-000069 V-228658
```

**Naming rule:** Override paths under `Overrides/` mirror the upstream Forward
Library path **exactly** — same folder names, same filename. The override's
import path differs from the stock import path only by the leading
`Overrides/` and (in the importing query) the `@fwd/` ↔ `Overrides/` swap. See
§5 ("Stock-vs-override switch").

---

## 3. The `@fwd/` import rule (settled)

This is the single most common cause of confusing import errors. Memorize it.

- **Org-repo queries** importing a Forward Library module: prefix is **required**.
  - ✅ `import "@fwd/Security/STIGs/Device Parameters";`
  - ❌ `import "Security/STIGs/Device Parameters";` — fails to resolve.
- **Forward Library files importing siblings** (what you see in `queries-export.proto`):
  prefix is **omitted**. These are bare paths.

**Never copy import lines verbatim** from `queries-export.proto` or any Forward
Library file into org-repo code. Prepend `@fwd/` to each.

This rule is documented in `NQE_Idioms_and_Patterns.md` §14 and
`NQE_Syntax_and_Logic.md` §14 (corrected in this thread).

---

## 4. Override file structure (settled)

Every override file follows the same skeleton. The structural parts are
non-negotiable; only the body of `isVulnerable` changes per rule.

```nqe
/**
 * @intent OVERRIDE of stock {RULE_VERSION} {VULN_ID}.
 * @description Brief reason this override exists (customer-specific threshold,
 *   real check vs stock Not-Reviewed stub, etc).
 *
 * Contract preserved from the stock file:
 *   - exports ruleData{VULN_ID_NO_DASH}
 *   - exports isVulnerable{VULN_ID_NO_DASH}(params: StigParameters, config: List<ConfigLine>) : Bool
 *   - same ruleData record shape (only the `skipped` flag may differ)
 *   - never builds its own result record — caller routes through deviceStigResult
 */

import "@fwd/Security/STIGs/Device Parameters";
import "@fwd/Security/STIGs/Rule Datas";
// Add any additional @fwd/ imports the stock file used (e.g. Cisco/Common).

// --- Override begins here ---

isVulnerable(params: StigParameters, config: List<ConfigLine>) : Bool =
  // TODO: real check. Return true if violated, false if compliant.
  true;

// --- Required exports (signatures identical to stock) ---

// Flip `skipped` to false to make the rule report a real pass/fail.
// Leave it true only if the override's intent is to keep the rule
// in Not-Reviewed state but adjust some other field.
export ruleData{VULN_ID_NO_DASH} =
  getRuleData("{STIG_NAME}", "{STIG_VERSION}", "{VULN_ID}", false);

export isVulnerable{VULN_ID_NO_DASH}(params: StigParameters,
                                     config: List<ConfigLine>) : Bool =
  isVulnerable(params, config);

// ---------------------------------------------------------------------------
// Standalone test scaffold (matches Forward Library file convention).
// When this file is run directly in the NQE Library IDE, the bare `g()` at the
// bottom emits one row per matching device with the violation result. When the
// file is imported by another query, only the `export`s above are visible and
// the scaffold is inert.
//
// The `{}` passed to `f` is a placeholder — `f` immediately rebinds `params`
// via getResolvedStigParameters, so the value is discarded.
// ---------------------------------------------------------------------------

f(params) =
  foreach device in network.devices
  where isPresent(device.files.config)
  where device.platform.os == OS.{PAN_OS_OR_OTHER}
  let policy = network.stigDatabase.policy
  let defaultParameters = network.stigDatabase.defaultParameters
  let params = getResolvedStigParameters(device, policy, defaultParameters)
  select stigRuleRecord(device, isVulnerable(params, device.files.config));

g() = f({});

g()
```

### Rules for overrides

1. **Keep every export's parameter list AND return type identical to stock.**
   `isVulnerable{ID}` must still return `Bool`. The compiler does not enforce
   the contract — discipline does.
2. **Keep every field of any overridden `ruleData` record.** Adding fields is
   safe; removing is not. (Currently overrides go through `getRuleData`, which
   returns the canonical shape; if you ever construct a record literal instead,
   match the canonical shape field-for-field.)
3. **Copy the stock file's `@fwd/` import header.** Override files must be
   self-contained — if the stock used a helper from `@fwd/Security/STIGs/Cisco/Common`,
   the override imports it too. Verify against `queries-export.proto`.
4. **An override may replace `ruleData` and/or `isVulnerable` but NEVER builds
   its own result record.** It must still route through `deviceStigResult` in
   the main query — that's where exemption logic lives (§6). An override that
   constructs its own result record bypasses the exemption chokepoint.
5. **Keep the test scaffold (`f` / `g`) at the bottom.** It lets the file run
   standalone for verification and is inert under `import`.

---

## 5. The stock-vs-override switch (settled)

`Custom STIG Findings` (the main query) controls which version of each rule is
active via its import header — and *only* via the import header.

```nqe
// Stock for V228860, V228877; override for V228658.
import "@fwd/Security/STIGs/Palo Alto Networks/PAN_OS Application Layer Gateway/PANW-AG-000102 V-228860";
import "@fwd/Security/STIGs/Palo Alto Networks/PAN_OS Application Layer Gateway/PANW-AG-000143 V-228877";
import "Projects/STIGs/Overrides/Palo Alto Networks/PAN_OS NDM/PANW-NM-000069 V-228658";
```

**Do not branch on stock-vs-override anywhere in the query body.** The import is
the single source of truth. If the override file's exports match the stock's
signatures (per §4 rule 1), the rest of the query is unchanged.

---

## 6. Exemption chokepoint (settled)

Per-device exemptions are applied in `deviceStigResult` inside the forked main
query — not in the final comprehension. Every row passes through
`deviceStigResult` regardless of OS branch, so editing it once applies
exemption to all callers uniformly.

- `Projects/STIGs/Configuration` holds an exported list of
  `{ device: String, vulnerabilityId: String, reason: String }`. Adding or
  removing an exemption is a one-line edit here.
- `Projects/STIGs/Utils` imports `Configuration` and exports `isExempt` and
  `exemptionReason`.
- `deviceStigResult` (inside the forked query) imports `Projects/STIGs/Utils`
  and, on every row, computes `let exempt = isExempt(...)`, sets `violation`
  to `null : Bool` when exempt, sets `Outcome` to `"Exempt"`, and adds an
  `"Exemption Reason"` field (null when not exempt).

The `let` inside `deviceStigResult` uses the `the(foreach x in [0] ...)`
wrapper because `let` is a comprehension clause and not valid in a function
body otherwise (verified `NQE_Syntax_and_Logic.md` §9).

---

## 7. Chassis rollup tail (settled)

The main query's terminal comprehension groups all vsys instances of a chassis
together and surfaces the worst row per `(physicalName, vulnerabilityId)`.

```nqe
violationPriority(v) = if !isPresent(v.violation) then 1
                       else if v.violation then 2 else 0;

foreach device in network.devices
where isPresent(device.files.config)
let macs = findMgmtMacs(device)
foreach record
  in deviceStigResultsInternal(device,
                               device.files.config,
                               false, false, false, false,
                               getParams(device, network.stigDatabase.policy),
                               macs)
let groupKey = { physicalName: device.system.physicalName,
                 vulnerabilityId: record["Vulnerability ID"] }
group record as records by groupKey as key
let worst = maxBy(records, violationPriority)
select {
  violation: worst.violation,
  "Physical Name": key.physicalName,
  Device: worst.Device,
  "Vulnerability ID": worst["Vulnerability ID"],
  // ... remaining fields field-by-field, see handover §5 ...
  "Exemption Reason": worst["Exemption Reason"],
  "VSYS Count": length(records)
}
```

**Load-bearing rules for the rollup:**

1. **No inline lambdas.** `maxBy(records, violationPriority)` — `violationPriority`
   is a named top-level function that takes the whole record and reads
   `.violation` itself. NQE has no `x -> expr` lambda syntax (verified
   `NQE_Standard_Library.md` `maxBy`).
2. **`maxBy` returns `T?`.** A `group by` group is never empty, so `worst` is
   non-null in practice, but the static type is nullable.
3. **`group by` drops all pre-group variables.** `device.system.physicalName`
   must be folded into `groupKey` BEFORE the `group` line — `device` is out of
   scope after (verified `NQE_Syntax_and_Logic.md` §9 "With `group by`").
4. **No record spread.** `{ ...worst, ... }` is not supported in this NQE
   dialect; rebuild record literals field-by-field.
5. **Bracket access for keys with spaces.** `record["Vulnerability ID"]`, not
   `record."Vulnerability ID"` (verified `NQE_Syntax_and_Logic.md` §4 "Field
   access"). Dot access still works for single-word field names like
   `worst.Device`.
6. **Typed null.** `null : Bool`, `null : String` — bare `null` does not
   type-check.
7. **`foreach` as the RHS of `let` must be parenthesized.** If the rollup ever
   uses `let xs = (foreach ... select ...)`, the parens are not optional
   (verified `NQE_Syntax_and_Logic.md` §9 "Critical: `let`-bound comprehensions
   also require parentheses").

---

## 8. Things that look right but aren't (settled)

These have all been verified against the project files (or against an earlier
draft that was wrong and got corrected). They're listed here because each one
is easy to slip back into.

| Looks right | Actually correct |
|---|---|
| `maxBy(records, r -> r.violation)` | `maxBy(records, violationPriority)` with `violationPriority(v) = ...v.violation...` |
| `record."Vulnerability ID"` | `record["Vulnerability ID"]` |
| `let xs = foreach ... select ...` | `let xs = (foreach ... select ...)` |
| `import "Security/STIGs/Rule Datas"` (in org-repo code) | `import "@fwd/Security/STIGs/Rule Datas"` |
| `{ ...worst, "VSYS Count": length(records) }` | Rebuild every field by name |
| `xs = [] : List<T>;` (postfix annotation on declaration RHS) | `xs : List<T> = [];` (prefix annotation on the name) |
| `null` (bare) | `null : Bool` |
| Treating `maxBy` as returning `T` | It returns `T?` (group is non-empty in practice; type is still nullable) |

---

## 9. STIG policy CSV — what it does and does not cover (settled)

The `fn-stig-policy.csv` policy file (loaded via NQE → Data Files) is keyed by
`Parameter`, not by vulnerability ID. The accepted `Parameter` values are
fields on the `StigPolicy` data type, e.g. `device.allowedBgpPeers`,
`device.managementSubnets`, `interface.connectivity.toExternalDevice`,
`interface.pseudowireVirtualCircuitId`.

**You cannot add arbitrary parameters** to the CSV — only fields Forward has
defined on `StigPolicy`. So:

- Per-device customizations to a parameter Forward exposes (e.g. allowed BGP
  peers) belong in the CSV.
- Per-device customizations to a value Forward does not expose (e.g. idle
  timeout threshold for V-228658) belong in an **override file** under
  `Projects/STIGs/Overrides/...`, where the value is a literal in the
  override's `isVulnerable` body.

This is why the V-228658 customer ask ("10 → 15 minutes") drives an override,
not a CSV edit.

---

## 10. Re-pull discipline (provisional)

Not yet decided. The two options:

- **Frozen snapshot.** The fork is a one-time copy from a specific Forward
  Library version and will not be re-synced. Override files can drift from
  stock freely.
- **Periodic re-sync.** Forward Library updates are re-pulled periodically.
  Override files should remain minimal (override only the parts that need
  overriding) so a `diff` between override and stock surfaces only intentional
  divergence.

Pending decision. If the answer is "periodic re-sync," override file rule §4.3
("copy the stock file's @fwd/ import header") gains a corollary: re-verify the
header against current stock at each re-pull.

---

## 11. Working-with-Claude rules (settled)

This is for whichever Claude instance picks up the project next.

1. **Verify every NQE construct against the project files before writing it,
   including ones that feel familiar.** Cite the file and section. If a
   construct cannot be found, flag it as needing confirmation against official
   Forward documentation — do not present it as verified.
2. **Treat the project `.md` files as authoritative over training knowledge.**
   They were generated from Forward docs and may contain interpretation
   artifacts, but they describe *this customer's NQE dialect*, which is what
   matters. If the docs say one thing and memory says another, the docs win.
3. **The project `.md` files are fallible.** Earlier drafts contained invented
   `r -> r.field` lambda examples. Be skeptical when a construct doesn't parse.
   If user-environment behavior contradicts the docs, the user's environment
   wins (and the doc should be corrected).
4. **`queries-export.proto` is the Forward Library source of truth** for what
   stock files look like. Read it (not memory) when verifying that an override
   preserves the stock contract.
5. **Do not present read-only project file edits inline.** Copy to
   `/home/claude/project-edits/` first, modify there, then offer to re-emit at
   the end of the conversation for the user to paste back.

---

## Appendix: known-unverified constructs

These are used in this project but are not documented in the four project `.md`
files. They are read directly from `queries-export.proto` and are
load-bearing — flagged for confirmation against official Forward documentation
the next time it is accessed.

- `getRuleData(stigName, stigVersion, vulnerabilityId, skipped)` — exported by
  `@fwd/Security/STIGs/Rule Datas`. Verified by direct read of the module's
  source in `queries-export.proto`.
- `stigRuleRecord(device, violation)` — exported by `@fwd/Security/STIGs/Rule Datas`.
  Same.
- `getResolvedStigParameters(device, policy, defaultParameters)` — exported by
  `@fwd/Security/STIGs/Device Parameters`. Used in every stock STIG file's `f()`
  test scaffold.
- `StigParameters` type — used as parameter type for every stock `isVulnerable`.
- `findMgmtMacs(device)` — used in the rollup tail; source not yet traced.
- `getParams(device, policy)` — used in the rollup tail; source not yet traced.
- `outcome(ruleData, violation)` — used in `deviceStigResult`; source not yet
  traced.

For each: if the next session needs to modify or extend its behavior, locate the
definition in `queries-export.proto` first.
