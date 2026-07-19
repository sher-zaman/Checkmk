#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Checkmk ruleset: Windows DHCP failover relationships (check parameters)
#
# Author: Sher Zaman (FirmaTrust)
# License: GPLv2

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Map each DHCP failover relationship state reported by the "
            "Windows DHCP server to a monitoring state."
        ),
        elements={
            "state_normal": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state for 'Normal'"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "state_communication_interrupted": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state for 'CommunicationInterrupted'"),
                    help_text=Help(
                        "The partners cannot reach each other but both may "
                        "still be serving leases."
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "state_partner_down": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state for 'PartnerDown'"),
                    help_text=Help(
                        "This server has been told its partner is down and "
                        "has taken over the full address pool."
                    ),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "state_transitional": DictElement(
                parameter_form=ServiceState(
                    title=Title(
                        "Monitoring state for transitional states "
                        "(Init, Startup, Recover, RecoverWait, RecoverDone)"
                    ),
                    help_text=Help(
                        "States passed through while a relationship starts "
                        "up or resynchronizes after an outage."
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "state_other": DictElement(
                parameter_form=ServiceState(
                    title=Title(
                        "Monitoring state for all other states "
                        "(PotentialConflict, ConflictDone, "
                        "ResolutionInterrupted, NoState)"
                    ),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_dhcp_failover = CheckParameters(
    name="dhcp_failover",
    title=Title("Windows DHCP failover relationships"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(
        item_title=Title("Failover relationship name"),
        item_form=String(),
    ),
)
