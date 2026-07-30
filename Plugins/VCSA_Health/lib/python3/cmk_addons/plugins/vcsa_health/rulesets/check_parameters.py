#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Check parameter rulesets for the VCSA health plugin.
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    SingleChoice,
    SingleChoiceElement,
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
            "steal_levels": _percent_levels(
                Title("Upper levels on CPU steal"), (5.0, 10.0)
            ),
            "page_rate_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on swap page rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="pages/s"),
                    prefill_fixed_levels=DefaultValue((100.0, 1000.0)),
                ),
            ),
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
            "apply_levels_to_archive": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Also apply these levels to the archive filesystem"),
                    help_text=Help(
                        "The archive filesystem is designed to fill and is "
                        "documented as safe to ignore when high, so it is "
                        "excluded from levels by default. Enable this to apply "
                        "the levels above to it as well."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
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
            "hostname_mismatch": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Appliance hostname not present in the certificate"),
                    help_text=Help(
                        "Clients connecting by the appliance hostname get a "
                        "certificate warning when the hostname appears in "
                        "neither the common name nor the subject alternative "
                        "names."
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
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


def _parameter_form_update():
    return Dictionary(
        title=Title("VCSA update status"),
        help_text=Help(
            "Thresholds for the age of the last update repository check of "
            "the vCenter Server Appliance. An appliance that has stopped "
            "checking the repository keeps reporting that it is up to date, "
            "so a stale check hides pending updates rather than being a "
            "harmless detail."
        ),
        elements={
            "last_check_age": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Maximum age of the last update check"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY, TimeMagnitude.HOUR]
                    ),
                    prefill_fixed_levels=DefaultValue((1209600.0, 2592000.0)),
                ),
            ),
        },
    )


rule_spec_vcsa_health_update = CheckParameters(
    name="vcsa_health_update",
    title=Title("VCSA update status"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_update,
    condition=HostCondition(),
)


def _parameter_form_certs():
    return Dictionary(
        title=Title("VCSA signing and trusted root certificates"),
        help_text=Help(
            "Thresholds for the remaining validity of the signing certificate "
            "and the trusted root chain certificates of the vCenter Server "
            "Appliance. These certificates expire on their own schedules, "
            "independently of the machine TLS certificate."
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


rule_spec_vcsa_health_certs = CheckParameters(
    name="vcsa_health_certs",
    title=Title("VCSA signing and trusted root certificates"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_certs,
    condition=HostAndItemCondition(item_title=Title("Certificate")),
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


def _parameter_form_timesync():
    return Dictionary(
        title=Title("VCSA time synchronization"),
        help_text=Help(
            "Configures the monitoring states for the time synchronization "
            "status of the vCenter Server Appliance. Accurate time is required "
            "for single sign-on token validation and certificate checks."
        ),
        elements={
            "mode_disabled": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Time synchronization disabled"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "no_servers": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("No NTP server configured"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "none_reachable": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("No configured NTP server reachable"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "some_unreachable": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Some NTP servers unreachable"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "drift_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on measured clock drift"),
                    help_text=Help(
                        "Drift is measured against the Checkmk server clock and "
                        "compared as a magnitude, so an appliance running fast "
                        "is treated the same as one running slow."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="s"),
                    prefill_fixed_levels=DefaultValue((30.0, 300.0)),
                ),
            ),
        },
    )


rule_spec_vcsa_health_timesync = CheckParameters(
    name="vcsa_health_timesync",
    title=Title("VCSA time synchronization"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_timesync,
    condition=HostCondition(),
)


def _parameter_form_local_accounts():
    return Dictionary(
        title=Title("VCSA root password expiry"),
        help_text=Help(
            "Thresholds for the remaining validity of the root account "
            "password of the vCenter Server Appliance. An expired root "
            "password locks administrators out of the appliance."
        ),
        elements={
            "expiry_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Minimum remaining time before expiry"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY]
                    ),
                    prefill_fixed_levels=DefaultValue((1209600.0, 604800.0)),
                ),
            ),
            "never_expires": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Root password does not expire"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
        },
    )


rule_spec_vcsa_health_local_accounts = CheckParameters(
    name="vcsa_health_local_accounts",
    title=Title("VCSA root password expiry"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_local_accounts,
    condition=HostCondition(),
)


def _parameter_form_interfaces():
    return Dictionary(
        title=Title("VCSA network interfaces"),
        help_text=Help(
            "Configures the monitoring state for the link status and the "
            "thresholds for packet errors and drops on the network interfaces "
            "of the vCenter Server Appliance. Error and drop values are "
            "per-sample counts reported by the appliance monitoring API."
        ),
        elements={
            "link_down": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Interface link is down"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "error_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on packet errors"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue((10.0, 100.0)),
                ),
            ),
            "drop_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels on dropped packets"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue((10.0, 100.0)),
                ),
            ),
            "expected_address_mode": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Expected IPv4 address mode"),
                    help_text=Help(
                        "Both static and DHCP addressing are legitimate, so no "
                        "expectation is set by default. Choose one to detect an "
                        "appliance whose addressing has changed."
                    ),
                    elements=[
                        SingleChoiceElement(name="any", title=Title("No expectation")),
                        SingleChoiceElement(name="STATIC", title=Title("Static")),
                        SingleChoiceElement(name="DHCP", title=Title("DHCP")),
                    ],
                    prefill=DefaultValue("any"),
                ),
            ),
            "mode_deviation_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Address mode differs from the expectation"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_vcsa_health_interfaces = CheckParameters(
    name="vcsa_health_interfaces",
    title=Title("VCSA network interfaces"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_interfaces,
    condition=HostAndItemCondition(item_title=Title("Interface")),
)


def _parameter_form_dns():
    return Dictionary(
        title=Title("VCSA DNS configuration"),
        help_text=Help(
            "Configures the monitoring state when the vCenter Server "
            "Appliance has no DNS server configured. Name resolution "
            "failures on vCenter cause widespread and confusing errors."
        ),
        elements={
            "no_servers": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("No DNS server configured"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_vcsa_health_dns = CheckParameters(
    name="vcsa_health_dns",
    title=Title("VCSA DNS configuration"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_dns,
    condition=HostCondition(),
)


def _expected_access_choice(title, help_text):
    return DictElement(
        required=False,
        parameter_form=SingleChoice(
            title=title,
            help_text=help_text,
            elements=[
                SingleChoiceElement(name="any", title=Title("No expectation")),
                SingleChoiceElement(name="enabled", title=Title("Should be enabled")),
                SingleChoiceElement(name="disabled", title=Title("Should be disabled")),
            ],
            prefill=DefaultValue("any"),
        ),
    )


def _parameter_form_access():
    return Dictionary(
        title=Title("VCSA access settings"),
        help_text=Help(
            "Whether SSH, the direct console interface, the BASH shell and the "
            "console CLI should be enabled is a site policy decision rather "
            "than a universal one, so no expectation is set by default and the "
            "service reports the current state as OK. Declare the expected "
            "state per method to detect configuration drift."
        ),
        elements={
            "expected_ssh": _expected_access_choice(
                Title("Expected SSH state"), Help("SSH access to the appliance.")
            ),
            "expected_dcui": _expected_access_choice(
                Title("Expected DCUI state"),
                Help("Direct Console User Interface access."),
            ),
            "expected_shell": _expected_access_choice(
                Title("Expected BASH shell state"),
                Help("BASH shell access from within the appliance shell."),
            ),
            "expected_consolecli": _expected_access_choice(
                Title("Expected console CLI state"),
                Help("Console-based controlled CLI access."),
            ),
            "deviation_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when a method deviates from the expectation"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_vcsa_health_access = CheckParameters(
    name="vcsa_health_access",
    title=Title("VCSA access settings"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_access,
    condition=HostCondition(),
)


def _parameter_form_proxy():
    return Dictionary(
        title=Title("VCSA proxy configuration"),
        help_text=Help(
            "The service is only discovered on appliances that have a proxy "
            "enabled. A broken or changed proxy stops the appliance reaching "
            "the update repository, so the configuration is worth watching "
            "where one is in use."
        ),
        elements={
            "expected_state": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Expected proxy state"),
                    elements=[
                        SingleChoiceElement(name="any", title=Title("No expectation")),
                        SingleChoiceElement(
                            name="disabled", title=Title("No proxy should be enabled")
                        ),
                    ],
                    prefill=DefaultValue("any"),
                ),
            ),
            "deviation_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State when the proxy deviates from the expectation"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_vcsa_health_proxy = CheckParameters(
    name="vcsa_health_proxy",
    title=Title("VCSA proxy configuration"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_proxy,
    condition=HostCondition(),
)


def _parameter_form_syslog():
    return Dictionary(
        title=Title("VCSA syslog forwarding"),
        help_text=Help(
            "The service is only discovered on appliances that have at least "
            "one forwarding target, so an appliance that never forwarded logs "
            "gets no service. Where forwarding is required, set the state "
            "below so that losing the last target raises an alarm."
        ),
        elements={
            "no_targets": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("No forwarding target configured"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
        },
    )


rule_spec_vcsa_health_syslog = CheckParameters(
    name="vcsa_health_syslog",
    title=Title("VCSA syslog forwarding"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_syslog,
    condition=HostCondition(),
)


def _parameter_form_shutdown():
    return Dictionary(
        title=Title("VCSA pending shutdown"),
        help_text=Help(
            "Monitoring state when a shutdown or reboot has been scheduled on "
            "the appliance."
        ),
        elements={
            "pending_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("A shutdown or reboot is pending"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_vcsa_health_shutdown = CheckParameters(
    name="vcsa_health_shutdown",
    title=Title("VCSA pending shutdown"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_shutdown,
    condition=HostCondition(),
)


def _db_levels(title):
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            level_direction=LevelDirection.UPPER,
            form_spec_template=Float(unit_symbol="%"),
            prefill_fixed_levels=DefaultValue((60.0, 80.0)),
        ),
    )


def _parameter_form_database():
    return Dictionary(
        title=Title("VCSA database usage"),
        help_text=Help(
            "Levels on the vCenter database usage reported per category. No "
            "levels are applied by default: the appliance does not document "
            "what the reported percentage is relative to, so a shipped "
            "threshold would be arbitrary. The metrics are collected and "
            "graphed regardless, so levels can be chosen once the values have "
            "been observed over time."
        ),
        elements={
            "stats_levels": _db_levels(Title("Upper levels on statistics usage")),
            "events_levels": _db_levels(Title("Upper levels on events usage")),
            "alarms_levels": _db_levels(Title("Upper levels on alarms usage")),
            "tasks_levels": _db_levels(Title("Upper levels on tasks usage")),
        },
    )


rule_spec_vcsa_health_database = CheckParameters(
    name="vcsa_health_database",
    title=Title("VCSA database usage"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_database,
    condition=HostCondition(),
)


def _parameter_form_vcha():
    return Dictionary(
        title=Title("VCSA High Availability cluster"),
        help_text=Help(
            "Monitoring states for the vCenter High Availability cluster. The "
            "service is only discovered on appliances where VCHA is "
            "configured. Where the appliance reports a state that is not "
            "recognised, the service reports UNKNOWN rather than inferring "
            "health."
        ),
        elements={
            "degraded_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Cluster in maintenance or configuring mode"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "disabled_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Cluster disabled"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "node_down_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("A cluster node is not up"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_vcsa_health_vcha = CheckParameters(
    name="vcsa_health_vcha",
    title=Title("VCSA High Availability cluster"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_vcha,
    condition=HostCondition(),
)


def _parameter_form_replication():
    return Dictionary(
        title=Title("VCSA replication"),
        help_text=Help(
            "Monitoring state for Enhanced Linked Mode replication. The "
            "service is only discovered on appliances that actually have "
            "replication partners, so standalone deployments get no service."
        ),
        elements={
            "partner_unavailable_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("A replication partner is unavailable"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_vcsa_health_replication = CheckParameters(
    name="vcsa_health_replication",
    title=Title("VCSA replication"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_replication,
    condition=HostCondition(),
)


def _parameter_form_appliance():
    return Dictionary(
        title=Title("VCSA appliance health areas"),
        help_text=Help(
            "Maps the health colours reported by the appliance to monitoring "
            "states. The appliance reports green, yellow, orange, red or gray "
            "for each health area."
        ),
        elements={
            "green": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Status green"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "yellow": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Status yellow"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "orange": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Status orange"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "red": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Status red"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "gray": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("Status gray"),
                    prefill=DefaultValue(ServiceState.UNKNOWN),
                ),
            ),
        },
    )


rule_spec_vcsa_health_appliance = CheckParameters(
    name="vcsa_health_appliance",
    title=Title("VCSA appliance health areas"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_appliance,
    condition=HostAndItemCondition(item_title=Title("Health area")),
)
