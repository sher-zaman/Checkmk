#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA root account password expiry.
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
#   error;<http status>
#   root;<expires epoch>;<enabled>;<max days>;<warn days>;<last change epoch>
#   policy;<max days>;<min days>;<warn days>

import time

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    check_levels,
    render,
)


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_vcsa_health_local_accounts(string_table):
    section = {}
    for line in string_table:
        if not line:
            continue
        if line[0] == "error":
            section["error"] = line[1] if len(line) > 1 else "unknown"
        elif line[0] == "root" and len(line) >= 2:
            section["expires_at"] = _float_or_none(line[1])
            section["enabled"] = line[2] != "0" if len(line) > 2 else True
            section["max_days"] = line[3] if len(line) > 3 else ""
            section["warn_days"] = line[4] if len(line) > 4 else ""
            section["last_change"] = _float_or_none(line[5]) if len(line) > 5 else None
        elif line[0] == "policy" and len(line) >= 2:
            section["policy"] = {
                "max_days": line[1],
                "min_days": line[2] if len(line) > 2 else "",
                "warn_days": line[3] if len(line) > 3 else "",
            }
    return section or None


agent_section_vcsa_health_local_accounts = AgentSection(
    name="vcsa_health_local_accounts",
    parse_function=parse_vcsa_health_local_accounts,
)


def discover_vcsa_health_local_accounts(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_local_accounts(params, section) -> CheckResult:
    if not section:
        return

    # An appliance whose root password has already expired answers the account
    # endpoint with HTTP 500, so the failure itself is the finding.
    if "error" in section:
        detail = ""
        if section["error"] == "500":
            detail = ", this commonly indicates an expired root password"
        yield Result(
            state=State.CRIT,
            summary="Unable to retrieve root account details%s" % detail,
        )
        yield Result(state=State.OK, notice="API response: HTTP %s" % section["error"])
        policy = section.get("policy")
        if policy:
            yield Result(
                state=State.OK,
                notice="Appliance password policy: max %s days, min %s days, "
                "warn %s days" % (policy["max_days"], policy["min_days"],
                                  policy["warn_days"]),
            )
        return

    if not section.get("enabled", True):
        yield Result(state=State.WARN, summary="Root account is disabled")

    expires_at = section.get("expires_at")
    if expires_at is None:
        yield Result(
            state=State(params["never_expires"]),
            summary="Root password does not expire",
        )
    else:
        remaining = expires_at - time.time()
        if remaining <= 0:
            yield Result(
                state=State.CRIT,
                summary="Root password expired %s ago" % render.timespan(-remaining),
            )
        else:
            yield from check_levels(
                remaining,
                levels_lower=params.get("expiry_levels"),
                metric_name="vcsa_root_password_remaining",
                label="Root password expires in",
                render_func=render.timespan,
            )
        yield Result(
            state=State.OK, notice="Expiry date: %s" % render.datetime(expires_at)
        )

    if section.get("last_change"):
        yield Result(
            state=State.OK,
            notice="Last password change: %s" % render.datetime(section["last_change"]),
        )
    if section.get("max_days") not in (None, ""):
        yield Result(
            state=State.OK,
            notice="Maximum days between password changes: %s" % section["max_days"],
        )

    # The appliance-wide policy is reported for context. It does not govern the
    # root account, which carries its own max-days value.
    policy = section.get("policy")
    if policy:
        yield Result(
            state=State.OK,
            notice="Appliance password policy: max %s days, min %s days, warn %s days"
            % (policy["max_days"], policy["min_days"], policy["warn_days"]),
        )


check_plugin_vcsa_health_local_accounts = CheckPlugin(
    name="vcsa_health_local_accounts",
    service_name="VCSA Root Password",
    sections=["vcsa_health_local_accounts"],
    discovery_function=discover_vcsa_health_local_accounts,
    check_function=check_vcsa_health_local_accounts,
    check_ruleset_name="vcsa_health_local_accounts",
    check_default_parameters={
        "expiry_levels": ("fixed", (1209600.0, 604800.0)),  # 14 d / 7 d
        "never_expires": 0,
    },
)
