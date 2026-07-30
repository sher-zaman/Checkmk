#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check plugin: VCSA appliance access settings.
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
#   <method>;<1 enabled | 0 disabled>;<timeout or empty>
#
# Whether a given access method should be on is a site policy decision, not a
# universal one, so every state is OK by default and the ruleset carries the
# policy.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

# Agent label -> ruleset parameter key
_METHODS = {
    "SSH": "ssh",
    "DCUI": "dcui",
    "Shell": "shell",
    "Console CLI": "consolecli",
}


def parse_vcsa_health_access(string_table):
    section = {}
    for line in string_table:
        if len(line) < 2 or line[0] not in _METHODS:
            continue
        section[line[0]] = {
            "enabled": line[1] == "1",
            "timeout": line[2] if len(line) > 2 else "",
        }
    return section


agent_section_vcsa_health_access = AgentSection(
    name="vcsa_health_access",
    parse_function=parse_vcsa_health_access,
)


def discover_vcsa_health_access(section) -> DiscoveryResult:
    if section:
        yield Service()


def check_vcsa_health_access(params, section) -> CheckResult:
    if not section:
        return

    enabled = [name for name, data in sorted(section.items()) if data["enabled"]]
    disabled = [name for name, data in sorted(section.items()) if not data["enabled"]]

    yield Result(
        state=State.OK,
        summary="Enabled: %s" % (", ".join(enabled) if enabled else "none"),
    )
    if disabled:
        yield Result(state=State.OK, notice="Disabled: %s" % ", ".join(disabled))

    # Per-method policy: a site declares the state it expects, and a deviation
    # takes the configured monitoring state.
    for label, key in sorted(_METHODS.items()):
        data = section.get(label)
        if data is None:
            continue
        expected = params.get("expected_%s" % key, "any")
        if expected == "any":
            continue
        if expected == "enabled" and not data["enabled"]:
            yield Result(
                state=State(params["deviation_state"]),
                summary="%s is disabled but expected enabled" % label,
            )
        elif expected == "disabled" and data["enabled"]:
            yield Result(
                state=State(params["deviation_state"]),
                summary="%s is enabled but expected disabled" % label,
            )

    shell = section.get("Shell")
    if shell and shell["timeout"] not in ("", "0"):
        yield Result(state=State.OK, notice="Shell timeout: %s" % shell["timeout"])


check_plugin_vcsa_health_access = CheckPlugin(
    name="vcsa_health_access",
    service_name="VCSA Access Settings",
    sections=["vcsa_health_access"],
    discovery_function=discover_vcsa_health_access,
    check_function=check_vcsa_health_access,
    check_ruleset_name="vcsa_health_access",
    check_default_parameters={
        "expected_ssh": "any",
        "expected_dcui": "any",
        "expected_shell": "any",
        "expected_consolecli": "any",
        "deviation_state": 1,
    },
)
