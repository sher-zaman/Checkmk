# system_reboot_required - CheckMK agent-based check plugin
#
# Copyright (C) 2026  Luca-Leon Hausdoerfer - (cmk@hausdoerfer.dev)
# Copyright (C) 2026  Sher Zaman - FirmaTrust (sher_zaman[at]outlook[dot]com)
#
# Modified 2026-07-18 by Sher Zaman (FirmaTrust):
#   - Made the service state for pending reboots with unknown age
#     configurable via ruleset (previously hardcoded to CRIT);
#     default is now WARN
#   - Added perfdata metric for pending reboot age with thresholds
#   - Malformed timestamps are treated the same as unknown age
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import time
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = dict[str, Any]

_DEFAULT_PARAMS: dict[str, Any] = {
    "warn_hours": 12,
    "crit_hours": 24,
    "unknown_since_state": 1,  # 0=OK, 1=WARN, 2=CRIT
}


def parse_system_reboot_required(string_table: StringTable) -> Section:
    parsed: Section = {}
    for line in string_table:
        if len(line) < 2:
            continue
        key = line[0].rstrip(":")
        value = " ".join(line[1:]).strip()
        parsed[key] = value
    return parsed


def discover_system_reboot_required(section: Section):
    if section:
        yield Service()


def check_system_reboot_required(params: dict[str, Any], section: Section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data received from agent plugin")
        return

    reboot_required = section.get("reboot_required", "0")
    detection_method = section.get("detection_method", "unknown")
    since_timestamp = section.get("since_timestamp", "unknown")
    packages = section.get("packages", "unknown")

    if reboot_required != "1":
        yield Result(state=State.OK, summary="No reboot pending")
        return

    warn_hours = params.get("warn_hours", _DEFAULT_PARAMS["warn_hours"])
    crit_hours = params.get("crit_hours", _DEFAULT_PARAMS["crit_hours"])
    unknown_since_state = params.get(
        "unknown_since_state", _DEFAULT_PARAMS["unknown_since_state"]
    )

    summary_parts = [f"Reboot pending (detected via: {detection_method})"]

    age_seconds: float | None = None
    if since_timestamp != "unknown":
        try:
            age_seconds = time.time() - float(since_timestamp)
        except ValueError:
            age_seconds = None

    if age_seconds is None:
        # Age cannot be determined: use the configured state (default WARN)
        state = State(unknown_since_state)
        summary_parts.append("pending since: unknown")
    else:
        age_hours = age_seconds / 3600.0

        hours_int = int(age_hours)
        minutes_int = int((age_hours - hours_int) * 60)
        if hours_int > 0:
            age_str = f"{hours_int}h {minutes_int}m"
        else:
            age_str = f"{minutes_int}m"

        summary_parts.append(f"pending since: {age_str}")

        if age_hours >= crit_hours:
            state = State.CRIT
        elif age_hours >= warn_hours:
            state = State.WARN
        else:
            state = State.OK  # reboot required but still within acceptable window

        yield Metric(
            "system_reboot_pending_age",
            age_seconds,
            levels=(warn_hours * 3600.0, crit_hours * 3600.0),
        )

    if packages and packages not in ("unknown", "none"):
        pkg_list = packages.split(",")
        if len(pkg_list) > 5:
            summary_parts.append(f"packages: {', '.join(pkg_list[:5])} (+{len(pkg_list) - 5} more)")
        else:
            summary_parts.append(f"packages: {packages}")

    yield Result(state=state, summary=", ".join(summary_parts))


agent_section_system_reboot_required = AgentSection(
    name="system_reboot_required",
    parse_function=parse_system_reboot_required,
)

check_plugin_system_reboot_required = CheckPlugin(
    name="system_reboot_required",
    service_name="System Reboot Required",
    discovery_function=discover_system_reboot_required,
    check_function=check_system_reboot_required,
    check_default_parameters=_DEFAULT_PARAMS,
    check_ruleset_name="system_reboot_required",
)
