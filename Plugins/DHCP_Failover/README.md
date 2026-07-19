# DHCP Failover Monitoring (Windows)

Checkmk agent-based extension for monitoring Windows Server DHCPv4 failover relationships.

## Why this exists

Windows DHCP failover is a common high-availability setup, but Checkmk has no built-in visibility into whether a failover relationship is healthy. This extension surfaces the live state of each relationship so a partner going down, or communication breaking between partners, is caught before it becomes a lease outage.

## What it monitors

One service per failover relationship, named "DHCP Failover <relationship>". Each service reports:

- Relationship state, mapped to Checkmk levels
- Failover mode (load balance or hot standby)
- Partner server
- Server role (hot standby only)
- Scope count as a metric, with the full scope list in service details

State mapping defaults: Normal is OK, CommunicationInterrupted and transitional states (Init, Startup, Recover) are WARN, PartnerDown and conflict states are CRIT.

A deleted relationship produces no output, so Checkmk flags the service as vanished rather than silently reporting OK.

## Requirements

- Windows Server with the DHCP role and one or more failover relationships
- Checkmk 2.3.0 or later
- The agent plugin deployed to the DHCP server (manually or via the bakery)

## Installation

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk, or place it in `local/` and run `mkp install`.
2. Deploy the agent plugin to the DHCP server, either manually into the agent's plugins directory, or by enabling the bakery rule "DHCP failover monitoring (Windows)" and baking a new agent.
3. Run a service discovery on the DHCP host. One service per relationship should appear.

The agent plugin exits silently on hosts without the DHCP role, so it is safe to bake broadly without creating phantom services.

## Configuration

- **Windows DHCP failover relationships** ruleset: remap any of the five state categories per relationship, no script edits needed.
- **DHCP failover monitoring (Windows)** bakery rule: deploy toggle plus an optional asynchronous execution interval (default 5 minutes). Inert on Checkmk Raw.

## Version

**1.0.0**

## Author

Sher Zaman

## License

See repository [LICENSE.md](../../LICENSE.md).
