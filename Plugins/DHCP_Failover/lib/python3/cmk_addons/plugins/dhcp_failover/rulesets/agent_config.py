#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Checkmk ruleset: DHCP failover monitoring agent plugin deployment (Bakery)
#
# Author: Sher Zaman (FirmaTrust)
# License: GPLv2
#
# On Checkmk Raw edition this rule exists but has no effect, since the
# Agent Bakery is only available in the commercial editions.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Deploy the dhcp_failover.ps1 agent plugin to Windows hosts. "
            "The plugin reports the state of all DHCPv4 failover "
            "relationships configured on the DHCP server. On hosts without "
            "the DHCP Server role the plugin exits silently."
        ),
        elements={
            "deploy": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Deployment"),
                    label=Label("Deploy the DHCP failover agent plugin"),
                    prefill=DefaultValue(True),
                ),
            ),
        },
    )


rule_spec_dhcp_failover_bakery = AgentConfig(
    name="dhcp_failover",
    title=Title("DHCP failover monitoring (Windows)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
