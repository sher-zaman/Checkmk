# Windows DHCP Failover Monitoring

Checkmk extension for monitoring DHCPv4 failover relationships on Windows DHCP servers through the Checkmk agent.

## Why this exists

Checkmk has no built-in coverage for DHCP failover. A broken relationship is silent: both servers keep serving leases from their own half of the pool until one runs out.

The extension deploys through the Agent Bakery instead of a manually placed script, so it survives every agent update without being re-copied.

## What it monitors

- **DHCP Failover n**: one service per failover relationship, reporting state, mode, partner server, and scope count. Defaults to OK for `Normal`, WARN for `CommunicationInterrupted` and transitional states, CRIT for `PartnerDown` and conflict states. Full scope list in the details.

On a server without the DHCP Server role the plugin exits silently and no services are discovered. A collection failure is reported as UNKNOWN rather than passing as healthy.

## Example services

```
DHCP Failover dc01-dc02           OK    State: Normal, Mode: LoadBalance, Partner: dc02, Scopes: 6
```

```
Summary   State: Normal, Mode: LoadBalance, Partner: dc02, Scopes: 6

Details   State: Normal
          Mode: LoadBalance
          Partner: dc02
          Scopes in this relationship: 10.0.10.0, 10.0.20.0, 10.0.30.0,
          10.0.40.0, 10.0.50.0, 10.0.60.0
```

## Graphing

- **DHCP Failover**: the number of scopes covered by the relationship, on its own graph, so a scope silently dropping out of failover protection is visible historically.

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- Windows Server with the DHCP Server role and the `DhcpServer` PowerShell module
- Checkmk agent installed on the DHCP server

## Installation

1. Install the package via **Setup > Extension packages > Upload package**.

2. Enable the bakery rule **DHCP failover monitoring (Windows)** and bake, or place `dhcp_failover.ps1` in the agent's plugins directory manually. Baking is recommended, since a manual copy is wiped on every agent update.

3. Run a service discovery on the host.

## Configuration

- **Windows DHCP failover relationships**: monitoring state per relationship state, per host and relationship. Defaults: OK for `Normal`, WARN for `CommunicationInterrupted` and transitional states, CRIT for `PartnerDown` and conflict states, since a partner-down server serves the pool alone.
- **DHCP failover monitoring (Windows)**: deploy toggle, defaulting to enabled. Inert on Checkmk Raw.

No ruleset configuration is required. The check ships with working defaults.

## Validated

Validated in multiple production Checkmk environments, covering load balance and hot standby relationships.

## Version history

- **1.0.1**: author metadata update
- **1.0.0**: initial release, one service per failover relationship with state, mode, partner, server role and scope reporting, a dedicated state mapping ruleset, and Agent Bakery deployment

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
