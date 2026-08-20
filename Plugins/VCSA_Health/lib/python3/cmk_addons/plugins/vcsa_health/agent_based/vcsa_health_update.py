#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA update status.
#
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   pending_count;<n>
#   pending;<version>;<severity>;<priority>;<type>;<release epoch>;<reboot>;<text>
#   pending_error;<http status>
#   update;<state>;<pending version>;<latest query epoch>
#   version;<version>;<build>;<product>

import time

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

_UPDATE_STATES = {
    "UP_TO_DATE": State.OK,
    "UPDATES_PENDING": State.WARN,
    "STAGE_IN_PROGRESS": State.WARN,
    "INSTALL_IN_PROGRESS": State.WARN,
    "INSTALL_FAILED": State.CRIT,
    "ROLLBACK_IN_PROGRESS": State.CRIT,
}

# Severity as reported by the appliance, mapped to a parameter key.
_SEVERITY_KEYS = {
    "CRITICAL": "severity_critical",
    "IMPORTANT": "severity_important",
    "MODERATE": "severity_moderate",
    "LOW": "severity_low",
}


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_vcsa_health_update(string_table):
    section = {"pending": [], "pending_count": None, "pending_error": None}
    for line in string_table:
        if not line:
            continue
        key = line[0]
        if key == "pending_count" and len(line) >= 2:
            try:
                section["pending_count"] = int(line[1])
            except ValueError:
                pass
        elif key == "pending_error" and len(line) >= 2:
            section["pending_error"] = line[1]
        elif key == "pending" and len(line) >= 2:
            section["pending"].append(
                {
                    "version": line[1],
                    "severity": (line[2] if len(line) > 2 else "").upper(),
                    "priority": line[3] if len(line) > 3 else "",
                    "type": line[4] if len(line) > 4 else "",
                    "release": _float_or_none(line[5]) if len(line) > 5 else None,
                    "reboot": line[6] == "1" if len(line) > 6 else False,
                    "text": line[7] if len(line) > 7 else "",
                }
            )
        elif key == "update" and len(line) >= 2:
            section["state"] = line[1]
            section["pending_version"] = line[2] if len(line) > 2 else ""
            section["query_time"] = _float_or_none(line[3]) if len(line) > 3 else None
        elif key == "version" and len(line) >= 2:
            section["version"] = line[1]
            section["build"] = line[2] if len(line) > 2 else ""
            section["product"] = line[3] if len(line) > 3 else ""
    return section or None


agent_section_vcsa_health_update = AgentSection(
    name="vcsa_health_update",
    parse_function=parse_vcsa_health_update,
)


def discover_vcsa_health_update(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_update(params, section) -> CheckResult:
    if not section:
        return

    pending = section["pending"]

    # The pending list is authoritative. The state field is known to report
    # UP_TO_DATE on appliances that do have updates available, so it is only
    # trusted when no pending list could be retrieved.
    if pending:
        worst = State.OK
        for entry in pending:
            key = _SEVERITY_KEYS.get(entry["severity"], "severity_unknown")
            worst = State.worst(worst, State(params[key]))

        severities = sorted({e["severity"] for e in pending if e["severity"]})
        summary = "%d update(s) available" % len(pending)
        if severities:
            summary += " (%s)" % ", ".join(s.title() for s in severities)
        yield Result(state=worst, summary=summary)

        if any(e["reboot"] for e in pending):
            yield Result(state=State.OK, summary="reboot required")

        for entry in pending:
            detail = "Version %s" % entry["version"]
            for label, value in (
                ("severity", entry["severity"]),
                ("priority", entry["priority"]),
                ("type", entry["type"]),
            ):
                if value:
                    detail += ", %s: %s" % (label, value)
            if entry["release"]:
                detail += ", released %s" % render.date(entry["release"])
            if entry["reboot"]:
                detail += ", reboot required"
            if entry["text"]:
                detail += " (%s)" % entry["text"]
            yield Result(state=State.OK, notice=detail)
    else:
        update_state = section.get("state")
        # The pending list could not be read. That is a degradation rather than
        # a failure: the appliance's own state field is still available and is
        # what earlier versions used, so it is reported rather than discarding
        # the check. The gap itself is surfaced separately so it is visible.
        if update_state:
            state = _UPDATE_STATES.get(update_state, State.UNKNOWN)
            summary = "Update status: %s" % update_state
            target = section.get("pending_version")
            if target and update_state != "UP_TO_DATE":
                summary += " (version %s)" % target
            yield Result(state=state, summary=summary)
        elif section["pending_error"] is not None:
            # Both the pending list and the status field are unavailable, so
            # there is nothing left to fall back to and no verdict can be given.
            yield Result(
                state=State.UNKNOWN,
                summary="Update status unavailable, neither the available "
                "update list nor the appliance status field could be read "
                "(HTTP %s)" % section["pending_error"],
            )
        else:
            yield Result(state=State.UNKNOWN, summary="No update status reported")

        # Only worth noting the degradation when a fallback verdict was
        # actually given; if nothing could be read the summary already says so.
        if section["pending_error"] is not None and update_state:
            detail = (
                "The list of available updates could not be retrieved "
                "(HTTP %s), so this status comes from the appliance's own "
                "update state field, which can report the appliance as up to "
                "date while updates are available"
                % section["pending_error"]
            )
            if section["pending_error"] in ("401", "403"):
                detail += (
                    ". The monitoring account is not permitted to read the "
                    "pending update list"
                )
            yield Result(state=State(params["pending_unavailable"]), notice=detail)

    yield Metric("vcsa_updates_pending", len(pending))

    version = section.get("version")
    if version:
        details = version
        if section.get("build"):
            details += " build %s" % section["build"]
        yield Result(state=State.OK, summary="Version: %s" % details)

    # An appliance that has stopped querying the repository keeps reporting
    # itself up to date, so the age of the last check is a blind spot in its own
    # right.
    query_time = section.get("query_time")
    if query_time:
        yield from check_levels(
            max(time.time() - query_time, 0),
            levels_upper=params.get("last_check_age"),
            metric_name="vcsa_update_check_age",
            label="Last update check",
            render_func=lambda v: "%s ago" % render.timespan(v),
        )


check_plugin_vcsa_health_update = CheckPlugin(
    name="vcsa_health_update",
    service_name="VCSA Update",
    sections=["vcsa_health_update"],
    discovery_function=discover_vcsa_health_update,
    check_function=check_vcsa_health_update,
    check_ruleset_name="vcsa_health_update",
    check_default_parameters={
        "last_check_age": ("fixed", (1209600.0, 2592000.0)),  # 14 d / 30 d
        "severity_critical": 2,
        "severity_important": 1,
        "severity_moderate": 1,
        "severity_low": 1,
        "severity_unknown": 1,
        "pending_unavailable": 0,
    },
)
