#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA CPU and memory utilization.
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   CPU;<percent>;percent
#   CPU_steal;<percent>;percent
#   Memory;<percent>;percent
#   Memory_used;<bytes>;bytes
#   Memory_total;<bytes>;bytes
#   Swap_page_rate;<pages per sec>;pages_per_sec

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    check_levels,
    render,
)

# Maps an agent key to the service item it belongs to and the field it fills.
_FIELDS = {
    "CPU": ("CPU", "util"),
    "CPU_steal": ("CPU", "steal"),
    "Memory": ("Memory", "util"),
    "Memory_used": ("Memory", "used"),
    "Memory_total": ("Memory", "total"),
    "Swap_page_rate": ("Memory", "page_rate"),
}

_UTIL_METRIC = {"CPU": "vcsa_cpu_util", "Memory": "vcsa_mem_util"}


def parse_vcsa_health_perf(string_table):
    section = {}
    for line in string_table:
        if len(line) < 2 or line[0] not in _FIELDS:
            continue
        item, field = _FIELDS[line[0]]
        try:
            section.setdefault(item, {})[field] = float(line[1])
        except ValueError:
            continue
    return section


agent_section_vcsa_health_perf = AgentSection(
    name="vcsa_health_perf",
    parse_function=parse_vcsa_health_perf,
)


def discover_vcsa_health_perf(section) -> DiscoveryResult:
    for item, values in section.items():
        if "util" in values:
            yield Service(item=item)


def check_vcsa_health_perf(item, params, section) -> CheckResult:
    values = section.get(item)
    if not values or "util" not in values:
        return

    yield from check_levels(
        values["util"],
        levels_upper=params.get("levels"),
        metric_name=_UTIL_METRIC.get(item),
        label="Utilization",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
    )

    # CPU steal shows how much runtime the host denied the appliance, which
    # distinguishes a busy appliance from a starved one.
    if "steal" in values:
        yield from check_levels(
            values["steal"],
            levels_upper=params.get("steal_levels"),
            metric_name="vcsa_cpu_steal",
            label="Steal",
            render_func=render.percent,
            boundaries=(0.0, 100.0),
        )

    used, total = values.get("used"), values.get("total")
    if used is not None and total is not None and total > 0:
        yield Result(
            state=State.OK,
            summary="%s of %s" % (render.bytes(used), render.bytes(total)),
        )
        yield Metric("vcsa_mem_used", used, boundaries=(0.0, total))
        yield Metric("vcsa_mem_total", total)
    elif used is not None:
        yield Result(state=State.OK, notice="Used: %s" % render.bytes(used))
        yield Metric("vcsa_mem_used", used)

    # An active page rate means the appliance is swapping now, which matters
    # more than swap occupancy sitting at a few percent.
    if "page_rate" in values:
        yield from check_levels(
            values["page_rate"],
            levels_upper=params.get("page_rate_levels"),
            metric_name="vcsa_swap_page_rate",
            label="Swap page rate",
            render_func=lambda v: "%.1f pages/s" % v,
            notice_only=True,
        )


check_plugin_vcsa_health_perf = CheckPlugin(
    name="vcsa_health_perf",
    service_name="VCSA %s utilization",
    sections=["vcsa_health_perf"],
    discovery_function=discover_vcsa_health_perf,
    check_function=check_vcsa_health_perf,
    check_ruleset_name="vcsa_health_perf",
    check_default_parameters={
        "levels": ("fixed", (80.0, 90.0)),
        "steal_levels": ("fixed", (5.0, 10.0)),
    },
)
