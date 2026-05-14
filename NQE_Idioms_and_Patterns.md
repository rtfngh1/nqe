# NQE Idioms and Patterns

This file captures the *non-obvious* patterns for writing effective NQE queries — the things you'd only learn by reading many worked examples. The other reference files document what the primitives are; this file documents how to combine them.

Each idiom shows:
- **When** to reach for it
- **The pattern**, in skeleton form
- **A worked example**
- **Pitfalls / variations**

---

## Table of Contents

1. [Joining one collection to another by a key field](#1-joining-one-collection-to-another-by-a-key-field)
2. [Joining raw CLI output back to the structured model via `aliases`](#2-joining-raw-cli-output-back-to-the-structured-model-via-aliases)
3. [Null-safe transformation via `the(foreach x in [x] ...)`](#3-null-safe-transformation-via-theforeach-x-in-x-)
4. [Pulling a raw show-command response off a device](#4-pulling-a-raw-show-command-response-off-a-device)
5. [Parsing arbitrary text with `parseConfigBlocks` + `blockMatches`](#5-parsing-arbitrary-text-with-parseconfigblocks--blockmatches)
6. [Matching nested config (parent + child lines)](#6-matching-nested-config-parent--child-lines)
7. [Aggregating with `group ... by ... as ...`](#7-aggregating-with-group--by--as-)
8. [Finding "things that appear in multiple places" (uniqueness violations)](#8-finding-things-that-appear-in-multiple-places-uniqueness-violations)
9. [Handling OneOf types with `when ... is ... -> ...`](#9-handling-oneof-types-with-when--is---)
10. [Filtering nulls out of a comprehension](#10-filtering-nulls-out-of-a-comprehension)
11. [Looking up a unique record from a collection](#11-looking-up-a-unique-record-from-a-collection)
12. [Producing a comma-separated string from a collection](#12-producing-a-comma-separated-string-from-a-collection)
13. [Reusable helpers via top-level functions](#13-reusable-helpers-via-top-level-functions)
14. [Sharing code via `import` and `@fwd` library](#14-sharing-code-via-import-and-fwd-library)
15. [Annotating a query with `@primaryKey`](#15-annotating-a-query-with-primarykey)
16. [Extracting "everything between X and Y" with negative lookahead in patterns](#16-extracting-everything-between-x-and-y-with-negative-lookahead-in-patterns)
17. [Choosing CDP/LLDP — the full neighbor-discovery pattern](#17-choosing-cdplldp--the-full-neighbor-discovery-pattern)
18. [Anti-patterns: things that look right but aren't](#18-anti-patterns-things-that-look-right-but-arent)

---

## 1. Joining one collection to another by a key field

**When:** You have a collection of records that reference another collection by name/ID and need to combine them.

**Pattern:**
```
foreach a in collectionA
foreach b in collectionB
where b.someKey == a.someKey
select { ... a..., ... b... }
```

**Worked example — MTU mismatch between two physically connected interfaces:**
```
foreach d1 in network.devices
foreach i1 in d1.interfaces
foreach link in i1.links
foreach d2 in network.devices
where d2.name == link.deviceName
foreach i2 in d2.interfaces
where i2.name == link.ifaceName
where isPresent(i1.mtu) && isPresent(i2.mtu)
select {
  device1: d1.name, iface1: i1.name, mtu1: i1.mtu,
  device2: d2.name, iface2: i2.name, mtu2: i2.mtu,
  violation: i1.mtu != i2.mtu
}
```

**Notes:**
- NQE has no `JOIN` keyword. Joining is just nested `foreach` + `where`.
- Order of `foreach` clauses matters for readability but not correctness — the query engine evaluates the cross product and filters.
- Always check `isPresent()` on nullable fields before comparing them.

---

## 2. Joining raw CLI output back to the structured model via `aliases`

**When:** You've parsed something out of a `show` command response and need to correlate it with an interface in `device.interfaces`. The raw output uses one name (`Eth1/1`); the structured model uses another (`Ethernet1/1`).

**Pattern:**
```
let parsedItems = (
  foreach match in patternMatches(parsedConfig, somePattern)
  select { interfaceName: match.data.interface, ... }
)

foreach interface in device.interfaces
let matchedItem = the(
  foreach p in parsedItems
  where p.interfaceName in interface.aliases   // <-- the join
  select p
)
...
```

**Why `aliases`:** `Iface.aliases: Bag<String>` is the set of all names that refer to the same interface. On Cisco, `"eth1"` and `"Ethernet1"` are both in the aliases bag for that interface. Matching raw text against `interface.name` directly is brittle; matching against `interface.aliases` is correct.

**Pitfall:** You may need to strip trailing commas or whitespace from the parsed value before checking membership: `replace(blockMatch.data.interface, ",", "")`.

**Pitfall — case and parent/child split:** `aliases` casing is not guaranteed consistent across vendors, so lowercase both sides before comparing. Also, a subinterface's variant names may live on the `SubInterface.aliases` bag *or* only on the parent `Iface.aliases` bag depending on vendor — check both. When you need to compare two differently-formatted names (e.g. a CSV value vs. a value parsed from another source) and decide if they are the *same* interface, resolve each to a canonical key rather than comparing directly:
```
// Resolve a (device, candidate-name) pair to a stable key, or null if no match.
resolveSubIntKey(device : Device, candidate : String) =
  the(foreach iface in device.interfaces
      foreach subint in iface.subinterfaces
      where toLowerCase(candidate) in (foreach a in subint.aliases select toLowerCase(a))
         || toLowerCase(candidate) in (foreach a in iface.aliases   select toLowerCase(a))
         || toLowerCase(candidate) == toLowerCase(subint.name)
         || toLowerCase(candidate) == toLowerCase(iface.name)
      select toLowerCase(subint.name));

// Two names match iff they resolve to the same key; null key => no match => treat as mismatch.
```

---

## 3. Null-safe transformation via `the(foreach x in [x] ...)`

**When:** You have a possibly-null value and want to transform it without crashing when null. NQE has no `if let` or monadic bind; this idiom fills that gap.

**Pattern:**
```
result = the(
  foreach x in [maybeNullValue]
  where isPresent(x)
  let transformed = doSomething(x)
  select transformed
);
```

**Worked example — format a CDP command response only if it's present:**
```
formatNxosCdp(cdpOutput) =
  the(foreach cdpOutput in [cdpOutput]
      where isPresent(cdpOutput)
      let result = replace(cdpOutput, "\n", "\n  ")
      let result = replace(result, "\n  Device ID:", "\nDevice ID:")
      select parseConfigBlocks(OS.NXOS, result));
```

**How it works:**
1. Wrap the nullable value in a singleton list `[x]`.
2. Iterate it with `foreach` so you can use `let` (which isn't allowed outside a comprehension).
3. Guard with `where isPresent(x)` — produces an empty bag if null.
4. `the()` unwraps the result: returns the single element if present, else null.

**Alternative for simpler cases:** Use `if isPresent(x) then ... else null : ResultType`. Use the `the(foreach...)` idiom when you need multiple `let` bindings in the transformation chain.

---

## 4. Pulling a raw show-command response off a device

**When:** The structured model doesn't expose what you need, and you want the raw text of a CLI command response.

**Path:** `device.outputs.commands` is a `Bag<Command>`. Each `Command` has:
- `commandType: CommandType` — enum: `CDP`, `LLDP`, `CONFIG`, `VERSION`, `INVENTORY`, `INTERFACES`, `HOSTNAME`, `FAILOVER`, `EVPN`, `OTV`, `UPTIME`, `CUSTOM`
- `commandText: String?` — only set when `commandType == CUSTOM`
- `response: String` — the raw text

**Pattern:**
```
let cdpOutput = the(
  foreach command in device.outputs.commands
  where command.commandType == CommandType.CDP
  select command.response
)
```

**Notes:**
- Use `the()` because there's typically zero or one command of a given type per device.
- For `CUSTOM` commands, filter on `commandText` as well: `where command.commandType == CommandType.CUSTOM && command.commandText == "show foo"`.
- The result may be null if the device wasn't collected for that command type. Always pair with `isPresent()` before parsing.

---

## 5. Parsing arbitrary text with `parseConfigBlocks` + `blockMatches`

**When:** You have a raw multi-line string (typically from `device.outputs.commands`) and want to apply block-pattern matching to it.

**Signatures:**
- `parseConfigBlocks(os: OS, text: String) : List<ConfigLine>`
- `blockMatches(config: List<ConfigLine>, pattern: PatternBlocks<T>) : Bag<{data: T, blocks: MatchBlocks, diffCount: Integer}>`

**Pattern:**
```
parsedBlocks = parseConfigBlocks(OS.NXOS, rawText);

foreach match in blockMatches(parsedBlocks, myBlockPattern)
select { ... match.data.someField ... }
```

**Worked example — parse NX-OS CDP output for platform info:**
```
nxosCdpPattern = ```
Device
  Platform: {platform:((!"Capabilities:" string)*)} Capabilities: {capabilities:(string*)}
  Interface: {interface:string}
```;

foreach blockMatch in blockMatches(parsedCdpOutput, nxosCdpPattern)
let platform = join(" ", blockMatch.data.platform)
select {
  interface: blockMatch.data.interface,
  platform: platform
}
```

**Important about `parseConfigBlocks`:**
- The OS parameter affects which lines get ignored (e.g., comments starting with `!`, `#`, `;`, `%`, "Building configuration..." preambles).
- For `OS.PAN_OS`, no lines are ignored.
- Pre-process the raw text with `replace()` first if you need to normalize indentation or strip headers (block patterns rely on indentation for hierarchy).

---

## 6. Matching nested config (parent + child lines)

**When:** You want to extract something from a child config line that depends on knowing its parent (e.g., `speed` under `interface`).

**Pattern — using `patternMatches` twice (cleaner):**
```
foreach parentMatch in patternMatches(device.files.config, `parent {name:string}`)
foreach childMatch in patternMatches(parentMatch.line.children, `child {value:number}`)
select {
  parent: parentMatch.data.name,
  value: childMatch.data.value
}
```

**Worked example — interfaces slower than 1Gbps:**
```
foreach device in network.devices
where device.platform.vendor == Vendor.CISCO && device.platform.os == OS.NXOS
foreach ifaceMatch in patternMatches(device.files.config, `interface {iface:string}`)
foreach speedMatch in patternMatches(ifaceMatch.line.children, `speed {speed:number}`)
where speedMatch.data.speed < 1000
select {
  device: device.name,
  iface: ifaceMatch.data.iface,
  speed: speedMatch.data.speed
}
```

**Why this works:** Each `ConfigLine` has a `children: List<ConfigLine>` field. `patternMatches` accepts any `List<ConfigLine>`, including the children of a previously-matched line. This naturally walks the indentation hierarchy.

---

## 7. Aggregating with `group ... by ... as ...`

**When:** You want to roll up multiple records by a shared key — count, sum, list, find max, etc.

**Syntax:** `group valueExpr as valuesVar by keyExpr as keyVar`

After this qualifier, only `valuesVar` and `keyVar` are in scope. Variables from before the `group by` are no longer accessible.

**Pattern — count and aggregate per key:**
```
foreach item in collection
group item.value as values by item.key as key
select {
  key: key,
  count: length(values),
  total: sum(values),
  max: max(values)
}
```

**Worked example — VLANs assigned to more than one device per VRF (IP uniqueness):**
```
foreach device in network.devices
foreach vrf in device.networkInstances
foreach ifaceSubiface in vrf.interfaces
foreach iface in device.interfaces
foreach subIface in iface.subinterfaces
where iface.name == ifaceSubiface.ifaceName && subIface.name == ifaceSubiface.subIfaceName
foreach address in subIface.ipv4.addresses
let location = {device: device.name, iface: iface.name}
group location as locations by {vrf: vrf.name, ip: address.ip} as vrfIp
where length(locations) > 1
select {
  vrf: vrfIp.vrf,
  ip: vrfIp.ip,
  count: length(locations),
  locations: (foreach loc in locations select loc.device + ":" + loc.iface)
}
```

**Notes:**
- The key can be a composite record: `by {a: x, b: y} as compositeKey`.
- The value can be a record too: `group {a: x, b: y} as valueRecords by ...`.
- Use `length(values) > 1` to find duplicates, `> 0` to find anything-matching, `== 1` for unique.

---

## 8. Finding "things that appear in multiple places" (uniqueness violations)

**When:** You want to detect when the same logical thing exists in multiple places (e.g., the same IP on multiple interfaces, the same VLAN ID on multiple devices).

**This is just `group by` (idiom 7) with `length(group) > 1`.**

Common variants:
- **Same IP, multiple interfaces:** `group {iface: i.name} by {ip: address.ip}`
- **Same name, multiple devices:** `group {device: d.name} by {name: thing.name}`
- **Same value, more than one VRF:** `group {vrf: v.name} by {ip: prefix}`

Always check `length(...) > 1` in a `where` clause after `group by`.

---

## 9. Handling OneOf types with `when ... is ... -> ...`

**When:** A field's type is a "tagged union" (OneOf). For example, `SubInterfaceVlan` is either `VLAN_ID(integer)` or `QINQ_ID(string)`. You can't access these as plain fields — you must pattern-match.

**Syntax:**
```
when expression is
  Constructor1(varName) -> useVarName;
  Constructor2 -> someValue;
  otherwise -> defaultValue
```

**Worked example — extract VLAN ID from a subinterface, ignoring QINQ subinterfaces:**
```
let vlan = when subiface.vlan is
             VLAN_ID(v) -> v;
             otherwise -> null : Integer
where isPresent(vlan)
```

**Rules:**
- Cases separated by `;`.
- `otherwise` must be the last case if present.
- For data-bearing constructors, `Constructor(varName)` binds the inner value. For data-less constructors (or to ignore the value), just write `Constructor` with no parens.
- The `null : T` form is essential for type-checking — every branch of `when` must return the same type.

**Examples of where this comes up in the data model:**
- `SubInterfaceVlan` — VLAN_ID vs QINQ_ID
- `NextHopType` — direct vs indirect resolution
- `DeviceSnapshotResult` — `completed`, `collectionFailed(error)`, `processingFailed(error)`

---

## 10. Filtering nulls out of a comprehension

**When:** A `let` binding might produce null and you only want non-null values.

**Pattern:**
```
foreach x in collection
let derived = someOperationThatMayReturnNull(x)
where isPresent(derived)
select { ..., derived: derived }
```

**Common cases:**
- After `patternMatch()` (which returns null when no match)
- After `the()` (which returns null when zero or >1 elements)
- After accessing a nullable field

**With `?.`:** For simple chains, you can use safe navigation:
```
let os = device?.platform?.os
where isPresent(os)
```
This is equivalent to chained `isPresent` checks but more concise.

---

## 11. Looking up a unique record from a collection

**When:** You expect at most one match (e.g., the device named "core-router-1"), and want the record itself, not a collection.

**Pattern:**
```
let target = the(
  foreach x in collection
  where x.matchesCriterion
  select x
)
where isPresent(target)
```

**Use cases:**
- Finding a specific neighbor on an interface
- Finding the global VRF on a device
- Finding the one CDP `Command` record per device

**Pitfall:** `the()` returns null both when there are zero matches AND when there are more than one. If you need to know which, use `length()` first or filter more precisely.

---

## 12. Producing a comma-separated string from a collection

**When:** You want to flatten a list/bag of strings into a single readable field.

**Pattern:** `join(separator, collection)`

**Examples:**
```
join(", ", deviceNames)
join(" | ", aliases)
join("\n", configLines)
```

**Combined with comprehension:**
```
locations: join(", ", foreach loc in locations select loc.device + ":" + loc.iface)
```

**Note:** `join` requires a List or Bag of Strings. Convert non-string values first with `toString()`.

---

## 13. Reusable helpers via top-level functions

**When:** A piece of logic gets used more than once in a query, or you want to give it a meaningful name.

**Pattern:**
```
helperName(param1, param2) = expression;
constantName = value;

foreach x in network.devices
select helperName(x, otherValue)
```

**With type annotations (recommended for clarity and type-checking):**
```
threshold : Integer = 100;
hasManySubInterfaces(iface : Iface) : Bool = length(iface.subinterfaces) > threshold;

foreach device in network.devices
foreach iface in device.interfaces
where hasManySubInterfaces(iface)
select { device: device.name, iface: iface.name }
```

**Rules:**
- Each declaration ends with `;`.
- Zero-parameter functions can omit the `()`: `myConstant = 5;`.
- Type annotations are optional, but if you annotate one parameter, you must annotate all of them.
- For records, you can use structural types: `iface : { subinterfaces: List<SubInterface> }` — accepts any record with at least that field.
- **A function body is a single expression — `let` is not valid in it.** `let` is a comprehension clause only. To get intermediate bindings inside a helper, wrap a one-element comprehension and unwrap with `the(...)`:
  ```
  // WRONG — let in a function body is a syntax error
  canonical(s : String) : String =
    let lower = toLowerCase(s)
    replaceRegexMatches(lower, re`_.*`, "");

  // RIGHT
  canonical(s : String) : String =
    the(foreach x in [0]
        let lower = toLowerCase(s)
        let stripped = replaceRegexMatches(lower, re`_.*`, "")
        select stripped);
  ```
  Without intermediate bindings, a plain expression body is fine — `if`/`then`/`else` and `&&`/`||` chains do not need a comprehension wrapper.

---

## 14. Sharing code via `import` and `@fwd` library

**When:** You want to reuse helpers across multiple queries.

**Defining an exportable module** (file `Shop/Inventory`):
```
export inventory =
  [{ make: "Tesla", model: "3" }, ...];

export doWeLikeMake(make: String) = make in ["Tesla", "McLaren"];
```

**Importing it elsewhere:**
```
import "Shop/Inventory";

foreach car in inventory
where doWeLikeMake(car.make)
select { make: car.make }
```

**Importing from the Forward Library (built-in helpers):**
```
import "@fwd/Interfaces/Interface IPs";

foreach device in network.devices
foreach subnet in getAllIfaceSubnets(device)
select { Device: device.name, Subnet: subnet }
```

**Rules:**
- Paths are absolute (starting from the root of your NQE library).
- Only `export`-marked declarations are visible to importers.
- `@fwd/...` paths reference Forward's built-in library of NQE helpers.

---

## 15. Annotating a query with `@primaryKey`

**When:** Every query that will produce diff-tracked output (verifications, Inventory+ queries) needs a primary key.

**Syntax:**
```
@primaryKey(deviceName, interface)
foreach device in network.devices
foreach iface in device.interfaces
select {
  deviceName: device.name,
  interface: iface.name,
  ...
}
```

**Rules:**
- Goes immediately above the main expression.
- Column names match the output record's field names (case-sensitive).
- Field names with spaces or special chars need quotes: `@primaryKey("Device Name", VRF)`.
- All primary key columns must be present in every result row.
- The combination of primary key columns must be unique across all output rows.
- Annotating with `@primaryKey` is also how you opt into diff tracking.

**`@query` annotation (related):** Marks a named declaration as the main query, often used for parameterized queries:
```
@query
findInterfacesWithSpeed(minSpeed: Integer) =
  foreach device in network.devices
  foreach iface in device.interfaces
  where iface.ethernet.negotiatedPortSpeed.speedMbps >= minSpeed
  select { ... };
```

---

## 16. Extracting "everything between X and Y" with negative lookahead in patterns

**When:** A pattern has a variable-length field followed by a known keyword (e.g., a multi-word platform name followed by "Capabilities:").

**Syntax inside a capture group:** `(!"literal" string)*` matches "any word that isn't the literal `literal`, zero or more times."

**Worked example — match everything in "Platform:" up to "Capabilities:":**
```
nxosCdpPattern = ```
Device
  Platform: {platform:((!"Capabilities:" string)*)} Capabilities: {capabilities:(string*)}
  Interface: {interface:string}
```;
```

This captures the multi-word platform string (e.g., `"cisco WS-C3850-48P"`) into `platform` as a `List<String>`. Use `join(" ", blockMatch.data.platform)` to assemble it back into a single string.

**Other repetition quantifiers:**
- `(pattern)*` — zero or more, returns a List
- `(pattern)+` — one or more, returns a List
- `pattern1 | pattern2` — alternation, returns `{left: ..., right: ...}` (one will be null)
- `!pattern` — negation, consumes nothing, returns empty record
- `empty` — always matches, consumes nothing, useful for optional pattern items

---

## 17. Choosing CDP/LLDP — the full neighbor-discovery pattern

**When:** You need neighbor information from CDP or LLDP.

**Three different paths in the data model — choose carefully:**

| Path | Type | What you get |
|---|---|---|
| `Iface.links` | `Bag<PhysicalLink>` | Just `deviceName` + `ifaceName` of physically-linked interfaces. **Topology only.** |
| `Iface.cdp.neighbors` | `Bag<DeviceDiscoveryNeighbor>` | CDP neighbors with `deviceName` + `portName`. No platform info. |
| `Iface.lldp.neighbors` | `Bag<DeviceDiscoveryNeighbor>` | LLDP neighbors with `deviceName` + `portName`. No platform info. |

The structured paths above give you **identity and topology** but **not platform/version/capabilities**. For those, you must parse the raw CDP/LLDP output from `device.outputs.commands`.

**Combined pattern — neighbor identity + platform parsed from raw output:**
```
nxosCdpPattern = ```
Device
  Platform: {platform:((!"Capabilities:" string)*)} Capabilities: {capabilities:(string*)}
  Interface: {interface:string}
```;

foreach device in network.devices
where device.platform.os in [OS.IOS_XE, OS.NXOS]

let cdpOutput = the(foreach c in device.outputs.commands
                    where c.commandType == CommandType.CDP
                    select c.response)
let parsedCdp = the(foreach o in [cdpOutput]
                    where isPresent(o)
                    select parseConfigBlocks(OS.NXOS, o))

let cdpNeighborsWithPlatform = (foreach p in [parsedCdp]
                                where isPresent(p)
                                foreach m in blockMatches(p, nxosCdpPattern)
                                select {
                                  interface: m.data.interface,
                                  platform: join(" ", m.data.platform)
                                })

foreach interface in device.interfaces
foreach neighbor in interface.cdp.neighbors + interface.lldp.neighbors
let platformInfo = the(foreach np in cdpNeighborsWithPlatform
                       where np.interface in interface.aliases
                       select np.platform)

select {
  device: device.name,
  localInt: interface.name,
  neighborName: neighbor.deviceName,
  neighborPort: neighbor.portName,
  neighborPlatform: platformInfo
}
```

**Key things to note:**
- `interface.cdp.neighbors + interface.lldp.neighbors` concatenates both — works because both produce `Bag<DeviceDiscoveryNeighbor>`.
- The join from raw-output platform back to structured interface uses `interface.aliases` because raw CDP/LLDP often uses short names (`Eth1/1`) while the structured model uses long names (`Ethernet1/1`).
- Pre-processing the raw text (normalize indentation, strip section headers) is often required before `parseConfigBlocks` — the original Forward example for NX-OS CDP does `replace(text, "\n", "\n  ")` and `replace(text, "\n  Device ID:", "\nDevice ID:")` to make the output match block-pattern indentation rules.

---

## 18. Anti-patterns: things that look right but aren't

### ❌ Using `Iface.links` to get CDP/LLDP *neighbor names*
`PhysicalLink` only has `deviceName` and `ifaceName` — and these refer to *the linked interface*, not the protocol-reported neighbor. For protocol-specific data, use `Iface.cdp.neighbors` and `Iface.lldp.neighbors`.

### ❌ Matching raw CLI interface names against `Iface.name` directly
Raw CDP output says `Eth1/1`; the structured model has `Ethernet1/1`. Match against `Iface.aliases` (a `Bag<String>` of all known names for the interface) instead.

### ❌ Calling `split()` on a string
NQE has no `split()`. Use `patternMatches`, `regexMatches`, or block patterns instead.

### ❌ Using `contains(s, "foo")`
No such function. Use `matches(s, "*foo*")` (wildcard) or `hasMatch(s, regex)`.

### ❌ Using `let` before any `foreach`
`let` requires at least one prior `foreach` qualifier. For top-level constants, use a top-level binding (`x = 5;`) instead.

### ❌ Comparing a `Bag` to a `List` directly (post-NQE 25.11)
This now generates a warning. Convert one side: either use `order by` to make a List, or wrap with `bag(...)` to make a Bag, then compare.

### ❌ Forgetting `null : Type` in `when ... otherwise -> null`
Bare `null` doesn't type-check. Always annotate: `otherwise -> null : Integer`.

### ❌ Skipping `@primaryKey`
Queries without primary keys can't be tracked for diffs. Always add one for verifications or Inventory+ queries.

### ❌ Trying to access a non-existent field on a record
Records are statically typed. Use `record["fieldName"]` for keys with special chars; use `record?.field` for nullable parents.

### ❌ Assuming `the()` returns the first element
`the()` returns null if the collection has zero OR more than one element. It's "the single unique element, if it exists." For "give me one of these," use `limit(orderBy(collection, ...), 1)` and take element 0.
