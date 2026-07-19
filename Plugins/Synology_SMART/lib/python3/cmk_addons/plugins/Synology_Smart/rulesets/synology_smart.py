#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# synology_smart - ruleset (optional threshold overrides)
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# The plugin is fully functional without any rule. This ruleset only
# allows raising or lowering the built-in thresholds (WARN >= 1,
# CRIT >= 10 on the raw value of the pre-failure counters), e.g. to
# accept a known-stable disk with a fixed number of reallocated
# sectors without suppressing the service.
###############################################################################

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _levels(title):
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(
                "Thresholds on the raw value of this SMART attribute. "
                "The attribute is only evaluated on drives that report it."
            ),
            form_spec_template=Integer(),
            level_direction=LevelDirection.UPPER,
            prefill_fixed_levels=DefaultValue(value=(1, 10)),
        ),
        required=True,
    )


def _parameter_form():
    return Dictionary(
        elements={
            "reallocated": _levels("Reallocated sector count (Reallocated_Sector_Ct)"),
            "pending": _levels("Current pending sectors (Current_Pending_Sector)"),
            "offline_uncorrectable": _levels(
                "Offline uncorrectable sectors (Offline_Uncorrectable)"
            ),
            "reported_uncorrect": _levels(
                "Reported uncorrectable errors (Reported_Uncorrect)"
            ),
            "udma_crc": _levels("UDMA CRC error count (UDMA_CRC_Error_Count)"),
        }
    )


rule_spec_synology_smart = CheckParameters(
    name="synology_smart",
    title=Title("Synology SMART attributes"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Drive")),
)
