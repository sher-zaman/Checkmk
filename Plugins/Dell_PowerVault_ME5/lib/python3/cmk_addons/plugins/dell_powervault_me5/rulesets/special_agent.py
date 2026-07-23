#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# dell_powervault_me5 - Special agent configuration ruleset
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
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
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _formspec() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 storage"),
        help_text=Help(
            "Monitor Dell PowerVault ME5 series storage systems through the "
            "controller HTTPS management API. Point this rule at the controller "
            "management IP and supply a read-only (monitor) account. Assign the "
            "rule to a dedicated host for the array."
        ),
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("API user"),
                    help_text=Help("A user with the monitor (read-only) role is sufficient."),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connection timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(30),
                ),
            ),
            "verify_ssl": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Verify TLS certificate"),
                    help_text=Help(
                        "ME5 controllers ship a self-signed certificate, so this "
                        "is off by default. Enable it once a trusted certificate "
                        "is installed on the array."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


rule_spec_dell_powervault_me5 = SpecialAgent(
    name="dell_powervault_me5",
    title=Title("Dell PowerVault ME5 storage"),
    topic=Topic.STORAGE,
    parameter_form=_formspec,
)
