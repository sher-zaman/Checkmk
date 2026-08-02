# DFS state check

Checkmk extension for monitoring the operational state of DFS Replication (DFSR) replicated folders through the `root\MicrosoftDFS` WMI provider.

## Attribution

This is a fixed build of an existing extension.

Original check: Allan GooD, allan.cassaro@gmail.com
Original MKP packaging: Roger Ellenberger, roger.ellenberger@wagner.ch (WagnerAG)
Upstream source: [github.com/WagnerAG/checkmk_dfs_state](https://github.com/WagnerAG/checkmk_dfs_state)

## Changes in this fork

- Bakery deployment was a silent no-op on Checkmk 2.4. The bakery module imported from the removed `cmk.base.api.bakery` namespace, which raised `ModuleNotFoundError` at bake time. The bakery skipped the plugin silently, so the deploy toggle never produced a file. Migrated to `register.bakery_plugin` with `.bakery_api.v1`.
- The Windows script was packaged under `agent_based/`, which the bakery does not read for `OS.WINDOWS` sources. Relocated to `agents/windows/plugins/`.
- The agent runs as a 32-bit process, and the `root\MicrosoftDFS` provider is only visible to 64-bit callers, so no section was produced even with a correctly deployed script. The plugin now relaunches itself under 64-bit PowerShell via `sysnative` before querying.
- Migrated to `Get-CimInstance`, switched output to `sep(9)` so folder and group names containing spaces parse correctly, and made WMI failures visible in the raw agent output instead of returning a blank section.
- The man page shipped in the legacy `checkman` part, which Checkmk 2.4 reports as outdated and ignores. Moved into the plugin family under `cmk_addons_plugins/dfs_state/checkman/`.
- Added a checkman page.

The check plugin and ruleset are unchanged from upstream, so existing discovered services keep their item names.

## Why this exists

Checkmk has no built-in coverage for DFS Replication state. A replicated folder can drop into Auto Recovery or Error without any visible symptom until users notice missing or stale files.

## What it monitors

- **DFS Share n**: one service per replicated folder, reporting the DFSR state. State 4 (Normal Operation) is OK, states 1 to 3 (Initializing, Initial Synchronization, Auto Recovery) are WARN, state 5 (Error) is CRIT, and state 0 (Not Initialized) is UNKNOWN.

No configuration is required for the check to work.

## Example services

```
DFS Share SYSVOL Share             OK    State: DFS in Normal Operation, ReplicationGroup: Domain System Volume
```

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- Windows Server with the DFS Replication role
- Checkmk agent installed on the DFSR member

## Installation

1. Install the package via **Setup > Extension packages > Upload package**.

2. Enable the bakery rule **DFS state plugin** and bake, or place `dfs_state.ps1` in the agent's plugins directory manually. Baking is recommended, since a manual copy is wiped on every agent update.

3. Run a service discovery on the host.

## Conflicts and supersedes

This package uses the same package name and file paths as the upstream `dfs_state` extension. Disable or remove the upstream package before installing this one.

## Configuration

- **DFS state plugin**: deploy toggle, defaulting to enabled.

No ruleset configuration is required. The check ships with working defaults.

## Validated

Validated in multiple production Checkmk environments.

## Version history

- **2.1.1**: DFS Replication state monitoring on Checkmk 2.4, one service per replicated folder with state mapped to OK, WARN, CRIT and UNKNOWN, deployed through the Agent Bakery with automatic 64-bit relaunch

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
