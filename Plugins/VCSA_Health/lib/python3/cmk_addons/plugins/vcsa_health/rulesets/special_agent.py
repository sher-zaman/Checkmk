#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Datasource rule for the VCSA health special agent.
#
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    SingleChoice,
    SingleChoiceElement,
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
            "update_source_type": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Source for the available update list"),
                    help_text=Help(
                        "Which source the appliance consults when listing "
                        "available updates. The cached last result performs no "
                        "network access and is suitable for frequent polling. "
                        "Querying the online repository is more current but "
                        "makes the appliance reach out to its update "
                        "repository on every check."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="LAST_CHECK",
                            title=Title("Cached result of the appliance's last check"),
                        ),
                        SingleChoiceElement(
                            name="LOCAL",
                            title=Title("Local repository only"),
                        ),
                        SingleChoiceElement(
                            name="LOCAL_AND_ONLINE",
                            title=Title("Local and online repository (live query)"),
                        ),
                    ],
                    prefill=DefaultValue("LAST_CHECK"),
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
