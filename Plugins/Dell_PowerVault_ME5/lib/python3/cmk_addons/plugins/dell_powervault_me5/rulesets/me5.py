#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# dell_powervault_me5 - Ruleset definitions
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# Pool capacity and sensor temperature deliberately have no ruleset here: the
# pool check registers against the built-in "filesystem" ruleset and the
# temperature check against the built-in "temperature" ruleset, so the stock
# Checkmk Filesystem and Temperature rules (levels, magic factor, trend) apply
# to the array out of the box.
#
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    Integer,
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


def _health_elements() -> dict[str, DictElement]:
    """The three configurable ME5 health-numeric problem states.

    health-numeric 0 (OK) and 4 (N/A) are always OK and not exposed.
    """
    return {
        "state_degraded": DictElement(
            required=False,
            parameter_form=ServiceState(
                title=Title("State when health is Degraded"),
                prefill=DefaultValue(1),
            ),
        ),
        "state_fault": DictElement(
            required=False,
            parameter_form=ServiceState(
                title=Title("State when health is Fault"),
                prefill=DefaultValue(2),
            ),
        ),
        "state_unknown": DictElement(
            required=False,
            parameter_form=ServiceState(
                title=Title("State when health is Unknown"),
                prefill=DefaultValue(1),
            ),
        ),
    }


# --------------------------------------------------------------------------- system
def _form_system() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 system health"),
        help_text=Help(
            "Mapping of the overall system health and management-controller "
            "redundancy conditions to monitoring states."
        ),
        elements={
            **_health_elements(),
            "state_not_redundant": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the system is not redundant"),
                    prefill=DefaultValue(1),
                ),
            ),
            "state_controller_down": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a controller is not operational"),
                    prefill=DefaultValue(2),
                ),
            ),
            "state_partner_mc": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the partner management controller is not operational"),
                    prefill=DefaultValue(1),
                ),
            ),
        },
    )


rule_spec_dell_me5_system = CheckParameters(
    name="dell_me5_system",
    title=Title("Dell PowerVault ME5 system health"),
    topic=Topic.STORAGE,
    parameter_form=_form_system,
    condition=HostCondition(),
)


# --------------------------------------------------------------------------- controllers
def _form_controllers() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 controller health"),
        help_text=Help("Monitoring states for controller health and operational conditions."),
        elements={
            **_health_elements(),
            "state_not_operational": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the controller is not operational"),
                    prefill=DefaultValue(2),
                ),
            ),
            "state_failed_over": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the controller has failed over"),
                    prefill=DefaultValue(1),
                ),
            ),
            "state_write_through": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the cache has dropped to write-through"),
                    prefill=DefaultValue(1),
                ),
            ),
            "state_not_redundant": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the controller is not redundant"),
                    prefill=DefaultValue(1),
                ),
            ),
        },
    )


rule_spec_dell_me5_controllers = CheckParameters(
    name="dell_me5_controllers",
    title=Title("Dell PowerVault ME5 controller health"),
    topic=Topic.STORAGE,
    parameter_form=_form_controllers,
    condition=HostAndItemCondition(item_title=Title("Controller")),
)


# --------------------------------------------------------------------------- host ports
def _form_host_ports() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 host port"),
        help_text=Help(
            "Monitoring states for host port health and link status. A link "
            "status other than Up is Critical by default. For ports that are "
            "intentionally uncabled, add a rule scoped to those ports and set "
            "the link status state to OK so they do not alert."
        ),
        elements={
            **_health_elements(),
            "state_not_up": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the port link status is not Up"),
                    prefill=DefaultValue(2),
                ),
            ),
        },
    )


rule_spec_dell_me5_host_ports = CheckParameters(
    name="dell_me5_host_ports",
    title=Title("Dell PowerVault ME5 host port"),
    topic=Topic.STORAGE,
    parameter_form=_form_host_ports,
    condition=HostAndItemCondition(item_title=Title("Host port")),
)


# --------------------------------------------------------------------------- disk groups
def _form_disk_groups() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 disk group"),
        help_text=Help(
            "Monitoring states for disk group condition and background jobs. A "
            "verify/scrub is normal maintenance and stays informational; a "
            "reconstruct implies a failed member."
        ),
        elements={
            "state_not_fault_tolerant": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the disk group is not fault tolerant and online"),
                    prefill=DefaultValue(2),
                ),
            ),
            "state_reconstruct": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a reconstruct is running"),
                    prefill=DefaultValue(1),
                ),
            ),
            "state_no_spares": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the disk group has no spares"),
                    prefill=DefaultValue(0),
                ),
            ),
        },
    )


rule_spec_dell_me5_disk_groups = CheckParameters(
    name="dell_me5_disk_groups",
    title=Title("Dell PowerVault ME5 disk group"),
    topic=Topic.STORAGE,
    parameter_form=_form_disk_groups,
    condition=HostAndItemCondition(item_title=Title("Disk group")),
)


# --------------------------------------------------------------------------- volumes
def _form_volumes() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 volume"),
        help_text=Help(
            "Monitoring states for volume health and path ownership, plus "
            "optional levels on the thin-provisioned fill ratio (off by default)."
        ),
        elements={
            **_health_elements(),
            "state_non_preferred_owner": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the current owner is not the preferred owner"),
                    prefill=DefaultValue(1),
                ),
            ),
            "levels_fill": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on thin-provisioned fill ratio"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(90.0, 95.0)),
                ),
            ),
        },
    )


rule_spec_dell_me5_volumes = CheckParameters(
    name="dell_me5_volumes",
    title=Title("Dell PowerVault ME5 volume"),
    topic=Topic.STORAGE,
    parameter_form=_form_volumes,
    condition=HostAndItemCondition(item_title=Title("Volume")),
)


# --------------------------------------------------------------------------- disks
def _form_disks() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 disk"),
        help_text=Help(
            "Monitoring states for disk health and error conditions, plus "
            "optional lower levels on remaining SSD life (off by default)."
        ),
        elements={
            **_health_elements(),
            "state_error": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the disk reports an error or is marked down"),
                    prefill=DefaultValue(2),
                ),
            ),
            "state_smart_disabled": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when SMART is not enabled"),
                    prefill=DefaultValue(0),
                ),
            ),
            "levels_ssd_life": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on remaining SSD life"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(10.0, 5.0)),
                ),
            ),
        },
    )


rule_spec_dell_me5_disks = CheckParameters(
    name="dell_me5_disks",
    title=Title("Dell PowerVault ME5 disk"),
    topic=Topic.STORAGE,
    parameter_form=_form_disks,
    condition=HostAndItemCondition(item_title=Title("Disk")),
)


# --------------------------------------------------------------------------- power supplies
def _form_power_supplies() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 power supply"),
        help_text=Help("Monitoring states for power supply health and status."),
        elements={
            **_health_elements(),
            "state_not_up": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the power supply status is not Up"),
                    prefill=DefaultValue(2),
                ),
            ),
        },
    )


rule_spec_dell_me5_power_supplies = CheckParameters(
    name="dell_me5_power_supplies",
    title=Title("Dell PowerVault ME5 power supply"),
    topic=Topic.STORAGE,
    parameter_form=_form_power_supplies,
    condition=HostAndItemCondition(item_title=Title("Power supply")),
)


# --------------------------------------------------------------------------- fans
def _form_fans() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 fan"),
        help_text=Help(
            "Monitoring states for fan health and status, plus optional levels "
            "on fan speed (off by default, since speed varies with thermal load)."
        ),
        elements={
            **_health_elements(),
            "state_not_up": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the fan status is not Up"),
                    prefill=DefaultValue(2),
                ),
            ),
            "levels_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on fan speed"),
                    form_spec_template=Integer(unit_symbol="RPM"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(2000, 1000)),
                ),
            ),
            "levels_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on fan speed"),
                    form_spec_template=Integer(unit_symbol="RPM"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(8000, 10000)),
                ),
            ),
        },
    )


rule_spec_dell_me5_fans = CheckParameters(
    name="dell_me5_fans",
    title=Title("Dell PowerVault ME5 fan"),
    topic=Topic.STORAGE,
    parameter_form=_form_fans,
    condition=HostAndItemCondition(item_title=Title("Fan")),
)


# --------------------------------------------------------------------------- sensors (state only)
def _form_sensor() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 sensor"),
        help_text=Help(
            "Monitoring state for the non-temperature enclosure sensors, "
            "grouped by type (voltage, current and the capacitor/supercap "
            "pack). One service per type aggregates all sensors of that type "
            "and raises if any single sensor reports a status other than OK."
        ),
        elements={
            "state_not_ok": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when any sensor of this type is not OK"),
                    prefill=DefaultValue(1),
                ),
            ),
        },
    )


rule_spec_dell_me5_sensor = CheckParameters(
    name="dell_me5_sensor",
    title=Title("Dell PowerVault ME5 sensor"),
    topic=Topic.STORAGE,
    parameter_form=_form_sensor,
    condition=HostAndItemCondition(item_title=Title("Sensor type")),
)


# --------------------------------------------------------------------------- unwritable cache
def _form_unwritable_cache() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 unwritable cache"),
        help_text=Help(
            "Upper levels on the percentage of cache that cannot be written to "
            "disk. Any non-zero value indicates data at risk, so the default "
            "raises even at 1 percent."
        ),
        elements={
            "levels_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on unwritable cache"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(1.0, 1.0)),
                ),
            ),
        },
    )


rule_spec_dell_me5_unwritable_cache = CheckParameters(
    name="dell_me5_unwritable_cache",
    title=Title("Dell PowerVault ME5 unwritable cache"),
    topic=Topic.STORAGE,
    parameter_form=_form_unwritable_cache,
    condition=HostCondition(),
)


# --------------------------------------------------------------------------- snapshots
def _form_snapshots() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 snapshots"),
        help_text=Help(
            "Monitoring states for snapshot health, plus optional upper levels "
            "on the age of the newest snapshot per source volume. Enable the "
            "age levels to alert when a snapshot schedule stalls (for example "
            "26 hours warning and 50 hours critical for a daily schedule). Off "
            "by default because schedules vary."
        ),
        elements={
            **_health_elements(),
            "levels_age": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on newest snapshot age"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ]
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(93600.0, 180000.0)),
                ),
            ),
        },
    )


rule_spec_dell_me5_snapshots = CheckParameters(
    name="dell_me5_snapshots",
    title=Title("Dell PowerVault ME5 snapshots"),
    topic=Topic.STORAGE,
    parameter_form=_form_snapshots,
    condition=HostAndItemCondition(item_title=Title("Source volume")),
)


# --------------------------------------------------------------------------- connected hosts
def _form_hosts() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 connected host"),
        help_text=Help(
            "Monitoring states for initiator connectivity. A host is discovered "
            "while connected; if it later reports disconnected or disappears "
            "from the initiator table the service raises."
        ),
        elements={
            "state_disconnected": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a discovered initiator is disconnected"),
                    prefill=DefaultValue(2),
                ),
            ),
            "state_missing": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a discovered initiator is no longer present"),
                    prefill=DefaultValue(2),
                ),
            ),
        },
    )


rule_spec_dell_me5_hosts = CheckParameters(
    name="dell_me5_hosts",
    title=Title("Dell PowerVault ME5 connected host"),
    topic=Topic.STORAGE,
    parameter_form=_form_hosts,
    condition=HostAndItemCondition(item_title=Title("Host")),
)
