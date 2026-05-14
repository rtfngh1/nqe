# NQE Syntax and Logic Reference

Forward Networks Network Query Engine (NQE) language reference. This file covers types, expressions, comprehensions, pattern matching, and annotations. For idiomatic combinations of these primitives, see `NQE_Idioms_and_Patterns.md`. For function signatures, see `NQE_Standard_Library.md`. For the data model, see `NQE_Data_Model_Schema.md`.

---

## Table of Contents

1. [Top-Level Structure](#1-top-level-structure)
2. [Primitive Types](#2-primitive-types)
3. [Collections: Bag, List, Set](#3-collections-bag-list-set)
4. [Records](#4-records)
5. [OneOfs and Enumerations](#5-oneofs-and-enumerations)
6. [Null and Missing Values](#6-null-and-missing-values)
7. [Operators](#7-operators)
8. [If Expressions and `when` Expressions](#8-if-expressions-and-when-expressions)
9. [Comprehensions](#9-comprehensions)
10. [Pattern Matching (Single-Line)](#10-pattern-matching-single-line)
11. [Block Patterns (Multi-Line)](#11-block-patterns-multi-line)
12. [Regular Expressions](#12-regular-expressions)
13. [User-Defined Constants and Functions](#13-user-defined-constants-and-functions)
14. [Imports and the `@fwd` Library](#14-imports-and-the-fwd-library)
15. [Annotations: `@primaryKey`, `@query`](#15-annotations-primarykey-query)
16. [NQE Type Syntax](#16-nqe-type-syntax)
17. [CSV and JSON Data](#17-csv-and-json-data)
18. [NQE 25.11 Breaking Changes](#18-nqe-2511-breaking-changes)

---

## 1. Top-Level Structure

An NQE query is a single **expression** that evaluates to a `Bag` or `List` of records. The query may be preceded by zero or more top-level declarations (constants, helper functions, imports).

```
// Top-level declarations (optional, terminated with ;)
threshold = 10;
isCisco(d: Device) : Bool = d.platform.vendor == Vendor.CISCO;

// Main expression (required, no trailing ;)
foreach device in network.devices
where isCisco(device)
select { name: device.name }
```

### Result formatting

NQE auto-rewrites the result to coerce non-simple values to strings. A "simple value" is a primitive or a bag/list of primitives. Anything deeper (a record-of-records, a list-of-lists) is converted via `toStringTruncate()`. So:

```
foreach device in network.devices
select { name: device.name, device: device }
```

becomes:

```
select { name: device.name, device: toStringTruncate(device) }
```

If you want structured output, flatten with a nested comprehension instead.

### Always available

The `network` variable is in scope at the top level. `network.devices`, `network.cloudAccounts`, `network.endpoints`, etc. are the entry points to the data model.

---

## 2. Primitive Types

| Type | Literal example | Notes |
|---|---|---|
| `String` | `"hello"` or `"""multi\nline"""` | Escape with `\"`, `\t`, `\n`, `\\`. Triple-quoted blocks are literal (no escapes). |
| `Integer` | `42`, `-17` | Range: ±9.2×10¹⁸. |
| `Float` | `3.14`, `2.`, `.5` | Same range as Integer. Floating-point imprecision near boundaries. |
| `Bool` | `true`, `false` | |
| `IpAddress` | `ipAddress("1.2.3.4")` or `ipAddress("2001:db8::1")` | Both v4 and v6. |
| `IpSubnet` | `ipSubnet("10.0.0.0/24")` or `ipSubnet(ipAddr, 24)` | Constructed from string, address+length, or address+netmask. |
| `MacAddress` | `macAddress("aa:bb:cc:dd:ee:ff")` | |
| `Date` | via `date(...)` function | Calendar day. |
| `Timestamp` | via `timestamp("2000-01-01T00:00:00Z")` | UTC, second precision. |
| `Duration` | via `days(7)`, `hours(3)`, `seconds(60)`, `duration(...)` | Time interval. |

### Number coercion

- `int(x)` truncates decimal — `int(2.9)` → `2`. Same behavior as `floor(x)`.
- `float(x)` converts integer to float. Also `2.0` or `2.` as literals.
- A collection must contain values of the same type: `sum([1, 2.0, 3])` fails — use `[1.0, 2.0, 3.0]` or `[1, 2, 3]`.

### Time arithmetic

```
Date - Date = Duration
Date + Duration = Date           Date - Duration = Date
Timestamp - Timestamp = Duration
Timestamp + Duration = Timestamp Timestamp - Duration = Timestamp
Duration + Duration = Duration   Duration - Duration = Duration
```

### IP and subnet operations

- `length(subnet)` → prefix length
- `address(subnet)` → IP address part
- `networkAddress(subnet)` → IP with host bits zeroed
- `broadcastAddress(subnet)` → IP with host bits set
- `ip in subnet` / `ip not in subnet` → Bool
- `isIPv4(x)` / `isIPv6(x)` works on both `IpAddress` and `IpSubnet`
- `toNumber(ipv4)` → Integer (IPv4 only); `ipv4Address(integer)` → IpAddress
- `fromTo(ipAddr1, ipAddr2)` → List of addresses in range

### MAC operations

- `ouiVendors(mac)` → `List<Vendor>` from IEEE OUI database
- `ouiAssignee(mac)` → String (organization name) or null

---

## 3. Collections: Bag, List, Set

| Type | Description |
|---|---|
| `Bag<T>` | Unordered collection; elements may repeat. |
| `List<T>` | Ordered collection; supports indexing and `limit`. |
| `Set` | Currently only for IP address sets. Unordered, unique. |

**Key distinction:** Bags don't preserve order. Lists do. Many built-ins and data model fields return Bags. Use `order by` in a comprehension or `orderBy(collection, keyFn)` to convert a Bag to a List.

### Literals

- List: `[1, 2, 3]` (square brackets always = List)
- Bag: convert with `bag(...)`: `bag([1, 2, 3])`
- Empty: `[] : List<Integer>` (must type-annotate empty literals)

### Operations

| Operation | Description |
|---|---|
| `length(c)` | Element count |
| `item in c`, `item not in c` | Membership |
| `c1 + c2` | Concatenation. List+List=List. Otherwise Bag. |
| `c1 - c2` | Difference (removes c2 items from c1) |
| `c1 == c2` | Equality. Order matters for Lists, not for Bags. |
| `distinct(c)` | Remove duplicates |
| `length(c) == 0` or `isEmpty(c)` | Empty test |

### Ordering

- `order(c)` → List, sorted by natural order
- `orderBy(c, keyFn)` → List, sorted by a key function
- In a comprehension: `order by expr1 asc, expr2 desc`

### Limiting

- `limit(list, n)` → first n elements
- In a comprehension: `limit n` (must come after `order by`, or `foreach` over a list literal)

### List indexing

Lists support `[index]` and `?[index]`. Bags do not.

---

## 4. Records

A record is a struct with named fields.

### Construction

```
{name: "Bob", age: 30}                              // basic
{a: 1, b: {c: 2, d: 3}}                             // nested
{"Device Count": 100, "Mgmt IP": ipAddress("1.1.1.1")}  // quoted names for special chars
```

### Field access

| Operator | Behavior |
|---|---|
| `r.field` | Standard access. Errors if `r` is null. |
| `r?.field` | Safe access. Returns null if `r` is null. |
| `r["Field Name"]` | Bracket access. Required for keys with spaces or special chars. |
| `r?["Field Name"]` | Safe bracket access. |

**Important:** `r?.b.c` errors if `r?.b` returns null (because the second `.c` is not null-safe). Use `r?.b?.c` for full chain safety.

### Record types

Record types are written as `{field1: Type1, field2: Type2, ...}`. Optional fields use `?`: `{name: String, mtu?: Integer}`.

Records are **structurally typed** in function parameters — a function expecting `{subinterfaces: List<SubInterface>}` accepts any record that has at least that field.

---

## 5. OneOfs and Enumerations

A OneOf type is a tagged union — a value that's one of several constructors, each possibly carrying data.

### Enumerations (data-less OneOfs)

```
OperStatus.UP        AdminStatus.DOWN     OS.NXOS      Vendor.CISCO
```

### OneOfs with data

```
SubInterfaceVlan.VLAN_ID(123)
SubInterfaceVlan.QINQ_ID("1.2")
DeviceSnapshotResult.collectionFailed(error)
```

### Consuming OneOfs with `when ... is`

```
when expression is
  Constructor1(varName) -> resultExpr1;
  Constructor2 -> resultExpr2;
  otherwise -> defaultExpr
```

Rules:
- Cases separated by `;` (semicolons mandatory).
- `Con(var)` binds the inner value to `var`. Only works on data-bearing constructors.
- `Con` (no parens) matches without binding. Required for enum cases.
- `otherwise` matches anything; must be the last case.
- **All case expressions must return the same type.** Use `null : T` to fail through to a typed null.

### Example — extract VLAN ID, null for QINQ

```
let vlan = when subiface.vlan is
             VLAN_ID(v) -> v;
             otherwise -> null : Integer
where isPresent(vlan)
```

### Example — handle snapshot result variants

```
formatStatus(result) =
  when result is
    collectionFailed(err) -> "Collecting - " + toString(err);
    completed -> "Completed";
    processingFailed(err) -> "Processing - " + toString(err);
```

---

## 6. Null and Missing Values

Many data model fields are nullable (marked **nullable** in the data model docs). `isPresent(x)` returns true if `x` is not null.

### Creating null values

`null : T` produces a null of type `T`. Bare `null` won't type-check.

```
let x = null : Integer        // OK
let x = null                  // type error
```

### Null-safe operators

- `r?.field` — short-circuits to null if `r` is null
- `r?["Field Name"]` — bracket version

### Filtering nulls in a comprehension

```
foreach x in collection
let derived = maybeNull(x)
where isPresent(derived)
select { derived: derived }
```

### Note on `if` and null

Both branches of `if expr then ... else ...` must return the same type. If one branch could be null, annotate the null:

```
if isPresent(x) then x else null : Integer
```

---

## 7. Operators

### Arithmetic

`+`, `-`, `*`, `/`, `%` (modulo), `^` (exponentiation), `-x` (negation). Same operators work on Integer and Float (but don't mix in a collection).

### String

- `+` concatenation
- `length(s)` character count
- `substring(s, start, end)` — end exclusive
- `prefix(s, n)` — first n chars
- `suffix(s, n)` — last n chars
- `toUpperCase(s)`, `toLowerCase(s)`
- `replace(text, target, replacement)` — replaces ALL occurrences

### String matching (NQE has no `contains`, `startsWith`, `split`)

- `matches(s, "*foo*")` — case-sensitive wildcard. `*` is any chars, `?` is one char.
- For "starts with foo": `prefix(s, 3) == "foo"`
- For "ends with foo": `suffix(s, 3) == "foo"`
- For "contains foo": `matches(s, "*foo*")` or `hasMatch(s, re\`foo\`)`
- For "split": use `regexMatches` or `patternMatches`

### Boolean

`&&`, `||`, `!`.

### Comparison

`==`, `!=`, `<`, `<=`, `>`, `>=`. Work on most types — see ordering rules below.

### Ordering rules (relevant for `order by` and `<`, `>`)

| Type | Order |
|---|---|
| Numbers | Numerical |
| Strings | Alphabetical |
| Booleans | `false < true` |
| IpAddress | Numerical |
| IpSubnet | By prefix length first, then by host bits |
| MacAddress | Numerical |
| Date, Timestamp | Chronological |
| Duration | Numerical |
| List | Lexicographic |
| Bag | Converted to list using natural order, then compared as list |
| Record | Lexicographic on fields in alphabetical name order |
| OneOf | Alphabetical by constructor name; then by inner value |
| `null` | Less than all values; equal to itself |

### Membership

- `x in collection` / `x not in collection`
- `ip in subnet` / `ip not in subnet`

---

## 8. If Expressions and `when` Expressions

### `if`

```
if condition then expr1 else expr2
```

- Both branches must produce values of the same type.
- This is an **expression**, not a statement — it returns a value.
- Equivalent to ternary `condition ? expr1 : expr2` in other languages.

### `when` (see [Section 5](#5-oneofs-and-enumerations))

Use for OneOf / enum case analysis. `if` won't work because OneOfs have multi-variant structure beyond two-way branching.

---

## 9. Comprehensions

The core looping/filtering/aggregation construct. Built from qualifiers that read top-to-bottom.

### Qualifier types

| Qualifier | Effect |
|---|---|
| `foreach var in collection` | Iterate; introduces `var` |
| `where condition` | Filter |
| `let var = expr` | Bind intermediate value (only after first `foreach`) |
| `group valueExpr as valuesVar by keyExpr as keyVar` | Group by key |
| `select expr` | Compute output record (terminal) |
| `select distinct expr` | Deduplicated output |
| `order by expr asc/desc[, ...]` | Sort (after `select`) |
| `limit n` | Restrict count (after `select`/`order by`) |

### Minimal comprehension

```
foreach x in collection
select x
```

### With filtering

```
foreach device in network.devices
where device.platform.vendor == Vendor.CISCO
select { name: device.name }
```

### With `let`

```
foreach device in network.devices
let os = device.platform.os
where os == OS.NXOS
select { name: device.name, os: os }
```

**Rule:** `let` is a *comprehension clause* — it exists **only** inside a `foreach ... select` comprehension, and only after the first `foreach`. It cannot appear before the first `foreach`, in a function body, or in any other expression context.

- **Top-level constants:** use `name = value;` at the top of the file.
- **Intermediate bindings inside a function body** (or any expression context that is not already a comprehension): wrap a single-element comprehension and extract the scalar with `the(...)`:

```
// WRONG — let is not valid in a function body
normalize(s: String) =
  let lower = toLowerCase(s)        // syntax error
  replaceRegexMatches(lower, re`_.*`, "")

// RIGHT — wrap foreach over a one-element list, pull the result out with the()
normalize(s: String) =
  the(foreach x in [0]
      let lower = toLowerCase(s)
      let stripped = replaceRegexMatches(lower, re`_.*`, "")
      select stripped);
```

The `[0]` is an arbitrary one-element list — the loop runs exactly once and `the()` unwraps the single result. This is the standard way to get `let` chains (or `where` / `when` logic) into a function body. See also the `the(foreach x in [x] ...)` null-safety idiom in `NQE_Standard_Library.md`; it is the same pattern.

### With `group by`

```
foreach part in parts
group part.price as prices by part.weight as weight
where length(prices) > 1
select { weight: weight, priceCount: length(prices), maxPrice: max(prices) }
```

After `group by`, only the variables it introduces (here `prices` and `weight`) are in scope. Earlier variables (`part`) are no longer accessible.

The general form: `group valueExpr as valuesVar by keyExpr as keyVar`. The key and value can be records (composite keys).

### With `order by` and `limit`

```
foreach device in network.devices
select { name: device.name, model: device.platform.model }
order by name asc, model desc
limit 10
```

Both `asc`/`ascending` and `desc`/`descending` work. `order by` always produces a List.

### Nested comprehensions

Comprehensions can appear inside expressions if enclosed in parentheses:

```
foreach d in network.devices
select {
  device: d.name,
  ifaceNames: (foreach iface in d.interfaces select iface.name)
}
```

### Qualifier ordering

Order matters: variables must be in scope when referenced. Generally:

```
foreach ... (introduces variables)
foreach ... (can use prior)
let ... (can use prior)
where ... (can use prior)
group ... by ... (introduces new variables; drops prior)
where ... (can use group's variables)
select ...
order by ...
limit ...
```

---

## 10. Pattern Matching (Single-Line)

Used to extract structured data from configuration lines or arbitrary text strings.

### Patterns are written in backticks

```
`tacacs-server host {server:string}`
`interface {iface:string}`
`speed {speed:number}`
```

### Two main functions

| Function | First arg | Returns |
|---|---|---|
| `patternMatches(config, pattern)` | `List<ConfigLine>` | `Bag<{line: ConfigLine, data: T}>` of all matches |
| `patternMatch(text, pattern)` | `String` | `T?` — single match or null |

**Prefer `patternMatches`** for cleaner queries. `patternMatch` is useful when you have raw text from a single source.

### Capture group syntax

- `{name:Type}` — named capture, typed
- `{Type}` — unnamed (rare; usually you want a name)

### Capture group types

These are the **literal keywords** the pattern grammar accepts. They are lowercase, and the keyword for an integer is `number` — `{n:integer}` is a parse error.

| Keyword | Matches | Value type produced |
|---|---|---|
| `string` | Any non-whitespace sequence | `String` |
| `number` | Integer (e.g., `42`, `-17`) | `Integer` |
| `float` | Decimal (e.g., `3.14`, `.5`) | `Float` |
| `ipv4Address` | IPv4 like `1.2.3.4` | `IpAddress` |
| `ipv6Address` | IPv6 like `2001:db8::1` | `IpAddress` |
| `ipv4Subnet` | `10.0.0.0/24` | `IpSubnet` |
| `ipv6Subnet` | IPv6 subnet | `IpSubnet` |
| `macAddress` | MAC in various formats | `MacAddress` |

> **⚠ Integer-type spelling is context-dependent.** `Integer` is the language-wide type name — use it for parameter annotations, `null : Integer`, regex typed captures (`re\`(?<n:Integer>\d+)\``), and type-parameterized functions (`extractJson[Integer](...)`). The capitalized `Number` is **deprecated** — it still parses but the editor flags *"Usage of 'Number' is deprecated. Use 'Integer' instead."*
>
> **The exception:** inside **pattern and block-pattern literals** (`patternMatch`, `patternMatches`, `blockMatches`), the capture-type grammar uses the lowercase keyword `number`. It still produces a value of type `Integer` — only the keyword inside the `` ` ` `` literal differs. `{n:integer}` and `{n:Integer}` are both parse errors there.
>
> | Where | Spelling | Example |
> |---|---|---|
> | Type annotations, `null : T` | `Integer` | `candidate: Integer` |
> | Regex typed capture (`re\`...\``, `match`, `regexMatches`) | `Integer` | `re\`(?<id:Integer>\d{3})\`` |
> | `extractJson[...]` and other type-parameterized fns | `Integer` | `extractJson[Integer]("5")` |
> | Pattern / block-pattern literal capture | `number` | `` patternMatch(s, `{n:number}`) `` |
> | *(deprecated everywhere)* | ~~`Number`~~ | — |

### Pattern composition (inside `{ ... }`)

- `"literal"` — matches exact text (alternative: top-level literals don't need quotes)
- `eof` — end of input
- `empty` — always matches, consumes nothing
- `pattern1 pattern2` — sequence
- `pattern1 | pattern2` — alternation; returns `{left: T?, right: U?}` (one null)
- `pattern*` — zero or more; returns List
- `pattern+` — one or more; returns List
- `!pattern` — negative lookahead; consumes nothing, returns empty record
- `var:pattern` — captures the value into field `var`

### Example with capture types

```
foreach device in network.devices
foreach match in patternMatches(device.files.config, `ip route {prefix:ipv4Subnet} Null0`)
select { device: device.name, prefix: match.data.prefix }
```

### Example with negation (extract value before a known token)

```
// Match: "Platform: cisco WS-C3850-48P Capabilities: ..."
// Captures multi-word platform until "Capabilities:" is seen
{platform:((!"Capabilities:" string)*)} Capabilities:
```

Use `join(" ", result.data.platform)` to recombine the captured List<String>.

### Optional pattern items

```
logging {"host" | empty} {ipv4Address}
```

Matches both `logging host 1.2.3.4` and `logging 1.2.3.4`.

### Walking the config hierarchy

Each `ConfigLine` has `children: List<ConfigLine>`. To match a parent and its children:

```
foreach ifaceMatch in patternMatches(device.files.config, `interface {iface:string}`)
foreach speedMatch in patternMatches(ifaceMatch.line.children, `speed {speed:number}`)
select {
  iface: ifaceMatch.data.iface,
  speed: speedMatch.data.speed
}
```

---

## 11. Block Patterns (Multi-Line)

Block patterns match multi-line configuration structures with hierarchy.

### Literal syntax

Block patterns are enclosed in **triple backticks** on their own lines:

```
pattern = ```
interface
  zone-member security
  ip address {ip:string}
parameter-map
  log dropped-packets
```;
```

Each line is a single-line pattern (see Section 10). Indentation defines hierarchy — children are indented under parents.

### Matching is hierarchical and unordered

A block pattern matches if every line in the pattern matches some configuration line, respecting the hierarchy. Order of sibling lines in the configuration doesn't matter; order of lines in the pattern doesn't matter.

By default, **extra lines in the configuration that aren't covered by the pattern are allowed**. Toggle this with `{%unmatched-config:forbid%}`.

### Functions for block patterns

| Function | Signature | Purpose |
|---|---|---|
| `blockMatches(config, pattern)` | `List<ConfigLine> -> PatternBlocks<T> -> Bag<{data:T, blocks:MatchBlocks, diffCount:Integer}>` | Find all matches |
| `hasBlockMatch(config, pattern)` | `... -> Bool` | True if any matches |
| `blockDiff(config, pattern)` | Diff config against pattern | |
| `blockPattern(string)` | Construct a block pattern from a runtime string | |
| `mergeBlocks(patterns)` | Combine multiple block patterns sharing parents | |
| `withOption(pattern, option)` | Modify pattern options programmatically | |

### Forbidding extra lines

```
pattern = ```
interface
  zone-member security
  ip address {ip:string}
  {%unmatched-config:forbid%}
```;
```

Applies to the block it's in and all descendants. Place at top level to apply globally.

### Negation — assert a line does NOT exist

```
pattern = ```
interface
  {%-%} zone-member security
  ip address {ip:string}
```;
```

Matches interfaces with an IP address that do *not* have a zone-member.

### Handling non-indentation-based config (JunOS)

Block patterns rely on indentation. For JunOS-style braced configuration:

```
system {
  syslog {
    host 1.2.3.4 {
      facility-override kernel;
    }
  }
}
```

Strip the braces and indent according to the original hierarchy:

```
pattern = ```
system
  syslog
    host 1.2.3.4
      facility-override kernel;
```;
```

### Parsing raw command output for block matching

`parseConfigBlocks(os: OS, text: String) : List<ConfigLine>` parses an arbitrary string (e.g., command output) into a `List<ConfigLine>` that can be passed to `blockMatches`. Useful when the structured `device.files.config` doesn't contain what you need.

For `OS.PAN_OS`, no lines are ignored. For other OSes, lines starting with `!`, `#`, `;`, `%`, "Building configuration...", or "Current configuration :" (case-insensitive) are skipped.

---

## 12. Regular Expressions

NQE supports regex for text matching and extraction. Regex is more flexible than patterns but doesn't understand config hierarchy.

### Literal syntax

```
ipRegex = re`\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`;
nameRegex = re`(?<Location>\w{1,4})(?<ID:Integer>\d{3})`;
```

### Runtime construction

```
dynamicRegex = regex("pattern here");
```

`regex(...)` builds from a string but does **not** support capture groups for data extraction. Use the literal `re\`...\`` form for any regex that needs to extract data.

### Functions

| Function | Signature | Purpose |
|---|---|---|
| `hasMatch(text, regex)` | `String -> Regex<T> -> Bool` | Test only |
| `match(text, regex)` | `String -> Regex<T> -> T?` | Single match, returns null on no match |
| `regexMatches(text, regex)` | `String -> Regex<T> -> List<{string, start, end, data}>` | All matches |
| `replaceMatches(text, pattern, replacement)` | | Replace matches of single-line pattern |
| `replaceRegexMatches(text, regex, replacement)` | | Replace matches of regex |
| `matches(text, wildcard)` | `String -> String -> Bool` | Wildcard (`*`, `?`) — NOT regex |

### Match result structure

For `regexMatches`, each result is `{string, start, end, data}`:
- `string` — the matched substring
- `start`, `end` — char offsets
- `data` — record of capture groups (record with fields named per group)

### Capture groups

| Syntax | Description |
|---|---|
| `(x)` | Numbered capture — access via `data["1"]`, `data["2"]`, etc. |
| `(?<name>x)` | Named capture — access via `data.name` |
| `(?<name:Type>x)` | Named + typed capture — coerces value, fails match if invalid |
| `(?:x)` | Shy (non-capturing) group — for precedence only |

### Typed capture types

`String`, `Integer`, `Float`, `IpAddress`. Untyped defaults to String.

### Examples

```
// Match and extract
foreach device in network.devices
let result = match(device.name, re`(?<Location>\w{1,4})(?<ID:Integer>\d{3})`)
where isPresent(result)
select { device: device.name, location: result.data.Location, id: result.data.ID }
```

```
// Replace
foreach device in network.devices
foreach command in device.outputs.commands
where command.commandType == CommandType.CONFIG
select { device: device.name, redacted: replaceRegexMatches(command.response, re`\d+\.\d+\.\d+\.\d+`, "<IP>") }
```

### Regex syntax (highlights)

Standard: `.`, `[abc]`, `[^abc]`, `\d`, `\D`, `\s`, `\S`, `\w`, `\W`, `\b`, `\B`, `^`, `$`, `\n`, `\t`, `\r`, `\R`, `\f`, `\v`.
Quantifiers: `*`, `+`, `?`, `{n}`, `{n,}`, `{n,m}`. Add `?` for non-greedy: `*?`, `+?`, etc.
Alternation: `x|y`.

### Regex limitations

- **No back-references** (`\1` etc).
- **Cannot quantify a named capture group with an upper bound > 1.** Use a shy group: `(?:\w+){1,3}` not `(\w+){1,3}`.
- **Cannot nest quantifiers directly.** Use a shy group: `(?:\d{3})*` not `\d{3}*`.
- **Cannot reuse a capture name with different types.**

---

## 13. User-Defined Constants and Functions

### Top-level declarations

Place above the main expression. Each terminated with `;`.

```
threshold = 10;
isCisco(device) = device.platform.vendor == Vendor.CISCO;

foreach device in network.devices
where isCisco(device) && length(device.interfaces) > threshold
select { name: device.name }
```

### Zero-parameter functions

Parens optional:

```
defaultMtu = 1500;
defaultMtu() = 1500;       // equivalent
```

### Type annotations

Optional but recommended. If you annotate parameters, you must annotate **all** parameters.

```
threshold : Integer = 100;
hasManySubInterfaces(iface : Iface) : Bool = length(iface.subinterfaces) > threshold;
```

### Structural parameter types

Functions can accept any record with at least the required fields:

```
hasManySubs(x : { subinterfaces: List<SubInterface> }) : Bool =
  length(x.subinterfaces) > 10;
```

Now `hasManySubs` works on `Iface` or any other record with that field.

### Multiple `let` chained

`let` in a comprehension can rebind the same name — useful for transformation chains:

```
foreach text in [rawText]
let text = replace(text, "\n", "\n  ")
let text = replace(text, "old", "new")
let text = trim(text)
select text
```

---

## 14. Imports and the `@fwd` Library

### Exporting from a module

In file `Shop/Inventory`:

```
export inventory = [
  {make: "Tesla", model: "3"},
  {make: "Toyota", model: "Prius"}
];

export isApproved(make: String) = make in ["Tesla", "Toyota"];
```

Only `export`-marked declarations are visible to importers.

### Importing

```
import "Shop/Inventory";

foreach car in inventory
where isApproved(car.make)
select { make: car.make, model: car.model }
```

Paths are **absolute** (from the root of your NQE library).

### Forward built-in library

```
import "@fwd/Interfaces/Interface IPs";

foreach device in network.devices
foreach subnet in getAllIfaceSubnets(device)
select { device: device.name, subnet: subnet }
```

The `@fwd/...` prefix references Forward's bundled helpers. Available modules include `Interfaces/*`, `Time/Utils`, and others — see what's available in the NQE Library IDE.

### Common `@fwd` imports

- `@fwd/Time/Utils` — provides `formatSeconds` and other duration helpers
- `@fwd/Interfaces/Interface IPs` — provides `getAllIfaceSubnets(device)` and similar

---

## 15. Annotations: `@primaryKey`, `@query`

### `@primaryKey`

Placed immediately before the main expression. Declares which output columns form the unique key.

```
@primaryKey(DeviceName, VRF, Prefix)
foreach device in network.devices
foreach vrf in device.networkInstances
foreach entry in vrf.afts.ipv4Unicast.ipEntries
select {
  DeviceName: device.name,
  VRF: vrf.name,
  Prefix: entry.prefix,
  NextHops: (foreach nh in entry.nextHops select nh.ipAddress)
}
```

**Rules:**
- Column names match output field names exactly (case-sensitive).
- Names with spaces or special chars must be quoted: `@primaryKey("Device Name", VRF)`.
- All primary key columns must be present in every output row.
- Combined values must be unique across all rows.
- Required for: NQE Verifications, Inventory+ queries, queries whose diffs matter.

### `@query`

Marks a named declaration as the main query. Useful for parameterized queries:

```
@query
findInterfacesWithMTU(targetMtu : Integer) =
  foreach device in network.devices
  foreach iface in device.interfaces
  where iface.mtu == targetMtu
  select { device: device.name, iface: iface.name };
```

The `@query`-marked declaration runs as if it were the main expression. Parameters must have type annotations.

### Combining `@query` and `@primaryKey`

Place both above the declaration:

```
@primaryKey(device, iface)
@query
slowInterfaces(minSpeedMbps : Integer) =
  foreach device in network.devices
  foreach iface in device.interfaces
  where iface.ethernet.negotiatedPortSpeed.speedMbps < minSpeedMbps
  select { device: device.name, iface: iface.name };
```

---

## 16. NQE Type Syntax

Used in type annotations on parameters, returns, and `null : T`.

| Type literal | Meaning |
|---|---|
| `String`, `Integer`, `Float`, `Bool` | Primitives |
| `IpAddress`, `IpSubnet`, `MacAddress` | Network primitives |
| `Date`, `Timestamp`, `Duration` | Time primitives |
| `List<T>` | Ordered collection |
| `Bag<T>` | Unordered collection |
| `Regex<T>` | Regex whose match-result type is T |
| `Pattern<T>` | Single-line pattern with result type T |
| `PatternBlocks<T>` | Block pattern with result type T |
| `TypeName` | Named type from data model (e.g., `Device`, `Iface`) |
| `{ field1: T1, field2: T2 }` | Record type |
| `{ name: String, mtu?: Integer }` | Record with optional field |
| `T?` | Equivalent to nullable T (rare; more commonly seen as field nullability) |

---

## 17. CSV and JSON Data

### CSV

CSV data can be embedded directly as a triple-quoted literal and assigned to a name:

```
dxConnections =
  """csv
Dx VIF ID,VLAN,Onprem Device
dxvif-abc123,545,router-01
""";
```

This produces a collection of records, one per data row.

- **Column access:** header names become field names with spaces replaced by underscores — `Dx VIF ID` → `record.Dx_VIF_ID`.
- **Columns are typed by inference, per column.** A column whose every value parses as an integer arrives as `Integer`; likewise `Float`, `Bool`, etc.; otherwise `String`. **Do not coerce** a column that is already the right type — e.g. if `VLAN` holds only integers, `record.VLAN` is already an `Integer`. (There is no String→Integer conversion function anyway — see the "lacks" table in `NQE_Standard_Library.md`.)
- Inference is over **all rows** of the column: a single non-numeric value makes the entire column `String`.

CSV can also be ingested via stdlib `csv` functions for data connectors and external sources.

### JSON

For parsing JSON strings (e.g., from HTTP endpoint responses or device JSON output):

- `extractJson(jsonText, "path.to.value", type)` — extract a typed value from JSON
- `splitJsonObjects(jsonText)` — split a JSON array into a list of JSON objects

JSON command output (e.g., `show interface | json`) often lives in `device.outputs.commands[i].response` and needs `extractJson` or `splitJsonObjects` to navigate.

---

## 18. NQE 25.11 Breaking Changes

Stricter typing introduced in NQE 25.11. Queries written before may need updates:

### Bag vs List comparisons now generate warnings

```
// This bag-of-strings...
deviceNames = foreach d in network.devices select d.name;
// ...compared with this list-literal...
isEqual: deviceNames == ["device1", "device2"]
// ...used to use order-sensitive semantics. Now it's order-insensitive (Bag) with a warning.
```

**Fix options:**

```
// Option 1: Force order via order by
deviceNames = foreach d in network.devices
              let name = d.name
              select name
              order by name;
isEqual: deviceNames == ["device1", "device2"]

// Option 2: Use bag() to convert literal
isEqual: deviceNames == bag(["device1", "device2"])
```

Square brackets `[...]` always produce a List. Comprehensions without `order by` produce a Bag.

---

## Appendix: Snapshot Data

`network` is always in scope. It represents the currently-selected snapshot's data:

- `network.devices : Bag<Device>`
- `network.cloudAccounts : Bag<CloudAccount>`
- `network.endpoints : Bag<NetworkEndpoint>` — SNMP/HTTP sources
- `network.locations : Bag<Location>`
- `network.externalSources : ExternalSources`

For details on traversal paths from `network`, see `NQE_Data_Model_Schema.md`.
