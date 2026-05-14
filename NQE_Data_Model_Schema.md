# NQE Data Model Schema

Forward Networks NQE data model — the structure of the `network` variable and all types reachable from it. This file documents the **load-bearing types** in full detail and provides an index for the rest.

For language syntax, see `NQE_Syntax_and_Logic.md`. For built-in functions, see `NQE_Standard_Library.md`. For combining these primitives idiomatically, see `NQE_Idioms_and_Patterns.md`.

**Conventions in this file:**
- `Type` = the type name as it appears in NQE
- `Bag<T>` = unordered collection, `List<T>` = ordered collection
- A field marked `(nullable)` may be `null`; check with `isPresent(x)` before accessing
- Field names link conceptually to related types in this file or to the index

---

## Table of Contents

1. [Root: `network`](#root-network)
2. [Device and Platform](#device-and-platform)
3. [Interfaces](#interfaces)
4. [Configuration Files and Command Outputs](#configuration-files-and-command-outputs)
5. [Network Instances (VRFs) and Routing](#network-instances-vrfs-and-routing)
6. [BGP](#bgp)
7. [OSPF](#ospf)
8. [ACLs, NAT, Firewalls](#acls-nat-firewalls)
9. [STP, VLANs, Bridging](#stp-vlans-bridging)
10. [ARP, FHRP, Neighbor Discovery](#arp-fhrp-neighbor-discovery)
11. [Cloud (AWS, Azure, GCP)](#cloud-aws-azure-gcp)
12. [Endpoints, Locations, CVE](#endpoints-locations-cve)
13. [Enumerations Reference](#enumerations-reference)
14. [Complete Type Index](#complete-type-index)

---

## 1. Root: `network`

### `Network`

```
interface Network {
  devices: Bag<Device>;  // Devices in the network, such as routers, switches, and firewalls.
  endpoints: Bag<NetworkEndpoint>;  // Devices collected via a custom operation, such as HTTP, CLI or SNMP.
  locations: Bag<Location>;  // The set of all locations defined in the network.
  cloudAccounts: Bag<CloudAccount>;
  cloudOrganizationalUnits: Bag<OrganizationalUnit>;
  externalSources: ExternalSources;  // Inferred data from structured data sources, such as CSV and JSON sources served over HTTP.
  dataConnectors: Bag<DataConnector>;  // Data made available to the Forward platform by sources outside the network, such as an HTTP service.
  cveDatabase: CveDatabase;
  stigDatabase: StigDatabase;
  extensions: NetworkExtensions;
}
```

---

## 2. Device and Platform

### `Device`

```
interface Device {
  name: String;
  locationName: String?;  // The location name, or null if no location is assigned.
  locationId: String?;  // The location ID or null if no location is assigned.
  groupNames: Bag<String>;  // Names of the device groups that contain this device.
  tagNames: Bag<String>;  // Names of the device tags that contain this device.
  accessLabelNames: Bag<String>;  // Device access labels for this device.
  snapshotInfo: DeviceSnapshotInfo;  // Contains metadata about the inclusion of this device in the selected snapshot. Contains information about the world a...
  ha: Ha;
  system: System;  // System-level attributes of a device, whether maintained by the device or inferred by Forward Networks about the system.
  platform: Platform;
  vlans: Bag<NamedVlanCollection>;  // Globally-defined VLANs on the device. This includes VLANs that are not associated with any interfaces.
  interfaces: Bag<Iface>;
  networkInstances: Bag<NetworkInstance>;
  bgpRib: BgpRib?;
  stp: Stp;
  aclEntries: List<AclEntry>;  // ACL entries defined on the device. The entries are unique based on all their non-lifecycle-data attributes. Note that...
  natEntries: List<NatEntry>;
  hosts: Bag<DeviceHost>;
  cveFindings: Bag<CveFinding>;  // The CVE findings for this device. Includes only the CVEs that impact the device or that do not impact the device on t...
  outputs: Outputs;  // Information about data sources for a device.
  securityZones: Bag<DeviceSecurityZone>;  // Security zones defined on this firewall device. Empty if this device is not a firewall or is a firewall but has no se...
  files: Files;  // Information about config data sources for a device.
}
```

### `Platform`

```
interface Platform {
  deviceType: DeviceType;
  vendor: Vendor;
  model: String?;
  os: OS;
  osVersion: String?;
  osSupport: OsSupport?;  // End-of-life dates for the OS of this device. Absent if the OS value is not ARISTA_EOS, CHECKPOINT, CLOUD_GENIX, F5, F...
  components: Bag<DevicePart>;  // A (non-comprehensive) list of components. On all platforms, the main device component and its serial number are avail...
  managementIps: Bag<IpAddress>;
}
```

### `System`

```
interface System {
  hostNames: Bag<String>;  // Configured host names on the device
  otherNames: Bag<String>;  // Other names that the device is also known by in the snapshot. Usually obtained from configuration settings such as ...
  physicalName: String;  // Name of the physical device of which this modeled device is a part. Differs from the device name only if the device i...
  uptimeSeconds: Integer?;  // Uptime for this device in seconds. Present for systems that were successfully collected and have one of these operati...
  uptime: Duration?;  // Uptime for this device. Present for systems that were successfully collected and have one of these operating systems:...
}
```

### `DeviceSnapshotInfo`

```
interface DeviceSnapshotInfo {
  result: DeviceSnapshotResult;
  collectionIp: IpAddress?;  // The user-provided IP address used to collect for this device. There are some special cases. This value is (1) the DNS...
  collectionTime: Timestamp?;  // The approximate time at which collection occured for this device in this snapshot. Absent for synthetic devcies, when...
  backfillTime: Timestamp?;  // If the data for this device has been backfilled from a previous snapshot, then the approximate time at which that dat...
}
```

### `DeviceSnapshotResult`

Enum with 0 values:

| Value | Description |
|---|---|

---

## 3. Interfaces

### `Iface`

```
interface Iface {
  name: String;  // The name of the interface.
  interfaceType: IfaceType;  // The type of the interface.
  layer: Layer;  // Denotes whether this is a Layer 2 (physical) or Layer 3 (logical) interface.
  mtu: Integer?;  // The max transmission unit size in octets for the physical interface. Note that this is the L2 MTU, which is normalize...
  loopbackMode: Bool;  // When set to true, the interface is logically looped back, such that packets that are forwarded via the interface are ...
  aliases: Bag<String>;  // The set of all names that refer to this interface. For example, on Cisco, an interface named "eth1" might also be ref...
  description: String?;  // A textual description of the interface.
  adminStatus: AdminStatus;  // The desired state of the interface. Here, it reflects the administrative state as set by enabling or disabling the in...
  operStatus: OperStatus;  // The current operational state of the interface.
  subinterfaces: Bag<SubInterface>;  // The list of subinterfaces (logical interfaces) associated with a physical interface.
  ethernet: Ethernet;  // Ethernet-specific configuration and state of the interface.
  acls: IfaceAcls;  // Access control list details specific to this interface.
  routedVlan: RoutedVlan?;  // Non-null when the interface is a logical interface providing L3 routing for VLANs.
  bridge: Bridge?;  // Non-null when the interface is a bridge (BVI, BDI, etc.)
  aggregation: Aggregation?;  // Non-null when the interface is set to type IF_AGGREGATE.
  tunnel: Tunnel?;  // In the case that the interface is logical tunnel interface, the parameters for the tunnel are specified within this s...
  teTunnel: TeTunnel?;  // In the case that the interface is a logical Traffic Engineering (TE) tunnel interface, the parameters for the TE tunn...
  links: Bag<PhysicalLink>;  // The other interfaces that this interface connects to.
  cdp: DeviceDiscoveryIfaceInfo;
  lldp: DeviceDiscoveryIfaceInfo;
}
```

### `SubInterface`

Subinterface data for logical interfaces associated with a given interface.

```
interface SubInterface {
  name: String;  // The system-assigned name for the sub-interface. This MAY be a combination of the base interface name and the subinter...
  layer: Layer;  // Denotes whether this is a Layer 2 (physical) or Layer 3 (logical) interface.
  aliases: Bag<String>;  // The set of all names that refer to this subinterface. For example, on Cisco, an interface named "eth1.100" might also...
  description: String?;  // A textual description of the interface.
  adminStatus: AdminStatus;  // The desired state of the interface. Here, it reflects the administrative state as set by enabling or disabling the in...
  operStatus: OperStatus;  // The current operational state of the interface.
  acls: IfaceAcls;  // Access control list details specific to this interface.
  vlan: SubInterfaceVlan?;
  ipv4: IfaceIpv4Info;  // Configuration and state for IPv4 interfaces.
  ipv6: IfaceIpv6Info;  // Configuration and state for IPv6 interfaces.
  switchedVlans: SwitchedSubInterfaceVlans?;  // Switched VLAN configuration of the subinterface. Non-null if this interface is a switch-subinterface.
  networkInstanceName: String?;  // The network instance (i.e. VRF) that this interface is part of. Non-null if this interface is not a switch-subinterface.
}
```

### `IfaceIpv4Info`

The IPv4 addresses configured on an interface.

```
interface IfaceIpv4Info {
  addresses: Bag<Ipv4Address>;
  fhrpAddresses: Bag<Ipv4Address>;
  neighbors: Bag<ArpEntry>;  // IPv4 address and link-layer address of neighbors discovered on this interface.
  fhrp: IfaceFhrp;
  multicastMode: MulticastMode?;  // The Protocol-Independent Multicast (PIM) mode enabled on this interface for IPv4 multicast traffic. if PIM is not ena...
}
```

### `IfaceIpv6Info`

The IPv6 addresses configured on an interface.

```
interface IfaceIpv6Info {
  addresses: Bag<Ipv6Address>;
  fhrpAddresses: Bag<Ipv6Address>;
  neighbors: Bag<ArpEntry>;  // IPv6 address and link-layer address of neighbors discovered on this interface.
  fhrp: IfaceFhrp;
  multicastMode: MulticastMode?;  // The Protocol-Independent Multicast (PIM) mode enabled on this interface for IPv6 multicast traffic. Absent if PIM is ...
}
```

### `Ipv4Address`

```
interface Ipv4Address {
  ip: IpAddress;  // The IPv4 address on an interface.
  prefixLength: Integer;  // The length of the subnet prefix.
}
```

### `Ipv6Address`

```
interface Ipv6Address {
  ip: IpAddress;  // The IPv6 address on an interface.
  prefixLength: Integer;  // The length of the subnet prefix.
}
```

### `Ethernet`

```
interface Ethernet {
  macAddress: MacAddress?;  // MAC address of the Ethernet interface.
  negotiatedDuplexMode: DuplexMode;  // This value shows the duplex mode that has been negotiated.
  negotiatedPortSpeed: PortSpeed;  // This value shows the interface speed that has been negotiated.
  speedMbps: Integer?;  // The effective speed in Mbps of the interface. If interface bandwidth is statically configured, then the configured ba...
  aggregateId: String?;  // Specifies the logical aggregate interface to which this interface belongs.
  switchedVlan: SwitchedVlan?;
}
```

### `RoutedVlan`

```
interface RoutedVlan {
  vlan: Integer;  // References the VLAN for which this IP interface provides routing services -- similar to a switch virtual interface (S...
  ipv4: IfaceIpv4Info;
  ipv6: IfaceIpv6Info;
  networkInstanceName: String;  // The network instance (i.e. VRF) that this interface is part of.
}
```

### `Bridge`

Bridge domain related data for a bridge interface.

```
interface Bridge {
  memberNames: Bag<String>;  // The members of the bridge interface.
  ipv4: IfaceIpv4Info;  // The IPv4 addresses configured on the bridge interface.
  ipv6: IfaceIpv6Info;  // The IPv6 addresses configured on the bridge interface.
  vlan: Integer?;  // The VLAN of the bridge interface. This VLAN will be pushed on packets while sending them out of this bridge interface...
  networkInstanceName: String;  // The network instance (i.e. VRF) that this interface is part of.
}
```

### `Aggregation`

```
interface Aggregation {
  memberNames: Bag<String>;  // List of actual, current member interfaces for the aggregate, expressed as references to existing interfaces.
  configuredMemberNames: Bag<String>;  // List of configured member interfaces for the aggregate.
  switchedVlan: SwitchedVlan?;
}
```

### `Tunnel`

Configuraton parameters relating to a tunnel interface.

```
interface Tunnel {
  src: IpAddress;  // The source address for the tunnel.
  dst: IpAddress;  // The destination address for the tunnel.
  ipv4: IfaceIpv4Info;
  ipv6: IfaceIpv6Info;
  networkInstanceName: String;  // The network instance (i.e. VRF) that this interface is part of.
}
```

### `IfaceAcls`

Access control list details for an interface.

```
interface IfaceAcls {
  inboundAclNames: List<String>;  // Names of the ACL entries that secure inbound traffic to this interface. The ACLs are applied in the order in which th...
  outboundAclNames: List<String>;  // Names of the ACL entries that secure outbound traffic from this interface. The ACLs are applied in the order in which...
}
```

### `PhysicalLink`

```
interface PhysicalLink {
  deviceName: String;
  ifaceName: String;
}
```

### `DeviceDiscoveryIfaceInfo`

```
interface DeviceDiscoveryIfaceInfo {
  neighbors: Bag<DeviceDiscoveryNeighbor>;
}
```

### `DeviceDiscoveryNeighbor`

Information about a CDP or LLDP neighbor. Note that the neighbor may not be a collected device. For example, it may be an end host.

```
interface DeviceDiscoveryNeighbor {
  deviceName: String;
  portName: String;
}
```

---

## 4. Configuration Files and Command Outputs

### `Files`

Information about config data sources for a device.

```
interface Files {
  config: List<ConfigLine>?;  // Lines of config for a device. Some lines from the original config are not included. See the parseConfigBlock document...
  panos: PanosFiles?;  // PANOS-specific files
}
```

### `ConfigLine`

Information about a single line in a device config file.

```
interface ConfigLine {
  text: String;  // The text of the line.
  lineNumber: Integer;  // The line number (starting from zero) on which the line appears within the configuration.
  children: List<ConfigLine>;  // Lines of config that are nested directly under this line. For example, on Cisco NX-OS devices, the children are the s...
}
```

### `Outputs`

```
interface Outputs {
  commands: Bag<Command>;
  snmpOutputs: Bag<OidOutput>;  // Collected custom SNMP OID outputs for the device.
  bluecat: BluecatOutputs?;
}
```

### `Command`

```
interface Command {
  commandType: CommandType;
  commandText: String?;  // The command that was used to collect this source. Only present for CUSTOM commands.
  response: String;  // The text value returned in response to the command.
}
```

---

## 5. Network Instances (VRFs) and Routing

### `NetworkInstance`

```
interface NetworkInstance {
  name: String;  // A unique name identifying the network instance. The value is either "default" or a unique VRF name.
  instanceType: NetworkInstanceType;  // Type of network instance.
  afts: Afts;  // The abstract forwarding tables (AFTs) that are associated with the network instance.
  interfaces: Bag<IfaceSubIface>;  // The interfaces that are associated with this network instance.
  vlans: Bag<Vlan>;  // VLANs that are associated with this network instance. Only populated for the "default" network instance and only incl...
  protocols: Bag<NetworkInstanceProtocol>;  // The routing protocols that are enabled for this network instance.
  fdb: NetworkInstanceFdb;  // Forwarding database for this network instance.
}
```

### `Afts`

The abstract forwarding tables (AFTs) that are associated with the network instance. An AFT is instantiated per-protocol running within the network-instance - such that one exists for IPv4 Unicast, IPv6 Unicast, MPLS, L2 forwarding entries, etc. A forwarding entry within the FIB has a set of next-hops, which may be a reference to an entry within another table - e.g., where a Layer 3 next-hop has an associated Layer 2 forwarding entry.

```
interface Afts {
  ipv4Unicast: IpUnicast?;  // The abstract forwarding table for IPv4 unicast. Entries within this table are uniquely keyed on the IPv4 unicast dest...
  ipv6Unicast: IpUnicast?;  // The abstract forwarding table for IPv6 unicast. Entries within this table are uniquely keyed on the IPv6 unicast dest...
}
```

### `IpUnicast`

```
interface IpUnicast {
  ipEntries: Bag<IpEntry>;  // List of the IP unicast entries within the abstract forwarding table. This list is keyed by the destination IPv4/IPv6 ...
}
```

### `IpEntry`

```
interface IpEntry {
  prefix: IpSubnet;  // Reference to the IP destination prefix which must be matched to utilise the AFT entry.
  nextHops: Bag<NextHop>;  // The list of next-hops that are to be used for entry within the AFT table. The structure of each next-hop is address f...
}
```

### `NextHop`

```
interface NextHop {
  weight: Integer;  // The weight of the next-hop. Traffic is balanced according to the ratio described by the relative weights of the next ...
  ipAddress: IpAddress?;  // The IP address of the next-hop system.
  macAddress: MacAddress?;  // The MAC address of the next-hop if resolved by the local network instance.
  vrf: String?;  // The next VRF to process the packet.
  poppedMplsLabels: Bag<Integer>;  // The MPLS labels to be popped from the packet when switched by the system. A swap operation is reflected by entries in...
  pushedMplsLabels: Bag<Integer>;  // The MPLS labels to be pushed from the packet when switched by the system. A swap operation is reflected by entries in...
  interfaceName: String?;  // The interface on this system to get to the next-hop.
  subInterfaceName: String?;  // The sub-interface on this system to get to the next-hop.
  nextHopType: NextHopType;  // Type of next-hop.
  encapsulateHeader: EncapsulationHeaderType?;  // When forwarding a packet to the specified next-hop the local system performs an encapsulation of the packet - adding ...
  originProtocol: OriginProtocol;  // The protocol from which the AFT entry was learned.
}
```

### `NetworkInstanceProtocol`

```
interface NetworkInstanceProtocol {
  identifier: RoutingProtocolType;  // The protocol identifier for the instance. Only identifier currently possible is BGP.
  bgp: Bgp?;  // Top-level configuration and state for the BGP router. Present if identifer is BGP.
  ospf: Ospf?;  // Top-level state for the OSPF router. Present if identifer is OSPF.
}
```

### `NetworkInstanceFdb`

```
interface NetworkInstanceFdb {
  macEntries: Bag<MacEntry>;  // Learned MAC addresses. Present only in default network instance.
}
```

---

## 6. BGP

### `Bgp`

```
interface Bgp {
  neighbors: Bag<BgpNeighbor>;  // List of BGP neighbors configured on the local system, uniquely identified by peer IPv4 or IPv6 address.
  routerId: IpAddress?;  // An identifier for the BGP sessions in this network instance.
  asNumber: Integer?;  // AS number of this network instance. Present for devices with OS ACOS, APIC, ARISTA_EOS, ASA, CUMULUS, EXTREME_NOS, FX...
}
```

### `BgpNeighbor`

```
interface BgpNeighbor {
  neighborAddress: IpAddress;  // Address of the BGP peer, either in IPv4 or IPv6
  peerDeviceName: String?;  // Device name of the BGP peer if one could be discovered in the snapshot, otherwise absent.
  peerVrf: String?;  // The VRF under which this connection was configured on the peer's device. Absent if peerDeviceName is absent.
  peerRouterId: IpAddress?;  // Router ID of the peer. Present for devices with OS ACOS, APIC, ARISTA_EOS, ASA, CUMULUS, EXTREME_NOS, F5, FORTINET, F...
  sessionState: BgpSessionState?;  // Operational state of the BGP peer. Absent if enabled is false or if the data is not available.
  enabled: Bool;  // Whether the BGP peer is enabled. In cases where enabled is false, the local system does not initiate connections to t...
  description: String?;  // Description of the neighbor.
  peerAS: Integer;  // AS number of the peer.
  localAS: Integer?;  // The secondary AS number of the local device if a local AS is configured for an eBGP peer. Absent if no local AS is co...
  peerType: PeerType?;  // Explicitly designate the neighbor as internal (iBGP) or external (eBGP).
  statistics: BgpNeighborStatistics?;  // Absent if the session state is not ESTABLISHED.
}
```

### `BgpRib`

Defines a data model for representing BGP routing table contents.

```
interface BgpRib {
  afiSafis: Bag<AfiSafi>;  // Address families.
}
```

### `AfiSafi`

```
interface AfiSafi {
  afiSafiName: AfiSafiType;  // The afi-safi type.
  neighbors: Bag<AfiSafiNeighbor>;  // List of neighbors (peers) of the local BGP speaker.
}
```

### `AfiSafiNeighbor`

```
interface AfiSafiNeighbor {
  neighborAddress: IpAddress;  // The address of the neighbor (peer).
  adjRibInPost: AfiSafiNeighborAdjRib?;  // This is a per-neighbor table containing the routes received from the neighbor that are eligible for best-path selecti...
  adjRibOutPost: AfiSafiNeighborAdjRib?;  // Per-neighbor table containing paths eligble for sending (advertising) to the neighbor after output policy rules have ...
}
```

### `AfiSafiNeighborAdjRib`

```
interface AfiSafiNeighborAdjRib {
  routes: Bag<Route>;  // List of routes in the table, keyed by vrf, route distinguisher and route prefix.
}
```

### `Route`

```
interface Route {
  vrf: String?;  // Vrf for the route; may be undefined for route-reflector routes.
  routeDistinguisher: String?;  // Route distinguisher for the route; may be undefined for some AfiSafis.
  prefix: IpSubnet;  // Prefix for the route.
  pathAttributes: Bag<AttrSet>;  // Attributes for paths for the route. More than one path may exist if multipath BGP is used.
}
```

### `AttrSet`

Path attributes that may be in use by multiple routes in the table.

```
interface AttrSet {
  origin: BgpOrigin;  // BGP attribute defining the origin of the path information.
  nextHop: IpAddress;  // The IP address of the router that should be used as the next hop to the destination.
  med: Integer?;  // The multi-exit discriminator attribute used in BGP route selection process.
  localPref: Integer?;  // Local preference attribute sent to internal peers to indicate the degree of preference for externally learned routes....
  originatorId: IpAddress?;  // BGP attribute that provides the id as an IPv4 address of the originator of the announcement.
  asPath: AsPath;  // BGP AS-PATH attribute.
  activeRoute: Bool?;  // Whether path is active.
}
```

### `AsPath`

```
interface AsPath {
  asType: AsType;  // The type of AS-PATH.
  members: Bag<Integer>;  // List of the AS numbers in the AS-PATH.
}
```

---

## 7. OSPF

### `Ospf`

```
interface Ospf {
  areas: Bag<OspfArea>;
}
```

### `OspfArea`

```
interface OspfArea {
  id: Integer;  // The area identifier.
  domain: String?;  // The routing domain this area is part of. Absent if the device has no inferred neighbors and is not part of the OSPF t...
  processId: String?;  // The ID of the process in which this area is configured. Absent if the device does not support multiple OSPF processes.
  lsaCount: Integer?;  // The number of link state advertisements in this area. Absent if not reported by the device.
  areaType: OspfAreaType;
  routerType: OspfRouterType?;  // The router type. Absent if it is not a area border or AS boundary router.
  neighbors: Bag<OspfNeighbor>;  // OSPF neighbors in this area.
}
```

---

## 8. ACLs, NAT, Firewalls

### `AclEntry`

```
interface AclEntry {
  headerMatches: HeaderRegion;
  metadataMatches: MetadataMatches;
  action: AclAction;
  name: String;
  uuid: String?;  // The UUID of this entry's security rule. Present for operating systems CHECKPOINT, FORTINET, and PAN_OS.
  description: String?;  // A user-defined description of the ACL entry. Only present on PanOS devices.
  implicitRule: Bool;  // Indicates whether an entry is added to the Forward Networks model to capture some aspects of device behavior (e.g. se...
  defaultRule: Bool;  // Whether this is a default rule.
  lifecycleData: LifecycleData?;  // Stores lifecycle metadata, including timestamps for creation, last use, and modification, along with a hit count, if ...
}
```

### `HeaderRegion`

```
interface HeaderRegion {
  ipv4Src: Bag<IpSubnet>;
  ipv4Dst: Bag<IpSubnet>;
  ipv6Src: Bag<IpSubnet>;
  ipv6Dst: Bag<IpSubnet>;
  ipProtocol: Bag<IntRange>;
  tpSrc: Bag<IntRange>;  // Source transport ports
  tpDst: Bag<IntRange>;  // Destination transport ports
  icmpType: Bag<IntRange>;
  icmpCode: Bag<IntRange>;
  overApproximated: Bool;  // Whether any header field is overapproximated. In this case, the value for each overapproximated header field will be ...
  domains: Bag<String>;  // L7 domain matches. Example members include "google.com" and ".aws.com". There are no restrictions when empty. Always ...
}
```

### `MetadataMatches`

```
interface MetadataMatches {
  ingressInterfaces: Bag<String>;  // The set of ingress interfaces declared in the ACL or NAT rule, either explicitly or via declared zones. Empty for ACL...
  egressInterfaces: Bag<String>;  // The set of egress interfaces declared in the ACL or NAT rule, either explicitly or via declared zones. Empty for ACL ...
}
```

### `NatEntry`

```
interface NatEntry {
  headerMatches: HeaderRegion;
  metadataMatches: MetadataMatches;
  name: String;
  description: String?;  // A user-defined description of the NAT entry. Only present on PanOS devices.
  rewrites: Bag<HeaderRewrite>;
  interfaceNat: Bool;  // Indicates that ipv4Src is rewritten to the IP address of the egress interface, and in this case the ipv4Src field of ...
  natType: NatType;
}
```

---

## 9. STP, VLANs, Bridging

### `Stp`

Top-level container for spanning tree configuration and state data.

```
interface Stp {
  rstp: Rstp;  // Rapid Spanning-tree protocol configuration and operation data.
  mstp: Mstp;  // Multi Spanning-tree protocol configuration and operation data.
  rapidPvst: RapidPvst;  // Rapid per vlan Spanning-tree protocol configuration and operation data.
}
```

### `NamedVlanCollection`

```
interface NamedVlanCollection {
  name: String?;  // Name of the VLAN object. Absent if no name was configured for these VLANs.
  ranges: Bag<VlanRange>;  // List of disjoint VLAN ranges associated with this name.
}
```

### `Vlan`

```
interface Vlan {
  vlanId: Integer;
  name: String?;  // Name for this vlan.
  memberNames: Bag<String>;  // Interfaces carrying this vlan.
}
```

### `SwitchedVlan`

Type for VLAN interface-specific data on Ethernet interfaces. These are for standard L2, switched-style VLANs.

```
interface SwitchedVlan {
  interfaceMode: VlanModeType;  // Access or trunk mode for VLANs.
  nativeVlan: Integer?;  // Native VLAN is valid for trunk mode interface.
  accessVlan: Integer?;  // Access VLAN assigned to the interface.
  voiceVlan: Integer?;  // Voice VLAN assigned to the interface. Not present on non-access interfaces.
  defaultVlan: Integer?;  // When present, frames tagged with this VLAN ID are accepted on the interface and are mapped to the same VLAN to which ...
  trunkVlans: Bag<VlanIdOrRange>;  // Specifies VLANs, or ranges thereof, that the interface may carry when in trunk mode. If not specified, all VLANs are ...
}
```

---

## 10. ARP, FHRP, Neighbor Discovery

### `ArpEntry`

```
interface ArpEntry {
  ip: IpAddress;  // The IPv4 address of the neighbor node.
  linkLayerAddress: MacAddress;  // The link-layer address of the neighbor node.
}
```

### `IfaceFhrp`

```
interface IfaceFhrp {
  hsrp: IfaceFhrpInfo;
  vrrp: IfaceFhrpInfo;
}
```

---

## 11. Cloud (AWS, Azure, GCP)

### `CloudAccount`

Defines a data model for representing NQE cloud account with all related data.

```
interface CloudAccount {
  name: String;  // The account name, if account information was collected. Otherwise, it is a synthetic name formed from cloud setup ID.
  cloudSetupId: String;  // The cloud setup ID from which this account was discovered. Note that this is the value of the cloud setup ID at the t...
  id: String;  // The account ID, if account information was collected. Otherwise, it has the same value as name.
  email: String?;  // The email address associated with this account or null for old snapshots where account information was not collected.
  collected: Bool;  // Whether or not objects in this account were collected. When this is false, then all these collection types in this ac...
  cloudType: CloudType;
  vpcs: Bag<VpcData>;
  transitGateways: Bag<TransitGateway>;
  externalLoadBalancers: Bag<LoadBalancer>;  // This field is GCP only.
  dcGateways: Bag<DcGateway>;
  firewallRules: Bag<FirewallRule>;
  firewallPolicy: FirewallPolicy;  // Definitions of policies used in VPC firewalls. Referenced by policy name in CloudFirewallRuleDefinition.
  globalAccelerators: Bag<GlobalAccelerator>;  // This field is AWS only.
  organizationalUnitIds: Bag<String>;  // IDs of all OUs of which this account is a member. This field is populated for AWS and GCP. Empty for Azure.
  publicUnallocatedIps: Bag<PublicUnallocatedIp>;  // The public unallocated IPv4 addresses of this account, where public means non-private as defined in RFC 1918. For the...
  publicUnallocatedSubnets: Bag<PublicUnallocatedIpSubnet>;  // The public unallocated IPv4 subnet of this account, where public means non-private as defined in RFC 1918. For the al...
}
```

### `VpcData`

```
interface VpcData {
  name: String?;  // Never null for GCP.
  id: String;
  tags: Bag<String>;
  cloudRegions: Bag<String>;
  cloudType: CloudType;
  subnets: Bag<Subnet>;
  computeInstances: Bag<ComputeInstance>;
  serviceEndpoints: Bag<ServiceEndpoint>;  // The field serviceEndpoints is AWS only.
  securityGroups: Bag<SecurityGroup>;
  networkAcls: Bag<NetworkAcl>;
  routeTables: Bag<RouteTable>;
  vpnGateways: Bag<VpnGateway>;
  dcGatewayIds: Bag<String>;
  inetGateways: Bag<InetGateway>;
  loadBalancers: Bag<LoadBalancer>;
  natGateways: Bag<NatGateway>;
  vpcPeerings: Bag<VpcPeering>;
  ipv4CidrBlocks: Bag<IpSubnet>;
  ipv6CidrBlocks: Bag<IpSubnet>;
  firewalls: Bag<CloudFirewall>;
}
```

### `CloudIface`

```
interface CloudIface {
  name: String?;  // Never null for GCP.
  description: String?;  // Present on AWS.
  id: String;
  tags: Bag<String>;
  isUp: Bool;
  computeInstanceId: String?;  // The ID of the compute instance attached to this interface. Absent if no compute instance is attached to this interfac...
  macAddress: MacAddress?;
  ipAddresses: Bag<IpAddress>;  // IP addresses allocated to this interface, where public means non-private as defined in RFC 1918. For the unallocated ...
  securityGroupIds: Bag<String>;
}
```

### `SecurityGroup`

```
interface SecurityGroup {
  name: String?;
  id: String;
  groupName: String?;
  description: String?;
  tags: Bag<String>;
  ingressRules: List<SecurityRule>;
  egressRules: List<SecurityRule>;
}
```

### `CloudFirewall`

Defined within a VPC

```
interface CloudFirewall {
  name: String;  // An optional name for the cloud-provided firewall. Empty if none was configured.
  id: String;
  resourceGroups: Bag<String>;  // Logical groups to which this firewall belongs. The firewall can act on virtual machines, interfaces, groups of interf...
  rules: List<CloudFirewallRule>;  // Evaluate in priority order, first match wins.
}
```

### `ComputeInstance`

```
interface ComputeInstance {
  name: String?;  // Never null for GCP.
  id: String;
  tags: Bag<String>;
  isUp: Bool;
  imageName: String?;
  instanceType: String;
  instanceIfaces: Bag<InstanceIface>;
}
```

### `RouteTable`

```
interface RouteTable {
  name: String?;  // Never null for GCP.
  id: String;
  tags: Bag<String>;
  region: String?;
  routes: Bag<CloudRoute>;
}
```

### `CloudRoute`

```
interface CloudRoute {
  prefixes: Bag<IpSubnet>;
  tags: Bag<String>;
  routeType: CloudRouteType;
  nextHop: CloudRouteNextHop?;  // Route with null nextHop drops traffic.
  priority: Integer?;  // GCP only.
  subnetIdMatch: String;
  inactive: Bool?;
}
```

---

## 12. Endpoints, Locations, CVE

### `NetworkEndpoint`

```
interface NetworkEndpoint {
  name: String;  // The name of the device endpoint. Unique across all collection sources.
  locationName: String?;  // The location name. Absent if no location is assigned.
  tagNames: Bag<String>;  // Names of the device tags that contain this device.
  snapshotInfo: DeviceSnapshotInfo;  // Metadata about the inclusion of this source in the snapshot.
  profileName: String;  // The name of the profile from which this source was derived.
  httpResults: Bag<HttpApiEndpointResult>;  // Non-empty when this is an HTTP network endpoint.
  cliCommandResponses: Bag<CliCommandResponse>;  // Non-empty when this is a CLI network endpoint.
  snmpOutputs: Bag<OidOutput>;  // Non-empty when this is an SNMP network endpoint.
}
```

### `Location`

```
interface Location {
  name: String;  // The user-defined name of the location.
  id: String;  // The ID of the location.
  city: String?;  // The city can be null if the location has been defined in the platform (with latitude and longitude values), but no ci...
  adminDivision: String?;  // Could be a state in the United States like California or a territory in Canada like Ontario.
  country: String?;  // Present if and only if city is present.
}
```

### `CveDatabase`

```
interface CveDatabase {
  cves: Bag<Cve>;
}
```

### `CveFinding`

```
interface CveFinding {
  cveId: String;
  isVulnerable: Bool;  // Whether or not this Device is vulnerable to this CVE.
  basis: CveFindingBasis;  // The grounds on which the isVulnerable was determined.
}
```

---

## 13. Enumerations Reference

Key enums used throughout the data model. Reference these constants in queries via `EnumName.VALUE`.

### `OS`

Enum with 67 values:

| Value | Description |
|---|---|
| `ACOS` |  |
| `ALKIRA_CXP` |  |
| `APIC` |  |
| `ARISTA_EOS` |  |
| `ARUBA_AOS_CX` |  |
| `ARUBA_SWITCH` |  |
| `ARUBA_WIFI` |  |
| `ASA` |  |
| `AVAYA` |  |
| `AVAYA_ERS` |  |
| `AVI_VANTAGE` |  |
| `BLUECAT` |  |
| `BLUECOAT` |  |
| `BROCADE_SWITCH` |  |
| `CHECKPOINT` |  |
| `CISCO_WIRELESS` |  |
| `CLOUD_GENIX` |  |
| `CUMULUS` |  |
| `DELL_OS10` |  |
| `DELL_OS6` |  |
| `DELL_OS9` |  |
| `DELL_SONIC` |  |
| `EDGE_CORE_SONIC` |  |
| `ENCRYPTOR` |  |
| `ENCS_NFV` |  |
| `ESXI` |  |
| `EXTREME_NOS` |  |
| `F5` |  |
| `F5_OS_HYPERVISOR` |  |
| `FORCEPOINT` |  |
| `FORTINET` |  |
| `FXOS` |  |
| `GENERAL_DYNAMICS_ENCRYPTOR` |  |
| `HP_COMWARE` |  |
| `HP_PROVISION` |  |
| `HUAWEI` |  |
| `INTERNET_SERVICE` |  |
| `INTRANET_SERVICE` |  |
| `IOS` |  |
| `IOS_XE` |  |
| `IOS_XR` |  |
| `JUNOS` |  |
| `L2_VPN_SERVICE` |  |
| `LINUX` |  |
| `LINUX_OVS_OFCTL` |  |
| `MERAKI_MR` |  |
| `MERAKI_MS` |  |
| `MERAKI_MX` |  |
| `MPLS_VPN_SERVICE` |  |
| `NETSCALER` |  |
| `NETSCREEN` |  |
| `NOKIA` |  |
| `NXOS` |  |
| `OTHER` |  |
| `PAN_OS` |  |
| `PENSANDO` |  |
| `PICA8_OVS_OFCTL` |  |
| `SG` |  |
| `SILVER_PEAK` |  |
| `SRX` |  |
| `T128` |  |
| `UNKNOWN` |  |
| `VELOCLOUD_EDGE` |  |
| `VELOCLOUD_GATEWAY` |  |
| `VERSA` |  |
| `VIASAT_ENCRYPTOR` |  |
| `VIPTELA` |  |

### `Vendor`

Enum with 39 values:

| Value | Description |
|---|---|
| `A10` |  |
| `ALKIRA` |  |
| `AMAZON` |  |
| `ARISTA` |  |
| `ARUBA` |  |
| `AVAYA` |  |
| `AVI_NETWORKS` |  |
| `AZURE` |  |
| `BLUECAT` |  |
| `BROCADE` |  |
| `CHECKPOINT` |  |
| `CISCO` |  |
| `CITRIX` |  |
| `CUMULUS` |  |
| `DELL` |  |
| `EDGE_CORE` |  |
| `EXTREME` |  |
| `F5` |  |
| `FORCEPOINT` |  |
| `FORTINET` |  |
| `FORWARD_CUSTOM` |  |
| `GENERAL_DYNAMICS` |  |
| `GOOGLE` |  |
| `HP` |  |
| `HUAWEI` |  |
| `JUNIPER` |  |
| `LINUX_GENERIC` |  |
| `NOKIA` |  |
| `PALO_ALTO_NETWORKS` |  |
| `PENSANDO` |  |
| `PICA8` |  |
| `RIVERBED` |  |
| `SILVER_PEAK` |  |
| `SYMANTEC` |  |
| `T128` |  |
| `UNKNOWN` |  |
| `VERSA` |  |
| `VIASAT` |  |
| `VMWARE` |  |

### `CommandType`

Enum with 177 values:

| Value | Description |
|---|---|
| `A10_AFLEX_RULES` | ACOS: 'show aflex {}' |
| `A10_BW_LISTS` | ACOS: 'show bw-list {} detail' |
| `ACL_ADDRESSES` | PAN_OS: 'show running security-policy' |
| `ACL_CONFIG` | AVI_VANTAGE: 'GET /api/networksecuritypolicy', 'show networksecuritypolicy' BLUE... |
| `ACL_CONFIG_IPV6` | LINUX: 'ip6tables -L -v -n' |
| `ACL_STATE` | ACOS: 'show access-list' |
| `APPLICATION_PROFILE` | AVI_VANTAGE: 'GET /api/applicationprofile', 'show applicationprofile' |
| `AP_ESSID` | ARUBA_WIFI: 'show ap essid' IOS_XE: 'show ap wlan summary' |
| `AP_USERS` | ARUBA_WIFI: 'show user rows 1 {}' |
| `ARP_TABLE` | ACOS: 'show arp' ARISTA_EOS: 'show ip arp' ARUBA_WIFI: 'show arp' ASA: 'show arp... |
| `ARP_VRF` | APIC: 'fabric {} show ip arp vrf all' ARISTA_EOS: 'show ip arp vrf {}', 'show ip... |
| `AVI_CLOUD` | AVI_VANTAGE: 'GET /api/cloud', 'show cloud' |
| `AVI_SERVICE_ENGINE_GROUP` | AVI_VANTAGE: 'GET /api/serviceenginegroup', 'show serviceenginegroup' |
| `AVI_VIRTUAL_SERVICE` | AVI_VANTAGE: 'GET /api/virtualservice', 'show virtualservice' |
| `BGP_PEERS` | ACOS: 'show ip bgp neighbors' APIC: 'fabric {} show bgp sessions vrf all' ARISTA... |
| `BGP_SUMMARY` | ARISTA_EOS: 'show bgp instance vrf all' ARUBA_AOS_CX: 'show bgp all', 'show bgp ... |
| `BLOCKED_CLIENT_IPS` | BLUECOAT: 'show attack-detection client blocked' |
| `BLUECAT_CONFIG` |  |
| `BLUECOAT_ADN` | BLUECOAT: 'show advanced-url /ADN/configuration' |
| `BRIDGE_DOMAIN` | IOS: 'show bridge-domain' IOS_XE: 'show bridge-domain' VIPTELA: 'show bridge tab... |
| `BRIDGE_INTERFACES` | APIC: 'show interface bridge-domain' ASA: 'show bridge-group' CHECKPOINT: 'brctl... |
| `BUNDLE_STATE` | HP_COMWARE: 'display irf' IOS: 'show switch virtual' IOS_XE: 'show switch virtua... |
| `CDP` | APIC: 'fabric {} show cdp neighbors detail' ARUBA_AOS_CX: 'show cdp neighbor-inf... |
| `CISCO_ACI_EPM_ENDPOINTS` | APIC: 'fabric {} show system internal epm endpoint all' NXOS: 'show system inter... |
| `CISCO_ACI_FABRIC_NODES` | NXOS: 'acidiag fnvread' |
| `CISCO_ACI_FABRIC_VRFS` | APIC: 'fabric {} show system internal epm vrf all' NXOS: 'show system internal e... |
| `CISCO_ACI_NODE_TYPE` | APIC: 'fabric {} show coop internal info global' |
| `CISCO_ACI_SPINE_INTERFACE_MODE` | APIC: 'fabric {} show ip interface |
| `CISCO_ACI_SPINE_IP_ENDPOINTS` | APIC: 'fabric {} show coop internal info ip-db' NXOS: 'show coop internal info i... |
| `CISCO_ACI_SPINE_TUNNELS_NEXTHOP` | APIC: 'fabric {} show coop internal info tun-nh' NXOS: 'show coop internal info ... |
| `CISCO_ACI_TUNNELS_ENDPOINTS` | APIC: 'fabric {} show isis dteps vrf all' NXOS: 'show isis dteps vrf all' |
| `CISCO_ACI_ZONING_FILTER` | APIC: 'fabric {} show zoning-filter' NXOS: 'show zoning-filter' |
| `CISCO_ACI_ZONING_RULE` | APIC: 'fabric {} show zoning-rule' NXOS: 'show zoning-rule' |
| `CISCO_APIC_CONTROLLER_DETAIL` | APIC: 'show controller detail' |
| `CISCO_APIC_EXT_L3OUT_INTERFACES` | APIC: 'show external-l3 interfaces detail' |
| `CISCO_APIC_SWITCH` | APIC: 'show switch detail' |
| `CISCO_APIC_VLAN_LEAF` | APIC: 'fabric {} show vlan extended' NXOS: 'show vlan extended' |
| `CISCO_APIC_VLAN_STATUS_LEAF` | APIC: 'fabric {} show system internal epm vlan all detail' NXOS: 'show system in... |
| `CISCO_APIC_VPC_MAP` | APIC: 'show vpc map' |
| `CISCO_ASA_SHUN_TABLE` | ASA: 'show shun' FXOS: 'show shun' |
| `CISCO_IOS_VFI_INTERFACES` | IOS: 'show platform software ethernet fp active vfi detail' IOS_XE: 'show platfo... |
| `CISCO_IOS_VPLS_VFI_LIST` | IOS: 'show l2vpn vfi' IOS_XE: 'show l2vpn vfi' |
| `CISCO_ITD` | NXOS: 'show itd' |
| `CLUSTER_INTERFACES` | CHECKPOINT: 'cphaprob -a if', 'show cluster members interfaces all' |
| `CLUSTER_STATE` | ARUBA_WIFI: 'show lc-cluster group-membership' AVI_VANTAGE: 'GET /api/cluster/ru... |
| `CONFIG` | ACOS: 'show running-config' APIC: 'show running-config tenant', 'show running-co... |
| `CUSTOM` |  |
| `DEFAULT_GATEWAYS` | BLUECOAT: 'show ip-default-gateway' |
| `DEVICE_HARDWARE_INFO` | ARUBA_AOS_CX: 'show aruba-central' CUMULUS: 'cat /etc/lsb-release' HP_PROVISION:... |
| `DNS_CACHE` | ASA: 'show dns' FXOS: 'show dns' NETSCALER: 'show dns addrec {}' NETSCREEN: 'get... |
| `DOMAIN_NAME` | APIC: 'show dns-domain' CHECKPOINT: 'domainname', 'show domainname' FORTINET: 'g... |
| `EVPN` | ARISTA_EOS: 'show bgp evpn instance' IOS: 'show evpn peers vrf {}' IOS_XE: 'show... |
| `F5_AFM_CONFIG` | F5: 'list security', 'list security bot-defense', 'list security dos profile', '... |
| `F5_AFM_STATE` | F5: 'show security', 'show sys clock' |
| `F5_CM_MODULE_STATE` | F5: 'show cm failover-status;', 'show cm sync-status;' |
| `F5_LTM_CONFIG` | F5: 'bigpipe class list all', 'bigpipe ltm list all', 'bigpipe nat list all', 'b... |
| `F5_LTM_IRULES` | F5: 'bigpipe rule list all', 'show running-config ltm rule recursive;' |
| `F5_LTM_POOL_STATE` | F5: 'bigpipe pool all members show', 'show ltm pool recursive members;' |
| `F5_VCMP_GUESTS` | F5: 'show vcmp guest detail all-properties;' |
| `F5_VCMP_GUESTS_ADDRS` | F5: 'list vcmp guest hostname management-ip;' |
| `F5_VIRTUAL_SERVER_STATE` | F5: 'bigpipe virtual show', 'show ltm virtual recursive;' |
| `FABRICPATH_TABLE` | NXOS: 'show fabricpath route' |
| `FAILOVER` | ACOS: 'show ha detail', 'show ha mac' ASA: 'show failover' BLUECOAT: 'show failo... |
| `FIREWALL_DYNAMIC_OBJECTS` | CHECKPOINT: '([ -f '<FW-dir>/CTX/CTX<context-id>/database/<dynamic_objects.db>' ... |
| `FIREWALL_IDENTITY_MONITOR` | CHECKPOINT: 'pdp monitor all' |
| `FIREWALL_IDENTITY_ROLES` | CHECKPOINT: '([ -f '<FW-dir>/CTX/CTX<context-id>/database/<identity_roles.C>' ] ... |
| `FIREWALL_OBJECTS` | CHECKPOINT: '([ -f '<FW-dir>/CTX/CTX<context-id>/database/<objects.C>' ] && cat ... |
| `FIREWALL_POLICIES` | CHECKPOINT: '([ -f '<FW-dir>/CTX/CTX<context-id>/database/<rules.C>' ] && cat '<... |
| `FORWARDING_MODES` | SRX: 'show security flow status' |
| `HAIPE_BATTERY_CHANGE_DATE` |  |
| `HAIPE_DVROW_STATUS` |  |
| `HAIPE_FIREFLY_EXPIRATION` |  |
| `HAIPE_FIREFLY_NATIONAL_SHORT_TITLE` |  |
| `HAIPE_FIREFLY_TABLE` |  |
| `HAIPE_STATION_IDENTIFIER` |  |
| `HAIPE_SYSTEM_DATE` |  |
| `HAIPE_SYSTEM_UPTIME` |  |
| `HEALTH_CHECKS_STATS` | BLUECOAT: 'show health-checks statistics' |
| `HOSTNAME` | APIC: 'fabric {} show hostname' ARISTA_EOS: 'show hostname' ARUBA_AOS_CX: 'show ... |
| `HSRP_STATE` | IOS: 'show standby' IOS_XE: 'show standby' IOS_XR: 'show hsrp brief' NXOS: 'show... |
| `IFINDEX2_IPV4` |  |
| `IFINDEX_IPV4` |  |
| `IGMP_GROUPS` | ARISTA_EOS: 'show ip igmp groups' IOS: 'show ip igmp group' IOS_XE: 'show ip igm... |
| `IGMP_INTERFACES` | ARISTA_EOS: 'show ip igmp interface' IOS: 'show ip igmp interface' IOS_XE: 'show... |
| `IGMP_VRF_GROUPS` | ARISTA_EOS: 'show ip igmp vrf {} groups' IOS: 'show ip igmp vrf {} groups' IOS_X... |
| `IGMP_VRF_INTERFACES` | ARISTA_EOS: 'show ip igmp vrf {} interface' IOS: 'show ip igmp vrf {} interface'... |
| `INTERFACES` | ACOS: 'show interfaces', 'show interfaces management', 'show trunk' APIC: 'fabri... |
| `INTERFACES_MAC` | APIC: 'fabric {} show interface mac-address' F5: 'show sys mac-address;' FORTINE... |
| `INTERFACES_QUEUING_INFO` | NXOS: 'show queuing interface', 'show queuing interface {}' |
| `INTERFACES_STATUS` | APIC: 'fabric {} show ip interface brief' ARISTA_EOS: 'show interfaces status' C... |
| `INTERFACES_TRUNK` | IOS: 'show interface trunk' IOS_XE: 'show interface trunk' NXOS: 'show interface... |
| `INTERFACES_VRF` | APIC: 'fabric {} show vrf all interface' NXOS: 'show vrf all interface' |
| `INVENTORY` | APIC: 'fabric {} show inventory' ARISTA_EOS: 'show inventory' ARUBA_AOS_CX: 'sho... |
| `IPSEC_STATE` | ARUBA_WIFI: 'show crypto ipsec sa' F5: 'show net ipsec ike-sa all-properties', '... |
| `IPV4_INTERFACES` | HP_COMWARE: 'display ip interface' HP_PROVISION: 'show ip' PAN_OS: 'show interfa... |
| `IPV4_MCAST_RP` | ARISTA_EOS: 'show ip pim rp detail', 'show ip pim vrf {} rp detail' IOS: 'show i... |
| `IPV4_VRRP_STATE` | ACOS: 'show vrrp-a detail', 'show vrrp-a hostid', 'show vrrp-a mac' ARISTA_EOS: ... |
| `IPV6_IGMP_VRF_INTERFACES` | IOS: 'show ipv6 mld interface' IOS_XE: 'show ipv6 mld interface' IOS_XR: 'show p... |
| `IPV6_INTERFACES` | HP_COMWARE: 'display ipv6 interface', 'display ipv6 interface verbose' HP_PROVIS... |
| `IPV6_MCAST_RP` | ARISTA_EOS: 'show ipv6 pim rp detail', 'show ipv6 pim vrf {} rp detail' IOS: 'sh... |
| `IPV6_VRRP_STATE` | DELL_OS10: 'show vrrp ipv6 {}' DELL_OS6: 'show vrrp ipv6 {}' DELL_OS9: 'show vrr... |
| `IP_IGMP_SNOOP_TRACKING` | ARISTA_EOS: 'show ip igmp snooping groups local detail' NXOS: 'show ip igmp snoo... |
| `L2CIRCUITS_STATE` | JUNOS: 'show l2circuit connections' SRX: 'show l2circuit connections' |
| `L2VPN_BRIDGE_DOMAIN` | IOS_XR: 'show l2vpn bridge-domain detail' |
| `L2VPN_XCONNECT_STATE` | IOS_XR: 'show l2vpn xconnect detail' |
| `LICENSE_INFO` | ACOS: 'show license', 'show license-info' IOS_XR: 'show license udi' |
| `LLDP` | ACOS: 'show lldp neighbors' APIC: 'fabric {} show lldp neighbors', 'fabric {} sh... |
| `MAC_TABLE` | ACOS: 'show mac-address-table' ARISTA_EOS: 'show mac address-table' ARUBA_AOS_CX... |
| `MGMT_SERVICES` | BLUECOAT: 'show management-services' |
| `MIB_MAC_ADDRESSES` | HP_PROVISION: 'walkMIB ifPhysAddress' |
| `MLAG_INTERFACE_STATE` | ARISTA_EOS: 'show mlag interfaces detail' DELL_OS10: 'show vlt brief', 'show vlt... |
| `MLAG_STATE` | ARISTA_EOS: 'show mlag detail' CUMULUS: 'net show clag' HUAWEI: 'display dfs-gro... |
| `MPLS_BYPASS_LSP_TUNNEL_STATE` | JUNOS: 'show mpls lsp bypass detail' SRX: 'show mpls lsp bypass detail' |
| `MPLS_PSEUDOWIRE_STATE` | IOS: 'show mpls l2transport pwid' IOS_XE: 'show mpls l2transport pwid' |
| `MPLS_TE_TUNNELS_STATE` | ARISTA_EOS: 'show tunnel fib' HUAWEI: 'display mpls lsp verbose' IOS: 'show mpls... |
| `MPLS_VIRTUAL_CIRCUIT_STATE` | HUAWEI: 'display mpls l2vc' IOS: 'show mpls l2transport vc detail' IOS_XE: 'show... |
| `NAT_ADDRESSES` | PAN_OS: 'show running nat-policy' |
| `NDP_TABLE` | ACOS: 'show ipv6 neighbor' ARISTA_EOS: 'show ipv6 neighbors' ARUBA_AOS_CX: 'show... |
| `NETSCREEN_NSRP_STATE` | NETSCREEN: 'get nsrp cluster', 'get nsrp vsd-group' |
| `NETWORK_PROFILE` | AVI_VANTAGE: 'GET /api/networkprofile', 'show networkprofile' |
| `NHRP_STATE` | IOS: 'show ip nhrp', 'show ipv6 nhrp' IOS_XE: 'show ip nhrp', 'show ipv6 nhrp' |
| `OTV` | NXOS: 'show otv', 'show otv adjacency', 'show otv route' |
| `PACKET_FILTER_CONFIG` | HP_COMWARE: 'display packet-filter all', 'display packet-filter interface' |
| `PANOS_CONFIG_PUSHED_SHARED_POLICY` | PAN_OS: 'show config pushed-shared-policy vsys {}' |
| `PANOS_CONFIG_PUSHED_TEMPLATE` | PAN_OS: 'show config pushed-template' |
| `PANOS_EXTERNAL_IP_LIST` | PAN_OS: 'request system external-list show type ip name "{}"' |
| `PARTITION_CONFIG` | F5: 'list auth partition' |
| `POLICY_ORDER` | BLUECOAT: 'show policy order' |
| `POLICY_TRAFFIC_SELECTORS` |  |
| `PORT_CHANNEL_MEMBERS` | APIC: 'fabric {} show port-channel extended' ARISTA_EOS: 'show port-channel acti... |
| `PORT_LABELS` | OTHER: 'show port-label {}' |
| `PORT_MIRRORING_STATE` | F5: 'bigpipe mirror list', 'list net port-mirror;' |
| `PORT_SECURITY_STATE` | IOS: 'show port-security address' IOS_XE: 'show port-security address' NXOS: 'sh... |
| `PREDEFINED_APPS` | SRX: 'show configuration groups junos-defaults applications' |
| `PROXY_POLICIES` | BLUECOAT: 'show policy', 'show policy executable' |
| `PROXY_SERVICES` | BLUECOAT: 'show proxy-services' |
| `REGISTERED_IP_ADDRESSES` | PAN_OS: 'show object registered-ip all' |
| `RIVERBED_HOST_LABELS` | OTHER: 'show host-label {} detailed' |
| `RIVERBED_IN_PATH_NEIGHBORS` | OTHER: 'show in-path neighbor' |
| `RIVERBED_IN_PATH_RULES` | OTHER: 'show in-path rules' |
| `RIVERBED_PATH_SELECTION_RULES` | OTHER: 'show path-selection rules', 'show topology uplink {} site {} path-select... |
| `RIVERBED_STEELHEAD_NEIGHBORS` | OTHER: 'show steelhead name all' |
| `ROOT_CONTEXT_CONFIG` | ASA: 'show running-config' NETSCALER: 'show simpleacl -format INPUT' |
| `RSVP_SESSION_STATE` | JUNOS: 'show rsvp session detail' SRX: 'show rsvp session detail' |
| `SDWAN_CONFIG` | IOS_XE: 'show sdwan running-config', 'show sdwan running-config |
| `SLA_IP_TRACKING_STATE` | IOS: 'show ip sla summary' IOS_XE: 'show ip sla summary' IOS_XR: 'show track' VE... |
| `SLB_CS_VIRTUAL_SERVERS` | NETSCALER: 'show cs vserver' |
| `SLB_GSLB_SERVICES` | NETSCALER: 'show gslb service' |
| `SLB_GSLB_VIRTUAL_SERVERS` | NETSCALER: 'show gslb vserver' |
| `SLB_SERVERS` | ACOS: 'show slb server' |
| `SLB_SERVER_DETAILS` | ACOS: 'show slb server {} detail' |
| `SLB_SERVICES` | NETSCALER: 'show service' |
| `SLB_SERVICE_GROUPS` | ACOS: 'show slb service-group' NETSCALER: 'show serviceGroup -includeMembers' |
| `SLB_VIRTUAL_SERVERS` | ACOS: 'show slb virtual-server' NETSCALER: 'show lb vserver' |
| `SNMP_SYS_DESCR` |  |
| `SNMP_SYS_NAME` |  |
| `SNMP_TARGET_ADDRESS` |  |
| `SSH_RSA_KEY_LENGTH` | IOS_XR: 'show crypto key mypubkey rsa |
| `STP_STATE` | ARISTA_EOS: 'show spanning-tree' ARUBA_AOS_CX: 'show spanning-tree', 'show spann... |
| `SWITCHPORT_STATE` | APIC: 'fabric {} show interface switchport' ARISTA_EOS: 'show interfaces switchp... |
| `SYSTEM_SETTINGS` | ARUBA_AOS_CX: 'show system' ASA: 'show firewall' CUMULUS: 'net show system' DELL... |
| `TUNNELS_STATUS` |  |
| `UPTIME` | CHECKPOINT: 'show uptime', 'uptime -p' F5: 'bash -c uptime', 'uptime' FORTINET: ... |
| `VERSION` | ACOS: 'show hardware', 'show version' APIC: 'fabric {} show version', 'show vers... |
| `VIRTUAL_ADDRESSES` | PAN_OS: 'show high-availability virtual-address' |
| `VIRTUAL_CONTEXTS` | ASA: 'show context' CHECKPOINT: 'fw vsx stat -l' F5: 'show sys provision' NETSCA... |
| `VLAN_LIST` | ACOS: 'show vlans' ARISTA_EOS: 'show vlan' ARUBA_AOS_CX: 'show vlan' ARUBA_WIFI:... |
| `VNIC_STATE` | AVI_VANTAGE: 'GET /api/serviceengine/{name}/vnicdb', 'show serviceengine {} vnic... |
| `VPC_CONSISTENCY` | NXOS: 'show vpc', 'show vpc consistency-parameters global', 'show vpc consistenc... |
| `VPLS_FORWARDING` | HUAWEI: 'display vpls services all' JUNOS: 'show route forwarding-table family v... |
| `VPLS_MAC_TABLE` | JUNOS: 'show vpls mac-table' SRX: 'show vpls mac-table' |
| `VPN_TUNNELS` | ASA: 'show ipsec sa' FORTINET: 'get vpn ipsec tunnel details', 'get vpn ipsec tu... |
| `VRF_MCAST_ROUTING` | ARISTA_EOS: 'show ip mroute', 'show ip mroute vrf {}' IOS: 'show ip mroute', 'sh... |
| `VXLAN_ESI` | JUNOS: 'show ethernet-switching vxlan-tunnel-end-point esi', 'show l2-learning v... |
| `VXLAN_MAC_TABLE` | ARISTA_EOS: 'show vxlan address-table' |
| `VXLAN_STATE` | ARISTA_EOS: 'show vxlan vtep', 'show vxlan vtep detail' ARUBA_AOS_CX: 'show inte... |
| `WCCP_STATE` | ASA: 'show wccp', 'show wccp vrf {}', 'show wccp vrf {} {} detail', 'show wccp {... |

### `AdminStatus`

Enum with 2 values:

| Value | Description |
|---|---|
| `AdminStatus.DOWN` | Not ready to pass packets. |
| `AdminStatus.UP` | Ready to pass packets. |

### `OperStatus`

The current operational state of the interface.

Enum with 7 values:

| Value | Description |
|---|---|
| `OperStatus.DORMANT` | Waiting for some external event. |
| `OperStatus.DOWN` | The interface does not pass any packets. |
| `OperStatus.LOWER_LAYER_DOWN` | Down due to state of lower-layer interface(s). |
| `OperStatus.NOT_PRESENT` | Some component (typically hardware) is missing. |
| `OperStatus.TESTING` | In some test mode. No operational packets can be passed. |
| `OperStatus.UNKNOWN` | Status cannot be determined for some reason. |
| `OperStatus.UP` | Ready to pass packets. |

### `AclAction`

Enum with 3 values:

| Value | Description |
|---|---|
| `AclAction.DENY` |  |
| `AclAction.PBR` | [`PbrAction`](https://docs.fwd.app/latest/application/reference/nqe/data-model/type_pbraction/) -- |
| `AclAction.PERMIT` |  |

### `BgpSessionState`

Enum with 6 values:

| Value | Description |
|---|---|
| `BgpSessionState.ACTIVE` | Neighbor is down, and the local system is awaiting a connection from the remote peer. |
| `BgpSessionState.CONNECT` | Neighbor is down, and the session is waiting for the underlying transport session to be established. |
| `BgpSessionState.ESTABLISHED` | Neighbor is up - the BGP session with the peer is established. |
| `BgpSessionState.IDLE` | Neighbor is down, and in the Idle state of the FSM. |
| `BgpSessionState.OPENCONFIRM` | Neighbor is in the process of being established. The local system is awaiting a NOTIFICATION or KEEP... |
| `BgpSessionState.OPENSENT` | Neighbor is in the process of being established. The local system has sent an OPEN message. |

### `BgpOrigin`

Enum with 3 values:

| Value | Description |
|---|---|
| `BgpOrigin.EGP` | Origin of the NLRI is EGP. |
| `BgpOrigin.IGP` | Origin of the NLRI is internal. |
| `BgpOrigin.INCOMPLETE` | Origin of the NLRI is neither IGP or EGP. |

### `NextHopType`

Enum with 9 values:

| Value | Description |
|---|---|
| `NextHopType.ATTACHED` | Packet will be L2 forwarded. |
| `NextHopType.BROADCAST` | Packet will be broadcasted to all ports, except the incoming port. |
| `NextHopType.DROP` | Packet will be dropped. |
| `NextHopType.RECEIVE` | Packet will be received and consumed by the device. |
| `NextHopType.RECURSIVE` | Recursive lookup to determine next hop. |
| `NextHopType.REDIRECT` | Packet will be redirected to another port. |
| `NextHopType.REMOTE` | Packet will be L3 forwarded. |
| `NextHopType.UNDEFINED` |  |
| `NextHopType.VRF_FORWARDED` | Packet will be forwarded based on VRF. Next hop will be decided there. |

### `OriginProtocol`

Enum with 17 values:

| Value | Description |
|---|---|
| `OriginProtocol.BGP` | Border Gateway Protocol |
| `OriginProtocol.DIRECT_CONNECTED` | A directly connected route. |
| `OriginProtocol.EIGRP` | Enhanced Interior Gateway Routing Protocol. |
| `OriginProtocol.FRR` | Fast Re-Route protocol. |
| `OriginProtocol.IGMP` | Internet Group Management Protocol. |
| `OriginProtocol.ISIS` | Intermediate System to Intermediate System protocol. |
| `OriginProtocol.LDP` | Label Distribution Protocol. |
| `OriginProtocol.LOCAL_AGGREGATE` | Locally defined aggregate route. |
| `OriginProtocol.ODR` | On Demand Routing protocol. |
| `OriginProtocol.OSPF` | Open Shortest Path First protocol. |
| `OriginProtocol.PIM` | Protocol Independent Multicast. |
| `OriginProtocol.RIP` | Routing Information Protocol. |
| `OriginProtocol.RSVP` | Resource Reservation Protocol. |
| `OriginProtocol.STATIC` | Locally-installed static route. |
| `OriginProtocol.UNKNOWN` | Origin protocol unknown. |
| `OriginProtocol.VPLS` | Virtual Private LAN Service protocol. |
| `OriginProtocol.VPN` | Virtual Private Network protocol. |

### `PeerType`

Labels a peer or peer group as explicitly internal or external.

Enum with 2 values:

| Value | Description |
|---|---|
| `PeerType.EXTERNAL` | External (eBGP) peer. |
| `PeerType.INTERNAL` | Internal (iBGP) peer. |

### `AsType`

Enum with 1 values:

| Value | Description |
|---|---|
| `AsType.AS_SEQ` | Ordered set of autonomous systems that a route in the UPDATE message has traversed. |

### `AfiSafiType`

Identity type for AFI,SAFI tuples for BGP-4

Enum with 25 values:

| Value | Description |
|---|---|
| `IPV4_ANY` | IPv4 unicast and multicast, applies to Juniper only (AFI, SAFI = 1, 1/2) |
| `IPV4_LABELED_UNICAST` | Labeled IPv4 unicast (AFI,SAFI = 1,4) |
| `IPV4_MCAST_VPN` | IPv4 MCAST-VPN (AFI,SAFI = 1,5) |
| `IPV4_MDT` | BGP Multicast Distribution Tree (MDT) for IPv4 (AFI, SAFI = 1, 66) |
| `IPV4_MULTICAST` | IPv4 multicast (AFI,SAFI = 1,2) |
| `IPV4_UNICAST` | IPv4 unicast (AFI,SAFI = 1,1) |
| `IPV6_ANY` | IPv6 unicast and multicast, applies to Juniper only (AFI, SAFI = 1, 1/2) |
| `IPV6_LABELED_UNICAST` | Labeled IPv6 unicast (AFI,SAFI = 2,4) |
| `IPV6_MCAST_VPN` | IPv6 MCAST-VPN (AFI,SAFI = 2,6) |
| `IPV6_MDT` | BGP Multicast Distribution Tree (MDT) for IPv4 (AFI, SAFI = 2, 66) |
| `IPV6_MULTICAST` | IPv6 multicast (AFI,SAFI = 2,2) |
| `IPV6_UNICAST` | IPv6 unicast (AFI,SAFI = 2,1) |
| `L2VPN_EVPN` | BGP MPLS Based Ethernet VPN (AFI,SAFI = 25,70) |
| `L2VPN_VPLS` | BGP-signalled VPLS (AFI,SAFI = 25,65) |
| `L3VPN_IPV4_ANY` | Unicast and multicast IPv4 MPLS L3VPN, applies to Juniper only (AFI,SAFI = 1,128... |
| `L3VPN_IPV4_MULTICAST` | Multicast IPv4 MPLS L3VPN (AFI,SAFI = 1,129) |
| `L3VPN_IPV4_UNICAST` | Unicast IPv4 MPLS L3VPN (AFI,SAFI = 1,128) |
| `L3VPN_IPV6_ANY` | Unicast and multicast IPv6 MPLS L3VPN, applies to Juniper only (AFI,SAFI = 2,128... |
| `L3VPN_IPV6_MULTICAST` | Multicast IPv6 MPLS L3VPN (AFI,SAFI = 2,129) |
| `L3VPN_IPV6_UNICAST` | Unicast IPv6 MPLS L3VPN (AFI,SAFI = 2,128) |
| `LINK_STATE` | Link state (AFI, SAFI = 16388, 71) |
| `NSAP_UNICAST` | NSAP NLRI for unicast forwarding (AFI,SAFI = 3,1) |
| `RTFILTER_UNICAST` | IPv4 Route Target constrains (AFI,SAFI = 1,132) |
| `SRTE_POLICY_IPV4` | Segment Routing Traffic Engineering (SRTE) Policy for IPv4 (AFI,SAFI = 1,73) |
| `SRTE_POLICY_IPV6` | Segment Routing Traffic Engineering (SRTE) Policy for IPv6 (AFI,SAFI = 2,73) |

### `IfaceType`

Enum with 14 values:

| Value | Description |
|---|---|
| `IfaceType.IF_AGGREGATE` | An aggregated, or bonded, interface forming a Link Aggregation Group (LAG), or bundle, most often ba... |
| `IfaceType.IF_BRIDGE` | A bridge interface |
| `IfaceType.IF_ETHERNET` | Ethernet interfaces based on IEEE 802.3 standards, as well as FlexEthernet. |
| `IfaceType.IF_LOOPBACK` | A virtual interface designated as a loopback used for various management and operations tasks. |
| `IfaceType.IF_ROUTED_VLAN` | A logical interface used for routing services on a VLAN. Such interfaces are also known as switch vi... |
| `IfaceType.IF_SONET` | SONET/SDH interface. |
| `IfaceType.IF_TE_TUNNEL` | A TE tunnel interface. |
| `IfaceType.IF_TUNNEL_GRE4` | A GRE tunnel over IPv4 transport. |
| `IfaceType.IF_TUNNEL_GRE6` | A GRE tunnel over IPv6 transport. |
| `IfaceType.IF_TUNNEL_IPSEC` | An IPSEC tunnel. |
| `IfaceType.IF_TUNNEL_IP_IN_IP` | An IP-in-IP tunnel. |
| `IfaceType.IF_TUNNEL_L2_VPN` | An L2 VPN tunnel. |
| `IfaceType.IF_TUNNEL_UNKNOWN` | An unknown tunnel interface. |
| `IfaceType.IF_TUNNEL_VXLAN` | A VXLAN VTEP. |

### `Layer`

Network layer in the OSI model.

Enum with 2 values:

| Value | Description |
|---|---|
| `Layer.L2` | Corresponds to the data link layer of the OSI model. |
| `Layer.L3` | Corresponds to the network layer of the OSI model. |

### `NetworkInstanceType`

Enum with 2 values:

| Value | Description |
|---|---|
| `NetworkInstanceType.DEFAULT_INSTANCE` | A special routing instance which acts as the "default" or "global" routing instance for a network de... |
| `NetworkInstanceType.L3VRF` | A private Layer 3 only routing instance which is formed of one or more RIBs. |

### `PortSpeed`

Type to specify available Ethernet link speeds.

Enum with 11 values:

| Value | Description |
|---|---|
| `PortSpeed.SPEED_100GB` |  |
| `PortSpeed.SPEED_100MB` |  |
| `PortSpeed.SPEED_10GB` |  |
| `PortSpeed.SPEED_10MB` |  |
| `PortSpeed.SPEED_1GB` |  |
| `PortSpeed.SPEED_2500MB` |  |
| `PortSpeed.SPEED_25GB` |  |
| `PortSpeed.SPEED_40GB` |  |
| `PortSpeed.SPEED_50GB` |  |
| `PortSpeed.SPEED_5GB` |  |
| `PortSpeed.SPEED_UNKNOWN` | Interface speed is unknown. Systems may report speed UNKNOWN when an interface is down or unpopuplat... |

### `CloudType`

Enum with 3 values:

| Value | Description |
|---|---|
| `CloudType.AWS` |  |
| `CloudType.AZURE` |  |
| `CloudType.GCP` |  |

### `DuplexMode`

Enum with 2 values:

| Value | Description |
|---|---|
| `DuplexMode.FULL` |  |
| `DuplexMode.HALF` |  |

### `RoutingProtocolType`

Type for routing protocols, including those which may install prefixes into the RIB

Enum with 9 values:

| Value | Description |
|---|---|
| `RoutingProtocolType.BGP` | BGP |
| `RoutingProtocolType.DIRECTLY_CONNECTED` | A directly connected route |
| `RoutingProtocolType.IGMP` | Internet Group Management Protocol |
| `RoutingProtocolType.ISIS` | IS-IS |
| `RoutingProtocolType.LOCAL_AGGREGATE` | Locally defined aggregate route |
| `RoutingProtocolType.OSPF` | OSPFv2 |
| `RoutingProtocolType.OSPF3` | OSPFv3 |
| `RoutingProtocolType.PIM` | Protocol Independent Multicast |
| `RoutingProtocolType.STATIC` | Locally-installed static route |

---

## 14. Complete Type Index

Every NQE data model type, including those covered above and many more. For types not covered inline, this index shows their direct fields. Use it to discover types that may be useful for less-common queries.

- **`AclAction`** *(enum, 3 values)* — `DENY`, `PBR`, `PERMIT`
- **`AclEntry`** — `headerMatches: HeaderRegion`, `metadataMatches: MetadataMatches`, `action: AclAction`, `name: String`, `uuid: String?`, `description: String?`, `implicitRule: Bool`, `defaultRule: Bool`, … (9 fields)
- **`AdminStatus`** *(enum, 2 values)* — `DOWN`, `UP`
- **`AfiSafi`** — `afiSafiName: AfiSafiType`, `neighbors: Bag<AfiSafiNeighbor>`
- **`AfiSafiNeighbor`** — `neighborAddress: IpAddress`, `adjRibInPost: AfiSafiNeighborAdjRib?`, `adjRibOutPost: AfiSafiNeighborAdjRib?`
- **`AfiSafiNeighborAdjRib`** — `routes: Bag<Route>`
- **`AfiSafiType`** *(enum, 25 values)* — `IPV4_ANY`, `IPV4_LABELED_UNICAST`, `IPV4_MCAST_VPN`, `IPV4_MDT`, `IPV4_MULTICAST`, `IPV4_UNICAST`, `IPV6_ANY`, `IPV6_LABELED_UNICAST`, … (25 total)
- **`Afts`** — `ipv4Unicast: IpUnicast?`, `ipv6Unicast: IpUnicast?`
- **`Aggregation`** — `memberNames: Bag<String>`, `configuredMemberNames: Bag<String>`, `switchedVlan: SwitchedVlan?`
- **`AllowedBgpPeersDevicePolicy`** — `condition: StigPolicyCondition`, `value: Bag<IpSubnet>`
- **`AllowedCertificationAuthorityEnrollmentUrlsDevicePolicy`** — `condition: StigPolicyCondition`, `value: Bag<String>`
- **`AllowedServicesDevicePolicy`** — `condition: StigPolicyCondition`, `value: Bag<String>`
- **`AnycastConfigurationDetail`** — `enable: Bool`
- **`AnycastService`** — `configurations: Bag<AnycastServiceConfiguration>`
- **`AnycastServiceConfiguration`** — `anycastConfiguration: AnycastConfigurationDetail`
- **`ArcsightConfig`** — `enable: Bool`
- **`ArpEntry`** — `ip: IpAddress`, `linkLayerAddress: MacAddress`
- **`AsPath`** — `asType: AsType`, `members: Bag<Integer>`
- **`AsType`** *(enum, 1 values)* — `AS_SEQ`
- **`AttrSet`** — `origin: BgpOrigin`, `nextHop: IpAddress`, `med: Integer?`, `localPref: Integer?`, `originatorId: IpAddress?`, `asPath: AsPath`, `activeRoute: Bool?`
- **`Backend`** *(enum)*
- **`BackendBucket`** — `name: String`
- **`BackendServer`** — `isUp: Bool`, `backendIps: Bag<IpAddress>`, `backendPorts: Bag<Integer>`
- **`Bgp`** — `neighbors: Bag<BgpNeighbor>`, `routerId: IpAddress?`, `asNumber: Integer?`
- **`BgpNeighbor`** — `neighborAddress: IpAddress`, `peerDeviceName: String?`, `peerVrf: String?`, `peerRouterId: IpAddress?`, `sessionState: BgpSessionState?`, `enabled: Bool`, `description: String?`, `peerAS: Integer`, … (11 fields)
- **`BgpNeighborStatistics`** — `sessionDurationInSeconds: Integer`, `advertisedPrefixes: Integer`, `receivedPrefixes: Integer`
- **`BgpOrigin`** *(enum, 3 values)* — `EGP`, `IGP`, `INCOMPLETE`
- **`BgpRib`** — `afiSafis: Bag<AfiSafi>`
- **`BgpSessionState`** *(enum, 6 values)* — `ACTIVE`, `CONNECT`, `ESTABLISHED`, `IDLE`, `OPENCONFIRM`, `OPENSENT`
- **`BluecatConfig`** — `items: Bag<BluecatConfigItem>`
- **`BluecatConfigItem`** — `serverId: Integer`, `data: BluecatConfigItemData?`
- **`BluecatConfigItemData`** — `services: BluecatServices`, `version: String`
- **`BluecatOutputs`** — `config: BluecatConfig?`, `servers: BluecatServers?`
- **`BluecatRoute`** — `cidr: Integer`, `gateway: IpAddress`, `network: String`
- **`BluecatServerDataItem`** — `id: Integer`, `name: String`, `properties: String`
- **`BluecatServerItem`** — `configId: Integer`, `data: Bag<BluecatServerDataItem>`
- **`BluecatServers`** — `items: Bag<BluecatServerItem>`
- **`BluecatServices`** — `dnsActivity: DnsActivityService`, `interfaces: InterfacesService`, `anycast: AnycastService`, `edgeServicePoint: EdgeServicePointService`, `firewall: FirewallService`, `ssh: SshService`, `syslog: SyslogService`, `ntp: NtpService`, … (11 fields)
- **`Bridge`** — `memberNames: Bag<String>`, `ipv4: IfaceIpv4Info`, `ipv6: IfaceIpv6Info`, `vlan: Integer?`, `networkInstanceName: String`
- **`CisaExploitationEntry`** — `url: String`
- **`CliCommandResponse`** — `command: String`, `response: String`
- **`CliSource`** — `name: String`, `snapshotInfo: DeviceSnapshotInfo`, `profileName: String`, `commandResponses: Bag<CliCommandResponse>`
- **`CloudAccount`** — `name: String`, `cloudSetupId: String`, `id: String`, `email: String?`, `collected: Bool`, `cloudType: CloudType`, `vpcs: Bag<VpcData>`, `transitGateways: Bag<TransitGateway>`, … (16 fields)
- **`CloudFirewall`** — `name: String`, `id: String`, `resourceGroups: Bag<String>`, `rules: List<CloudFirewallRule>`
- **`CloudFirewallRule`** — `priority: Integer`, `name: String`, `definition: CloudFirewallRuleDefinition`, `match: HeaderRegion`, `action: SecurityRuleAction`
- **`CloudFirewallRuleDefinition`** — `origins: Bag<String>`, `sourceObjects: Bag<String>`, `destinationObjects: Bag<String>`, `sourcePorts: Bag<IntRange>`, `destinationPorts: Bag<IntRange>`, `sourceUsers: Bag<String>`, `services: Bag<String>`
- **`CloudIface`** — `name: String?`, `description: String?`, `id: String`, `tags: Bag<String>`, `isUp: Bool`, `computeInstanceId: String?`, `macAddress: MacAddress?`, `ipAddresses: Bag<IpAddress>`, … (9 fields)
- **`CloudRoute`** — `prefixes: Bag<IpSubnet>`, `tags: Bag<String>`, `routeType: CloudRouteType`, `nextHop: CloudRouteNextHop?`, `priority: Integer?`, `subnetIdMatch: String`, `inactive: Bool?`
- **`CloudRouteNextHop`** *(enum)*
- **`CloudRouteType`** *(enum, 2 values)* — `BGP`, `STATIC`
- **`CloudType`** *(enum, 3 values)* — `AWS`, `AZURE`, `GCP`
- **`ClusterHaInfo`** — `peerDevices: Bag<String>`, `operationMode: HaOperationMode`
- **`Command`** — `commandType: CommandType`, `commandText: String?`, `response: String`
- **`CommandType`** *(enum, 177 values)* — `A10_AFLEX_RULES`, `A10_BW_LISTS`, `ACL_ADDRESSES`, `ACL_CONFIG`, `ACL_CONFIG_IPV6`, `ACL_STATE`, `APPLICATION_PROFILE`, `AP_ESSID`, … (177 total)
- **`ComputeInstance`** — `name: String?`, `id: String`, `tags: Bag<String>`, `isUp: Bool`, `imageName: String?`, `instanceType: String`, `instanceIfaces: Bag<InstanceIface>`
- **`ConfigLine`** — `text: String`, `lineNumber: Integer`, `children: List<ConfigLine>`
- **`ConnectsToAccessLayerSwitchInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`ConnectsToCoreLayerInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`ConnectsToCustomerEdgeDeviceInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`ConnectsToDodinDeviceInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`ConnectsViaFiberOpticsInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`ContainerType`** *(enum, 3 values)* — `COLLECTION`, `GROUP`, `POLICY`
- **`Cve`** — `cveId: String`, `severity: Severity`, `description: String?`, `criteria: Bag<CveProductCriteria>`, `cisaKevEntry: CisaExploitationEntry?`, `vendorInfos: Bag<VendorCveInfo>`
- **`CveApplicationCriteria`** — `name: String`
- **`CveDatabase`** — `cves: Bag<Cve>`
- **`CveFinding`** — `cveId: String`, `isVulnerable: Bool`, `basis: CveFindingBasis`
- **`CveFindingBasis`** *(enum, 2 values)* — `CONFIG`, `PLATFORM`
- **`CveHardwareCriteria`** — `name: String`
- **`CveOsCriteria`** — `os: OS`, `dependsOnConfig: Bool?`
- **`CveProductCriteria`** — `vendor: Vendor`, `hardwareCriteria: Bag<CveHardwareCriteria>`, `osCriteria: Bag<CveOsCriteria>`, `applicationCriteria: Bag<CveApplicationCriteria>`
- **`DataConnector`** — `name: String`, `httpResults: Bag<HttpApiEndpointResult>`
- **`DcGateway`** — `name: String?`, `id: String`, `tags: Bag<String>`, `directConnections: Bag<DirectConnection>`
- **`DefaultInterfaceParameters`** — `requiresDefaultVlan: Bool?`, `requiresMulticast: Bool?`, `isHostGateway: Bool?`, `pseudowireVirtualCircuitId: Integer?`, `connectivity: InterfaceConnectivityParameters`
- **`DefaultStigParameters`** — `deviceParameters: DeviceParameters`, `ifaceParameters: DefaultInterfaceParameters`, `vrfParameters: DefaultVrfParameters`
- **`DefaultVrfParameters`** *(no parsed fields)*
- **`Device`** — `name: String`, `locationName: String?`, `locationId: String?`, `groupNames: Bag<String>`, `tagNames: Bag<String>`, `accessLabelNames: Bag<String>`, `snapshotInfo: DeviceSnapshotInfo`, `ha: Ha`, … (22 fields)
- **`DeviceCollectionError`** *(enum, 68 values)* — `APIC_CONFIG_COLLECTION_FAILED`, `API_SERVER_FAILED_TO_RESPOND`, `AUTHENTICATION_FAILED`, `AUTHORIZATION_FAILED`, `AVI_CONTROLLER_WITHOUT_HEALTHY_SERVICE_ENGINES`, `AVI_SHELL_AUTH_FAILED`, `BMP_COLLECTION_FAILED`, `BMP_COLLECTION_REFUSED`, … (68 total)
- **`DeviceDiscoveryIfaceInfo`** — `neighbors: Bag<DeviceDiscoveryNeighbor>`
- **`DeviceDiscoveryNeighbor`** — `deviceName: String`, `portName: String`
- **`DeviceHost`** — `name: String?`, `addresses: Bag<IpSubnet>`, `colocatedAddresses: Bag<IpAddress>`, `macAddress: MacAddress?`, `interfaces: Bag<String>`, `vlans: Bag<VlanRange>`, `gatewayInterfaces: Bag<DeviceL3IfaceName>`, `hostType: DeviceHostType`, … (9 fields)
- **`DeviceHostType`** *(enum)*
- **`DeviceL3IfaceName`** — `deviceName: String`, `ifaceName: String`, `subIfaceName: String?`
- **`DeviceParameters`** — `allowedServices: Bag<String>?`, `allowedCertificationAuthorityEnrollmentUrls: Bag<String>?`, `managementSubnets: Bag<IpSubnet>?`, `isProviderEdge: Bool?`, `allowedBgpPeers: Bag<IpSubnet>?`
- **`DevicePart`** — `name: String`, `partId: String?`, `serialNumber: String?`, `partType: DevicePartType`, `description: String?`, `versionId: String?`, `support: DevicePartSupport?`
- **`DevicePartSupport`** — `announcementUrl: String`, `lastMaintenanceDate: Date?`, `lastVulnerabilityDate: Date?`, `lastSupportDate: Date`
- **`DevicePartType`** *(enum, 16 values)* — `APPLICATION`, `CHASSIS`, `FABRIC_MODULE`, `FAN_MODULE`, `LINE_CARD`, `MOTHERBOARD`, `OTHER`, `POWER_SUPPLY`, … (16 total)
- **`DevicePolicy`** — `allowedServices: Bag<AllowedServicesDevicePolicy>`, `allowedCertificationAuthorityEnrollmentUrls: Bag<AllowedCertificationAuthorityEnrollmentUrlsDevicePolicy>`, `managementSubnets: Bag<ManagementSubnetsDevicePolicy>`, `isProviderEdge: Bag<IsProviderEdgeDevicePolicy>`, `allowedBgpPeers: Bag<AllowedBgpPeersDevicePolicy>`
- **`DeviceProcessingError`** *(enum, 6 values)* — `DUPLICATE`, `LICENSE_EXHAUSTED`, `MISSING_SIGNATURE`, `PARSER_EXCEPTION`, `UNSUPPORTED_DEVICE_TYPE`, `UNSUPPORTED_VENDOR`
- **`DeviceSecurityZone`** — `name: String`, `interfaces: Bag<IfaceSubIface>`
- **`DeviceSecurityZoneReference`** — `deviceName: String`, `zone: String`
- **`DeviceSnapshotInfo`** — `result: DeviceSnapshotResult`, `collectionIp: IpAddress?`, `collectionTime: Timestamp?`, `backfillTime: Timestamp?`
- **`DeviceSnapshotResult`** *(enum)*
- **`DeviceType`** *(enum, 16 values)* — `CONTROLLER`, `ENCRYPTOR`, `FIREWALL`, `INTERNET`, `INTRANET`, `L2_VPN`, `L3_VPN`, `LOAD_BALANCER`, … (16 total)
- **`DirectConnection`** — `name: String?`, `id: String`, `tags: Bag<String>`, `isUp: Bool`, `cloudIp: IpSubnet?`, `customerIp: IpSubnet?`, `vlanId: Integer?`, `virtualIfaceId: String?`, … (11 fields)
- **`DnsActivityConfigurationDetail`** — `enable: Bool`, `serviceId: String?`
- **`DnsActivityService`** — `configurations: Bag<DnsActivityServiceConfiguration>`
- **`DnsActivityServiceConfiguration`** — `dnsActivityConfiguration: DnsActivityConfigurationDetail`
- **`DnsResolverConfigurationDetail`** — `servers: Bag<IpAddress>`
- **`DnsResolverService`** — `configurations: Bag<DnsResolverServiceConfiguration>`
- **`DnsResolverServiceConfiguration`** — `dnsResolverConfiguration: DnsResolverConfigurationDetail`
- **`DuplexMode`** *(enum, 2 values)* — `FULL`, `HALF`
- **`EdgeServicePointConfigurationDetail`** — `enable: Bool`
- **`EdgeServicePointService`** — `configurations: Bag<EdgeServicePointServiceConfiguration>`
- **`EdgeServicePointServiceConfiguration`** — `edgeServicePointConfiguration: EdgeServicePointConfigurationDetail`
- **`EncapsulationHeaderType`** *(enum, 4 values)* — `GRE`, `IPV4`, `IPV6`, `MPLS`
- **`Ethernet`** — `macAddress: MacAddress?`, `negotiatedDuplexMode: DuplexMode`, `negotiatedPortSpeed: PortSpeed`, `speedMbps: Integer?`, `aggregateId: String?`, `switchedVlan: SwitchedVlan?`
- **`ExternalSources`** — `httpSources: Bag<HttpSource>`, `cliSources: Bag<CliSource>`, `snmpSources: Bag<SnmpSource>`
- **`FhrpState`** *(enum, 3 values)* — `BACKUP`, `MASTER`, `OTHER`
- **`Files`** — `config: List<ConfigLine>?`, `panos: PanosFiles?`
- **`FirewallConfigurationDetail`** — `allowPing: Bool`, `enable: Bool`
- **`FirewallPolicy`** — `networkObjects: Bag<NetworkObject>`, `ruleContainers: Bag<RuleContainer>`
- **`FirewallRule`** — `id: String`, `securityRule: SecurityRule`, `appliedToVpcId: String?`, `appliedToSourceInstanceTags: Bag<String>`, `appliedToTargetInstanceTags: Bag<String>`
- **`FirewallService`** — `configurations: Bag<FirewallServiceConfiguration>`
- **`FirewallServiceConfiguration`** — `firewallConfiguration: FirewallConfigurationDetail`
- **`GatewayConfigurationDetail`** — `removeImage: Bool`, `data: GatewayConfigurationDetailData`
- **`GatewayConfigurationDetailData`** — `enable: Bool`, `containers: Bag<GatewayContainer>`, `version: Integer`
- **`GatewayContainer`** — `name: String`, `image: String`, `ports: Bag<String>`, `volumes: Bag<String>`, `environment: Bag<String>`
- **`GatewayService`** — `configurations: Bag<GatewayServiceConfiguration>`
- **`GatewayServiceConfiguration`** — `gatewayConfiguration: GatewayConfigurationDetail`
- **`GlobalAccelerator`** — `name: String?`, `id: String`, `dnsName: String`, `publicIps: Bag<IpAddress>`, `tags: Bag<String>`, `status: GlobalAcceleratorStatus`, `listeners: Bag<GlobalAcceleratorListener>`
- **`GlobalAcceleratorListener`** — `id: String`, `protocol: String`, `ports: Bag<String>`, `endpointGroups: Bag<GlobalAcceleratorListenerEndpointGroup>`
- **`GlobalAcceleratorListenerEndpoint`** *(enum)*
- **`GlobalAcceleratorListenerEndpointGroup`** — `name: String?`, `id: String`, `tags: Bag<String>`, `region: String`, `portOverrides: Bag<String>`, `isHealthy: Bool`, `endpoints: Bag<GlobalAcceleratorListenerEndpoint>`
- **`GlobalAcceleratorStatus`** *(enum, 2 values)* — `DEPLOYED`, `IN_PROGRESS`
- **`Ha`** — `mlagPeer: String?`, `vpc: VpcDomain`, `clusterHa: ClusterHaInfo?`
- **`HaOperationMode`** *(enum, 5 values)* — `ACTIVE`, `ACTIVEBACKUP`, `BACKUP`, `STANDALONE`, `STANDALONE_INACTIVE`
- **`HeaderRegion`** — `ipv4Src: Bag<IpSubnet>`, `ipv4Dst: Bag<IpSubnet>`, `ipv6Src: Bag<IpSubnet>`, `ipv6Dst: Bag<IpSubnet>`, `ipProtocol: Bag<IntRange>`, `tpSrc: Bag<IntRange>`, `tpDst: Bag<IntRange>`, `icmpType: Bag<IntRange>`, … (11 fields)
- **`HeaderRewrite`** — `ipv4Src: Bag<IpSubnet>`, `ipv4Dst: Bag<IpSubnet>`, `ipv6Src: Bag<IpSubnet>`, `ipv6Dst: Bag<IpSubnet>`, `tpSrc: Bag<IntRange>`, `tpDst: Bag<IntRange>`, `overApproximated: Bool`
- **`Hop`** — `index: Integer`, `deviceName: String`, `ingressIfaceName: String`, `egressIfaceName: String?`, `nextDeviceName: String?`, `nextIfaceName: String?`
- **`HttpApiEndpointResult`** — `name: String`, `status: HttpApiEndpointStatus`, `error: String?`, `pages: Bag<HttpPage>`
- **`HttpApiEndpointStatus`** *(enum, 4 values)* — `ERROR`, `MAX_PAGES_REACHED`, `OK`, `TIMED_OUT`
- **`HttpEndpoint`** — `name: String`, `statusCode: Integer`, `reasonPhrase: String`, `responseBody: String?`
- **`HttpPage`** — `statusCode: Integer`, `reasonPhrase: String`, `responseBody: String?`
- **`HttpSource`** — `name: String`, `endpoints: Bag<HttpEndpoint>`, `paginatedEndpoints: Bag<PaginatedHttpEndpoint>`
- **`Iface`** — `name: String`, `interfaceType: IfaceType`, `layer: Layer`, `mtu: Integer?`, `loopbackMode: Bool`, `aliases: Bag<String>`, `description: String?`, `adminStatus: AdminStatus`, … (20 fields)
- **`IfaceAcls`** — `inboundAclNames: List<String>`, `outboundAclNames: List<String>`
- **`IfaceFhrp`** — `hsrp: IfaceFhrpInfo`, `vrrp: IfaceFhrpInfo`
- **`IfaceFhrpGroup`** — `virtualRouterId: Integer`, `state: FhrpState`, `virtualAddress: IpAddress`
- **`IfaceFhrpInfo`** — `fhrpGroups: Bag<IfaceFhrpGroup>`
- **`IfaceIpv4Info`** — `addresses: Bag<Ipv4Address>`, `fhrpAddresses: Bag<Ipv4Address>`, `neighbors: Bag<ArpEntry>`, `fhrp: IfaceFhrp`, `multicastMode: MulticastMode?`
- **`IfaceIpv6Info`** — `addresses: Bag<Ipv6Address>`, `fhrpAddresses: Bag<Ipv6Address>`, `neighbors: Bag<ArpEntry>`, `fhrp: IfaceFhrp`, `multicastMode: MulticastMode?`
- **`IfaceSubIface`** — `ifaceName: String`, `subIfaceName: String?`
- **`IfaceType`** *(enum, 14 values)* — `IF_AGGREGATE`, `IF_BRIDGE`, `IF_ETHERNET`, `IF_LOOPBACK`, `IF_ROUTED_VLAN`, `IF_SONET`, `IF_TE_TUNNEL`, `IF_TUNNEL_GRE4`, … (14 total)
- **`InetGateway`** — `name: String?`, `id: String`, `tags: Bag<String>`, `region: String?`, `routeTableIds: Bag<String>`
- **`InstanceIface`** — `subnetId: String`, `ifaceId: String`
- **`IntRange`** — `start: Integer`, `end: Integer`
- **`InterfaceConnectivityParameters`** — `toExternalDevice: Bool?`, `toAccessLayerSwitch: Bool?`, `toUntrustedDevice: Bool?`, `toCoreLayer: Bool?`, `viaFiberOptics: Bool?`, `toCustomerEdgeDevice: Bool?`, `toDodinBackbone: Bool?`
- **`InterfaceConnectivityPolicy`** — `toExternalDevice: Bag<IsExternalInterfacePolicy>`, `toAccessLayerSwitch: Bag<ConnectsToAccessLayerSwitchInterfacePolicy>`, `toUntrustedDevice: Bag<IsUntrustedInterfacePolicy>`, `toCoreLayer: Bag<ConnectsToCoreLayerInterfacePolicy>`, `viaFiberOptics: Bag<ConnectsViaFiberOpticsInterfacePolicy>`, `toCustomerEdgeDevice: Bag<ConnectsToCustomerEdgeDeviceInterfacePolicy>`, `toDodinBackbone: Bag<ConnectsToDodinDeviceInterfacePolicy>`
- **`InterfacePolicy`** — `requiresDefaultVlan: Bag<RequiresDefaultVlanInterfacePolicy>`, `requiresMulticast: Bag<RequiresMulticastInterfacePolicy>`, `isHostGateway: Bag<IsHostGatewayInterfacePolicy>`, `pseudowireVirtualCircuitId: Bag<VirtualCircuitIdInterfacePolicy>`, `connectivity: InterfaceConnectivityPolicy`
- **`InterfacesService`** — `configurations: Bag<InterfacesServiceConfiguration>`
- **`InterfacesServiceConfiguration`** — `interfacesConfiguration: InterfacesServiceConfigurationDetail`
- **`InterfacesServiceConfigurationDetail`** — `dedicatedManagement: Bool`, `routes: Bag<BluecatRoute>`
- **`IpEntry`** — `prefix: IpSubnet`, `nextHops: Bag<NextHop>`
- **`IpUnicast`** — `ipEntries: Bag<IpEntry>`
- **`Ipv4Address`** — `ip: IpAddress`, `prefixLength: Integer`
- **`Ipv6Address`** — `ip: IpAddress`, `prefixLength: Integer`
- **`IsExternalInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`IsHostGatewayInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`IsProviderEdgeDevicePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`IsUntrustedInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`KeepAliveStatus`** *(enum, 4 values)* — `ALIVE`, `DISABLED`, `NOT_REACHABLE`, `SUSPENDED`
- **`Layer`** *(enum, 2 values)* — `L2`, `L3`
- **`LifecycleData`** — `createdAt: Timestamp?`, `lastModified: Timestamp?`, `lastUsed: Timestamp?`, `truncatedHitCount: Integer?`
- **`LoadBalancer`** — `name: String?`, `id: String`, `tags: Bag<String>`, `isUp: Bool`, `region: String?`, `loadBalancerRules: List<LoadBalancerRule>`, `outboundRules: List<OutboundRule>`
- **`LoadBalancerRule`** — `frontendIps: Bag<IpAddress>`, `protocol: Integer?`, `frontendPorts: Bag<IntRange>`, `backends: Bag<Backend>`
- **`Location`** — `name: String`, `id: String`, `city: String?`, `adminDivision: String?`, `country: String?`
- **`MacEntry`** — `macAddress: MacAddress`, `vlan: Integer?`, `interfaces: Bag<MacEntryInterfaceInfo>`, `entryType: MacEntryType`, `sourceType: MacEntrySourceType`
- **`MacEntryInterfaceInfo`** — `interfaceName: String`, `subinterfaceName: String?`
- **`MacEntrySourceType`** *(enum, 4 values)* — `FABRIC_PATH`, `LOCAL`, `MPLS`, `VXLAN`
- **`MacEntryType`** *(enum, 2 values)* — `DYNAMIC`, `STATIC`
- **`ManagementSubnetsDevicePolicy`** — `condition: StigPolicyCondition`, `value: Bag<IpSubnet>`
- **`MetadataMatches`** — `ingressInterfaces: Bag<String>`, `egressInterfaces: Bag<String>`
- **`MstInstance`** — `id: Integer`, `vlans: Bag<VlanIdOrRange>`, `bridgePriority: Integer?`, `bridgeAddress: MacAddress?`, `designatedRootPriority: Integer?`, `designatedRootAddress: MacAddress?`, `rootPortName: String?`, `rootCost: Integer?`
- **`Mstp`** — `name: String?`, `instances: Bag<MstInstance>`
- **`MulticastMode`** *(enum, 5 values)* — `BIDIRECTIONAL`, `DENSE`, `SOURCE_SPECIFIC_MULTICAST`, `SPARSE`, `SPARSE_DENSE`
- **`NamedVlanCollection`** — `name: String?`, `ranges: Bag<VlanRange>`
- **`NatEntry`** — `headerMatches: HeaderRegion`, `metadataMatches: MetadataMatches`, `name: String`, `description: String?`, `rewrites: Bag<HeaderRewrite>`, `interfaceNat: Bool`, `natType: NatType`
- **`NatGateway`** — `name: String?`, `id: String`, `tags: Bag<String>`, `region: String?`, `privateSubnets: Bag<IpSubnet>`, `publicSubnets: Bag<IpSubnet>`
- **`NatType`** *(enum, 1 values)* — `LB`
- **`Network`** — `devices: Bag<Device>`, `endpoints: Bag<NetworkEndpoint>`, `locations: Bag<Location>`, `cloudAccounts: Bag<CloudAccount>`, `cloudOrganizationalUnits: Bag<OrganizationalUnit>`, `externalSources: ExternalSources`, `dataConnectors: Bag<DataConnector>`, `cveDatabase: CveDatabase`, … (10 fields)
- **`NetworkAcl`** — `name: String?`, `id: String`, `tags: Bag<String>`, `ingressRules: List<SecurityRule>`, `egressRules: List<SecurityRule>`
- **`NetworkEndpoint`** — `name: String`, `locationName: String?`, `tagNames: Bag<String>`, `snapshotInfo: DeviceSnapshotInfo`, `profileName: String`, `httpResults: Bag<HttpApiEndpointResult>`, `cliCommandResponses: Bag<CliCommandResponse>`, `snmpOutputs: Bag<OidOutput>`
- **`NetworkExtensions`** *(no parsed fields)*
- **`NetworkInstance`** — `name: String`, `instanceType: NetworkInstanceType`, `afts: Afts`, `interfaces: Bag<IfaceSubIface>`, `vlans: Bag<Vlan>`, `protocols: Bag<NetworkInstanceProtocol>`, `fdb: NetworkInstanceFdb`
- **`NetworkInstanceFdb`** — `macEntries: Bag<MacEntry>`
- **`NetworkInstanceProtocol`** — `identifier: RoutingProtocolType`, `bgp: Bgp?`, `ospf: Ospf?`
- **`NetworkInstanceType`** *(enum, 2 values)* — `DEFAULT_INSTANCE`, `L3VRF`
- **`NetworkObject`** — `name: String`, `subnets: Bag<IpSubnet>`
- **`NextHop`** — `weight: Integer`, `ipAddress: IpAddress?`, `macAddress: MacAddress?`, `vrf: String?`, `poppedMplsLabels: Bag<Integer>`, `pushedMplsLabels: Bag<Integer>`, `interfaceName: String?`, `subInterfaceName: String?`, … (11 fields)
- **`NextHopType`** *(enum, 9 values)* — `ATTACHED`, `BROADCAST`, `DROP`, `RECEIVE`, `RECURSIVE`, `REDIRECT`, `REMOTE`, `UNDEFINED`, … (9 total)
- **`NtpConfigurationDetail`** — `servers: Bag<NtpServer>`, `enable: Bool`
- **`NtpServer`** — `address: IpAddress`, `stratum: String`
- **`NtpService`** — `configurations: Bag<NtpServiceConfiguration>`
- **`NtpServiceConfiguration`** — `ntpConfiguration: NtpConfigurationDetail`
- **`OS`** *(enum, 67 values)* — `ACOS`, `ALKIRA_CXP`, `APIC`, `ARISTA_EOS`, `ARUBA_AOS_CX`, `ARUBA_SWITCH`, `ARUBA_WIFI`, `ASA`, … (67 total)
- **`OidCollectionStatus`** *(enum)*
- **`OidEntry`** — `oid: String`, `oidNumbers: Bag<Integer>`, `rawValue: String`
- **`OidOutput`** — `requestedOid: String`, `alias: String`, `status: OidCollectionStatus`, `rawOidEntries: Bag<OidEntry>`
- **`OperStatus`** *(enum, 7 values)* — `DORMANT`, `DOWN`, `LOWER_LAYER_DOWN`, `NOT_PRESENT`, `TESTING`, `UNKNOWN`, `UP`
- **`OrganizationalUnit`** — `id: String`, `name: String`, `parentUnitId: String?`
- **`OriginProtocol`** *(enum, 17 values)* — `BGP`, `DIRECT_CONNECTED`, `EIGRP`, `FRR`, `IGMP`, `ISIS`, `LDP`, `LOCAL_AGGREGATE`, … (17 total)
- **`OsSupport`** — `announcementUrl: String`, `lastMaintenanceDate: Date`, `lastVulnerabilityDate: Date?`, `lastSupportDate: Date`
- **`Ospf`** — `areas: Bag<OspfArea>`
- **`OspfArea`** — `id: Integer`, `domain: String?`, `processId: String?`, `lsaCount: Integer?`, `areaType: OspfAreaType`, `routerType: OspfRouterType?`, `neighbors: Bag<OspfNeighbor>`
- **`OspfAreaType`** *(enum, 6 values)* — `BACKBONE`, `NSSA`, `STANDARD`, `STUB`, `TOTALLY_NSSA`, `TOTALLY_STUBBY`
- **`OspfNeighbor`** — `localInterface: String`, `remoteInterfaceIp: IpSubnet`, `remoteRouterId: IpAddress`, `cost: Integer`, `role: OspfRole?`, `remotePeer: OspfRemotePeer?`
- **`OspfRemotePeer`** — `deviceName: String`, `interface: String`, `processId: String?`, `cost: Integer`
- **`OspfRole`** *(enum, 2 values)* — `BACKUP_DESIGNATED_ROUTER`, `DESIGNATED_ROUTER`
- **`OspfRouterType`** *(enum, 3 values)* — `ABR`, `ABR_ASBR`, `ASBR`
- **`OutboundRule`** — `privateSubnets: Bag<IpSubnet>`, `publicSubnets: Bag<IpSubnet>`, `protocol: Integer?`
- **`Outputs`** — `commands: Bag<Command>`, `snmpOutputs: Bag<OidOutput>`, `bluecat: BluecatOutputs?`
- **`PaginatedHttpEndpoint`** — `name: String`, `status: PaginatedHttpEndpointStatus`, `error: String?`, `pages: Bag<HttpPage>`
- **`PaginatedHttpEndpointStatus`** *(enum, 4 values)* — `ERROR`, `MAX_PAGES_REACHED`, `OK`, `TIMED_OUT`
- **`PanosFiles`** — `configTemplate: List<ConfigLine>`, `configPolicy: List<ConfigLine>`
- **`Path`** — `hops: List<Hop>`
- **`PbrAction`** *(no parsed fields)*
- **`PeerLink`** — `portName: String`, `isUp: Bool`, `activeVlans: Bag<Integer>`
- **`PeerStatus`** *(enum, 3 values)* — `ADJACENCY_OK`, `LINK_DOWN`, `LINK_NOT_CONFIGURED`
- **`PeerType`** *(enum, 2 values)* — `EXTERNAL`, `INTERNAL`
- **`PhysicalLink`** — `deviceName: String`, `ifaceName: String`
- **`Platform`** — `deviceType: DeviceType`, `vendor: Vendor`, `model: String?`, `os: OS`, `osVersion: String?`, `osSupport: OsSupport?`, `components: Bag<DevicePart>`, `managementIps: Bag<IpAddress>`
- **`PortSpeed`** *(enum, 11 values)* — `SPEED_100GB`, `SPEED_100MB`, `SPEED_10GB`, `SPEED_10MB`, `SPEED_1GB`, `SPEED_2500MB`, `SPEED_25GB`, `SPEED_40GB`, … (11 total)
- **`PublicUnallocatedIp`** — `ipAddress: IpAddress`, `description: String?`, `networkBorderGroup: String`
- **`PublicUnallocatedIpSubnet`** — `ipSubnet: IpSubnet`, `description: String?`, `networkBorderGroup: String`
- **`QRadarConfig`** — `enable: Bool`, `ip: IpAddress?`
- **`RapidPvst`** — `vlans: Bag<RapidPvstVlan>`
- **`RapidPvstVlan`** — `vlanId: Integer`, `bridgePriority: Integer?`, `bridgeAddress: MacAddress?`, `designatedRootPriority: Integer?`, `designatedRootAddress: MacAddress?`, `rootPortName: String?`, `rootCost: Integer?`
- **`RefObj`** — `refObjType: RefObjType`, `refObjId: String`
- **`RefObjType`** *(enum, 14 values)* — `ADDRESS_REFERENCE`, `AWS_OUTPOST_LGW`, `COMP_INSTANCE`, `DCGW`, `IGW`, `INTERFACE`, `NATGW`, `SUBNET`, … (14 total)
- **`RequiresDefaultVlanInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`RequiresMulticastInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Bool`
- **`Route`** — `vrf: String?`, `routeDistinguisher: String?`, `prefix: IpSubnet`, `pathAttributes: Bag<AttrSet>`
- **`RouteTable`** — `name: String?`, `id: String`, `tags: Bag<String>`, `region: String?`, `routes: Bag<CloudRoute>`
- **`RoutedVlan`** — `vlan: Integer`, `ipv4: IfaceIpv4Info`, `ipv6: IfaceIpv6Info`, `networkInstanceName: String`
- **`RoutingProtocolType`** *(enum, 9 values)* — `BGP`, `DIRECTLY_CONNECTED`, `IGMP`, `ISIS`, `LOCAL_AGGREGATE`, `OSPF`, `OSPF3`, `PIM`, … (9 total)
- **`Rstp`** — `bridgePriority: Integer?`, `bridgeAddress: MacAddress?`, `designatedRootPriority: Integer?`, `designatedRootAddress: MacAddress?`, `rootPortName: String?`, `rootCost: Integer?`
- **`RuleContainer`** — `name: String`, `containerType: ContainerType`
- **`SecurityGroup`** — `name: String?`, `id: String`, `groupName: String?`, `description: String?`, `tags: Bag<String>`, `ingressRules: List<SecurityRule>`, `egressRules: List<SecurityRule>`
- **`SecurityRule`** — `match: HeaderRegion`, `action: SecurityRuleAction`
- **`SecurityRuleAction`** *(enum, 2 values)* — `DENY`, `PERMIT`
- **`ServiceEndpoint`** — `name: String?`, `id: String`, `tags: Bag<String>`, `region: String`, `ipSubnets: Bag<IpSubnet>`, `backendLoadBalancerIds: Bag<String>`
- **`Severity`** *(enum, 5 values)* — `CRITICAL`, `HIGH`, `LOW`, `MEDIUM`, `NONE`
- **`SnmpAgentService`** — `system: SnmpAgentServiceSystem`, `v2c: SnmpAgentV2C`, `loglevel: String`, `pollingPeriod: Integer`, `v1: SnmpAgentV1`, `v3: SnmpAgentV3`
- **`SnmpAgentServiceSystem`** — `contact: String`, `name: String`, `description: String`, `location: String`
- **`SnmpAgentV1`** — `enable: Bool`, `community: String`
- **`SnmpAgentV2C`** — `enable: Bool`, `community: String`
- **`SnmpAgentV3`** — `securityLevel: String`, `privtype: String`, `enable: Bool`, `username: String?`, `authtype: String`
- **`SnmpConfigurationDetail`** — `enable: Bool`, `agentService: SnmpAgentService`, `trapService: SnmpTrapService`
- **`SnmpService`** — `configurations: Bag<SnmpServiceConfiguration>`
- **`SnmpServiceConfiguration`** — `snmpConfiguration: SnmpConfigurationDetail`
- **`SnmpSource`** — `name: String`, `snapshotInfo: DeviceSnapshotInfo`, `profileName: String`, `outputs: Bag<OidOutput>`
- **`SnmpTrapServer`** — `address: IpAddress`, `port: Integer`, `enable: Bool`, `v3: SnmpAgentV3?`
- **`SnmpTrapService`** — `trapServers: Bag<SnmpTrapServer>`
- **`SshConfigurationDetail`** — `tacacs: SshTacacsConfig`, `enable: Bool`
- **`SshService`** — `configurations: Bag<SshServiceConfiguration>`
- **`SshServiceConfiguration`** — `sshConfiguration: SshConfigurationDetail`
- **`SshTacacsConfig`** — `enable: Bool`
- **`StigDatabase`** — `policy: StigPolicy`, `parameterUsages: Bag<StigParameterUsage>`, `defaultParameters: DefaultStigParameters`, `guides: Bag<StigGuide>`
- **`StigGuide`** — `name: String`, `versions: Bag<StigRuleCollection>`
- **`StigParameterUsage`** — `parameterName: String`, `rules: Bag<String>`
- **`StigPolicy`** — `devicePolicy: DevicePolicy`, `ifacePolicy: InterfacePolicy`, `vrfPolicy: VrfPolicy`
- **`StigPolicyCondition`** — `ordinal: Integer`, `deviceNamePattern: String`, `ifaceNamePattern: String`, `vrfName: String`, `tagNames: Bag<String>`, `locationNames: Bag<String>`
- **`StigRule`** — `id: String`, `vulnerabilityId: String`, `version: String`, `intent: String`, `description: String`, `checkContent: String`, `fixText: String`, `severity: StigSeverity`, … (10 fields)
- **`StigRuleCollection`** — `id: String`, `rules: Bag<StigRule>`
- **`StigSeverity`** *(enum, 3 values)* — `HIGH`, `LOW`, `MEDIUM`
- **`Stp`** — `rstp: Rstp`, `mstp: Mstp`, `rapidPvst: RapidPvst`
- **`SubInterface`** — `name: String`, `layer: Layer`, `aliases: Bag<String>`, `description: String?`, `adminStatus: AdminStatus`, `operStatus: OperStatus`, `acls: IfaceAcls`, `vlan: SubInterfaceVlan?`, … (12 fields)
- **`SubInterfaceVlan`** *(enum, 2 values)* — `QINQ_ID`, `VLAN_ID`
- **`Subnet`** — `name: String?`, `id: String`, `tags: Bag<String>`, `addresses: Bag<IpSubnet>`, `region: String`, `availabilityZone: String`, `ifaces: Bag<CloudIface>`, `routeTableId: String`, … (9 fields)
- **`SwitchedSubInterfaceVlans`** — `outerVlans: VlanIdSetOrAll?`, `innerVlans: VlanIdSetOrAll?`
- **`SwitchedVlan`** — `interfaceMode: VlanModeType`, `nativeVlan: Integer?`, `accessVlan: Integer?`, `voiceVlan: Integer?`, `defaultVlan: Integer?`, `trunkVlans: Bag<VlanIdOrRange>`
- **`SyslogConfigurationDetail`** — `qradar: QRadarConfig`, `arcsight: ArcsightConfig`, `servers: Bag<SyslogServer>`
- **`SyslogServer`** — `ip: IpAddress`, `port: Integer`, `transport: String`
- **`SyslogService`** — `configurations: Bag<SyslogServiceConfiguration>`
- **`SyslogServiceConfiguration`** — `syslogConfiguration: SyslogConfigurationDetail`
- **`System`** — `hostNames: Bag<String>`, `otherNames: Bag<String>`, `physicalName: String`, `uptimeSeconds: Integer?`, `uptime: Duration?`
- **`TeTunnel`** — `nextHops: Bag<TeTunnelNextHop>`, `networkInstanceName: String`
- **`TeTunnelNextHop`** — `interfaceName: String`, `ipAddress: IpAddress`, `mplsLabels: Bag<Integer>`
- **`TransitGateway`** — `name: String?`, `id: String`, `tags: Bag<String>`, `region: String?`, `attachments: Bag<TransitGatewayAttachment>`, `routeTables: Bag<TransitGatewayRouteTable>`
- **`TransitGatewayAttachment`** — `name: String?`, `id: String`, `tags: Bag<String>`, `attachmentType: TransitGatewayAttachmentType`, `routeTables: Bag<TransitGatewayRouteTable>`
- **`TransitGatewayAttachmentType`** *(enum, 5 values)* — `CONNECT`, `DC`, `TGW_PEERING`, `VPC`, `VPN`
- **`TransitGatewayRoute`** — `prefixes: Bag<IpSubnet>`, `routeType: CloudRouteType`, `nextHopAttachmentIds: Bag<String>`
- **`TransitGatewayRouteTable`** — `name: String`, `id: String`, `tags: Bag<String>`, `routes: Bag<TransitGatewayRoute>`
- **`Tunnel`** — `src: IpAddress`, `dst: IpAddress`, `ipv4: IfaceIpv4Info`, `ipv6: IfaceIpv6Info`, `networkInstanceName: String`
- **`Url`** — `host: String`, `path: String`
- **`Vendor`** *(enum, 39 values)* — `A10`, `ALKIRA`, `AMAZON`, `ARISTA`, `ARUBA`, `AVAYA`, `AVI_NETWORKS`, `AZURE`, … (39 total)
- **`VendorCveInfo`** — `vendor: Vendor`, `publicationDate: Date?`, `url: String?`, `severity: Severity`, `hasKnownExploit: Bool?`, `baseScore: Float?`, `baseScoreV2: Float?`, `baseScoreV3: Float?`, … (11 fields)
- **`VirtualCircuitIdInterfacePolicy`** — `condition: StigPolicyCondition`, `value: Integer`
- **`Vlan`** — `vlanId: Integer`, `name: String?`, `memberNames: Bag<String>`
- **`VlanIdOrRange`** *(enum, 2 values)* — `ID`, `RANGE`
- **`VlanIdSet`** — `vlans: Bag<Integer>`
- **`VlanIdSetOrAll`** *(enum, 2 values)* — `ALL`, `IDS`
- **`VlanModeType`** *(enum, 2 values)* — `ACCESS`, `TRUNK`
- **`VlanPair`** — `from: Integer`, `to: Integer`
- **`VlanRange`** — `from: Integer`, `to: Integer`
- **`Vpc`** — `id: Integer`, `portName: String`, `isUp: Bool`, `isConsistent: Bool`, `activeVlans: Bag<Integer>`
- **`VpcData`** — `name: String?`, `id: String`, `tags: Bag<String>`, `cloudRegions: Bag<String>`, `cloudType: CloudType`, `subnets: Bag<Subnet>`, `computeInstances: Bag<ComputeInstance>`, `serviceEndpoints: Bag<ServiceEndpoint>`, … (20 fields)
- **`VpcDomain`** — `domainId: Integer`, `peerStatus: PeerStatus?`, `vpcKeepAliveStatus: KeepAliveStatus?`, `vpcRole: VpcRole?`, `peerGatewayEnabled: Bool`, `gracefulConsistencyCheckEnabled: Bool`, `autoRecoveryStatusEnabled: Bool`, `peerLinkStatus: PeerLink?`, … (9 fields)
- **`VpcPeering`** — `name: String`, `id: String`, `tags: Bag<String>`, `sourceVpcId: String`, `destinationVpcId: String?`
- **`VpcRole`** *(enum, 4 values)* — `OPERATIONAL_PRIMARY`, `OPERATIONAL_SECONDARY`, `PRIMARY`, `SECONDARY`
- **`VpnConnection`** — `name: String?`, `id: String`, `tags: Bag<String>`, `isUp: Bool`, `tunnelSrcIps: Bag<IpAddress>`, `tunnelDstIps: Bag<IpAddress>`
- **`VpnGateway`** — `name: String?`, `id: String`, `tags: Bag<String>`, `region: String?`, `vpnConnections: Bag<VpnConnection>`
- **`VrfPolicy`** *(no parsed fields)*