# DFSR backlog check

Checkmk extension for monitoring the DFS Replication (DFSR) backlog per replicated folder and partner through the `root\MicrosoftDFS` WMI provider.

## Attribution

This is a fixed build of an existing extension.

Original check: Kai Biebel
Original MKP packaging: Roger Ellenberger, roger.ellenberger@wagner.ch (WagnerAG)
Upstream source: [github.com/WagnerAG/checkmk_dfs_backlog](https://github.com/WagnerAG/checkmk_dfs_backlog)

## Changes in this fork

- Bakery deployment was a silent no-op on Checkmk 2.4. The bakery module imported from the removed `cmk.base.api.bakery` namespace, which raised `ModuleNotFoundError` at bake time. The bakery skipped the plugin silently, so the deploy toggle never produced a file. Migrated to `register.bakery_plugin` with `.bakery_api.v1`.
- The Windows script was packaged under `agent_based/`, which the bakery does not read for `OS.WINDOWS` sources. Relocated to `agents/windows/plugins/`.
- The agent runs as a 32-bit process, and the `root\MicrosoftDFS` provider is only visible to 64-bit callers, so no section was produced even with a correctly deployed script. The plugin now relaunches itself under 64-bit PowerShell via `sysnative` before querying.
- Rewrote the collector using `Get-CimInstance` and cached CIM/DCOM sessions to partners, with per-pairing error isolation so one unreachable partner no longer blanks the whole section.
- The man page shipped in the legacy `checkman` part, which Checkmk 2.4 reports as outdated and ignores. Moved into the plugin family under `cmk_addons_plugins/dfs_backlog/checkman/`.
- Added a checkman page.

The check plugin and ruleset are unchanged from upstream, so existing discovered services keep their item names.

## Why this exists

Checkmk has no built-in coverage for DFS Replication backlog. Replication can keep running while silently falling behind, and a state-only check cannot show that.

## What it monitors

- **DFS Backlog n**: one service per replicated folder, partner, and direction (from the partner, to the partner), reporting the queued file count. Defaults to WARN at 300 files, CRIT at 1000 files. A pairing that cannot be evaluated, for example an unreachable partner, is reported as DFSR Disabled (OK) rather than a false alarm.

No configuration is required for the check to work.

## Example services

```
DFS Backlog Data from dc02          WARN  Backlog: 412 files
```

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- Windows Server with the DFS Replication role
- WMI and DCOM access to replication partners, performed under the machine account. Computing the backlog requires reading the partner's version vector.
- Checkmk agent installed on the DFSR member

## Installation

1. Install the package via **Setup > Extension packages > Upload package**.

2. Enable the bakery rule **DFS Backlog plugin** and bake, or place `dfs_backlog.ps1` in the agent's plugins directory manually. Baking is recommended, since a manual copy is wiped on every agent update.

3. Run a service discovery on the host.

## Conflicts and supersedes

This package uses the same package name and file paths as the upstream `dfs_backlog` extension. Disable or remove the upstream package before installing this one.

## Configuration

- **DFS Backlog plugin**: deploy toggle, defaulting to enabled.

No ruleset configuration is required. The check ships with working defaults.

## Known limitation

The check derives the item name from the first space-delimited token of the folder name. A replicated folder whose name contains a space, for example SYSVOL Share, renders with a truncated item. This is an upstream limitation, left unchanged so service item names stay stable.

## Validated

Validated in multiple production Checkmk environments.

## Version history

- **1.5.1**: DFS Replication backlog monitoring on Checkmk 2.4, one service per replicated folder, partner, and direction with configurable file-count levels, deployed through the Agent Bakery with automatic 64-bit relaunch and per-pairing error isolation

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
