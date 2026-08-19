#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA machine TLS certificate validity.
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
#   tls;<valid_to epoch>;<subject dn>;<issuer dn>;<hostname>;<san csv>

import re
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


def _cn_from_dn(dn):
    match = re.search(r"CN=([^,]+)", dn or "")
    return match.group(1).strip() if match else ""


def hostname_matches_cert(hostname, subject_dn, san_list):
    """Whether the appliance hostname appears in the certificate.

    DNS names are case-insensitive, and a certificate legitimately carries the
    FQDN in the SAN list while the CN holds something else, so both are checked
    case-insensitively. SAN lists can also contain non-hostname entries such as
    IP addresses, which simply will not match.
    """
    if not hostname:
        return None
    target = hostname.strip().lower()
    if target and target == _cn_from_dn(subject_dn).lower():
        return True
    return target in {entry.strip().lower() for entry in san_list}


def parse_vcsa_health_cert(string_table):
    for line in string_table:
        if len(line) < 2 or line[0] != "tls":
            continue
        try:
            valid_to = float(line[1])
        except ValueError:
            continue
        san = [x for x in (line[5].split(",") if len(line) > 5 else []) if x]
        return {
            "valid_to": valid_to,
            "subject": line[2] if len(line) > 2 else "",
            "issuer": line[3] if len(line) > 3 else "",
            "hostname": line[4] if len(line) > 4 else "",
            "san": san,
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

    matched = hostname_matches_cert(
        section["hostname"], section["subject"], section["san"]
    )
    if matched is False:
        yield Result(
            state=State(params["hostname_mismatch"]),
            summary="Appliance hostname %s not present in certificate"
            % section["hostname"],
        )
    elif matched is True:
        yield Result(
            state=State.OK,
            notice="Hostname %s found in certificate" % section["hostname"],
        )
    if section["san"]:
        yield Result(state=State.OK, notice="SAN: %s" % ", ".join(section["san"]))

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
    check_default_parameters={
        "validity_levels": ("fixed", (2592000.0, 1296000.0)),
        "hostname_mismatch": 1,
    },
)
