#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check parameter rulesets for the VCSA health plugin.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)


def _percent_levels(title, default):
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            level_direction=LevelDirection.UPPER,
            form_spec_template=Float(unit_symbol="%"),
            prefill_fixed_levels=DefaultValue(default),
        ),
    )


def _parameter_form_perf():
    return Dictionary(
        title=Title("VCSA resource utilization"),
        help_text=Help(
            "Thresholds for the CPU, memory and swap utilization services "
            "of the vCenter Server Appliance."
        ),
        elements={
            "levels": _percent_levels(Title("Upper levels on utilization"), (80.0, 90.0)),
        },
    )


rule_spec_vcsa_health_perf = CheckParameters(
    name="vcsa_health_perf",
    title=Title("VCSA resource utilization"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_perf,
    condition=HostAndItemCondition(item_title=Title("Resource")),
)


def _parameter_form_filesystems():
    return Dictionary(
        title=Title("VCSA filesystem usage"),
        help_text=Help(
            "Thresholds for the appliance filesystem usage services, e.g. "
            "the root, seat, db and log partitions of the vCenter Server "
            "Appliance."
        ),
        elements={
            "levels": _percent_levels(Title("Upper levels on used space"), (80.0, 90.0)),
        },
    )


rule_spec_vcsa_health_filesystems = CheckParameters(
    name="vcsa_health_filesystems",
    title=Title("VCSA filesystem usage"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_filesystems,
    condition=HostAndItemCondition(item_title=Title("Filesystem")),
)


def _parameter_form_backup():
    return Dictionary(
        title=Title("VCSA file-based backup"),
        help_text=Help(
            "Thresholds for the age of the last file-based (VAMI) backup "
            "job of the vCenter Server Appliance."
        ),
        elements={
            "age_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximum age of the last backup"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue((93600.0, 180000.0)),
                ),
            ),
        },
    )


rule_spec_vcsa_health_backup = CheckParameters(
    name="vcsa_health_backup",
    title=Title("VCSA file-based backup"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_backup,
    condition=HostCondition(),
)


def _parameter_form_certificate():
    return Dictionary(
        title=Title("VCSA TLS certificate"),
        help_text=Help(
            "Thresholds for the remaining validity of the machine TLS "
            "certificate of the vCenter Server Appliance."
        ),
        elements={
            "validity_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimum remaining validity"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY]
                    ),
                    prefill_fixed_levels=DefaultValue((2592000.0, 1296000.0)),
                ),
            ),
        },
    )


rule_spec_vcsa_health_certificate = CheckParameters(
    name="vcsa_health_certificate",
    title=Title("VCSA TLS certificate"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_certificate,
    condition=HostCondition(),
)


def _parameter_form_services():
    return Dictionary(
        title=Title("VCSA vMon service states"),
        help_text=Help(
            "Configures the monitoring state assigned to the vMon services of "
            "the vCenter Server Appliance based on their startup type, running "
            "state and reported health. A running service is evaluated by its "
            "health; a service that is not running is evaluated by its startup "
            "type."
        ),
        elements={
            "automatic_stopped": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Automatic service not running"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "manual_stopped": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Manual service not running"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "disabled_stopped": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Disabled service not running"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "disabled_started": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Disabled service unexpectedly running"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "health_warnings": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Running service health: healthy with warnings"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "health_degraded": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Running service health: degraded"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_vcsa_health_services = CheckParameters(
    name="vcsa_health_services",
    title=Title("VCSA vMon service states"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_services,
    condition=HostAndItemCondition(item_title=Title("Service")),
)
