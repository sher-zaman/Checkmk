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
# Checkmk Filesystem and Temperature rules apply to the array out of the box.
#
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
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


def _throughput_element(title: Title) -> DictElement:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            form_spec_template=Float(unit_symbol="B/s"),
            level_direction=LevelDirection.UPPER,
            prefill_fixed_levels=DefaultValue(value=(1e9, 1.15e9)),
        ),
    )


def _iops_element(title: Title) -> DictElement:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            form_spec_template=Integer(unit_symbol="IO/s"),
            level_direction=LevelDirection.UPPER,
            prefill_fixed_levels=DefaultValue(value=(50000, 100000)),
        ),
    )


def _latency_element(title: Title) -> DictElement:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            form_spec_template=TimeSpan(
                displayed_magnitudes=[TimeMagnitude.MILLISECOND, TimeMagnitude.SECOND]
            ),
            level_direction=LevelDirection.UPPER,
            prefill_fixed_levels=DefaultValue(value=(0.02, 0.05)),
        ),
    )


# --------------------------------------------------------------------------- system health
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
            "Monitoring states for host port health and link status, and "
            "optional upper levels on the port's I/O statistics. A link status "
            "other than Up is Critical by default; for ports that are "
            "intentionally uncabled, add a rule scoped to those ports and set "
            "the link status state to OK. The I/O levels are off by default; "
            "throughput and IOPS are graphed for trending regardless."
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
            "levels_throughput": _throughput_element(Title("Upper levels on throughput")),
            "levels_iops": _iops_element(Title("Upper levels on IOPS")),
            "levels_latency": _latency_element(Title("Upper levels on average response time")),
            "levels_queue": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on queue depth"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(32, 64)),
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
            "verify or scrub is normal maintenance and stays informational; a "
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
            "optional levels on the thin-provisioned fill ratio, the volume's "
            "I/O statistics and its cache hit ratios. All levels are off by "
            "default; the values are graphed for trending regardless."
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
            "levels_throughput": _throughput_element(Title("Upper levels on throughput")),
            "levels_iops": _iops_element(Title("Upper levels on IOPS")),
            "levels_read_hit": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on read cache hit ratio"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(30.0, 10.0)),
                ),
            ),
            "levels_write_hit": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on write cache hit ratio"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(30.0, 10.0)),
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
            "Monitoring states for disk health and error conditions, the "
            "predictive error counters, and optional levels on remaining SSD "
            "life and I/O statistics. The predictive counters (SMART events, "
            "media errors, bad blocks, block reassignments, spin-up retries, "
            "I/O timeouts and no-response events) raise when they increase "
            "between checks. Non-media errors are reported but not alerted by "
            "default, because low non-zero values are normal."
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
            "state_errors_increasing": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a predictive error counter increases"),
                    prefill=DefaultValue(1),
                ),
            ),
            "monitor_nonmedia_errors": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Also alert on increasing non-media errors"),
                    prefill=DefaultValue(False),
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
            "levels_throughput": _throughput_element(Title("Upper levels on throughput")),
            "levels_iops": _iops_element(Title("Upper levels on IOPS")),
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


# --------------------------------------------------------------------------- sensors
def _form_sensor() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 sensor"),
        help_text=Help(
            "Monitoring state for the power-supply electrical sensors, grouped "
            "by type (voltage and current). One service per type aggregates all "
            "sensors of that type and raises if any single sensor reports a "
            "status other than OK, naming the sensor concerned."
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


# --------------------------------------------------------------------------- supercapacitor
def _form_supercapacitor() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 supercapacitor"),
        help_text=Help(
            "Monitoring state for a controller's cache-protection "
            "supercapacitor pack: charge level, capacitance, internal "
            "resistance, pack voltage and the individual cell voltages. The "
            "service raises if any of those sensors reports a status other than "
            "OK. Optional lower levels on the charge level are available and "
            "off by default, since the array reports a fault itself when the "
            "pack cannot protect the cache."
        ),
        elements={
            "state_not_ok": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when any supercapacitor sensor is not OK"),
                    prefill=DefaultValue(1),
                ),
            ),
            "levels_charge": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on charge level"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(90.0, 75.0)),
                ),
            ),
        },
    )


rule_spec_dell_me5_supercapacitor = CheckParameters(
    name="dell_me5_supercapacitor",
    title=Title("Dell PowerVault ME5 supercapacitor"),
    topic=Topic.STORAGE,
    parameter_form=_form_supercapacitor,
    condition=HostAndItemCondition(item_title=Title("Controller")),
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
def _schedule_elements() -> dict[str, DictElement]:
    """Conditions for a snapshot schedule."""
    return {
        "state_not_ready": DictElement(
            required=False,
            parameter_form=ServiceState(
                title=Title("State when the schedule status is not Ready"),
                prefill=DefaultValue(1),
            ),
        ),
        "state_error": DictElement(
            required=False,
            parameter_form=ServiceState(
                title=Title("State when the schedule reports an error"),
                prefill=DefaultValue(1),
            ),
        ),
        "state_overdue": DictElement(
            required=False,
            parameter_form=ServiceState(
                title=Title("State when the next scheduled run is overdue"),
                prefill=DefaultValue(0),
            ),
        ),
    }


def _form_snapshots() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 snapshots"),
        help_text=Help(
            "One service per source volume covers both the volume's snapshots "
            "and the schedule that creates them, so a single service shows "
            "whether the volume is protected and whether protection is still "
            "running.\n\n"
            "The overdue state is OK by default, so arrays with abandoned or "
            "unbound schedules stay quiet; set it to Warning or Critical to "
            "alert when a schedule that should be running has stalled. The "
            "snapshot age levels are off by default and provide the same "
            "protection from the snapshot side (for example 26 hours warning "
            "and 50 hours critical for a daily schedule)."
        ),
        elements={
            "state_not_available": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a snapshot is not available"),
                    prefill=DefaultValue(1),
                ),
            ),
            "state_no_snapshots": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a schedule exists but there are no snapshots"),
                    prefill=DefaultValue(1),
                ),
            ),
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
            **_schedule_elements(),
        },
    )


rule_spec_dell_me5_snapshots = CheckParameters(
    name="dell_me5_snapshots",
    title=Title("Dell PowerVault ME5 snapshots"),
    topic=Topic.STORAGE,
    parameter_form=_form_snapshots,
    condition=HostAndItemCondition(item_title=Title("Source volume")),
)


# --------------------------------------------------------------------------- snapshot schedules
def _form_schedules() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 schedule"),
        help_text=Help(
            "Monitoring states for a schedule that is not tied to a specific "
            "volume. Schedules that create snapshots for a volume are reported "
            "by that volume's snapshots service instead. The overdue state is "
            "OK by default; set it to Warning or Critical to alert when a "
            "schedule that should be running has stalled."
        ),
        elements={**_schedule_elements()},
    )


rule_spec_dell_me5_schedules = CheckParameters(
    name="dell_me5_schedules",
    title=Title("Dell PowerVault ME5 schedule"),
    topic=Topic.STORAGE,
    parameter_form=_form_schedules,
    condition=HostAndItemCondition(item_title=Title("Schedule")),
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


# --------------------------------------------------------------------------- system performance
def _form_system_performance() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 system performance"),
        help_text=Help(
            "Optional upper levels on array-wide IOPS, throughput and average "
            "response time. All are off by default; the values, including the "
            "read and write split, are graphed for performance and capacity "
            "trending."
        ),
        elements={
            "levels_iops": _iops_element(Title("Upper levels on system IOPS")),
            "levels_throughput": _throughput_element(Title("Upper levels on system throughput")),
            "levels_latency": _latency_element(
                Title("Upper levels on system average response time")
            ),
        },
    )


rule_spec_dell_me5_system_performance = CheckParameters(
    name="dell_me5_system_performance",
    title=Title("Dell PowerVault ME5 system performance"),
    topic=Topic.STORAGE,
    parameter_form=_form_system_performance,
    condition=HostCondition(),
)


# --------------------------------------------------------------------------- health alerts
def _form_alerts() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 health alerts"),
        help_text=Help(
            "Monitoring states for the array's unresolved health alerts. "
            "Informational alerts are ignored; only unresolved critical and "
            "warning alerts are reported, with the affected component, the "
            "reason and the array's recommended action in the service details."
        ),
        elements={
            "state_critical": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when unresolved critical alerts exist"),
                    prefill=DefaultValue(2),
                ),
            ),
            "state_warning": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when unresolved warning alerts exist"),
                    prefill=DefaultValue(1),
                ),
            ),
        },
    )


rule_spec_dell_me5_alerts = CheckParameters(
    name="dell_me5_alerts",
    title=Title("Dell PowerVault ME5 health alerts"),
    topic=Topic.STORAGE,
    parameter_form=_form_alerts,
    condition=HostCondition(),
)


# --------------------------------------------------------------------------- enclosures
def _form_enclosures() -> Dictionary:
    return Dictionary(
        title=Title("Dell PowerVault ME5 enclosure"),
        help_text=Help(
            "Monitoring states for enclosure health and status, plus optional "
            "upper levels on enclosure power draw. Power is graphed regardless."
        ),
        elements={
            **_health_elements(),
            "state_not_ok": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the enclosure status is not OK"),
                    prefill=DefaultValue(2),
                ),
            ),
            "levels_power": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on enclosure power draw"),
                    form_spec_template=Float(unit_symbol="W"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(500.0, 600.0)),
                ),
            ),
        },
    )


rule_spec_dell_me5_enclosures = CheckParameters(
    name="dell_me5_enclosures",
    title=Title("Dell PowerVault ME5 enclosure"),
    topic=Topic.STORAGE,
    parameter_form=_form_enclosures,
    condition=HostAndItemCondition(item_title=Title("Enclosure")),
)
