#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# fortiswitch_health - Device health monitoring for Fortinet FortiSwitch
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# Monitors CPU utilization, memory usage, chassis temperature, PSU state
# and fan speed on Fortinet FortiSwitch devices via SNMP.
#
# Data sources:
#   - FORTINET-FORTISWITCH-MIB (.1.3.6.1.4.1.12356.106.4.1): CPU / memory
#   - ENTITY-SENSOR-MIB (.1.3.6.1.2.1.99.1.1.1) joined with
#     ENTITY-MIB (.1.3.6.1.2.1.47.1.1.1.1.7): temperature / PSU / fan
#
# Sensor presence varies by chassis class AND firmware (verified against
# 28 production walks across 12 FortiSwitch models). Discovery is therefore
# strictly evidence-based per unit:
#   - Sensors are classified by the entPhySensorUnitsDisplay string, never
#     by model name or entity friendly name (the 148F exposes its fan with
#     no "Fan" entity label at all).
#   - Fanless units (108F, 124G, 124E) discover no fan/PSU services.
#   - entPhySensorOperStatus is unreliable for fans: FS-1024D reports
#     status 2 (unavailable) on all fans while delivering live speed
#     values, so status 2 with live speed maps to OK.
#   - SFP/DOM optical sensors (units "C", volts, dBm, mAmps) share the
#     same sensor table. They carry no entity names on most models and no
#     switchport mapping exists in the FORTINET-FORTISWITCH-MIB, so optics
#     are grouped by their characteristic five-sensor index run
#     (temperature, voltage, TX power, RX power, bias current) and named
#     positionally ("SFP 1", "SFP 2"). Only optics with live DOM values
#     are discovered (known-good baseline), so copper modules and empty
#     cages produce no services.
#
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
    any_of,
    check_levels,
    contains,
    exists,
    get_value_store,
    render,
)
from cmk.plugins.lib.temperature import check_temperature

# Primary detection is sysObjectID (cheap, standard). The exists() fallback
# covers FortiLink-managed members observed in the field that expose ONLY
# the Fortinet enterprise tree over SNMP, with no MIB-2 system group at all
# (verified on a production FS-M426E FortiLink stack member).
_DETECT = any_of(
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.106."),
    exists(".1.3.6.1.4.1.12356.106.4.1.1.0"),
)

# ---------------------------------------------------------------------------
# Section 1: system info scalars (CPU / memory)
# .1.3.6.1.4.1.12356.106.4.1.1.0  version string
# .1.3.6.1.4.1.12356.106.4.1.2.0  CPU utilization (%)
# .1.3.6.1.4.1.12356.106.4.1.3.0  memory used (KB)
# .1.3.6.1.4.1.12356.106.4.1.4.0  memory total (KB)
# ---------------------------------------------------------------------------


def parse_fortiswitch_sysinfo(string_table: StringTable) -> Mapping[str, Any] | None:
    if not string_table or not string_table[0]:
        return None
    row = string_table[0]

    def _int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        "version": row[0] if len(row) > 0 else "",
        "cpu_util": _int(row[1]) if len(row) > 1 else None,
        "mem_used_kb": _int(row[2]) if len(row) > 2 else None,
        "mem_total_kb": _int(row[3]) if len(row) > 3 else None,
    }


snmp_section_fortiswitch_sysinfo = SimpleSNMPSection(
    name="fortiswitch_sysinfo",
    parse_function=parse_fortiswitch_sysinfo,
    detect=_DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.106.4.1",
        oids=["1.0", "2.0", "3.0", "4.0"],
    ),
)

# ---------------------------------------------------------------------------
# CPU utilization
# ---------------------------------------------------------------------------


def discover_fortiswitch_cpu(section: Mapping[str, Any]) -> Any:
    if section.get("cpu_util") is not None:
        yield Service()


def check_fortiswitch_cpu(params: Mapping[str, Any], section: Mapping[str, Any]) -> Any:
    cpu = section.get("cpu_util")
    if cpu is None:
        yield Result(state=State.UNKNOWN, summary="CPU utilization not reported")
        return
    yield from check_levels(
        float(cpu),
        levels_upper=params.get("levels_upper"),
        metric_name="util",
        label="Total CPU",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )


check_plugin_fortiswitch_cpu = CheckPlugin(
    name="fortiswitch_cpu",
    sections=["fortiswitch_sysinfo"],
    service_name="CPU utilization",
    discovery_function=discover_fortiswitch_cpu,
    check_function=check_fortiswitch_cpu,
    check_default_parameters={"levels_upper": ("fixed", (80.0, 90.0))},
    check_ruleset_name="fortiswitch_cpu",
)

# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


def discover_fortiswitch_memory(section: Mapping[str, Any]) -> Any:
    if section.get("mem_used_kb") is not None and section.get("mem_total_kb"):
        yield Service()


def check_fortiswitch_memory(params: Mapping[str, Any], section: Mapping[str, Any]) -> Any:
    used_kb = section.get("mem_used_kb")
    total_kb = section.get("mem_total_kb")
    if used_kb is None or not total_kb:
        yield Result(state=State.UNKNOWN, summary="Memory usage not reported")
        return

    used_pct = used_kb * 100.0 / total_kb
    yield from check_levels(
        used_pct,
        levels_upper=params.get("levels_upper"),
        metric_name="mem_used_percent",
        label="Usage",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )
    yield Result(
        state=State.OK,
        summary=f"{render.bytes(used_kb * 1024)} of {render.bytes(total_kb * 1024)}",
    )


check_plugin_fortiswitch_memory = CheckPlugin(
    name="fortiswitch_memory",
    sections=["fortiswitch_sysinfo"],
    service_name="Memory",
    discovery_function=discover_fortiswitch_memory,
    check_function=check_fortiswitch_memory,
    check_default_parameters={"levels_upper": ("fixed", (80.0, 90.0))},
    check_ruleset_name="fortiswitch_memory",
)

# ---------------------------------------------------------------------------
# Section 2: hardware sensors (ENTITY-MIB + ENTITY-SENSOR-MIB)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FSwitchSensor:
    kind: str  # "temp" | "psu" | "fan"
    name: str
    value: float | None
    oper_status: int | None  # 1=ok, 2=unavailable, 3=nonoperational


def _classify(units_display: str) -> str | None:
    """Classify a sensor row by its entPhySensorUnitsDisplay string.

    Chassis temperature reports 'Celsius' while SFP/DOM temperature
    reports plain 'C', which is what keeps optics out of scope here.
    """
    units = units_display.strip()
    lowered = units.lower()
    if lowered == "celsius":
        return "temp"
    if lowered.startswith("ok (1)"):
        return "psu"
    if lowered.startswith("percent"):
        return "fan"
    if lowered == "c" or lowered.startswith("volts") or lowered.startswith("dbm") or lowered.startswith("mamps"):
        return "dom"
    return None


def parse_fortiswitch_sensors(
    string_table: list[StringTable],
) -> Mapping[str, Mapping[str, FSwitchSensor]] | None:
    if len(string_table) < 2:
        return None
    entity_rows, sensor_rows = string_table[0], string_table[1]

    names: dict[str, str] = {}
    for row in entity_rows:
        if len(row) >= 2 and row[1].strip():
            names[row[0]] = row[1].strip()

    fallback_labels = {"temp": "Sensor", "psu": "PSU", "fan": "Fan"}
    section: dict[str, dict[str, Any]] = {"temp": {}, "psu": {}, "fan": {}, "sfp": {}}
    dom_rows: list[tuple[int, str, float | None, int | None]] = []

    for row in sensor_rows:
        if len(row) < 5:
            continue
        idx, _sensor_type, raw_value, raw_oper, units_display = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
        )
        kind = _classify(units_display)
        if kind is None:
            continue

        try:
            value: float | None = float(raw_value)
        except (TypeError, ValueError):
            value = None
        try:
            oper: int | None = int(raw_oper)
        except (TypeError, ValueError):
            oper = None

        if kind == "dom":
            try:
                dom_rows.append((int(idx), units_display.strip().lower(), value, oper))
            except (TypeError, ValueError):
                pass
            continue

        name = names.get(idx) or f"{fallback_labels[kind]} {idx}"
        # Guarantee uniqueness of service items even on odd firmware
        if name in section[kind]:
            name = f"{name} ({idx})"

        section[kind][name] = FSwitchSensor(
            kind=kind, name=name, value=value, oper_status=oper
        )

    # Group DOM rows into optics. Each optic is a run of five consecutive
    # sensor indices in the fixed firmware order: temperature (C), supply
    # voltage (volts), TX power (dBm), RX power (dBm), bias current (mAmps).
    # Values are milli-scaled by the firmware and divided by 1000 here.
    dom_rows.sort(key=lambda r: r[0])
    pattern = ("c", "volts", "dbm", "dbm", "mamps")
    fields = ("temp", "voltage", "tx_dbm", "rx_dbm", "bias")
    i, optic_no = 0, 0
    while i + len(pattern) <= len(dom_rows):
        window = dom_rows[i : i + len(pattern)]
        units_seq = tuple(r[1].split()[0] for r in window)
        consecutive = all(
            window[j + 1][0] == window[j][0] + 1 for j in range(len(window) - 1)
        )
        if units_seq == pattern and consecutive:
            optic_no += 1
            values = {
                field: (row[2] / 1000.0 if row[2] is not None else None)
                for field, row in zip(fields, window)
            }
            live = any(v not in (None, 0.0) for v in values.values())
            section["sfp"][f"SFP {optic_no}"] = {"values": values, "live": live}
            i += len(pattern)
        else:
            i += 1

    if not any(section.values()):
        return None
    return section


snmp_section_fortiswitch_sensors = SNMPSection(
    name="fortiswitch_sensors",
    parse_function=parse_fortiswitch_sensors,
    detect=_DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],  # entPhysicalIndex, entPhysicalName
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.99.1.1.1",
            oids=[
                OIDEnd(),  # entPhysicalIndex
                "1",  # entPhySensorType
                "4",  # entPhySensorValue
                "5",  # entPhySensorOperStatus
                "6",  # entPhySensorUnitsDisplay
            ],
        ),
    ],
)

# ---------------------------------------------------------------------------
# Temperature - one service per chassis sensor, standard temperature ruleset
# ---------------------------------------------------------------------------


def discover_fortiswitch_temp(section: Mapping[str, Mapping[str, FSwitchSensor]]) -> Any:
    for name, sensor in section.get("temp", {}).items():
        if sensor.value is not None:
            yield Service(item=name)


def check_fortiswitch_temp(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, FSwitchSensor]]
) -> Any:
    sensor = section.get("temp", {}).get(item)
    if sensor is None or sensor.value is None:
        return
    yield from check_temperature(
        sensor.value,
        params,
        unique_name=f"fortiswitch_temp_{item}",
        value_store=get_value_store(),
    )


check_plugin_fortiswitch_temp = CheckPlugin(
    name="fortiswitch_temp",
    sections=["fortiswitch_sensors"],
    service_name="Temperature %s",
    discovery_function=discover_fortiswitch_temp,
    check_function=check_fortiswitch_temp,
    check_default_parameters={"levels": (60.0, 70.0)},
    check_ruleset_name="temperature",
)

# ---------------------------------------------------------------------------
# PSU - state check with optional state-override ruleset
# ---------------------------------------------------------------------------


def discover_fortiswitch_psu(section: Mapping[str, Mapping[str, FSwitchSensor]]) -> Any:
    for name in section.get("psu", {}):
        yield Service(item=name)


def check_fortiswitch_psu(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, FSwitchSensor]]
) -> Any:
    sensor = section.get("psu", {}).get(item)
    if sensor is None:
        return

    # entPhySensorValue for PSU truthvalue: 1 = OK, 2 = Not OK.
    # entPhySensorOperStatus 3 (nonoperational) is treated as failed too;
    # verified on a live failed PSU which reported value=2 AND oper=3.
    is_ok = sensor.value == 1 and sensor.oper_status != 3

    if is_ok:
        yield Result(state=State.OK, summary="Status: OK")
        return

    mapped = State(params.get("state_not_ok", 2))
    detail = "Status: not OK"
    if sensor.oper_status == 3:
        detail += " (sensor nonoperational)"
    yield Result(state=mapped, summary=detail)


check_plugin_fortiswitch_psu = CheckPlugin(
    name="fortiswitch_psu",
    sections=["fortiswitch_sensors"],
    service_name="PSU %s",
    discovery_function=discover_fortiswitch_psu,
    check_function=check_fortiswitch_psu,
    check_default_parameters={"state_not_ok": 2},
    check_ruleset_name="fortiswitch_psu",
)

# ---------------------------------------------------------------------------
# Fan - state-led check with optional configurable speed levels
#
# Approved state mapping:
#   oper 1 (ok)             -> OK
#   oper 3 (nonoperational) -> CRIT (overridable)
#   oper 2 (unavailable)    -> OK with info text when a live speed value is
#                              present (FS-1024D behaviour); WARN
#                              (overridable) when no speed is reported.
# Speed is always shown and graphed; WARN/CRIT speed levels are opt-in.
# ---------------------------------------------------------------------------

_FAN_OPER_TEXT = {1: "ok", 2: "unavailable", 3: "nonoperational"}


def discover_fortiswitch_fan(section: Mapping[str, Mapping[str, FSwitchSensor]]) -> Any:
    # Only discover fans that report a live speed at discovery time. A
    # discovered fan is therefore a known-good baseline, which is what makes
    # the hard failure defaults (0% speed or vanished reading -> CRIT) safe:
    # they can only ever fire on a deviation from an observed working state.
    # Models whose fan sensors benignly report no speed never discover a
    # service and cannot false-alarm.
    for name, sensor in section.get("fan", {}).items():
        if sensor.value is not None and sensor.value > 0:
            yield Service(item=name)


def check_fortiswitch_fan(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, FSwitchSensor]]
) -> Any:
    sensor = section.get("fan", {}).get(item)
    if sensor is None:
        return

    oper = sensor.oper_status
    speed = sensor.value
    has_speed = speed is not None and speed > 0

    if oper == 3:
        yield Result(
            state=State(params.get("state_nonoperational", 2)),
            summary="Sensor status: nonoperational",
        )
    elif oper == 2:
        if has_speed:
            yield Result(
                state=State.OK,
                summary="Sensor status: unavailable, speed reporting active",
            )
        else:
            yield Result(
                state=State(params.get("state_unavailable_no_speed", 1)),
                summary="Sensor status: unavailable, no speed reported",
            )
    elif oper == 1:
        yield Result(state=State.OK, summary="Sensor status: ok")
    else:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Sensor status: unknown ({oper})",
        )

    if speed is not None:
        yield from check_levels(
            speed,
            levels_upper=params.get("levels_upper"),
            levels_lower=params.get("levels_lower"),
            metric_name="fortiswitch_fan_speed_percent",
            label="Speed",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
        )


check_plugin_fortiswitch_fan = CheckPlugin(
    name="fortiswitch_fan",
    sections=["fortiswitch_sensors"],
    service_name="Fan %s",
    discovery_function=discover_fortiswitch_fan,
    check_function=check_fortiswitch_fan,
    check_default_parameters={
        "state_nonoperational": 2,
        "state_unavailable_no_speed": 2,
        "levels_lower": ("fixed", (5.0, 2.0)),
    },
    check_ruleset_name="fortiswitch_fan",
)


# ---------------------------------------------------------------------------
# SFP optical diagnostics (DOM) - one service per populated optic
# ---------------------------------------------------------------------------


def discover_fortiswitch_sfp(section: Mapping[str, Mapping[str, Any]]) -> Any:
    # Only optics with live DOM values are discovered (known-good baseline);
    # empty cages and copper modules report all-zero values and are skipped.
    for name, optic in section.get("sfp", {}).items():
        if optic.get("live"):
            yield Service(item=name)


def check_fortiswitch_sfp(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> Any:
    optic = section.get("sfp", {}).get(item)
    if optic is None or not optic.get("live"):
        # A previously discovered optic no longer reports DOM values:
        # pulled, dead, or replaced by a non-DOM module.
        yield Result(
            state=State(params.get("state_vanished", 2)),
            summary="Optic no longer reporting (removed or failed)",
        )
        return

    values = optic["values"]

    if (rx := values.get("rx_dbm")) is not None:
        yield from check_levels(
            rx,
            levels_lower=params.get("levels_rx_lower"),
            metric_name="fortiswitch_sfp_rx_dbm",
            label="RX power",
            render_func=lambda v: f"{v:.2f} dBm",
        )
    if (tx := values.get("tx_dbm")) is not None:
        yield from check_levels(
            tx,
            levels_lower=params.get("levels_tx_lower"),
            metric_name="fortiswitch_sfp_tx_dbm",
            label="TX power",
            render_func=lambda v: f"{v:.2f} dBm",
        )
    if (temp := values.get("temp")) is not None:
        yield from check_levels(
            temp,
            levels_upper=params.get("levels_temp_upper"),
            metric_name="fortiswitch_sfp_temp",
            label="Temperature",
            render_func=lambda v: f"{v:.1f} °C",
        )
    if (volt := values.get("voltage")) is not None:
        yield from check_levels(
            volt,
            levels_upper=params.get("levels_voltage_upper"),
            levels_lower=params.get("levels_voltage_lower"),
            metric_name="fortiswitch_sfp_voltage",
            label="Voltage",
            render_func=lambda v: f"{v:.2f} V",
        )
    if (bias := values.get("bias")) is not None:
        yield from check_levels(
            bias,
            levels_upper=params.get("levels_bias_upper"),
            metric_name="fortiswitch_sfp_bias",
            label="Bias current",
            render_func=lambda v: f"{v:.1f} mA",
        )


check_plugin_fortiswitch_sfp = CheckPlugin(
    name="fortiswitch_sfp",
    sections=["fortiswitch_sensors"],
    service_name="SFP %s",
    discovery_function=discover_fortiswitch_sfp,
    check_function=check_fortiswitch_sfp,
    check_default_parameters={
        "state_vanished": 2,
        "levels_rx_lower": ("fixed", (-16.0, -20.0)),
        "levels_tx_lower": ("fixed", (-10.0, -13.0)),
        "levels_temp_upper": ("fixed", (70.0, 80.0)),
        "levels_voltage_lower": ("fixed", (3.13, 2.97)),
        "levels_voltage_upper": ("fixed", (3.47, 3.63)),
        "levels_bias_upper": ("fixed", (70.0, 90.0)),
    },
    check_ruleset_name="fortiswitch_sfp",
)
