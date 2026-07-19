# FortiSwitch Device Health

Checkmk extension for monitoring Fortinet FortiSwitch device health over SNMP.

## Why this exists

FortiSwitch coverage in Checkmk typically stops at interfaces, PoE, and uptime. This extension adds the missing hardware-health telemetry: CPU, memory, temperature, PSU, fan, and SFP optical diagnostics.

Sensors are discovered per unit from the live sensor tables rather than assumed from the model, so fanless and PSU-less units, and switches without fiber optics, are handled correctly. FortiLink members that expose only the Fortinet enterprise tree degrade gracefully to CPU and memory monitoring.

## What it monitors

- **CPU utilization**, configurable levels, default 80/90%
- **Memory usage**, configurable levels, default 80/90%
- **Chassis temperature**, per sensor, uses the built-in Temperature ruleset
- **PSU state**, per supply, OK / not-OK, optional state override
- **Fan**, per fan, state plus speed. Discovered only when reporting a live speed, so a fan later dropping to 0% or vanishing is CRIT by default. Configurable speed levels and state overrides
- **SFP optical diagnostics**, one service per populated optic: RX power, TX power, temperature, voltage, laser bias current. Empty cages and copper modules are not discovered

## Data sources

CPU and memory come from `FORTINET-FORTISWITCH-MIB`. Temperature, PSU, fan, and SFP/DOM come from `ENTITY-SENSOR-MIB` joined with `ENTITY-MIB`.

## Requirements

- Fortinet FortiSwitch with SNMP enabled
- Checkmk 2.3.0 or later
- SNMP read access to the switch from the Checkmk site

## Installation

1. Upload the `.mkp` file via **Setup > Extension Packages** in Checkmk, or place it in `local/` and run `mkp install`.
2. Run a service discovery on the FortiSwitch host.
3. Services will appear based on what the unit actually reports, no manual sensor selection needed.

## Configuration

Dedicated rulesets are available for CPU, memory, fan speed, and SFP levels, so thresholds can be tuned per host or model.

## Verified against

FortiSwitch 108F, 124E, 124G, 148F, 224E, 248E, 424E, M426E, 448E, 524D, 548D, and 1024D.

## Version history

- **1.0.0**: initial release, CPU, memory, temperature, PSU, and fan checks with dedicated rulesets and per-unit sensor discovery
- **1.0.1**: hardened fan failure handling, fan discovery gated on a live speed reading so failures cannot false-alarm on models that report no speed
- **1.1.0**: added SFP optical diagnostics (DOM), one service per populated optic with configurable levels on all five values

## Author

Sher Zaman

## License

See repository [LICENSE.md](../../LICENSE.md).
