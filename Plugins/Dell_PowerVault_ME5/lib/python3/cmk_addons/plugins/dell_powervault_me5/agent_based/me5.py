#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# dell_powervault_me5 - Health, capacity and hardware checks for PowerVault ME5
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# Consumes the JSON sections produced by agent_dell_powervault_me5 (one section
# per controller "show" command) and turns them into per-object services:
# system, controllers, controller firmware, host ports, disk groups, pools,
# volumes, disks, power supplies, fans, sensors (temperature and the state-only
# electrical / capacitor sensors), unwritable cache, snapshots and connected
# hosts.
#
# State for every health-bearing object is taken from the array's own numeric
# health/status enum, never from the display string, so locale and firmware
# wording changes do not affect alerting. All alert states are configurable
# through per-check rulesets; pool capacity uses the built-in Filesystem
# ruleset and temperature uses the built-in Temperature ruleset.
#
from __future__ import annotations

import json
import time
from typing import Any, Mapping, MutableMapping, Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    check_levels,
    get_value_store,
    render,
)
from cmk.plugins.lib.temperature import check_temperature
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

# ME5 virtual pool / disk-group page size is 4 MiB.
_PAGE_MIB = 4.0


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load(string_table: StringTable) -> Any:
    """Join a sep(0) section back into one string and JSON-decode it."""
    if not string_table:
        return None
    raw = "".join("".join(row) for row in string_table).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        # tolerate strings like "66 C", "10.79 V", "5.00"
        try:
            token = str(value).strip().split()[0]
            return float(token)
        except (ValueError, IndexError):
            return None


def _health_state(health_numeric: int | None, params: Mapping[str, Any]) -> State:
    """Standard ME5 health-numeric: 0 OK, 1 Degraded, 2 Fault, 3 Unknown, 4 N/A.

    OK and N/A are always OK; the three problem states are ruleset-configurable.
    """
    if health_numeric is None:
        return State.UNKNOWN
    return {
        0: State.OK,
        1: State(int(params.get("state_degraded", 1))),
        2: State(int(params.get("state_fault", 2))),
        3: State(int(params.get("state_unknown", 1))),
        4: State.OK,
    }.get(health_numeric, State.UNKNOWN)


# ===========================================================================
# System (overall health + management-controller redundancy)  ->  1 service
# ===========================================================================


def parse_me5_system(string_table: StringTable) -> Mapping[str, Any] | None:
    data = _load(string_table)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


agent_section_me5_system = AgentSection(
    name="dell_powervault_me5_system",
    parse_function=parse_me5_system,
)


def discover_me5_system(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()


def check_me5_system(params: Mapping[str, Any], section: Mapping[str, Any]) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No system data received")
        return

    health_txt = section.get("health", "unknown")
    yield Result(
        state=_health_state(_as_int(section.get("health-numeric")), params),
        summary=f"Health: {health_txt}",
        details=section.get("health-reason") or None,
    )

    redundancy = section.get("redundancy")
    if isinstance(redundancy, list) and redundancy:
        redundancy = redundancy[0]
    if isinstance(redundancy, dict):
        red_status = redundancy.get("redundancy-status", "unknown")
        red_state = State.OK
        if _as_int(redundancy.get("redundancy-status-numeric")) != 2:
            red_state = State(int(params.get("state_not_redundant", 1)))
        yield Result(state=red_state, summary=f"Redundancy: {red_status}")

        for ctrl in ("a", "b"):
            st = redundancy.get(f"controller-{ctrl}-status")
            if st is None:
                continue
            ctrl_state = State.OK
            if _as_int(redundancy.get(f"controller-{ctrl}-status-numeric")) != 0:
                ctrl_state = State(int(params.get("state_controller_down", 2)))
            yield Result(state=ctrl_state, summary=f"Controller {ctrl.upper()}: {st}")

    other_mc = section.get("other-MC-status")
    if other_mc is not None:
        mc_state = State.OK
        if _as_int(section.get("other-MC-status-numeric")) != 0:
            mc_state = State(int(params.get("state_partner_mc", 1)))
        yield Result(state=mc_state, summary=f"Partner MC: {other_mc}")


check_plugin_me5_system = CheckPlugin(
    name="dell_powervault_me5_system",
    service_name="ME5 System",
    discovery_function=discover_me5_system,
    check_function=check_me5_system,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_not_redundant": 1,
        "state_controller_down": 2,
        "state_partner_mc": 1,
    },
    check_ruleset_name="dell_me5_system",
)


# ===========================================================================
# Controllers (health service, one per controller) + host ports + firmware
# ===========================================================================


def parse_me5_controllers(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for ctrl in data:
        cid = ctrl.get("controller-id")
        if cid:
            result[str(cid)] = ctrl
    return result or None


agent_section_me5_controllers = AgentSection(
    name="dell_powervault_me5_controllers",
    parse_function=parse_me5_controllers,
)


def discover_me5_controllers(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for cid in section:
        yield Service(item=cid)


def check_me5_controllers(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    ctrl = section.get(item)
    if not ctrl:
        yield Result(state=State.UNKNOWN, summary="Controller not found")
        return

    yield Result(
        state=_health_state(_as_int(ctrl.get("health-numeric")), params),
        summary=f"Health: {ctrl.get('health', 'unknown')}",
        details=ctrl.get("health-reason") or None,
    )

    status = ctrl.get("status")
    if status is not None:
        st_state = State.OK
        if _as_int(ctrl.get("status-numeric")) != 0:
            st_state = State(int(params.get("state_not_operational", 2)))
        yield Result(state=st_state, summary=f"Status: {status}")

    if str(ctrl.get("failed-over", "No")).lower() != "no":
        yield Result(
            state=State(int(params.get("state_failed_over", 1))),
            summary=f"Failed over: {ctrl.get('failed-over')} ({ctrl.get('fail-over-reason', '')})",
        )

    write_policy = str(ctrl.get("write-policy", "")).lower()
    if write_policy and "through" in write_policy:
        yield Result(
            state=State(int(params.get("state_write_through", 1))),
            summary=f"Cache policy: {ctrl.get('write-policy')}",
        )

    if _as_int(ctrl.get("redundancy-status-numeric")) not in (2, None):
        yield Result(
            state=State(int(params.get("state_not_redundant", 1))),
            summary=f"Redundancy: {ctrl.get('redundancy-status')}",
        )

    info = (
        f"{ctrl.get('model', '')}, cache {ctrl.get('cache-memory-size', '?')} MB, "
        f"{ctrl.get('disks', '?')} disks, {ctrl.get('host-ports', '?')} host ports"
    )
    yield Result(state=State.OK, notice=info)


check_plugin_me5_controllers = CheckPlugin(
    name="dell_powervault_me5_controllers",
    service_name="ME5 Controller %s",
    sections=["dell_powervault_me5_controllers"],
    discovery_function=discover_me5_controllers,
    check_function=check_me5_controllers,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_not_operational": 2,
        "state_failed_over": 1,
        "state_write_through": 1,
        "state_not_redundant": 1,
    },
    check_ruleset_name="dell_me5_controllers",
)


# ---- Controller firmware (one info-only service per controller) -----------


def discover_me5_firmware(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for cid in section:
        yield Service(item=cid)


def check_me5_firmware(item: str, section: Mapping[str, Mapping[str, Any]]) -> CheckResult:
    ctrl = section.get(item)
    if not ctrl:
        yield Result(state=State.UNKNOWN, summary="Controller not found")
        return
    sc_fw = ctrl.get("sc-fw") or "Not Available"
    yield Result(state=State.OK, summary=f"Storage controller firmware: {sc_fw}")


check_plugin_me5_firmware = CheckPlugin(
    name="dell_powervault_me5_firmware",
    service_name="ME5 Firmware Controller %s",
    sections=["dell_powervault_me5_controllers"],
    discovery_function=discover_me5_firmware,
    check_function=check_me5_firmware,
)


# ---- Host ports (one service per port, discovered from controllers) -------


def _iter_ports(section: Mapping[str, Mapping[str, Any]]) -> Any:
    for ctrl in section.values():
        ports = ctrl.get("port")
        if isinstance(ports, list):
            for port in ports:
                pid = port.get("port")
                if pid:
                    yield str(pid), port


def discover_me5_host_ports(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for pid, _port in _iter_ports(section):
        yield Service(item=pid)


def check_me5_host_ports(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    for pid, port in _iter_ports(section):
        if pid != item:
            continue

        yield Result(
            state=_health_state(_as_int(port.get("health-numeric")), params),
            summary=f"Health: {port.get('health', 'unknown')}",
            details=port.get("health-reason") or None,
        )

        status = port.get("status")
        if status is not None:
            link_state = State.OK
            if _as_int(port.get("status-numeric")) != 0:
                link_state = State(int(params.get("state_not_up", 0)))
            yield Result(state=link_state, summary=f"{port.get('port-type', '')} {status}")

        speed = port.get("actual-speed")
        if speed and str(speed).lower() not in ("", "unknown"):
            yield Result(state=State.OK, notice=f"Speed: {speed}")
        return

    yield Result(state=State.UNKNOWN, summary="Port not found")


check_plugin_me5_host_ports = CheckPlugin(
    name="dell_powervault_me5_host_ports",
    service_name="ME5 Host Port %s",
    sections=["dell_powervault_me5_controllers"],
    discovery_function=discover_me5_host_ports,
    check_function=check_me5_host_ports,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_not_up": 2,
    },
    check_ruleset_name="dell_me5_host_ports",
)


# ===========================================================================
# Disk groups (one service per group)
# ===========================================================================


def parse_me5_disk_groups(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for dg in data:
        name = dg.get("name")
        if name:
            result[str(name)] = dg
    return result or None


agent_section_me5_disk_groups = AgentSection(
    name="dell_powervault_me5_disk_groups",
    parse_function=parse_me5_disk_groups,
)


def discover_me5_disk_groups(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


# ME5 disk-group status-numeric: 0 = FTOL (fault tolerant, online) is healthy.
# Anything else (FTDN down-disk, CRIT critical, OFFL offline, quarantined...)
# is a degraded/critical condition.
def check_me5_disk_groups(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    dg = section.get(item)
    if not dg:
        yield Result(state=State.UNKNOWN, summary="Disk group not found")
        return

    status = dg.get("status", "unknown")
    status_numeric = _as_int(dg.get("status-numeric"))
    if status_numeric == 0:
        state = State.OK
    else:
        state = State(int(params.get("state_not_fault_tolerant", 2)))
    yield Result(state=state, summary=f"Status: {status}")

    raidtype = dg.get("raidtype", "")
    diskcount = dg.get("diskcount", "?")
    sparecount = _as_int(dg.get("sparecount"))
    yield Result(state=State.OK, summary=f"{raidtype}, {diskcount} disks")

    if sparecount is not None:
        spare_state = State.OK
        if sparecount == 0:
            spare_state = State(int(params.get("state_no_spares", 0)))
        yield Result(state=spare_state, notice=f"Spares: {sparecount}")

    # Background jobs. A verify/scrub (VRSC) or disk scrub (DRSC) is normal
    # maintenance and stays informational; a reconstruct (RCON) implies a
    # failed member and is alertable.
    job = dg.get("current-job")
    if job:
        completion = dg.get("current-job-completion", "")
        job_state = State.OK
        if str(job).upper() in ("RCON",):
            job_state = State(int(params.get("state_reconstruct", 1)))
        yield Result(state=job_state, summary=f"Job: {job} {completion}".strip())
        pct = _as_float(str(dg.get("current-job-completion", "")).replace("%", ""))
        if pct is not None:
            yield Metric("dell_me5_dg_job_percent", pct, boundaries=(0.0, 100.0))

    pool_pct = _as_float(dg.get("pool-percentage"))
    if pool_pct is not None:
        yield Result(state=State.OK, notice=f"Pool share: {render.percent(pool_pct)}")


check_plugin_me5_disk_groups = CheckPlugin(
    name="dell_powervault_me5_disk_groups",
    service_name="ME5 Disk Group %s",
    discovery_function=discover_me5_disk_groups,
    check_function=check_me5_disk_groups,
    check_default_parameters={
        "state_not_fault_tolerant": 2,
        "state_reconstruct": 1,
        "state_no_spares": 0,
    },
    check_ruleset_name="dell_me5_disk_groups",
)


# ===========================================================================
# Pools (one service per pool; capacity via built-in Filesystem ruleset)
# ===========================================================================


def parse_me5_pools(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for pool in data:
        name = pool.get("name")
        if name:
            result[str(name)] = pool
    return result or None


agent_section_me5_pools = AgentSection(
    name="dell_powervault_me5_pools",
    parse_function=parse_me5_pools,
)


def discover_me5_pools(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_me5_pools(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    pool = section.get(item)
    if not pool:
        yield Result(state=State.UNKNOWN, summary="Pool not found")
        return

    allocated = _as_int(pool.get("allocated-pages"))
    available = _as_int(pool.get("available-pages"))
    if allocated is not None and available is not None:
        total_mib = (allocated + available) * _PAGE_MIB
        avail_mib = available * _PAGE_MIB
        yield from df_check_filesystem_single(
            get_value_store(),
            item,
            total_mib,
            avail_mib,
            0.0,
            None,
            None,
            params,
        )
    else:
        yield Result(state=State.UNKNOWN, summary="Pool capacity not reported")

    # Over-commit is expected on thin-provisioned pools; informational only.
    over = pool.get("over-committed")
    if over is not None:
        yield Result(state=State.OK, notice=f"Over-committed: {over}")

    health = pool.get("health")
    if health is not None:
        yield Result(state=State.OK, notice=f"Pool health: {health}")


check_plugin_me5_pools = CheckPlugin(
    name="dell_powervault_me5_pools",
    service_name="ME5 Pool %s",
    discovery_function=discover_me5_pools,
    check_function=check_me5_pools,
    check_default_parameters=dict(FILESYSTEM_DEFAULT_PARAMS),
    check_ruleset_name="filesystem",
)


# ===========================================================================
# Volumes (one service per volume)
# ===========================================================================


def parse_me5_volumes(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for vol in data:
        name = vol.get("volume-name")
        if name:
            result[str(name)] = vol
    return result or None


agent_section_me5_volumes = AgentSection(
    name="dell_powervault_me5_volumes",
    parse_function=parse_me5_volumes,
)


def _is_base_volume(vol: Mapping[str, Any]) -> bool:
    vtype = str(vol.get("volume-type", "")).lower()
    if vtype:
        return vtype == "base"
    return str(vol.get("snapshot", "")).lower() != "yes"


def discover_me5_volumes(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    # Snapshots are also volumes in the ME5 API; they are covered by the
    # snapshots check, so only base volumes are discovered here.
    for name, vol in section.items():
        if _is_base_volume(vol):
            yield Service(item=name)


def check_me5_volumes(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    vol = section.get(item)
    if not vol:
        yield Result(state=State.UNKNOWN, summary="Volume not found")
        return

    yield Result(
        state=_health_state(_as_int(vol.get("health-numeric")), params),
        summary=f"Health: {vol.get('health', 'unknown')}",
        details=vol.get("health-reason") or None,
    )

    owner = vol.get("owner")
    preferred = vol.get("preferred-owner")
    if owner is not None and preferred is not None and str(owner) != str(preferred):
        yield Result(
            state=State(int(params.get("state_non_preferred_owner", 1))),
            summary=f"Owner {owner} (preferred {preferred})",
        )
    else:
        yield Result(state=State.OK, notice=f"Owner: {owner}")

    raidtype = vol.get("raidtype")
    size = vol.get("size", "")
    allocated = vol.get("allocated-size", "")
    summary = f"size {size}, allocated {allocated}"
    if raidtype and str(raidtype).upper() != "N/A":
        summary = f"{raidtype}, {summary}"
    yield Result(state=State.OK, summary=summary)

    size_b = _as_int(vol.get("size-numeric"))
    alloc_b = _as_int(vol.get("allocated-size-numeric"))
    # size-numeric / allocated-size-numeric are in 512-byte blocks
    if alloc_b is not None:
        yield Metric("dell_me5_volume_allocated_bytes", alloc_b * 512.0)
    if size_b is not None and alloc_b is not None and size_b > 0:
        fill_pct = alloc_b / size_b * 100.0
        yield from check_levels(
            fill_pct,
            levels_upper=params.get("levels_fill"),
            metric_name="dell_me5_volume_fill_percent",
            label="Thin fill",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
            notice_only=True,
        )


check_plugin_me5_volumes = CheckPlugin(
    name="dell_powervault_me5_volumes",
    service_name="ME5 Volume %s",
    discovery_function=discover_me5_volumes,
    check_function=check_me5_volumes,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_non_preferred_owner": 1,
        # thin-provisioning fill alerting is off by default
    },
    check_ruleset_name="dell_me5_volumes",
)


# ===========================================================================
# Disks (one service per drive)
# ===========================================================================


def parse_me5_disks(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for disk in data:
        loc = disk.get("location") or disk.get("durable-id")
        if loc:
            result[str(loc)] = disk
    return result or None


agent_section_me5_disks = AgentSection(
    name="dell_powervault_me5_disks",
    parse_function=parse_me5_disks,
)


def discover_me5_disks(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for loc in section:
        yield Service(item=loc)


def check_me5_disks(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    disk = section.get(item)
    if not disk:
        yield Result(state=State.UNKNOWN, summary="Disk not found")
        return

    state = _health_state(_as_int(disk.get("health-numeric")), params)

    error = _as_int(disk.get("error"))
    down = _as_int(disk.get("drive-down-code"))
    if error not in (0, None) or down not in (0, None):
        state = State.worst(state, State(int(params.get("state_error", 2))))

    yield Result(
        state=state,
        summary=(
            f"Health: {disk.get('health', 'unknown')}, "
            f"{disk.get('vendor', '').strip()} {disk.get('model', '').strip()}, "
            f"{disk.get('state', '')}"
        ),
        details=disk.get("health-reason") or None,
    )

    smart = str(disk.get("smart", "")).lower()
    if smart and smart != "enabled":
        yield Result(
            state=State(int(params.get("state_smart_disabled", 0))),
            notice=f"SMART: {disk.get('smart')}",
        )

    temp = _as_float(disk.get("temperature"))
    if temp is not None:
        yield Metric("temp", temp)
        yield Result(state=State.OK, notice=f"Temperature: {temp:.0f} C")

    life = _as_int(disk.get("ssd-life-left-numeric"))
    if life is not None and life >= 0:
        yield from check_levels(
            float(life),
            levels_lower=params.get("levels_ssd_life"),
            metric_name="dell_me5_ssd_life_left_percent",
            label="SSD life left",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
            notice_only=True,
        )

    poh = _as_int(disk.get("power-on-hours"))
    if poh is not None:
        yield Result(state=State.OK, notice=f"Power-on hours: {poh}")


check_plugin_me5_disks = CheckPlugin(
    name="dell_powervault_me5_disks",
    service_name="ME5 Disk %s",
    discovery_function=discover_me5_disks,
    check_function=check_me5_disks,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_error": 2,
        "state_smart_disabled": 0,
        # ssd life lower levels off by default
    },
    check_ruleset_name="dell_me5_disks",
)


# ===========================================================================
# Power supplies (one service per PSU) and fans (one service per fan)
# ===========================================================================


def parse_me5_power_supplies(string_table: StringTable) -> Sequence[Mapping[str, Any]] | None:
    data = _load(string_table)
    if isinstance(data, list):
        return data
    return None


agent_section_me5_power_supplies = AgentSection(
    name="dell_powervault_me5_power_supplies",
    parse_function=parse_me5_power_supplies,
)


def discover_me5_power_supplies(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for psu in section:
        name = psu.get("name") or psu.get("durable-id")
        if name:
            yield Service(item=str(name))


def check_me5_power_supplies(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    for psu in section:
        name = psu.get("name") or psu.get("durable-id")
        if str(name) != item:
            continue

        yield Result(
            state=_health_state(_as_int(psu.get("health-numeric")), params),
            summary=f"Health: {psu.get('health', 'unknown')}",
            details=psu.get("health-reason") or None,
        )
        status = psu.get("status")
        if status is not None:
            st_state = State.OK
            if _as_int(psu.get("status-numeric")) != 0:
                st_state = State(int(params.get("state_not_up", 2)))
            yield Result(state=st_state, summary=f"Status: {status}")

        model = psu.get("model") or psu.get("part-number")
        if model:
            yield Result(state=State.OK, notice=f"Model: {model}")
        return

    yield Result(state=State.UNKNOWN, summary="Power supply not found")


check_plugin_me5_power_supplies = CheckPlugin(
    name="dell_powervault_me5_power_supplies",
    service_name="ME5 Power Supply %s",
    discovery_function=discover_me5_power_supplies,
    check_function=check_me5_power_supplies,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_not_up": 2,
    },
    check_ruleset_name="dell_me5_power_supplies",
)


def _iter_fans(section: Sequence[Mapping[str, Any]]) -> Any:
    for psu in section:
        fans = psu.get("fan")
        if isinstance(fans, list):
            for fan in fans:
                fid = fan.get("durable-id") or fan.get("name")
                if fid:
                    yield str(fid), fan


def discover_me5_fans(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for fid, fan in _iter_fans(section):
        # known-good baseline: only discover fans reporting a live speed
        if _as_int(fan.get("speed")) is not None:
            yield Service(item=fid)


def check_me5_fans(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    for fid, fan in _iter_fans(section):
        if fid != item:
            continue

        yield Result(
            state=_health_state(_as_int(fan.get("health-numeric")), params),
            summary=f"Health: {fan.get('health', 'unknown')} ({fan.get('name', '')})",
            details=fan.get("health-reason") or None,
        )
        status = fan.get("status")
        if status is not None:
            st_state = State.OK
            if _as_int(fan.get("status-numeric")) != 0:
                st_state = State(int(params.get("state_not_up", 2)))
            yield Result(state=st_state, summary=f"Status: {status}")

        speed = _as_float(fan.get("speed"))
        if speed is not None:
            yield from check_levels(
                speed,
                levels_upper=params.get("levels_upper"),
                levels_lower=params.get("levels_lower"),
                metric_name="fan_speed",
                label="Speed",
                render_func=lambda v: f"{v:.0f} RPM",
            )
        return

    yield Result(state=State.UNKNOWN, summary="Fan not found")


check_plugin_me5_fans = CheckPlugin(
    name="dell_powervault_me5_fans",
    service_name="ME5 Fan %s",
    sections=["dell_powervault_me5_power_supplies"],
    discovery_function=discover_me5_fans,
    check_function=check_me5_fans,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_not_up": 2,
        # RPM levels off by default (speed varies with thermal load)
    },
    check_ruleset_name="dell_me5_fans",
)


# ===========================================================================
# Sensors: temperature (levels) + all other types (state only)
# ===========================================================================


def parse_me5_sensors(string_table: StringTable) -> Sequence[Mapping[str, Any]] | None:
    data = _load(string_table)
    if isinstance(data, list):
        return data
    return None


agent_section_me5_sensors = AgentSection(
    name="dell_powervault_me5_sensors",
    parse_function=parse_me5_sensors,
)

# sensor-type-numeric: 0 Temperature, 1 Current, 2 Voltage, 3 Charge Capacity,
# 4 Capacitance, 5 Resistance, 6 Unknown (used by the enclosure status roll-up).
_TEMP_TYPE = 0

# Friendlier service labels for sensor types whose API name is unhelpful.
_SENSOR_TYPE_LABELS = {6: "Enclosure Status"}


def _sensor_type_name(sensor: Mapping[str, Any]) -> str:
    type_numeric = _as_int(sensor.get("sensor-type-numeric"))
    if type_numeric in _SENSOR_TYPE_LABELS:
        return _SENSOR_TYPE_LABELS[type_numeric]
    return sensor.get("sensor-type") or (
        f"Type {type_numeric}" if type_numeric is not None else "Sensor"
    )


def _sensor_id(sensor: Mapping[str, Any]) -> str | None:
    return sensor.get("durable-id") or sensor.get("sensor-name")


def discover_me5_temperature(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for sensor in section:
        if _as_int(sensor.get("sensor-type-numeric")) == _TEMP_TYPE:
            sid = _sensor_id(sensor)
            if sid and _as_float(sensor.get("value")) is not None:
                yield Service(item=sid)


def check_me5_temperature(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    for sensor in section:
        if _sensor_id(sensor) != item:
            continue
        reading = _as_float(sensor.get("value"))
        if reading is None:
            yield Result(state=State.UNKNOWN, summary="No reading")
            return
        yield from check_temperature(
            reading,
            params,
            unique_name=f"dell_me5_temp_{item}",
            value_store=get_value_store(),
            dev_unit="c",
        )
        name = sensor.get("sensor-name")
        if name and name != item:
            yield Result(state=State.OK, notice=f"Sensor: {name}")
        return
    yield Result(state=State.UNKNOWN, summary="Sensor not found")


check_plugin_me5_temperature = CheckPlugin(
    name="dell_powervault_me5_temperature",
    service_name="ME5 Temperature %s",
    sections=["dell_powervault_me5_sensors"],
    discovery_function=discover_me5_temperature,
    check_function=check_me5_temperature,
    check_default_parameters={"levels": (60.0, 70.0)},
    check_ruleset_name="temperature",
)


def discover_me5_sensor(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    # One service per non-temperature sensor type (Voltage, Current, ...),
    # each aggregating every sensor of that type.
    seen: dict[str, bool] = {}
    for sensor in section:
        type_numeric = _as_int(sensor.get("sensor-type-numeric"))
        if type_numeric is None or type_numeric == _TEMP_TYPE:
            continue
        seen[_sensor_type_name(sensor)] = True
    for type_name in seen:
        yield Service(item=type_name)


def _sensor_label(sensor: Mapping[str, Any]) -> str:
    return sensor.get("sensor-name") or sensor.get("durable-id") or "sensor"


def check_me5_sensor(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    members = [
        s
        for s in section
        if _as_int(s.get("sensor-type-numeric")) != _TEMP_TYPE
        and _sensor_type_name(s) == item
    ]
    if not members:
        yield Result(state=State.UNKNOWN, summary="No sensors of this type")
        return

    not_ok = [s for s in members if _as_int(s.get("status-numeric")) != 1]
    detail = "\n".join(
        f"{_sensor_label(s)}: {s.get('value')} ({s.get('status', 'unknown')})" for s in members
    )

    if not_ok:
        names = ", ".join(
            f"{_sensor_label(s)} ({s.get('value')}, {s.get('status', 'unknown')})" for s in not_ok
        )
        yield Result(
            state=State(int(params.get("state_not_ok", 1))),
            summary=f"{len(not_ok)} of {len(members)} not OK: {names}",
            details=detail,
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"All {len(members)} sensors OK",
            details=detail,
        )


check_plugin_me5_sensor = CheckPlugin(
    name="dell_powervault_me5_sensor",
    service_name="ME5 %s Sensors",
    sections=["dell_powervault_me5_sensors"],
    discovery_function=discover_me5_sensor,
    check_function=check_me5_sensor,
    check_default_parameters={"state_not_ok": 1},
    check_ruleset_name="dell_me5_sensor",
)


# ===========================================================================
# Unwritable cache  ->  1 service
# ===========================================================================


def parse_me5_unwritable_cache(string_table: StringTable) -> Mapping[str, Any] | None:
    data = _load(string_table)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


agent_section_me5_unwritable_cache = AgentSection(
    name="dell_powervault_me5_unwritable_cache",
    parse_function=parse_me5_unwritable_cache,
)


def discover_me5_unwritable_cache(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()


def check_me5_unwritable_cache(params: Mapping[str, Any], section: Mapping[str, Any]) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data")
        return
    pct_a = _as_float(section.get("unwritable-a-percentage")) or 0.0
    pct_b = _as_float(section.get("unwritable-b-percentage")) or 0.0
    worst = max(pct_a, pct_b)
    yield from check_levels(
        worst,
        levels_upper=params.get("levels_upper"),
        metric_name="dell_me5_unwritable_cache_percent",
        label="Unwritable cache",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )
    yield Result(state=State.OK, notice=f"Controller A: {pct_a:.0f}%, Controller B: {pct_b:.0f}%")
    yield Metric("dell_me5_unwritable_cache_a_percent", pct_a, boundaries=(0.0, 100.0))
    yield Metric("dell_me5_unwritable_cache_b_percent", pct_b, boundaries=(0.0, 100.0))


check_plugin_me5_unwritable_cache = CheckPlugin(
    name="dell_powervault_me5_unwritable_cache",
    service_name="ME5 Unwritable Cache",
    discovery_function=discover_me5_unwritable_cache,
    check_function=check_me5_unwritable_cache,
    check_default_parameters={"levels_upper": ("fixed", (1.0, 1.0))},
    check_ruleset_name="dell_me5_unwritable_cache",
)


# ===========================================================================
# Snapshots (one service per source/parent volume).
# On the ME5 a snapshot is itself a volume, so snapshots are derived from the
# volumes section and grouped by their parent volume. The parent is resolved
# from the parent serial to the base volume name, which works on any ME5
# regardless of naming convention.
# ===========================================================================


def _is_snapshot_volume(vol: Mapping[str, Any]) -> bool:
    if str(vol.get("volume-type", "")).lower() == "snapshot":
        return True
    return str(vol.get("snapshot", "")).lower() == "yes"


def _snapshot_groups(
    section: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    serial_to_name: dict[str, str] = {}
    for name, vol in section.items():
        if _is_base_volume(vol):
            serial = vol.get("serial-number")
            if serial:
                serial_to_name[str(serial)] = name

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for vol in section.values():
        if not _is_snapshot_volume(vol):
            continue
        parent = str(vol.get("volume-parent") or "")
        label = serial_to_name.get(parent) or parent or "unknown"
        grouped.setdefault(label, []).append(vol)
    return grouped


def discover_me5_snapshots(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for label in _snapshot_groups(section):
        yield Service(item=label)


def check_me5_snapshots(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    snaps = _snapshot_groups(section).get(item)
    if not snaps:
        yield Result(state=State.UNKNOWN, summary="No snapshots for this source volume")
        return

    worst = State.OK
    for snap in snaps:
        worst = State.worst(worst, _health_state(_as_int(snap.get("health-numeric")), params))
    yield Result(state=worst, summary=f"{len(snaps)} snapshot(s)")
    yield Metric("dell_me5_snapshot_count", float(len(snaps)))

    # Newest snapshot age: catches a stalled snapshot schedule ("no new
    # snapshot in ..."). Off by default because schedules vary; set levels_age
    # to e.g. 26h/50h for a daily schedule.
    epochs = [e for e in (_as_int(s.get("creation-date-time-numeric")) for s in snaps) if e]
    if epochs:
        newest = max(epochs)
        age = max(0.0, time.time() - float(newest))
        yield from check_levels(
            age,
            levels_upper=params.get("levels_age"),
            metric_name="dell_me5_snapshot_age",
            label="Newest snapshot age",
            render_func=render.timespan,
        )
        yield Result(
            state=State.OK,
            notice=f"Newest snapshot: {time.strftime('%Y-%m-%d %H:%M', time.localtime(newest))}",
        )

    total_bytes = 0
    have_size = False
    for snap in snaps:
        b = _as_int(snap.get("allocated-size-numeric"))
        if b is not None:
            total_bytes += b * 512
            have_size = True
    if have_size:
        yield Metric("dell_me5_snapshot_bytes", float(total_bytes))
        yield Result(state=State.OK, notice=f"Snapshot data: {render.bytes(total_bytes)}")


check_plugin_me5_snapshots = CheckPlugin(
    name="dell_powervault_me5_snapshots",
    service_name="ME5 Snapshots %s",
    sections=["dell_powervault_me5_volumes"],
    discovery_function=discover_me5_snapshots,
    check_function=check_me5_snapshots,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        # newest-snapshot-age alerting off by default (schedules vary)
    },
    check_ruleset_name="dell_me5_snapshots",
)


# ===========================================================================
# Connected hosts / initiators (one service per host)
# Discovery captures initiators currently connected (known-good baseline);
# an initiator that was discovered and later reports disconnected goes CRIT.
# Field names follow "show initiators"; parsing tolerates common alternates.
# ===========================================================================


def _initiator_name(ini: Mapping[str, Any]) -> str | None:
    return (
        ini.get("nickname")
        or ini.get("host-name")
        or ini.get("hostname")
        or ini.get("id")
        or ini.get("durable-id")
    )


def _initiator_connected(ini: Mapping[str, Any]) -> bool | None:
    for key in ("connected", "host-port-status", "discovered"):
        val = ini.get(key)
        if val is None:
            continue
        text = str(val).strip().lower()
        if text in ("yes", "up", "connected", "true", "1"):
            return True
        if text in ("no", "down", "disconnected", "false", "0"):
            return False
    num = _as_int(ini.get("connected-numeric"))
    if num is not None:
        return num != 0
    return None


def parse_me5_initiators(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for ini in data:
        name = _initiator_name(ini)
        if name:
            result[str(name)] = ini
    return result or None


agent_section_me5_initiators = AgentSection(
    name="dell_powervault_me5_initiators",
    parse_function=parse_me5_initiators,
)


def discover_me5_hosts(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for name, ini in section.items():
        # only baseline-discover initiators that are currently connected
        if _initiator_connected(ini) is not False:
            yield Service(item=name)


def check_me5_hosts(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    ini = section.get(item)
    if not ini:
        yield Result(
            state=State(int(params.get("state_missing", 2))),
            summary="Initiator no longer present in initiator table",
        )
        return

    connected = _initiator_connected(ini)
    if connected is False:
        yield Result(
            state=State(int(params.get("state_disconnected", 2))),
            summary="Initiator disconnected",
        )
    elif connected is True:
        yield Result(state=State.OK, summary="Connected")
    else:
        yield Result(state=State.OK, summary="Present")

    detail_bits = []
    for key in ("host-bus-type", "id", "host-group-name", "discovered"):
        val = ini.get(key)
        if val:
            detail_bits.append(f"{key}: {val}")
    if detail_bits:
        yield Result(state=State.OK, notice=", ".join(detail_bits))


check_plugin_me5_hosts = CheckPlugin(
    name="dell_powervault_me5_hosts",
    service_name="ME5 Host %s",
    sections=["dell_powervault_me5_initiators"],
    discovery_function=discover_me5_hosts,
    check_function=check_me5_hosts,
    check_default_parameters={
        "state_disconnected": 2,
        "state_missing": 2,
    },
    check_ruleset_name="dell_me5_hosts",
)
