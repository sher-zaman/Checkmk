#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# dell_powervault_me5 - Health, capacity, performance and hardware checks
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# Consumes the JSON sections produced by agent_dell_powervault_me5 and turns
# them into per-object services: system health, controllers, controller
# firmware, host ports (health and I/O), disk groups, pools, volumes (health,
# capacity and performance), disks (health, wear and performance), power
# supplies, fans, temperature sensors, power-supply electrical sensors,
# supercapacitor packs, unwritable cache, snapshots, connected hosts, system
# performance, health alerts, enclosures and snapshot schedules.
#
# State for every health-bearing object is taken from the array's own numeric
# health/status value, never from the display string, so locale and firmware
# wording changes do not affect alerting. Temperature state follows the array's
# own per-sensor verdict, because the ME5 knows the correct limits for each
# sensor; numeric levels remain available through the built-in Temperature
# ruleset for anyone who wants them.
#
from __future__ import annotations

import json
import re
import time
from typing import Any, Iterable, Mapping, Sequence

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
    get_rate,
    get_value_store,
    render,
)
from cmk.plugins.lib.temperature import check_temperature
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

# ME5 virtual pool / disk-group page size is 4 MiB.
_PAGE_MIB = 4.0
# Volume and snapshot sizes are reported in 512-byte blocks.
_BLOCK_BYTES = 512
# Guard against the firmware reporting a 64-bit underflow instead of a
# negative value (seen in snapshot unique-data counters).
_UINT64_GUARD = 2**63


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
        # tolerate strings like "66 C", "10.79 V", "25043.76"
        try:
            return float(str(value).strip().split()[0])
        except (ValueError, IndexError):
            return None


def _sane_counter(value: Any) -> int | None:
    """Return a counter value, discarding obvious 64-bit underflows."""
    number = _as_int(value)
    if number is None or number < 0 or number >= _UINT64_GUARD:
        return None
    return number


def _rate(key: str, value: float, now: float | None = None) -> float | None:
    """Per-second rate of a monotonic counter, or None on the first check."""
    try:
        return get_rate(
            get_value_store(),
            key,
            now if now is not None else time.time(),
            float(value),
            raise_overflow=False,
        )
    except Exception:
        # First check for this counter, or a counter reset.
        return None


def _health_state(health_numeric: int | None, params: Mapping[str, Any]) -> State:
    """ME5 health-numeric: 0 OK, 1 Degraded, 2 Fault, 3 Unknown, 4 N/A.

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


def _enclosure_index(durable_id: str) -> int | None:
    """Enclosure index from a durable-id such as psu_0.1 or sensor_temp_iom_0.A.1."""
    match = re.search(r"(?:psu|iom|fan|encl|enclosure|disk)_(\d+)", durable_id)
    if match:
        return _as_int(match.group(1))
    return None


def _with_enclosure(name: str, durable_id: str, existing: Iterable[str]) -> str:
    """Build a stable, unique service item from a firmware name.

    Objects in the base enclosure keep the plain name so that attaching an
    expansion enclosure later does not rename existing services. Objects in
    further enclosures get the enclosure appended, and any residual collision
    falls back to the durable-id.
    """
    enclosure = _enclosure_index(durable_id)
    item = name if not enclosure else f"{name} (enclosure {enclosure})"
    if item in set(existing) and durable_id:
        item = f"{item} [{durable_id}]"
    return item


# ===========================================================================
# System health  ->  1 service
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

    health_numeric = _as_int(section.get("health-numeric"))
    mc_numeric = _as_int(section.get("other-MC-status-numeric"))
    mc_bad = mc_numeric is not None and mc_numeric != 0

    redundancy = section.get("redundancy")
    if isinstance(redundancy, list) and redundancy:
        redundancy = redundancy[0]
    redundancy = redundancy if isinstance(redundancy, dict) else {}

    down_controllers = [
        ctrl.upper()
        for ctrl in ("a", "b")
        if redundancy.get(f"controller-{ctrl}-status") is not None
        and _as_int(redundancy.get(f"controller-{ctrl}-status-numeric")) != 0
    ]
    not_redundant = (
        redundancy.get("redundancy-status") is not None
        and _as_int(redundancy.get("redundancy-status-numeric")) != 2
    )

    # Name the reason on the health line, so an Unknown or Degraded verdict is
    # self-explanatory instead of having to be pieced together.
    causes: list[str] = []
    if mc_bad:
        causes.append("partner management controller not operational")
    if down_controllers:
        causes.append(
            f"controller {' and '.join(down_controllers)} not operational"
        )
    if not_redundant:
        causes.append(f"redundancy {redundancy.get('redundancy-status')}")

    summary = f"Health: {section.get('health', 'unknown')}"
    if health_numeric != 0 and causes:
        summary += f" ({', '.join(causes)})"

    yield Result(
        state=_health_state(health_numeric, params),
        summary=summary,
        details=section.get("health-reason") or None,
    )

    if redundancy:
        red_state = State(int(params.get("state_not_redundant", 1))) if not_redundant else State.OK
        yield Result(
            state=red_state,
            summary=f"Redundancy: {redundancy.get('redundancy-status', 'unknown')}",
        )

        for ctrl in ("a", "b"):
            status = redundancy.get(f"controller-{ctrl}-status")
            if status is None:
                continue
            is_down = ctrl.upper() in down_controllers
            ctrl_state = (
                State(int(params.get("state_controller_down", 2))) if is_down else State.OK
            )
            yield Result(state=ctrl_state, summary=f"Controller {ctrl.upper()}: {status}")

    other_mc = section.get("other-MC-status")
    if other_mc is not None:
        # When the overall health already reflects this and names it as the
        # cause, do not raise a second time for the same root cause.
        if mc_bad and health_numeric == 0:
            mc_state = State(int(params.get("state_partner_mc", 1)))
        else:
            mc_state = State.OK
        yield Result(state=mc_state, summary=f"Partner MC: {other_mc}")


check_plugin_me5_system = CheckPlugin(
    name="dell_powervault_me5_system",
    service_name="ME5 System Health",
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
# Controllers and controller firmware
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

    if "through" in str(ctrl.get("write-policy", "")).lower():
        yield Result(
            state=State(int(params.get("state_write_through", 1))),
            summary=f"Cache policy: {ctrl.get('write-policy')}",
        )

    if _as_int(ctrl.get("redundancy-status-numeric")) not in (2, None):
        yield Result(
            state=State(int(params.get("state_not_redundant", 1))),
            summary=f"Redundancy: {ctrl.get('redundancy-status')}",
        )

    yield Result(
        state=State.OK,
        notice=(
            f"{ctrl.get('model', '')}, cache {ctrl.get('cache-memory-size', '?')} MB, "
            f"{ctrl.get('disks', '?')} disks, {ctrl.get('host-ports', '?')} host ports"
        ),
    )


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


def discover_me5_firmware(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for cid in section:
        yield Service(item=cid)


def check_me5_firmware(item: str, section: Mapping[str, Mapping[str, Any]]) -> CheckResult:
    ctrl = section.get(item)
    if not ctrl:
        yield Result(state=State.UNKNOWN, summary="Controller not found")
        return
    yield Result(
        state=State.OK,
        summary=f"Storage controller firmware: {ctrl.get('sc-fw') or 'Not Available'}",
    )
    for label, key in (
        ("Management controller", "mc-fw"),
        ("Expander", "ex-fw"),
        ("CPLD", "cpld-rev"),
    ):
        value = ctrl.get(key)
        if value:
            yield Result(state=State.OK, notice=f"{label}: {value}")


check_plugin_me5_firmware = CheckPlugin(
    name="dell_powervault_me5_firmware",
    service_name="ME5 Controller %s Firmware",
    sections=["dell_powervault_me5_controllers"],
    discovery_function=discover_me5_firmware,
    check_function=check_me5_firmware,
)


# ===========================================================================
# Host ports: health, link and I/O in one service per port
# ===========================================================================


def parse_me5_host_ports(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for port in data:
        pid = port.get("port")
        if pid:
            result[str(pid)] = port
    return result or None


agent_section_me5_host_ports = AgentSection(
    name="dell_powervault_me5_host_ports",
    parse_function=parse_me5_host_ports,
)


def _us_to_seconds(value: Any) -> float | None:
    micros = _as_float(value)
    return micros / 1_000_000.0 if micros is not None else None


def discover_me5_host_ports(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for pid in section:
        yield Service(item=pid)


def check_me5_host_ports(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    port = section.get(item)
    if not port:
        yield Result(state=State.UNKNOWN, summary="Port not found")
        return

    yield Result(
        state=_health_state(_as_int(port.get("health-numeric")), params),
        summary=f"Health: {port.get('health', 'unknown')}",
        details=port.get("health-reason") or None,
    )

    status = port.get("status")
    if status is not None:
        link_state = State.OK
        if _as_int(port.get("status-numeric")) != 0:
            link_state = State(int(params.get("state_not_up", 2)))
        yield Result(state=link_state, summary=f"{port.get('port-type', '')} {status}")

    speed = port.get("actual-speed")
    if speed and str(speed).lower() not in ("", "unknown"):
        yield Result(state=State.OK, notice=f"Speed: {speed}")

    stats = port.get("statistics") or {}
    if not stats:
        return

    throughput = _as_float(stats.get("bytes-per-second-numeric"))
    if throughput is not None:
        yield from check_levels(
            throughput,
            levels_upper=params.get("levels_throughput"),
            metric_name="dell_me5_hostport_throughput",
            label="Throughput",
            render_func=render.iobandwidth,
        )

    iops = _as_float(stats.get("iops"))
    if iops is not None:
        yield from check_levels(
            iops,
            levels_upper=params.get("levels_iops"),
            metric_name="dell_me5_hostport_iops",
            label="IOPS",
            render_func=lambda v: f"{v:.0f}",
        )

    latency = _us_to_seconds(stats.get("avg-rsp-time"))
    if latency is not None:
        yield from check_levels(
            latency,
            levels_upper=params.get("levels_latency"),
            metric_name="dell_me5_hostport_latency",
            label="Avg response time",
            render_func=render.timespan,
        )

    queue = _as_float(stats.get("queue-depth"))
    if queue is not None:
        yield from check_levels(
            queue,
            levels_upper=params.get("levels_queue"),
            metric_name="dell_me5_hostport_queue_depth",
            label="Queue depth",
            render_func=lambda v: f"{v:.0f}",
            notice_only=True,
        )

    read_latency = _us_to_seconds(stats.get("avg-read-rsp-time"))
    write_latency = _us_to_seconds(stats.get("avg-write-rsp-time"))
    if read_latency is not None:
        yield Metric("dell_me5_hostport_read_latency", read_latency)
    if write_latency is not None:
        yield Metric("dell_me5_hostport_write_latency", write_latency)

    data_read = stats.get("data-read")
    data_written = stats.get("data-written")
    if data_read or data_written:
        yield Result(
            state=State.OK,
            notice=f"Since counter reset: {data_read or '?'} read, {data_written or '?'} written",
        )


check_plugin_me5_host_ports = CheckPlugin(
    name="dell_powervault_me5_host_ports",
    service_name="ME5 Host Port %s",
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
# Disk groups
# ===========================================================================


def parse_me5_disk_groups(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for group in data:
        name = group.get("name")
        if name:
            result[str(name)] = group
    return result or None


agent_section_me5_disk_groups = AgentSection(
    name="dell_powervault_me5_disk_groups",
    parse_function=parse_me5_disk_groups,
)


def discover_me5_disk_groups(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_me5_disk_groups(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    group = section.get(item)
    if not group:
        yield Result(state=State.UNKNOWN, summary="Disk group not found")
        return

    # status-numeric 0 == FTOL (fault tolerant and online)
    state = State.OK
    if _as_int(group.get("status-numeric")) != 0:
        state = State(int(params.get("state_not_fault_tolerant", 2)))
    yield Result(state=state, summary=f"Status: {group.get('status', 'unknown')}")

    yield Result(
        state=State.OK,
        summary=f"{group.get('raidtype', '')}, {group.get('diskcount', '?')} disks",
    )

    spares = _as_int(group.get("sparecount"))
    if spares is not None:
        spare_state = State.OK
        if spares == 0:
            spare_state = State(int(params.get("state_no_spares", 0)))
        yield Result(state=spare_state, notice=f"Spares: {spares}")

    job = group.get("current-job")
    if job:
        completion = str(group.get("current-job-completion", "") or "")
        job_state = State.OK
        if str(job).upper() == "RCON":
            job_state = State(int(params.get("state_reconstruct", 1)))
        yield Result(state=job_state, summary=f"Job: {job} {completion}".strip())
        pct = _as_float(completion.replace("%", ""))
        if pct is not None:
            yield Metric("dell_me5_dg_job_percent", pct, boundaries=(0.0, 100.0))

    pool_pct = _as_float(group.get("pool-percentage"))
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
# Pools (capacity through the built-in Filesystem ruleset)
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
    if allocated is None or available is None:
        yield Result(state=State.UNKNOWN, summary="Pool capacity not reported")
    else:
        yield from df_check_filesystem_single(
            get_value_store(),
            item,
            (allocated + available) * _PAGE_MIB,
            available * _PAGE_MIB,
            0.0,
            None,
            None,
            params,
        )

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
# Volumes: health, capacity and performance (base volumes only)
# ===========================================================================


def _is_base_volume(vol: Mapping[str, Any]) -> bool:
    vtype = str(vol.get("volume-type", "")).lower()
    if vtype:
        return vtype == "base"
    return str(vol.get("snapshot", "")).lower() != "yes"


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


def discover_me5_volumes(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for name, vol in section.items():
        # Snapshots are volumes too; they are covered by the snapshots check.
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

    yield Result(
        state=State.OK,
        summary=f"size {vol.get('size', '?')}, allocated {vol.get('allocated-size', '?')}",
    )

    size_blocks = _as_int(vol.get("size-numeric"))
    alloc_blocks = _as_int(vol.get("allocated-size-numeric"))
    if alloc_blocks is not None:
        yield Metric("dell_me5_volume_allocated_bytes", alloc_blocks * float(_BLOCK_BYTES))
    if size_blocks and alloc_blocks is not None:
        yield from check_levels(
            alloc_blocks / size_blocks * 100.0,
            levels_upper=params.get("levels_fill"),
            metric_name="dell_me5_volume_fill_percent",
            label="Thin fill",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
            notice_only=True,
        )

    # ---- performance ----
    stats = vol.get("statistics") or {}
    if not stats:
        return

    now = time.time()
    key = item.replace(" ", "_")

    throughput = _as_float(stats.get("bytes-per-second-numeric"))
    if throughput is not None:
        yield from check_levels(
            throughput,
            levels_upper=params.get("levels_throughput"),
            metric_name="dell_me5_volume_throughput",
            label="Throughput",
            render_func=render.iobandwidth,
        )

    iops = _as_float(stats.get("iops"))
    if iops is not None:
        yield from check_levels(
            iops,
            levels_upper=params.get("levels_iops"),
            metric_name="dell_me5_volume_iops",
            label="IOPS",
            render_func=lambda v: f"{v:.0f}",
        )

    for label, counter, metric in (
        ("Read IOPS", "number-of-reads", "dell_me5_volume_read_iops"),
        ("Write IOPS", "number-of-writes", "dell_me5_volume_write_iops"),
    ):
        total = _sane_counter(stats.get(counter))
        if total is None:
            continue
        rate = _rate(f"me5_vol_{key}_{counter}", total, now)
        if rate is None:
            continue
        yield Metric(metric, max(0.0, rate))
        yield Result(state=State.OK, notice=f"{label}: {max(0.0, rate):.0f}")

    for label, counter, metric in (
        ("Read throughput", "data-read-numeric", "dell_me5_volume_read_throughput"),
        ("Write throughput", "data-written-numeric", "dell_me5_volume_write_throughput"),
    ):
        total = _sane_counter(stats.get(counter))
        if total is None:
            continue
        rate = _rate(f"me5_vol_{key}_{counter}", total, now)
        if rate is None:
            continue
        yield Metric(metric, max(0.0, rate))
        yield Result(state=State.OK, notice=f"{label}: {render.iobandwidth(max(0.0, rate))}")

    for prefix, label, metric, param in (
        ("read", "Read cache hit ratio", "dell_me5_volume_read_cache_hit_ratio", "levels_read_hit"),
        (
            "write",
            "Write cache hit ratio",
            "dell_me5_volume_write_cache_hit_ratio",
            "levels_write_hit",
        ),
    ):
        hits = _sane_counter(stats.get(f"{prefix}-cache-hits"))
        misses = _sane_counter(stats.get(f"{prefix}-cache-misses"))
        if hits is None or misses is None:
            continue
        hit_rate = _rate(f"me5_vol_{key}_{prefix}_hits", hits, now)
        miss_rate = _rate(f"me5_vol_{key}_{prefix}_misses", misses, now)
        if hit_rate is None or miss_rate is None:
            continue
        total = hit_rate + miss_rate
        if total <= 0:
            continue
        yield from check_levels(
            hit_rate / total * 100.0,
            levels_lower=params.get(param),
            metric_name=metric,
            label=label,
            render_func=render.percent,
            boundaries=(0.0, 100.0),
            notice_only=True,
        )

    lifetime_read = stats.get("data-read")
    lifetime_written = stats.get("data-written")
    if lifetime_read or lifetime_written:
        yield Result(
            state=State.OK,
            notice=(
                f"Since counter reset: {lifetime_read or '?'} read, "
                f"{lifetime_written or '?'} written"
            ),
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
    },
    check_ruleset_name="dell_me5_volumes",
)


# ===========================================================================
# Disks: health, wear, performance and predictive error counters
# ===========================================================================

# Counter families reported per SAS port (suffixes -1 and -2).
_DISK_ERROR_COUNTERS: tuple[tuple[str, str, str], ...] = (
    ("smart-count", "SMART events", "dell_me5_disk_smart_errors"),
    ("number-of-media-errors", "Media errors", "dell_me5_disk_media_errors"),
    ("number-of-bad-blocks", "Bad blocks", "dell_me5_disk_bad_blocks"),
    ("number-of-block-reassigns", "Block reassignments", "dell_me5_disk_block_reassigns"),
    ("spinup-retry-count", "Spin-up retries", "dell_me5_disk_spinup_retries"),
    ("io-timeout-count", "I/O timeouts", "dell_me5_disk_io_timeouts"),
    ("no-response-count", "No-response events", "dell_me5_disk_no_response"),
)
_DISK_NONMEDIA = ("number-of-nonmedia-errors", "Non-media errors", "dell_me5_disk_nonmedia_errors")


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


def _both_ports(stats: Mapping[str, Any], base: str) -> int | None:
    first = _sane_counter(stats.get(f"{base}-1"))
    second = _sane_counter(stats.get(f"{base}-2"))
    if first is None and second is None:
        return None
    return (first or 0) + (second or 0)


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

    disk_state = str(disk.get("state", "") or "").strip()
    usage = f", in {disk_state.lower()}" if disk_state else ""
    yield Result(
        state=state,
        summary=(
            f"Health: {disk.get('health', 'unknown')}, "
            f"{str(disk.get('vendor', '')).strip()} {str(disk.get('model', '')).strip()}"
            f"{usage}"
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

    # ---- performance and error counters ----
    stats = disk.get("statistics") or {}
    if not stats:
        return

    now = time.time()
    key = item.replace(" ", "_").replace(".", "_")

    throughput = _as_float(stats.get("bytes-per-second-numeric"))
    if throughput is not None:
        yield from check_levels(
            throughput,
            levels_upper=params.get("levels_throughput"),
            metric_name="dell_me5_disk_throughput",
            label="Throughput",
            render_func=render.iobandwidth,
            notice_only=True,
        )

    iops = _as_float(stats.get("iops"))
    if iops is not None:
        yield from check_levels(
            iops,
            levels_upper=params.get("levels_iops"),
            metric_name="dell_me5_disk_iops",
            label="IOPS",
            render_func=lambda v: f"{v:.0f}",
            notice_only=True,
        )

    queue = _as_float(stats.get("queue-depth"))
    if queue is not None:
        yield Metric("dell_me5_disk_queue_depth", queue)
        yield Result(state=State.OK, notice=f"Queue depth: {queue:.0f}")

    families = list(_DISK_ERROR_COUNTERS)
    if params.get("monitor_nonmedia_errors"):
        families.append(_DISK_NONMEDIA)

    error_state = State(int(params.get("state_errors_increasing", 1)))
    for base, label, metric in families:
        total = _both_ports(stats, base)
        if total is None:
            continue
        yield Metric(metric, float(total))
        rate = _rate(f"me5_disk_{key}_{base}", total, now)
        if rate is not None and rate > 0:
            yield Result(
                state=error_state,
                summary=f"{label} increasing (total {total})",
            )
        else:
            yield Result(state=State.OK, notice=f"{label}: {total}")

    if not params.get("monitor_nonmedia_errors"):
        nonmedia = _both_ports(stats, _DISK_NONMEDIA[0])
        if nonmedia is not None:
            yield Metric(_DISK_NONMEDIA[2], float(nonmedia))
            yield Result(state=State.OK, notice=f"{_DISK_NONMEDIA[1]}: {nonmedia}")

    lifetime_read = stats.get("lifetime-data-read")
    lifetime_written = stats.get("lifetime-data-written")
    if lifetime_read or lifetime_written:
        yield Result(
            state=State.OK,
            notice=f"Lifetime: {lifetime_read or '?'} read, {lifetime_written or '?'} written",
        )


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
        "state_errors_increasing": 1,
        "monitor_nonmedia_errors": False,
    },
    check_ruleset_name="dell_me5_disks",
)


# ===========================================================================
# Power supplies and fans
# ===========================================================================


def parse_me5_power_supplies(string_table: StringTable) -> Sequence[Mapping[str, Any]] | None:
    data = _load(string_table)
    return data if isinstance(data, list) else None


agent_section_me5_power_supplies = AgentSection(
    name="dell_powervault_me5_power_supplies",
    parse_function=parse_me5_power_supplies,
)


def _psu_items(section: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Item per PSU, e.g. "PSU 0, Left" -> "0 Left"."""
    items: dict[str, Mapping[str, Any]] = {}
    for psu in section:
        durable_id = str(psu.get("durable-id") or "")
        name = str(psu.get("name") or durable_id).strip()
        pretty = re.sub(r"^PSU\s*", "", name).replace(",", "").strip()
        pretty = re.sub(r"\s+", " ", pretty) or durable_id
        items[_with_enclosure(pretty, durable_id, items)] = psu
    return items


def discover_me5_power_supplies(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for item in _psu_items(section):
        yield Service(item=item)


def check_me5_power_supplies(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    psu = _psu_items(section).get(item)
    if not psu:
        yield Result(state=State.UNKNOWN, summary="Power supply not found")
        return

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
    if psu.get("serial-number"):
        yield Result(state=State.OK, notice=f"Serial: {psu.get('serial-number')}")


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


def _fan_items(section: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Item per fan, e.g. name "Fan 0" -> "0"."""
    items: dict[str, Mapping[str, Any]] = {}
    for psu in section:
        for fan in psu.get("fan", []) or []:
            durable_id = str(fan.get("durable-id") or "")
            name = str(fan.get("name") or durable_id).strip()
            pretty = re.sub(r"^Fan\s*", "", name).strip() or durable_id
            items[_with_enclosure(pretty, durable_id, items)] = fan
    return items


def discover_me5_fans(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for item, fan in _fan_items(section).items():
        # Known-good baseline: only discover fans reporting a live speed.
        if _as_int(fan.get("speed")) is not None:
            yield Service(item=item)


def check_me5_fans(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    fan = _fan_items(section).get(item)
    if not fan:
        yield Result(state=State.UNKNOWN, summary="Fan not found")
        return

    yield Result(
        state=_health_state(_as_int(fan.get("health-numeric")), params),
        summary=f"Health: {fan.get('health', 'unknown')}",
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

    location = fan.get("location")
    if location:
        yield Result(state=State.OK, notice=f"Location: {location}")


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
    },
    check_ruleset_name="dell_me5_fans",
)


# ===========================================================================
# Sensors: temperature (per sensor), power-supply electrical sensors
# (grouped per type) and the supercapacitor packs (grouped per controller)
# ===========================================================================

# sensor-type-numeric: 0 Temperature, 1 Current, 2 Voltage, 3 Charge Capacity,
# 4 Capacitance, 5 Resistance, 6 Unknown (enclosure status roll-up, which the
# enclosure check reports properly and which is therefore skipped here).
_TEMP_TYPE = 0
_ROLLUP_TYPE = 6


def parse_me5_sensors(string_table: StringTable) -> Sequence[Mapping[str, Any]] | None:
    data = _load(string_table)
    return data if isinstance(data, list) else None


agent_section_me5_sensors = AgentSection(
    name="dell_powervault_me5_sensors",
    parse_function=parse_me5_sensors,
)


def _sensor_items(section: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Map service item -> sensor, using the firmware sensor name."""
    items: dict[str, Mapping[str, Any]] = {}
    for sensor in section:
        durable_id = str(sensor.get("durable-id") or "")
        name = str(sensor.get("sensor-name") or "").strip() or durable_id
        if not name:
            continue
        items[_with_enclosure(name, durable_id, items)] = sensor
    return items


def _sensor_ok(sensor: Mapping[str, Any]) -> bool:
    # status-numeric 1 == OK for sensor objects
    return _as_int(sensor.get("status-numeric")) == 1


def _supercap_controller(sensor: Mapping[str, Any]) -> str | None:
    """Controller id for a supercapacitor sensor, or None if not one."""
    durable_id = str(sensor.get("durable-id") or "")
    if "_cap_" not in durable_id and "volt_ctrl" not in durable_id:
        return None
    match = re.search(r"_ctrl_([AB])", durable_id)
    return match.group(1) if match else None


# ---- temperature (one service per sensor) ---------------------------------


def discover_me5_temperature(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for item, sensor in _sensor_items(section).items():
        if _as_int(sensor.get("sensor-type-numeric")) != _TEMP_TYPE:
            continue
        if _as_float(sensor.get("value")) is not None:
            yield Service(item=item)


def check_me5_temperature(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    sensor = _sensor_items(section).get(item)
    if sensor is None:
        yield Result(state=State.UNKNOWN, summary="Sensor not found")
        return

    reading = _as_float(sensor.get("value"))
    if reading is None:
        yield Result(state=State.UNKNOWN, summary="No reading")
        return

    # The array applies the correct limits per sensor, so its own verdict
    # drives the state. Numeric levels stay available via the ruleset.
    dev_status = State.OK if _sensor_ok(sensor) else State.CRIT
    yield from check_temperature(
        reading,
        params,
        unique_name=f"dell_me5_temp_{item}",
        value_store=get_value_store(),
        dev_unit="c",
        dev_status=dev_status,
        dev_status_name=str(sensor.get("status", "")),
    )

    durable_id = sensor.get("durable-id")
    if durable_id:
        yield Result(state=State.OK, notice=f"Sensor ID: {durable_id}")


check_plugin_me5_temperature = CheckPlugin(
    name="dell_powervault_me5_temperature",
    service_name="ME5 Temperature %s",
    sections=["dell_powervault_me5_sensors"],
    discovery_function=discover_me5_temperature,
    check_function=check_me5_temperature,
    check_default_parameters={},
    check_ruleset_name="temperature",
)


# ---- power-supply electrical sensors (one service per type) ---------------


def _psu_sensor_groups(section: Sequence[Mapping[str, Any]]) -> dict[str, list[tuple[str, Mapping[str, Any]]]]:
    groups: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for item, sensor in _sensor_items(section).items():
        type_numeric = _as_int(sensor.get("sensor-type-numeric"))
        if type_numeric in (_TEMP_TYPE, _ROLLUP_TYPE, None):
            continue
        if _supercap_controller(sensor):
            continue
        type_name = sensor.get("sensor-type") or f"Type {type_numeric}"
        groups.setdefault(str(type_name), []).append((item, sensor))
    return groups


def discover_me5_sensor(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for type_name in _psu_sensor_groups(section):
        yield Service(item=type_name)


def _sensor_group_result(
    members: Sequence[tuple[str, Mapping[str, Any]]], params: Mapping[str, Any]
) -> CheckResult:
    detail = "\n".join(
        f"{name}: {sensor.get('value')} ({sensor.get('status', 'unknown')})"
        for name, sensor in members
    )
    faulted = [(name, sensor) for name, sensor in members if not _sensor_ok(sensor)]

    if faulted:
        names = ", ".join(
            f"{name} ({sensor.get('value')}, {sensor.get('status', 'unknown')})"
            for name, sensor in faulted
        )
        yield Result(
            state=State(int(params.get("state_not_ok", 1))),
            summary=f"{len(faulted)} of {len(members)} not OK: {names}",
            details=detail,
        )
    elif len(members) == 1:
        name, sensor = members[0]
        yield Result(
            state=State.OK,
            summary=f"{name}: {sensor.get('value')}",
            details=detail,
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"All {len(members)} sensors OK",
            details=detail,
        )


def check_me5_sensor(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    members = _psu_sensor_groups(section).get(item)
    if not members:
        yield Result(state=State.UNKNOWN, summary="No sensors of this type")
        return
    yield from _sensor_group_result(members, params)


check_plugin_me5_sensor = CheckPlugin(
    name="dell_powervault_me5_sensor",
    service_name="ME5 %s Sensors",
    sections=["dell_powervault_me5_sensors"],
    discovery_function=discover_me5_sensor,
    check_function=check_me5_sensor,
    check_default_parameters={"state_not_ok": 1},
    check_ruleset_name="dell_me5_sensor",
)


# ---- supercapacitor packs (one service per controller) --------------------


def _supercap_groups(
    section: Sequence[Mapping[str, Any]],
) -> dict[str, list[tuple[str, Mapping[str, Any]]]]:
    groups: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for item, sensor in _sensor_items(section).items():
        controller = _supercap_controller(sensor)
        if controller:
            groups.setdefault(f"Controller {controller}", []).append((item, sensor))
    return groups


def discover_me5_supercapacitor(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    for item in _supercap_groups(section):
        yield Service(item=item)


def check_me5_supercapacitor(
    item: str, params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    members = _supercap_groups(section).get(item)
    if not members:
        yield Result(state=State.UNKNOWN, summary="Supercapacitor sensors not found")
        return

    yield from _sensor_group_result(members, params)

    # Headline readings for the pack, plus graphs for the wear indicators.
    for name, sensor in members:
        lowered = name.lower()
        value = _as_float(sensor.get("value"))
        if value is None:
            continue
        if "charge" in lowered:
            yield from check_levels(
                value,
                levels_lower=params.get("levels_charge"),
                metric_name="dell_me5_supercap_charge_percent",
                label="Charge",
                render_func=render.percent,
                boundaries=(0.0, 100.0),
                notice_only=True,
            )
        elif "capacitance" in lowered:
            yield Metric("dell_me5_supercap_capacitance", value)
            yield Result(state=State.OK, notice=f"Capacitance: {value:.1f} F")
        elif "resistance" in lowered:
            yield Metric("dell_me5_supercap_resistance", value)
            yield Result(state=State.OK, notice=f"Resistance: {value:.1f} Ohm")
        elif "pack voltage" in lowered:
            yield Metric("dell_me5_supercap_pack_voltage", value)
            yield Result(state=State.OK, notice=f"Pack voltage: {value:.2f} V")


check_plugin_me5_supercapacitor = CheckPlugin(
    name="dell_powervault_me5_supercapacitor",
    service_name="ME5 Supercapacitor %s",
    sections=["dell_powervault_me5_sensors"],
    discovery_function=discover_me5_supercapacitor,
    check_function=check_me5_supercapacitor,
    check_default_parameters={"state_not_ok": 1},
    check_ruleset_name="dell_me5_supercapacitor",
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


def check_me5_unwritable_cache(
    params: Mapping[str, Any], section: Mapping[str, Any]
) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data")
        return

    pct_a = _as_float(section.get("unwritable-a-percentage")) or 0.0
    pct_b = _as_float(section.get("unwritable-b-percentage")) or 0.0
    yield from check_levels(
        max(pct_a, pct_b),
        levels_upper=params.get("levels_upper"),
        metric_name="dell_me5_unwritable_cache_percent",
        label="Unwritable cache",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )
    yield Result(
        state=State.OK,
        notice=f"Controller A: {pct_a:.0f}%, Controller B: {pct_b:.0f}%",
    )
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
# Snapshot protection: snapshots and their schedule, one service per source
# volume. The agent joins "show snapshots" with "show schedules", so a single
# service answers whether a volume is protected and whether protection is
# still running.
# ===========================================================================


def parse_me5_snapshots(string_table: StringTable) -> Mapping[str, Any] | None:
    data = _load(string_table)
    if isinstance(data, dict) and ("volumes" in data or "orphan_schedules" in data):
        return data
    return None


agent_section_me5_snapshots = AgentSection(
    name="dell_powervault_me5_snapshots",
    parse_function=parse_me5_snapshots,
)


def _schedule_results(
    schedule: Mapping[str, Any], params: Mapping[str, Any], prefix: str = ""
) -> CheckResult:
    """Status, last run, next run and error for one schedule."""
    label = f"{prefix}status" if prefix else "Status"
    status = str(schedule.get("status", "") or "unknown")
    status_state = State.OK
    if status.lower() not in ("ready", "running", "active"):
        status_state = State(int(params.get("state_not_ready", 1)))
    yield Result(state=status_state, summary=f"{label.capitalize()}: {status}")

    error = str(schedule.get("error-message", "") or "").strip()
    if error:
        yield Result(
            state=State(int(params.get("state_error", 1))),
            summary=f"Schedule error: {error}",
        )

    last = _as_int(schedule.get("last-initiated-numeric"))
    if last:
        yield Result(
            state=State.OK,
            summary=f"Last run: {time.strftime('%Y-%m-%d %H:%M', time.localtime(last))}",
        )
        yield Metric("dell_me5_schedule_last_run_age", max(0.0, time.time() - float(last)))

    # An overdue next run means the scheduler is no longer firing. Default OK,
    # so arrays with abandoned or unbound schedules stay quiet; raise it to
    # alert on a stalled active schedule.
    next_run = _as_int(schedule.get("next-time-numeric"))
    if next_run:
        overdue = time.time() - float(next_run)
        if overdue > 0:
            yield Result(
                state=State(int(params.get("state_overdue", 0))),
                summary=(
                    f"Schedule overdue by {render.timespan(overdue)} "
                    f"(next run was {time.strftime('%Y-%m-%d %H:%M', time.localtime(next_run))})"
                ),
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Next run: {time.strftime('%Y-%m-%d %H:%M', time.localtime(next_run))}",
            )
        yield Metric("dell_me5_schedule_overdue", max(0.0, overdue))

    spec = schedule.get("schedule-specification")
    if spec:
        yield Result(state=State.OK, notice=f"Schedule: {schedule.get('name', '')} ({spec})")


def discover_me5_snapshots(section: Mapping[str, Any]) -> DiscoveryResult:
    # Discover every volume that has snapshots or a schedule, so a volume with
    # a schedule but no snapshots surfaces instead of silently disappearing.
    for volume in section.get("volumes", {}):
        yield Service(item=volume)


def check_me5_snapshots(
    item: str, params: Mapping[str, Any], section: Mapping[str, Any]
) -> CheckResult:
    entry = section.get("volumes", {}).get(item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary="Source volume not found")
        return

    snaps = entry.get("snapshots") or []
    schedules = entry.get("schedules") or []

    worst = State.OK
    for snap in snaps:
        status_numeric = _as_int(snap.get("status-numeric"))
        if status_numeric is not None and status_numeric != 0:
            worst = State.worst(worst, State(int(params.get("state_not_available", 1))))
    if not snaps and schedules:
        worst = State.worst(worst, State(int(params.get("state_no_snapshots", 1))))
        yield Result(state=worst, summary="No snapshots, but a schedule exists")
    else:
        yield Result(state=worst, summary=f"{len(snaps)} snapshot(s)")
    yield Metric("dell_me5_snapshot_count", float(len(snaps)))

    epochs = [e for e in (_as_int(s.get("creation-date-time-numeric")) for s in snaps) if e]
    if epochs:
        newest = max(epochs)
        yield from check_levels(
            max(0.0, time.time() - float(newest)),
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
        blocks = _sane_counter(snap.get("snap-data-numeric"))
        if blocks is not None:
            total_bytes += blocks * _BLOCK_BYTES
            have_size = True
    if have_size:
        yield Metric("dell_me5_snapshot_bytes", float(total_bytes))
        yield Result(state=State.OK, notice=f"Snapshot data: {render.bytes(total_bytes)}")

    # ---- the schedule that protects this volume ----
    for schedule in schedules:
        yield from _schedule_results(schedule, params)

    for snap in snaps:
        yield Result(
            state=State.OK,
            notice=(
                f"{snap.get('name')}: {snap.get('status', 'unknown')}, "
                f"created {snap.get('creation-date-time', 'unknown')}, "
                f"data {snap.get('snap-data', '?')}"
            ),
        )


check_plugin_me5_snapshots = CheckPlugin(
    name="dell_powervault_me5_snapshots",
    service_name="ME5 Snapshots %s",
    discovery_function=discover_me5_snapshots,
    check_function=check_me5_snapshots,
    check_default_parameters={
        "state_not_available": 1,
        "state_no_snapshots": 1,
        "state_not_ready": 1,
        "state_error": 1,
        "state_overdue": 0,
    },
    check_ruleset_name="dell_me5_snapshots",
)


# ---- schedules that do not map to a volume --------------------------------


def discover_me5_schedules(section: Mapping[str, Any]) -> DiscoveryResult:
    for name in section.get("orphan_schedules", {}):
        yield Service(item=name)


def check_me5_schedules(
    item: str, params: Mapping[str, Any], section: Mapping[str, Any]
) -> CheckResult:
    schedule = section.get("orphan_schedules", {}).get(item)
    if schedule is None:
        yield Result(state=State.UNKNOWN, summary="Schedule not found")
        return
    yield from _schedule_results(schedule, params)
    task = schedule.get("task-to-run")
    if task:
        yield Result(state=State.OK, notice=f"Task: {task}")


check_plugin_me5_schedules = CheckPlugin(
    name="dell_powervault_me5_schedules",
    service_name="ME5 Schedule %s",
    sections=["dell_powervault_me5_snapshots"],
    discovery_function=discover_me5_schedules,
    check_function=check_me5_schedules,
    check_default_parameters={
        "state_not_ready": 1,
        "state_error": 1,
        "state_overdue": 0,
    },
    check_ruleset_name="dell_me5_schedules",
)


# ===========================================================================
# Connected hosts (initiators)
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
        value = ini.get(key)
        if value is None:
            continue
        text = str(value).strip().lower()
        if text in ("yes", "up", "connected", "true", "1"):
            return True
        if text in ("no", "down", "disconnected", "false", "0"):
            return False
    numeric = _as_int(ini.get("connected-numeric"))
    if numeric is not None:
        return numeric != 0
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

    details = [
        f"{key}: {ini[key]}"
        for key in ("host-bus-type", "id", "host-group-name", "discovered")
        if ini.get(key)
    ]
    if details:
        yield Result(state=State.OK, notice=", ".join(details))


check_plugin_me5_hosts = CheckPlugin(
    name="dell_powervault_me5_hosts",
    service_name="ME5 Connected Host %s",
    sections=["dell_powervault_me5_initiators"],
    discovery_function=discover_me5_hosts,
    check_function=check_me5_hosts,
    check_default_parameters={
        "state_disconnected": 2,
        "state_missing": 2,
    },
    check_ruleset_name="dell_me5_hosts",
)


# ===========================================================================
# System performance  ->  1 service
#
# The agent joins controller statistics (IOPS, throughput, cache counters)
# with host port statistics (response times), since the array only reports
# latency per port.
# ===========================================================================


def parse_me5_system_performance(string_table: StringTable) -> Mapping[str, Any] | None:
    data = _load(string_table)
    if isinstance(data, dict) and (data.get("controllers") or data.get("ports")):
        return data
    return None


agent_section_me5_system_performance = AgentSection(
    name="dell_powervault_me5_system_performance",
    parse_function=parse_me5_system_performance,
)


def discover_me5_system_performance(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()


def _weighted_latency(ports: Sequence[Mapping[str, Any]], key: str) -> float | None:
    """IOPS-weighted average response time across ports that carry traffic."""
    total_weight = 0.0
    weighted = 0.0
    unweighted: list[float] = []
    for port in ports:
        latency = _us_to_seconds(port.get(key))
        if latency is None:
            continue
        iops = _as_float(port.get("iops")) or 0.0
        if iops > 0:
            weighted += latency * iops
            total_weight += iops
        elif latency > 0:
            unweighted.append(latency)
    if total_weight > 0:
        return weighted / total_weight
    if unweighted:
        return sum(unweighted) / len(unweighted)
    return None


def check_me5_system_performance(
    params: Mapping[str, Any], section: Mapping[str, Any]
) -> CheckResult:
    controllers = section.get("controllers") or []
    ports = section.get("ports") or []
    if not controllers and not ports:
        yield Result(state=State.UNKNOWN, summary="No performance data received")
        return

    now = time.time()

    total_iops = sum(_as_float(c.get("iops")) or 0.0 for c in controllers)
    total_throughput = sum(
        _as_float(c.get("bytes-per-second-numeric")) or 0.0 for c in controllers
    )

    yield from check_levels(
        total_iops,
        levels_upper=params.get("levels_iops"),
        metric_name="dell_me5_system_iops",
        label="IOPS",
        render_func=lambda v: f"{v:.0f}",
    )
    yield from check_levels(
        total_throughput,
        levels_upper=params.get("levels_throughput"),
        metric_name="dell_me5_system_throughput",
        label="Throughput",
        render_func=render.iobandwidth,
    )

    # Read/write split from the cumulative counters.
    for label, counter, metric in (
        ("Read IOPS", "number-of-reads", "dell_me5_system_read_iops"),
        ("Write IOPS", "number-of-writes", "dell_me5_system_write_iops"),
    ):
        totals = [c for c in (_sane_counter(x.get(counter)) for x in controllers) if c is not None]
        if not totals:
            continue
        rate = _rate(f"me5_sys_{counter}", float(sum(totals)), now)
        if rate is None:
            continue
        yield Metric(metric, max(0.0, rate))
        yield Result(state=State.OK, notice=f"{label}: {max(0.0, rate):.0f}")

    for label, counter, metric in (
        ("Read throughput", "data-read-numeric", "dell_me5_system_read_throughput"),
        ("Write throughput", "data-written-numeric", "dell_me5_system_write_throughput"),
    ):
        totals = [c for c in (_sane_counter(x.get(counter)) for x in controllers) if c is not None]
        if not totals:
            continue
        rate = _rate(f"me5_sys_{counter}", float(sum(totals)), now)
        if rate is None:
            continue
        yield Metric(metric, max(0.0, rate))
        yield Result(state=State.OK, notice=f"{label}: {render.iobandwidth(max(0.0, rate))}")

    # Latency, from the host ports.
    latency = _weighted_latency(ports, "avg-rsp-time")
    if latency is not None:
        yield from check_levels(
            latency,
            levels_upper=params.get("levels_latency"),
            metric_name="dell_me5_system_latency",
            label="Avg response time",
            render_func=render.timespan,
        )
    for label, key, metric in (
        ("Read response time", "avg-read-rsp-time", "dell_me5_system_read_latency"),
        ("Write response time", "avg-write-rsp-time", "dell_me5_system_write_latency"),
    ):
        value = _weighted_latency(ports, key)
        if value is None:
            continue
        yield Metric(metric, value)
        yield Result(state=State.OK, notice=f"{label}: {render.timespan(value)}")

    # Per-controller context.
    for ctrl in controllers:
        cid = str(ctrl.get("durable-id", "")).replace("controller_", "") or "?"
        cpu = _as_float(ctrl.get("cpu-load"))
        cache_used = _as_float(ctrl.get("write-cache-used"))
        if cpu is not None:
            yield Metric(f"dell_me5_controller_{cid.lower()}_cpu_load", cpu)
        bits = []
        if cpu is not None:
            bits.append(f"CPU {cpu:.0f}%")
        if cache_used is not None:
            bits.append(f"write cache used {cache_used:.0f}%")
        if bits:
            yield Result(state=State.OK, notice=f"Controller {cid}: {', '.join(bits)}")


check_plugin_me5_system_performance = CheckPlugin(
    name="dell_powervault_me5_system_performance",
    service_name="ME5 System Performance",
    discovery_function=discover_me5_system_performance,
    check_function=check_me5_system_performance,
    check_default_parameters={},
    check_ruleset_name="dell_me5_system_performance",
)


# ===========================================================================
# Health alerts  ->  1 service
# ===========================================================================

_ALERT_CRITICAL = "critical"
_ALERT_WARNING = "warning"


def parse_me5_alerts(string_table: StringTable) -> Sequence[Mapping[str, Any]] | None:
    data = _load(string_table)
    return data if isinstance(data, list) else None


agent_section_me5_alerts = AgentSection(
    name="dell_powervault_me5_alerts",
    parse_function=parse_me5_alerts,
)


def discover_me5_alerts(section: Sequence[Mapping[str, Any]]) -> DiscoveryResult:
    if section is not None:
        yield Service()


def _alert_severity(alert: Mapping[str, Any]) -> str:
    return str(alert.get("severity", "")).strip().lower()


def _alert_unresolved(alert: Mapping[str, Any]) -> bool:
    resolved = _as_int(alert.get("resolved-numeric"))
    if resolved is not None:
        return resolved == 0
    return str(alert.get("resolved", "")).strip().lower() != "yes"


def check_me5_alerts(
    params: Mapping[str, Any], section: Sequence[Mapping[str, Any]]
) -> CheckResult:
    if section is None:
        yield Result(state=State.UNKNOWN, summary="No alert data received")
        return

    unresolved = [a for a in section if _alert_unresolved(a)]
    critical = [a for a in unresolved if _alert_severity(a) == _ALERT_CRITICAL]
    warning = [a for a in unresolved if _alert_severity(a) == _ALERT_WARNING]

    health_alerts = critical + warning
    yield Metric("dell_me5_health_alerts", float(len(health_alerts)))

    if not health_alerts:
        yield Result(state=State.OK, summary="No health alerts")
    else:
        state = State.OK
        if critical:
            state = State.worst(state, State(int(params.get("state_critical", 2))))
        if warning:
            state = State.worst(state, State(int(params.get("state_warning", 1))))
        yield Result(
            state=state,
            summary=f"{len(critical)} critical, {len(warning)} warning",
        )
        for alert in health_alerts:
            yield Result(
                state=State.OK,
                notice=(
                    f"[{alert.get('severity')}] {alert.get('component', '')}: "
                    f"{alert.get('description', '')} | {alert.get('reason', '')} | "
                    f"Action: {alert.get('recommended-action', '')}"
                ),
            )


check_plugin_me5_alerts = CheckPlugin(
    name="dell_powervault_me5_alerts",
    service_name="ME5 Health Alerts",
    discovery_function=discover_me5_alerts,
    check_function=check_me5_alerts,
    check_default_parameters={
        "state_critical": 2,
        "state_warning": 1,
    },
    check_ruleset_name="dell_me5_alerts",
)


# ===========================================================================
# Enclosures (one service per enclosure)
# ===========================================================================


def parse_me5_enclosures(string_table: StringTable) -> Mapping[str, Mapping[str, Any]] | None:
    data = _load(string_table)
    if not isinstance(data, list):
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for enc in data:
        eid = enc.get("enclosure-id")
        if eid is None:
            eid = str(enc.get("durable-id", "")).replace("enclosure_", "")
        if eid != "" and eid is not None:
            result[str(eid)] = enc
    return result or None


agent_section_me5_enclosures = AgentSection(
    name="dell_powervault_me5_enclosures",
    parse_function=parse_me5_enclosures,
)


def discover_me5_enclosures(section: Mapping[str, Mapping[str, Any]]) -> DiscoveryResult:
    for eid in section:
        yield Service(item=eid)


def check_me5_enclosures(
    item: str, params: Mapping[str, Any], section: Mapping[str, Mapping[str, Any]]
) -> CheckResult:
    enc = section.get(item)
    if not enc:
        yield Result(state=State.UNKNOWN, summary="Enclosure not found")
        return

    yield Result(
        state=_health_state(_as_int(enc.get("health-numeric")), params),
        summary=f"Health: {enc.get('health', 'unknown')}",
        details=(
            "\n".join(
                filter(
                    None,
                    [enc.get("health-reason") or "", enc.get("health-recommendation") or ""],
                )
            )
            or None
        ),
    )

    # status-numeric 1 == OK for enclosure objects
    status = enc.get("status")
    if status is not None:
        status_state = State.OK
        if _as_int(enc.get("status-numeric")) != 1:
            status_state = State(int(params.get("state_not_ok", 2)))
        yield Result(state=status_state, summary=f"Status: {status}")

    power = _as_float(enc.get("enclosure-power"))
    if power is not None:
        yield from check_levels(
            power,
            levels_upper=params.get("levels_power"),
            metric_name="dell_me5_enclosure_power",
            label="Power",
            render_func=lambda v: f"{v:.0f} W",
        )

    model = enc.get("model")
    vendor = enc.get("vendor")
    if model or vendor:
        yield Result(
            state=State.OK,
            notice=f"Model: {model or '?'} ({vendor or '?'})",
        )
    if enc.get("midplane-type"):
        yield Result(state=State.OK, notice=f"Midplane: {enc.get('midplane-type')}")

    disks = _as_int(enc.get("number-of-disks"))
    slots = _as_int(enc.get("slots"))
    if disks is not None:
        yield Result(
            state=State.OK,
            notice=f"Disks: {disks}{f' of {slots} slots' if slots else ''}",
        )
    psus = _as_int(enc.get("number-of-power-supplies"))
    fans = _as_int(enc.get("number-of-coolings-elements"))
    if psus is not None or fans is not None:
        yield Result(
            state=State.OK,
            notice=f"Power supplies: {psus if psus is not None else '?'}, "
            f"Cooling elements: {fans if fans is not None else '?'}",
        )
    if enc.get("enclosure-wwn"):
        yield Result(state=State.OK, notice=f"WWN: {enc.get('enclosure-wwn')}")


check_plugin_me5_enclosures = CheckPlugin(
    name="dell_powervault_me5_enclosures",
    service_name="ME5 Enclosure %s",
    discovery_function=discover_me5_enclosures,
    check_function=check_me5_enclosures,
    check_default_parameters={
        "state_degraded": 1,
        "state_fault": 2,
        "state_unknown": 1,
        "state_not_ok": 2,
    },
    check_ruleset_name="dell_me5_enclosures",
)
