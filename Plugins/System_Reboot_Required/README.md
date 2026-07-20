# System Reboot Required (Linux)

Checkmk agent-based extension that detects whether a Linux host has a pending reboot, typically after a kernel or core library update.

## Attribution

This is a maintenance fork of the `system_reboot_required` extension originally written by Luca-Leon Hausdoerfer. The original author's copyright is preserved. Licensed under GPLv3.

This fork fixes an upstream issue where a pending reboot after a kernel update was not detected on Ubuntu when the reboot-required sentinel file is never created, and adds SUSE support, which was previously non-functional. It also adds Agent Bakery support for automatic deployment.

## What it monitors

One service per host reporting whether a reboot is pending. The service is OK when no reboot is required. When a reboot is pending, the state is driven by how long it has been pending:

- OK below the WARN threshold
- WARN between the thresholds
- CRIT at or above the CRIT threshold

Defaults are 12 hours (WARN) and 24 hours (CRIT), both configurable. If the pending-since time cannot be determined, a configurable state is used instead (default WARN). When the age is known, the check produces a perfdata metric for the pending reboot age, with a perfometer.

## Detection methods

The agent plugin tries the following in order and stops at the first positive result:

1. `/var/run/reboot-required` and `/run/reboot-required` sentinel files (Debian, Ubuntu, Kali)
2. `needrestart` in kernel-only batch mode (Debian, Ubuntu, Kali)
3. `needs-restarting` from dnf-utils (RHEL, CentOS, Rocky Linux, AlmaLinux, Fedora)
4. `zypper needs-rebooting` (SUSE, openSUSE)
5. Running kernel compared against the newest installed kernel package, as a fallback (kernel, kernel-core, and kernel-default package naming)

Where the detection method provides no native timestamp, the modification time of the newest kernel image in `/boot` is used as a best-effort pending-since time.

## Requirements

- Linux host (Debian, Ubuntu, Kali, RHEL, CentOS, Rocky Linux, AlmaLinux, Fedora, SUSE, or openSUSE)
- Checkmk 2.3.0 or later
- The agent plugin deployed to the host (manually or via the bakery)

## Installation

**Important:** this package supersedes `system_reboot_required` v1.0.1 by Luca-Leon Hausdoerfer and uses the same package name and file paths. You must disable or remove the original package before installing this version.

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk, or place it in `local/` and run `mkp install`.
2. Deploy the agent plugin to the host, either manually into the agent's plugins directory, or by enabling the bakery rule "System Reboot Required (Linux)" and baking a new agent.
3. Run a service discovery on the host. One service should appear if the agent section is present.

## Configuration

- Check parameters ruleset: WARN/CRIT age thresholds and the service state used when the pending age is unknown.
- Bakery rule "System Reboot Required (Linux)": deploy toggle for automatic agent deployment.

## Version

**1.1.0**

## License

GPLv3, preserving the original author's copyright. See repository [LICENSE.md](../../LICENSE.md).
