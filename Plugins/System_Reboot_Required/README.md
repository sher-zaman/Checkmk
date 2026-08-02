# System Reboot Required (Linux)

Checkmk agent-based extension that detects whether a Linux host has a pending reboot, typically after a kernel or core library update.

## Attribution

Fork of the `system_reboot_required` extension by Luca-Leon Hausdoerfer ([lhausdoerfer on Checkmk Exchange](https://exchange.checkmk.com/u/lhausdoerfer), [blaugrau90 on GitHub](https://github.com/blaugrau90/cmk-linux-server-reboot)).

This is a maintenance fork. The original author's copyright is preserved on all derived files, and new files added in this fork carry their own copyright. Licensed under GPLv3.

## Changes in this fork

Additions and fixes on top of the original v1.0.1:

- **Fixes missed reboots on Ubuntu.** Adds `needrestart` detection so a pending reboot after a kernel update is caught even when the `reboot-required` sentinel file is never created (the original relied on that file alone).
- **Adds working SUSE support** via `zypper needs-rebooting`, which was previously non-functional.
- **Adds Agent Bakery support** for automatic agent deployment.
- **Configurable state for unknown pending-since age.** Previously fixed; now selectable in the ruleset and defaulting to WARN instead of CRIT.
- **Pending-age metric.** Adds perfdata and a perfometer for the pending reboot age when it can be determined.
- **More robust kernel-package fallback**, handling `kernel`, `kernel-core`, and `kernel-default` package naming across RPM-based distributions.

## Why this exists

Checkmk has no built-in coverage for pending Linux reboots. A host can sit for months on an unapplied kernel or library update without anyone noticing.

## What it monitors

One service per host reporting whether a reboot is pending. The service is OK when no reboot is required. When a reboot is pending, the state is driven by how long it has been pending:

- OK below the WARN threshold
- WARN between the thresholds
- CRIT at or above the CRIT threshold

Defaults are 12 hours (WARN) and 24 hours (CRIT), both configurable. If the pending-since time cannot be determined, a configurable state is used instead (default WARN). When the age is known, the check produces a perfdata metric for the pending reboot age, with a perfometer.

## Example services

```
System Reboot Required   OK    No reboot pending
```

```
System Reboot Required   CRIT  Reboot pending (detected via: reboot-required-file), pending since: 546h 13m, packages: linux-image-6.17.0-1019-aws, linux-base
```

## Graphing

- **System Reboot Required**: pending reboot age, shown on a perfometer and graphed over time, whenever the pending-since time can be determined.

Services with no metrics: the System Reboot Required service emits no metric when no reboot is pending, or when a reboot is pending but the pending-since time cannot be determined.

## Detection methods

The agent plugin tries the following in order and stops at the first positive result:

1. `/var/run/reboot-required` and `/run/reboot-required` sentinel files (Debian, Ubuntu, Kali)
2. `needrestart` in kernel-only batch mode (Debian, Ubuntu, Kali)
3. `needs-restarting` from dnf-utils/yum-utils (RHEL, CentOS, Rocky Linux, AlmaLinux, Fedora, Amazon Linux 2/2023)
4. `zypper needs-rebooting` (SUSE, openSUSE)
5. Running kernel compared against the newest installed kernel package, as a fallback (kernel, kernel-core, and kernel-default package naming)

Where the detection method provides no native timestamp, the modification time of the newest kernel image in `/boot` is used as a best-effort pending-since time.

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- Linux host (Debian, Ubuntu, Kali, RHEL, CentOS, Rocky Linux, AlmaLinux, Fedora, SUSE, openSUSE, or Amazon Linux 2/2023)
- The agent plugin deployed to the host (manually or via the bakery)

## Installation

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk, or place it in `local/` and run `mkp install`.
2. Deploy the agent plugin to the host, either manually into the agent's plugins directory, or by enabling the bakery rule "System Reboot Required (Linux)" and baking a new agent.
3. Run a service discovery on the host. One service should appear if the agent section is present.

## Conflicts and supersedes

This package uses the same package name and file paths as the original `system_reboot_required` v1.0.1 by [lhausdoerfer](https://exchange.checkmk.com/u/lhausdoerfer). You must disable or remove the original package before installing this version.

## Configuration

- Check parameters ruleset: WARN/CRIT age thresholds and the service state used when the pending age is unknown.
- Bakery rule "System Reboot Required (Linux)": deploy toggle for automatic agent deployment.

## Validated

Validated on Debian, Ubuntu, Kali, and RHEL.

## Version history

- **1.1.0**: adds needrestart detection to catch missed reboots on Ubuntu, adds working SUSE support via zypper needs-rebooting, adds Agent Bakery deployment, makes the unknown pending-age state configurable (default WARN), adds a pending-age metric with perfometer, and hardens the kernel-package fallback across RPM-based distributions

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPLv3, preserving the original author's copyright. See [LICENSE.md](LICENSE.md) in this folder.
