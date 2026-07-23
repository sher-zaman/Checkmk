#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Datasource rule for the VCSA health special agent.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    String,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form():
    return Dictionary(
        title=Title("VMware vCenter Server Appliance (VCSA) health"),
        help_text=Help(
            "This rule activates the VCSA health special agent, which "
            "monitors the vCenter Server Appliance itself via its REST API: "
            "vMon service states, appliance health areas, CPU, memory, swap "
            "and filesystem usage, update status, file-based backup jobs and "
            "the machine TLS certificate. Supports VCSA 7.x, 8.x and 9.x. "
            "The configured user needs read access to the appliance "
            "management API (e.g. a member of the SystemConfiguration "
            "administrators or a role with the corresponding privileges)."
        ),
        elements={
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "User for the appliance API, e.g. "
                        "administrator@vsphere.local or a dedicated "
                        "read-only monitoring account."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
            ),
            "no_cert_check": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Disable TLS certificate verification"),
                    help_text=Help(
                        "Skip verification of the appliance TLS certificate. "
                        "Only use this for appliances with self-signed "
                        "certificates."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Request timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(30),
                    custom_validate=(validators.NumberInRange(min_value=1),),
                ),
            ),
        },
    )


rule_spec_vcsa_health = SpecialAgent(
    name="vcsa_health",
    title=Title("VMware vCenter Server Appliance (VCSA) health"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form,
)
