#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GPL-2.0-only
#
###############################################################################
# synology_smart - ruleset (optional threshold overrides)
###############################################################################
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
###############################################################################
#
# The extension is fully functional without any rule. This ruleset
# allows raising or lowering the built-in counter thresholds
# (WARN >= 1, CRIT >= 10 on the raw values), for example to accept a
# known-stable disk with a fixed number of reallocated sectors
# without suppressing the service, and setting the state used for
# attributes that failed at some point in the past.
###############################################################################
#
# 2026-08-04: 1.1.0 adds the state for historic attribute failures
# 2026-07-28: 1.0.1 author metadata update
# 2026-07-15: 1.0.0 initial release
###############################################################################

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    ServiceState,
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
            "historic_failure_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State for an attribute that failed in the past"),
                    help_text=Help(
                        "Applies to attributes DSM reports as In_the_past, meaning the "
                        "attribute fell below its threshold at some point in the drive's "
                        "life and has since recovered. This is history held in the drive "
                        "and cannot be cleared, so it is ignored (OK) by default rather "
                        "than treated as a fault. Set it to WARN or CRIT to be notified "
                        "of historic failures instead. Any other status that is not OK "
                        "remains CRIT."
                    ),
                    prefill=DefaultValue(0),
                ),
                required=False,
            ),
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
