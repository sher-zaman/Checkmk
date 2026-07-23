#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA machine TLS certificate validity.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only
#
# Agent section format (sep 59):
#   tls;<valid_to epoch>;<subject dn>;<issuer dn>

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


def parse_vcsa_health_cert(string_table):
    for line in string_table:
        if len(line) < 2 or line[0] != "tls":
            continue
        try:
            valid_to = float(line[1])
        except ValueError:
            continue
        return {
            "valid_to": valid_to,
            "subject": line[2] if len(line) > 2 else "",
            "issuer": line[3] if len(line) > 3 else "",
        }
    return None


agent_section_vcsa_health_cert = AgentSection(
    name="vcsa_health_cert",
    parse_function=parse_vcsa_health_cert,
)


def discover_vcsa_health_cert(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_cert(params, section) -> CheckResult:
    if not section:
        return

    remaining = section["valid_to"] - time.time()
    if remaining <= 0:
        yield Result(
            state=State.CRIT,
            summary="Certificate expired %s ago" % render.timespan(-remaining),
        )
    else:
        yield from check_levels(
            remaining,
            levels_lower=params.get("validity_levels"),
            metric_name="vcsa_cert_remaining",
            label="Remaining validity",
            render_func=render.timespan,
        )

    if section["subject"]:
        yield Result(state=State.OK, notice="Subject: %s" % section["subject"])
    if section["issuer"]:
        yield Result(state=State.OK, notice="Issuer: %s" % section["issuer"])


check_plugin_vcsa_health_cert = CheckPlugin(
    name="vcsa_health_cert",
    service_name="VCSA Certificate",
    sections=["vcsa_health_cert"],
    discovery_function=discover_vcsa_health_cert,
    check_function=check_vcsa_health_cert,
    check_ruleset_name="vcsa_health_certificate",
    check_default_parameters={"validity_levels": ("fixed", (2592000.0, 1296000.0))},
)
