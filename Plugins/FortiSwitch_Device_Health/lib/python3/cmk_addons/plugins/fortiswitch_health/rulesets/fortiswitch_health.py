#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# fortiswitch_health - Ruleset definitions
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# Temperature deliberately has no ruleset here: the temperature check
# registers against the built-in "temperature" ruleset, so the stock
# Checkmk Temperature rule (levels, trend computation, unit display)
# applies to FortiSwitch chassis sensors out of the box.
#
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)


def _parameter_form_cpu() -> Dictionary:
    return Dictionary(
        title=Title("FortiSwitch CPU utilization"),
        help_text=Help(
            "WARN/CRIT levels for FortiSwitch CPU utilization. The value is "
            "an instantaneous sample; brief spikes are normal on these "
            "platforms, so consider pairing lower levels with averaging on "
            "the service if you tighten them."
        ),
        elements={
            "levels_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on CPU utilization"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
            ),
        },
    )


rule_spec_fortiswitch_cpu = CheckParameters(
    name="fortiswitch_cpu",
    title=Title("FortiSwitch CPU utilization"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_cpu,
    condition=HostCondition(),
)


def _parameter_form_memory() -> Dictionary:
    return Dictionary(
        title=Title("FortiSwitch memory usage"),
        help_text=Help(
            "WARN/CRIT levels for FortiSwitch memory usage in percent of "
            "total memory. Embedded platforms hold a high, stable baseline; "
            "the trend over time matters more than the instant value."
        ),
        elements={
            "levels_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on memory usage"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
            ),
        },
    )


rule_spec_fortiswitch_memory = CheckParameters(
    name="fortiswitch_memory",
    title=Title("FortiSwitch memory usage"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_memory,
    condition=HostCondition(),
)


def _parameter_form_psu() -> Dictionary:
    return Dictionary(
        title=Title("FortiSwitch PSU state"),
        help_text=Help(
            "Monitoring state to assign when a FortiSwitch power supply "
            "reports 'not OK'. Default is CRIT. Downgrade to WARN for units "
            "with a known-unplugged second PSU instead of leaving the "
            "service permanently acknowledged."
        ),
        elements={
            "state_not_ok": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when PSU reports not OK"),
                    prefill=DefaultValue(2),
                ),
            ),
        },
    )


rule_spec_fortiswitch_psu = CheckParameters(
    name="fortiswitch_psu",
    title=Title("FortiSwitch PSU state"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_psu,
    condition=HostAndItemCondition(item_title=Title("PSU name")),
)


def _parameter_form_fan() -> Dictionary:
    return Dictionary(
        title=Title("FortiSwitch fan"),
        help_text=Help(
            "State mapping and optional speed levels for FortiSwitch fans. "
            "Fan speed is reported as percent of maximum. Some models "
            "(e.g. FS-1024D) report sensor status 'unavailable' while "
            "delivering live speed values; that combination is treated as "
            "OK by default."
        ),
        elements={
            "state_nonoperational": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when sensor reports nonoperational"),
                    prefill=DefaultValue(2),
                ),
            ),
            "state_unavailable_no_speed": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when sensor is unavailable and no speed is reported"),
                    prefill=DefaultValue(2),
                ),
            ),
            "levels_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on fan speed"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(5.0, 2.0)),
                ),
            ),
            "levels_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on fan speed"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(90.0, 95.0)),
                ),
            ),
        },
    )


rule_spec_fortiswitch_fan = CheckParameters(
    name="fortiswitch_fan",
    title=Title("FortiSwitch fan"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_fan,
    condition=HostAndItemCondition(item_title=Title("Fan name")),
)


def _parameter_form_sfp() -> Dictionary:
    return Dictionary(
        title=Title("FortiSwitch SFP optical diagnostics"),
        help_text=Help(
            "Levels for SFP/DOM optical transceiver values. RX power is the "
            "primary degradation signal: a receive level drifting toward "
            "the receiver floor indicates a degrading fiber path or a dying "
            "far-end laser. Defaults are lenient enough for common 1G/10G "
            "optics; tune per optic type where needed. An optic that stops "
            "reporting DOM values entirely (removed or failed) is CRIT by "
            "default."
        ),
        elements={
            "levels_rx_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on RX power (dBm)"),
                    form_spec_template=Float(unit_symbol="dBm"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(-16.0, -20.0)),
                ),
            ),
            "levels_tx_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on TX power (dBm)"),
                    form_spec_template=Float(unit_symbol="dBm"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(-10.0, -13.0)),
                ),
            ),
            "levels_temp_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on transceiver temperature"),
                    form_spec_template=Float(unit_symbol="°C"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(70.0, 80.0)),
                ),
            ),
            "levels_voltage_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on supply voltage"),
                    form_spec_template=Float(unit_symbol="V"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(3.13, 2.97)),
                ),
            ),
            "levels_voltage_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on supply voltage"),
                    form_spec_template=Float(unit_symbol="V"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(3.47, 3.63)),
                ),
            ),
            "levels_bias_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on laser bias current"),
                    form_spec_template=Float(unit_symbol="mA"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(70.0, 90.0)),
                ),
            ),
            "state_vanished": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a discovered optic stops reporting"),
                    prefill=DefaultValue(2),
                ),
            ),
        },
    )


rule_spec_fortiswitch_sfp = CheckParameters(
    name="fortiswitch_sfp",
    title=Title("FortiSwitch SFP optical diagnostics"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_sfp,
    condition=HostAndItemCondition(item_title=Title("Optic name")),
)
