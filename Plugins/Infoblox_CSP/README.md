# Infoblox Cloud Services Portal (CSP) REST API Special Agent

Checkmk extension for monitoring the Infoblox Cloud Services Portal through its REST API.

## Why this exists

On-appliance monitoring only sees what each NIOS-X server knows about itself. This reads from the portal directly, so a service failing anywhere in the tenant is visible even if the server hosting it still reports online.

## What it monitors

- **Per NIOS-X server** (piggyback host): status, deployed services (DNS, DHCP, DFP, NTP, Data Connector, etc.), platform/application management, DHCP HA role and state, anycast advertisement, 24h peak DNS/DHCP/object counts
- **Service availability by type**: tenant-wide online count per service type
- **DHCP high availability**: group and per-node state, heartbeat age
- **Anycast**: configuration status, advertising host count, BGP/OSPF detail
- **IPAM**: DHCP ranges (default), subnets/address blocks (opt in), IP space rollup
- **DNS**: zones, views, global configuration
- **Threat Defense**: security policies, active DFPs, threat feeds, external networks
- **Tenant rollup**: server count, update deferrals
- **Inventory**: platform, OS/build version, cloud provider, template assignment

Configuration and inventory data is cached hourly with an honest age; health data is always fresh.

## Example services

```
Infoblox Server Status                             OK    Status: online
Infoblox Service DNS                                OK    Status: started
Infoblox Platform Management                        OK    Status: online
Infoblox DHCP HA Node                                OK    Role: active, state: hot-standby
Infoblox Anycast Node AC_DNS                         OK    This host: Active
Infoblox Peak Usage                                  OK    DNS queries: 70.68/s in the last 24h
Infoblox Service Availability DNS                    OK    2 of 2 online (100%)
Infoblox DHCP HA Group DHCP_Grp1                     OK    Status: ok
Infoblox Anycast AC_DNS                               OK    2 of 2 hosts advertising
Infoblox DHCP Range 10.1.10.100-10.1.10.200           OK    Utilization: 4.00%
Infoblox DNS Zones                                    OK    22 authoritative zones
Infoblox Active DFPs                                  OK    2 of 2 proxies active (100%)
Infoblox External Networks                            OK    1 external networks, 1 addresses
Infoblox Threat Feeds                                 OK    30 threat feeds subscribed
Infoblox Hosts                                        OK    3 of 3 servers online
```

## Graphing

- **IPAM**: address utilisation and counts, per range, subnet, block and IP space.
- **Peaks**: DNS, DHCP and object peaks, each as a separate graph.
- **Service availability**: with a perfometer.
- **Anycast and active DFPs**: counts.
- **DHCP high availability**: heartbeat, check-in and state-duration ages.

## Data source

One special agent, `agent_infoblox_csp`, against the portal REST API. Health endpoints are queried every cycle; configuration and inventory endpoints are cached on a configurable interval (default one hour). Each NIOS-X server is a piggyback host, named to match its display name in the portal. Host and service labels (cloud provider, deployment type, service type) are emitted for use with DCD or rules.

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- An Infoblox CSP account with a user or service API key

### Required permissions

Read only is sufficient. Use a dedicated read only or service account rather than a personal one.

## Installation

1. Install via **Setup > Extension packages > Upload package**.
2. Create a tenant host with agent type "Configured API integrations, no Checkmk agent".
3. Add a rule under **Setup > Agents > Other integrations > "Infoblox Cloud Services Portal (CSP)"** with the API key.
4. Discover on the tenant host.
5. Create a host per NIOS-X server (matching its portal display name), agent type "No API integrations, no Checkmk agent", piggyback set to "Always use and expect piggyback data". Discover on each.
6. Optional: enable subnet/address block discovery under the network discovery rule.

## Configuration

A ruleset per check under Setup > Services > Service monitoring rules, Applications: status mappings, age and utilisation levels, expected-value assertions, minimum-count thresholds. All ship with working defaults; no configuration is required.

## Validated

Validated against a production Infoblox CSP tenant covering DNS, DHCP, DFP, NTP, Data Connector and DHCP high availability. Anycast is validated against the documented API schema rather than a live configuration.

## Version history

- **1.6.0**: initial public release

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
