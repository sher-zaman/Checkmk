# FortiSwitch Device Health

Checkmk extension for monitoring Fortinet FortiSwitch hardware health through SNMP.

## Why this exists

FortiSwitch monitoring stops at interfaces, PoE and uptime, so nothing watches the hardware itself. Faults on these switches are silent by design: the unit keeps forwarding traffic while a component sits failed, so the first sign of trouble is usually an outage rather than a warning.

## What it monitors

- **CPU utilization**: instantaneous load in percent, default levels WARN at 80 and CRIT at 90.
- **Memory**: usage in percent with absolute values, default levels WARN at 80 and CRIT at 90.
- **Temperature n**: one service per chassis sensor, using the built-in **Temperature** ruleset.
- **PSU n**: one service per power supply, CRIT on anything other than OK.
- **Fan n**: one service per fan, sensor state plus speed as a percent of maximum, speed levels defaulting to WARN at 5 and CRIT at 2.
- **SFP n**: one service per populated optic, carrying receive and transmit power, transceiver temperature, supply voltage and laser bias current.

Fanless models produce no fan services, empty cages and copper transceivers produce no SFP services, and FortiLink members exposing only the Fortinet enterprise data fall back to CPU and memory. Fans are only discovered when they report a live speed, so the low speed levels can only fire on a fan that has actually stopped. Optic naming is positional, so re-run discovery after changing transceivers.

## Example services

Discovery on a 426E access switch with two fiber uplinks:

```
CPU utilization                   OK    Total CPU: 3.00%
Memory                            OK    Usage: 45.98%, 346 MiB of 752 MiB
Temperature Sensor1               OK    Temperature: 50.0 °C
Temperature Sensor2               OK    Temperature: 47.0 °C
PSU 1                             OK    Status: OK
PSU 2                             OK    Status: OK
Fan 1                             OK    Sensor status: ok, Speed: 40.00%
SFP 3                             OK    RX power: -0.94 dBm, TX power: -1.90 dBm, Temperature: 43.5 °C, Voltage: 3.29 V, Bias current: 5.7 mA
SFP 4                             OK    RX power: -2.90 dBm, TX power: -2.35 dBm, Temperature: 47.2 °C, Voltage: 3.34 V, Bias current: 8.7 mA
```

## Graphing

- **Fan**: speed as a percent of maximum, on its own graph, with the speed shown in the perfometer.
- **SFP**: transmit and receive power together on one graph so the link budget reads at a glance, with transceiver temperature, supply voltage and laser bias current each graphed separately and receive power in the perfometer.
- CPU utilization, memory usage and temperature use Checkmk's built-in metric names, so they appear on the standard graphs and perfometers.

## Data source

`FORTINET-FORTISWITCH-MIB` system information at `.1.3.6.1.4.1.12356.106.4.1` for CPU and memory, joined with the standard `ENTITY-SENSOR-MIB` sensor table at `.1.3.6.1.2.1.99.1.1.1` and the `ENTITY-MIB` physical table at `.1.3.6.1.2.1.47.1.1.1.1.7` for temperature, power supply, fan and optical sensors.

## Requirements

- Checkmk 2.3.0 or later, up to 2.5
- FortiSwitch OS 7.2 or later
- SNMP enabled on the switch, v2c or v3, with the standard entity and sensor tables readable in addition to the Fortinet enterprise tree

## Installation

1. Install the package via **Setup > Extension packages > Upload package**.

2. Run a service discovery on the host. Services appear based on what the device actually reports, so no manual sensor selection is required.

## Configuration

- **FortiSwitch CPU utilization**: upper levels on CPU load, defaulting to WARN at 80 and CRIT at 90. The value is an instantaneous sample, so brief spikes are normal.
- **FortiSwitch memory usage**: upper levels on memory usage in percent, defaulting to WARN at 80 and CRIT at 90.
- **FortiSwitch PSU state**: the state assigned when a supply reports not OK, defaulting to CRIT. Downgrade it on a unit with a deliberately disconnected second supply rather than leaving the service permanently acknowledged.
- **FortiSwitch fan**: state mapping and lower and upper speed levels, with lower levels defaulting to WARN at 5 and CRIT at 2.
- **FortiSwitch SFP optical diagnostics**: levels on receive power, transmit power, transceiver temperature, supply voltage and laser bias current, plus the state assigned when an optic stops reporting. Defaults suit common 1G and 10G optics; tune receive and transmit levels per optic type where the link budget calls for it.

Chassis temperature is configured through the built-in **Temperature** ruleset.

## Validated

FortiSwitch OS 7.2 and 7.6, on models 108F, 124E, 124G, 148F, 224E, 248E, 424E, 426E, 448E, 524D, 548D and 1024D, including desktop and rackmount units, stacked core switches, and FortiLink-managed members.

## Version history

- **1.2.0**: removed the duplicated word from PSU, fan and SFP service names; re-run service discovery after updating
- **1.1.0**: SFP optical diagnostics, one service per populated optic with levels on all five values
- **1.0.1**: hardened fan failure handling, fan discovery gated on a live speed reading
- **1.0.0**: initial release, CPU, memory, temperature, PSU and fan checks with per-unit sensor discovery and dedicated rulesets

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
