# NQE Standard Library Reference

All 73 built-in functions, grouped by category. Each entry has signature, one-line description, and usage notes where the function has non-obvious behavior.

For language constructs (operators, comprehensions, pattern syntax), see `NQE_Syntax_and_Logic.md`. For patterns combining these functions, see `NQE_Idioms_and_Patterns.md`.

---

## Table of Contents

1. [Collections — Aggregation and Reduction](#1-collections--aggregation-and-reduction)
2. [Collections — Construction and Conversion](#2-collections--construction-and-conversion)
3. [Collections — Ordering and Limiting](#3-collections--ordering-and-limiting)
4. [Collections — Element Extraction](#4-collections--element-extraction)
5. [Collections — Set Operations](#5-collections--set-operations)
6. [Strings](#6-strings)
7. [Numbers](#7-numbers)
8. [IP Addresses and Subnets](#8-ip-addresses-and-subnets)
9. [MAC Addresses](#9-mac-addresses)
10. [Date, Timestamp, Duration](#10-date-timestamp-duration)
11. [Null Handling](#11-null-handling)
12. [Single-Line Pattern Matching](#12-single-line-pattern-matching)
13. [Block Pattern Matching](#13-block-pattern-matching)
14. [Regular Expressions](#14-regular-expressions)
15. [Configuration Parsing](#15-configuration-parsing)
16. [JSON](#16-json)
17. [Interface Lookup](#17-interface-lookup)
18. [Stringification and Display](#18-stringification-and-display)

---

## 1. Collections — Aggregation and Reduction

### `length`
`length(collection: Bag<T>) : Integer`
Element count. Accepts Lists or Bags. Also overloaded for `String` (char count) and `IpSubnet` (prefix length).

### `sum`
`sum(numbers: Bag<Integer>) : Integer`
`sum(numbers: Bag<Float>) : Float`
Sum of numeric elements. Empty collection sums to 0. All elements must be the same numeric type.

### `max`
`max(collection: Bag<T>) : T?`
Greatest element by natural order. Returns null if empty.

### `min`
`min(collection: Bag<T>) : T?`
Least element by natural order. Returns null if empty.

### `maxBy`
`maxBy(collection: Bag<T>, keySelector: T -> K) : T?`
Greatest element by key function. Returns null if empty.
```
maxBy(routes, r -> r.metric)
```

### `minBy`
`minBy(collection: Bag<T>, keySelector: T -> K) : T?`
Least element by key function.

### `all`
`all(booleans: Bag<Bool>) : Bool`
True iff every element is true. Empty collection → true. Null elements treated as false.

### `any`
`any(booleans: Bag<Bool>) : Bool`
True iff at least one element is true. Empty collection → false. Null elements treated as false.

### `distinct`
`distinct(collection: List<T>) : List<T>`
`distinct(collection: Bag<T>) : Bag<T>`
Deduplicate. Preserves order on Lists.

### `join`
`join(delimiter: String, list: List<String>) : String`
Concatenate strings with delimiter between each. Also accepts Bag (deprecated path; will warn).
```
join(", ", deviceNames)
```

---

## 2. Collections — Construction and Conversion

### `bag`
`bag(list: List<T>) : Bag<T>`
Convert a List to a Bag (drops order). Use to fix Bag/List type-mismatch warnings in NQE 25.11+.

### `fromTo`
`fromTo(a: Integer, b: Integer) : List<Integer>`
`fromTo(a: IpAddress, b: IpAddress) : List<IpAddress>`
Inclusive range of integers, or list of IP addresses in range.

### `ipAddressSet`
`ipAddressSet(ipSubnets: Bag<IpSubnet>) : Set<IpAddress>`
Construct a Set of IP addresses from a Bag of subnets (expands each subnet to its constituent addresses).

---

## 3. Collections — Ordering and Limiting

### `order`
`order(collection: Bag<T>) : List<T>`
Sort by natural order, ascending. Returns a List.

### `orderBy`
`orderBy(collection: Bag<T>, keySelector: T -> K) : List<T>`
Sort by a key function, ascending.
```
orderBy(devices, d -> d.platform.osVersion)
```
For descending, use `order by ... desc` clause in a comprehension instead.

### `limit`
`limit(list: List<T>, n: Number) : List<T>`
First n elements. Requires a List (use `order` or `orderBy` first if you have a Bag).

---

## 4. Collections — Element Extraction

### `the`
`the(collection: List<T>) : T?`
`the(collection: Bag<T>) : T?`
Returns the **unique** element if the collection has exactly one element; otherwise returns null. **Returns null for zero OR more than one element** — it's not "give me one of these."

```
coreRouter = the(
  foreach d in network.devices
  where d.name == "core-router-1"
  select d
)
```

Also the idiomatic way to use comprehension-only clauses (`let`, `where`, `when`) in an expression context that is not already a comprehension — e.g. a function body. Wrap a one-element comprehension and unwrap it: `the(foreach x in [0] let ... select ...)`. The null-safe-transformation form `the(foreach x in [x] where isPresent(x) ...)` is one special case of this. See "With `let`" in `NQE_Syntax_and_Logic.md`.

---

## 5. Collections — Set Operations

### `intersect`
`intersect(set1: Set<T>, set2: Set<T>) : Set<T>`
Intersection of two Sets. Currently `Set` is only used for IP address sets (`Set<IpAddress>`).

### `isEmpty`
`isEmpty(set: Set<IpAddress>) : Bool`
True if Set has no members.

---

## 6. Strings

### `length`
`length(str: String) : Integer`
Character count.

### `prefix`
`prefix(str: String, n: Integer) : String`
First n characters. Safe — returns whole string if n exceeds length, empty string if n=0.

### `suffix`
`suffix(str: String, n: Integer) : String`
Last n characters.

### `substring`
`substring(str: String, start: Integer, end: Integer) : String`
Substring from index `start` (inclusive) to `end` (exclusive). Zero-indexed.

### `toUpperCase`
`toUpperCase(str: String) : String`

### `toLowerCase`
`toLowerCase(str: String) : String`

### `replace`
`replace(text: String, target: String, replacement: String) : String`
Replace **all** occurrences of `target` with `replacement`. Plain string replacement (no regex).

### `matches`
`matches(str: String, glob: String) : Bool`
**Wildcard match** (not regex). `*` = any chars, `?` = one char. Case-sensitive.
```
matches("Ethernet1/1", "Ether*")     // true
matches(devName, "*-prod-*")          // contains "-prod-"
```

### `replaceMatches`
`replaceMatches(text: String, glob: String, replacement: String) : String`
Replace all wildcard-matched substrings.

For regex equivalents see `replaceRegexMatches` in Section 14.

---

## 7. Numbers

### `int`
`int(number: Float) : Integer`
Truncate decimal (toward zero). `int(2.9)` → `2`. Same as `floor` for non-negatives.

### `float`
`float(number: Integer) : Float`
Convert integer to float.

### `floor`
`floor(number: Float) : Integer`
Round down to nearest integer.

### `ceil`
`ceil(number: Float) : Integer`
Round up to nearest integer.

### `round`
`round(number: Float) : Integer`
Round to nearest integer.

---

## 8. IP Addresses and Subnets

### `ipAddress`
`ipAddress(str: String) : IpAddress`
Parse v4 or v6 IP from a string.

### `ipv4Address`
`ipv4Address(num: Integer) : IpAddress`
Construct IPv4 from its integer representation. `ipv4Address(0)` = `0.0.0.0`. Range 0 to 2³²-1.

### `ipSubnet`
`ipSubnet(str: String) : IpSubnet`
`ipSubnet(ipAddress: IpAddress, prefixLength: Integer) : IpSubnet`
`ipSubnet(ipAddress: IpAddress, netmask: IpAddress) : IpSubnet`
Construct a subnet three ways.

### `address`
`address(subnet: IpSubnet) : IpAddress`
The IP address part of a subnet (preserves host bits).

### `networkAddress`
`networkAddress(subnet: IpSubnet) : IpAddress`
The subnet's network address (host bits cleared).

### `broadcastAddress`
`broadcastAddress(subnet: IpSubnet) : IpAddress`
The subnet's broadcast address (host bits set).

### `toNumber`
`toNumber(ipAddr: IpAddress) : Integer`
Convert IPv4 to its integer value. **IPv4 only** — fails on IPv6.

### `isIPv4`
`isIPv4(address: IpAddress) : Bool`
`isIPv4(subnet: IpSubnet) : Bool`

### `isIPv6`
`isIPv6(address: IpAddress) : Bool`
`isIPv6(subnet: IpSubnet) : Bool`

---

## 9. MAC Addresses

### `macAddress`
`macAddress(str: String) : MacAddress`
Accepts multiple formats: `aa:bb:cc:dd:ee:ff`, `aabb.ccdd.eeff`, `aabbcc.ddeeff`.

### `ouiVendors`
`ouiVendors(mac: MacAddress) : Bag<Vendor>`
Returns vendors associated with the OUI portion of the MAC. May return multiple (e.g., HP and Aruba share some OUIs).

### `ouiAssignee`
`ouiAssignee(mac: MacAddress) : String?`
Organization name from IEEE OUI database. Returns null if unknown.

---

## 10. Date, Timestamp, Duration

### `date`
`date(text: String) : Date`
Parse a date from a string (e.g., ISO 8601 date format).

### `timestamp`
`timestamp(text: String) : Timestamp`
Parse a UTC timestamp from ISO 8601 format: `"2000-01-01T00:00:00Z"`.

### `duration`
`duration(text: String) : Duration`
Parse a duration from a string.

### `days`
`days(value: Integer) : Duration`
Construct duration of N days.

### `hours`
`hours(value: Integer) : Duration`
Construct duration of N hours.

### `minutes`
`minutes(value: Integer) : Duration`
Construct duration of N minutes.

### `seconds`
`seconds(value: Integer) : Duration`
Construct duration of N seconds.

---

## 11. Null Handling

### `isPresent`
`isPresent(value: T) : Bool`
True if value is not null. Works on any type T.

---

## 12. Single-Line Pattern Matching

### `patternMatch`
`patternMatch(str: String, pattern: Pattern<T>) : T?`
Match a single string against a pattern. Returns the captured data on success, null on failure.

```
patternMatch(line.text, `interface {iface:string}`)
```

### `patternMatches`
`patternMatches(config: List<ConfigLine>, pattern: Pattern<T>) : Bag<{line: ConfigLine, data: T}>`
Match every config line against a pattern. Returns all successful matches.

```
patternMatches(device.files.config, `tacacs-server host {server:string}`)
```

Each result has `line` (the matched ConfigLine) and `data` (captured fields).

Accepts `Bag<ConfigLine>` for backwards compat (deprecated; will warn). Use `order(...)` if you have a Bag.

---

## 13. Block Pattern Matching

### `blockMatches`
`blockMatches(config: List<ConfigLine>, pattern: PatternBlocks<T>) : Bag<{data: T, blocks: MatchBlocks, diffCount: Integer}>`
Multi-line hierarchical match. Returns all matches with captured data, block metadata, and diff counts.

### `hasBlockMatch`
`hasBlockMatch(config: List<ConfigLine>, pattern: PatternBlocks<T>) : Bool`
True if any block match exists. Faster than counting `blockMatches`.

### `blockDiff`
`blockDiff(config: List<ConfigLine>, pattern: PatternBlocks<T>) : {data: T, blocks: MatchBlocks, diffCount: Integer}`
Returns the single best-fit match plus a diff count showing how far off it was.

### `blockPattern`
`blockPattern(text: String) : PatternBlocks<{}>`
Construct a block pattern from a runtime string (where the literal triple-backtick form doesn't work because the pattern is built dynamically).

### `mergeBlocks`
`mergeBlocks(blockPattern: PatternBlocks<{}>) : PatternBlocks<{}>`
Combine multiple sub-patterns sharing common root structure into a single coherent pattern. Useful when assembling patterns from parts.

### `withOption`
`withOption(pattern: PatternBlocks<T>, option: UnmatchedConfigOption) : PatternBlocks<T>`
`withOption(pattern: PatternBlocks<T>, option: LineMatchingOption) : PatternBlocks<T>`

Modify pattern behavior:
- `UnmatchedConfigOption.FORBID` — equivalent to inline `{%unmatched-config:forbid%}`. Default is `ALLOW`.
- `LineMatchingOption.COMPLETE` — pattern lines must match config lines entirely (not just a prefix). Default is `PREFIX`.

Equivalent forms:
```
pattern1 = ```
interface {string} {eof}
  switchport access vlan {number} {eof}
```;

pattern2 = withOption(```
interface {string}
  switchport access vlan {number}
```, LineMatchingOption.COMPLETE);
```

---

## 14. Regular Expressions

### `regex`
`regex(text: String) : Regex<{}>`
Construct a regex from a runtime string. **Does not support data extraction** — use `re\`...\`` literal syntax for that.

### `hasMatch`
`hasMatch(text: String, regex: Regex<T>) : Bool`
True iff the regex matches somewhere in the text.

### `match`
`match(text: String, regex: Regex<T>) : T?`
First (or only) match's captured data, or null.

### `regexMatches`
`regexMatches(text: String, regex: Regex<T>) : List<{string: String, start: Integer, end: Integer, data: T}>`
All matches in left-to-right order. Each has:
- `string` — matched substring
- `start`, `end` — char offsets (zero-based)
- `data` — capture groups as a record

### `replaceMatches`
`replaceMatches(text: String, glob: String, replacement: String) : String`
Replace all wildcard-matched (not regex) substrings. See `matches` in Section 6.

### `replaceRegexMatches`
`replaceRegexMatches(text: String, regex: Regex<T>, replacement: String) : String`
Replace all regex matches with `replacement` (literal string; no backreferences supported).

---

## 15. Configuration Parsing

### `parseConfigBlocks`
`parseConfigBlocks(os: OS, text: String) : List<ConfigLine>`
Parse arbitrary text (e.g., raw command output) into a List of ConfigLine records that can be passed to block pattern matchers.

For `OS.PAN_OS`, no lines are skipped. For other OSes, lines that look like comments or pre-config noise are filtered out:
- Blank lines
- Lines starting with `!`, `#`, `;`, `%`
- "Building configuration..." (any case)
- "Current configuration :" (any case)
- "Using N bytes of M..." preamble

This is the bridge between raw CLI output (`device.outputs.commands[i].response`) and block-pattern matching.

### `sourceConfigText`
`sourceConfigText(value: T) : String`
For any type `T`. Returns the original configuration text snippet that produced the given value in the data model. Useful for showing operators the literal source line.

---

## 16. JSON

### `extractJson`
`extractJson[T](json: String) : T`
Extract a typed NQE value from a JSON string. Type given in square brackets before the call.

```
extractJson[Integer]("1")                          // 1
extractJson[Bool]("true")                          // true
extractJson[String]("\"foo\"")                     // "foo"
extractJson[IpAddress]("\"192.168.0.1\"")          // ipAddress
extractJson[List<Integer>]("[1, 2, 3]")            // List
extractJson[{name: String, age: Integer}]("...")   // Record
```

OneOf types are not supported.

### `splitJsonObjects`
`splitJsonObjects(json: String) : List<String>`
Splits a JSON array string into a List of individual JSON object strings (each still as a String, to be further parsed with `extractJson`). Useful when device CLI returns a JSON array and you want to handle each element.

---

## 17. Interface Lookup

### `findInterface`
`findInterface(device: Device, ifaceName: String) : { interface: Iface, subInterface: SubInterface? }?`

**Looks up an interface by any of its names** (canonical, aliases, abbreviated forms). Returns:
- `null` — name didn't match any interface or sub-interface on this device
- `{interface: Iface, subInterface: null}` — matched a top-level interface
- `{interface: Iface, subInterface: SubInterface}` — matched a sub-interface

Critical for correlating raw command output (which often uses abbreviated names like "Po3", "Eth1/1") back to the structured data model (which uses canonical names like "port-channel3", "Ethernet1/1"). Cleaner than matching against `Iface.aliases` manually.

```
let result = findInterface(device, "Po3")
where isPresent(result)
select { iface: result.interface.name }
```

---

## 18. Stringification and Display

### `toString`
`toString(value: T) : String`
Generic string conversion. Works on any type.

### `toStringTruncate`
`toStringTruncate(value: T) : String`
Same as `toString` but caps very long output. NQE auto-applies this to non-simple values in `select` clauses (records, nested lists).

### `withInfoStatus`
`withInfoStatus(value: T, infoStatus: InfoStatus) : T`
Tag a value with an info status (`OK`, `WARNING`, `ERROR`) for display in verification results. The value itself is unchanged, but UI surfaces the status alongside it.

Supported value types: `String`, `Integer`, `Float`, `Bool`, `IpAddress`, `IpSubnet`, `MacAddress`, `Date`, `Timestamp`, `Duration`.

```
select {
  device: device.name,
  mtu: withInfoStatus(iface.mtu, if iface.mtu == 1500 then InfoStatus.OK else InfoStatus.WARNING)
}
```

---

## Notable Things Missing from the Standard Library

NQE intentionally lacks several functions common in other languages. Use the alternatives shown:

| What you want | NQE alternative |
|---|---|
| `split(s, sep)` | `regexMatches(s, re\`pattern\`)` or `patternMatches` with `parseConfigBlocks` |
| `contains(s, substr)` | `matches(s, "*substr*")` or `hasMatch(s, re\`substr\`)` |
| `startsWith(s, prefix)` | `prefix(s, length(prefix)) == "..."` or `hasMatch(s, re\`^prefix\`)` |
| `endsWith(s, suffix)` | `suffix(s, length(suffix)) == "..."` or `hasMatch(s, re\`suffix$\`)` |
| `trim(s)` | No built-in. Use `replaceRegexMatches(s, re\`^\s+|\s+$\`, "")`. |
| `toInteger(s)` / `parseInt(s)` | No String→Integer built-in. `int(...)` is **Float→Integer only**. Two working idioms: `extractJson[Integer](s)` (capitalized `Integer`) or `patternMatch(s, \`{n:number}\`)` (lowercase `number` inside the pattern literal). Same result type; the spelling differs by context — see the capture-type note in `NQE_Syntax_and_Logic.md`. Note: CSV columns are already typed by inference, so a numeric CSV column needs no conversion at all. |
| `flatten(list)` | Use nested `foreach`: `foreach inner in outer foreach x in inner select x` |
| `map(list, fn)` | Use `foreach x in list select fn(x)` |
| `filter(list, pred)` | Use `foreach x in list where pred(x) select x` |
| `reduce(list, fn, init)` | No built-in. Restructure with `group by` if possible. |
| Mutable variables | Not supported. Use `let` for rebinding within comprehensions. |
| `dict` / `map` types | Not supported. Use records (static) or comprehension-built lookups. |
