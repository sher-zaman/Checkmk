#!/usr/bin/env python3
"""Check parameter rulesets for the Infoblox CSP special agent.

Author:  Sher Zaman (sher[at]sherz[dot]dev, https://sherz.dev)
Repo:    https://github.com/sher-zaman/Checkmk
License: GPL-2.0-only
"""

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
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)

TOPIC = Topic.APPLICATIONS


def _state(title, default, help_text=None):
    return DictElement(
        required=False,
        parameter_form=ServiceState(
            title=title,
            help_text=help_text,
            prefill=DefaultValue(default),
        ),
    )


def _age_levels(title, warn, crit, help_text=None):
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            help_text=help_text,
            form_spec_template=TimeSpan(
                displayed_magnitudes=[
                    TimeMagnitude.DAY,
                    TimeMagnitude.HOUR,
                    TimeMagnitude.MINUTE,
                ]
            ),
            level_direction=LevelDirection.UPPER,
            prefill_fixed_levels=DefaultValue(value=(warn, crit)),
        ),
    )


# ---------------------------------------------------------------------------
# Server status
# ---------------------------------------------------------------------------
def _form_host() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox NIOS-X server status"),
        elements={
            "last_seen_levels": _age_levels(
                Title("Age of the last check-in"),
                1800.0,
                3600.0,
                Help(
                    "The portal does not expose a dedicated last seen field, so "
                    "this uses the host record update timestamp. Observed lag "
                    "is four to eleven minutes even on healthy servers, so keep "
                    "these levels generous rather than treating it as a "
                    "heartbeat."
                ),
            ),
            "status_states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Map reported status to monitoring state"),
                    elements={
                        "online": _state(Title("online"), 0),
                        "degraded": _state(Title("degraded"), 1),
                        "pending": _state(Title("pending"), 1),
                        "awaiting_approval": _state(Title("awaiting approval"), 1),
                        "error": _state(Title("error"), 2),
                        "offline": _state(Title("offline"), 2),
                    },
                ),
            ),
        },
    )


rule_spec_infoblox_csp_host = CheckParameters(
    name="infoblox_csp_host",
    title=Title("Infoblox NIOS-X server status"),
    topic=TOPIC,
    parameter_form=_form_host,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Deployed services
# ---------------------------------------------------------------------------
def _form_service() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox deployed service status"),
        help_text=Help(
            "Applies to DNS, DHCP, DNS Forwarding Proxy, NTP, Data Connector "
            "and any other service deployed on a NIOS-X server."
        ),
        elements={
            "service_states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Map reported status to monitoring state"),
                    elements={
                        "started": _state(Title("started"), 0),
                        "starting": _state(Title("starting"), 1),
                        "stopping": _state(Title("stopping"), 1),
                        "stopped": _state(Title("stopped"), 2),
                        "error": _state(Title("error"), 2),
                    },
                ),
            ),
        },
    )


rule_spec_infoblox_csp_service = CheckParameters(
    name="infoblox_csp_service",
    title=Title("Infoblox deployed service status"),
    topic=TOPIC,
    parameter_form=_form_service,
    condition=HostAndItemCondition(item_title=Title("Service type")),
)


# ---------------------------------------------------------------------------
# Platform managed services
# ---------------------------------------------------------------------------
def _form_config() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox platform managed service status"),
        help_text=Help(
            "Applies to Platform Management and Application Management, which "
            "the portal reports separately from deployed services and with a "
            "different set of status values."
        ),
        elements={
            "config_states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Map reported status to monitoring state"),
                    elements={
                        "online": _state(Title("online"), 0),
                        "degraded": _state(Title("degraded"), 1),
                        "error": _state(Title("error"), 2),
                        "offline": _state(Title("offline"), 2),
                    },
                ),
            ),
        },
    )


rule_spec_infoblox_csp_config = CheckParameters(
    name="infoblox_csp_config",
    title=Title("Infoblox platform managed service status"),
    topic=TOPIC,
    parameter_form=_form_config,
    condition=HostAndItemCondition(item_title=Title("Service type")),
)


# ---------------------------------------------------------------------------
# DHCP high availability
# ---------------------------------------------------------------------------
_HA_NODE_HELP = Help(
    "These are Kea high availability state machine values. In hot standby mode "
    "both nodes report hot-standby during normal operation, so a passive node "
    "reporting it is healthy. The state that matters most is terminated: "
    "high availability has given up, both servers keep answering clients, and "
    "their lease databases diverge silently. Clock skew above sixty seconds is "
    "a common cause, which is why the NTP service on each server is worth "
    "watching alongside this."
)


def _ha_node_states() -> DictElement:
    return DictElement(
        required=False,
        parameter_form=Dictionary(
            title=Title("Map node state to monitoring state"),
            help_text=_HA_NODE_HELP,
            elements={
                "hot_standby": _state(Title("hot-standby"), 0),
                "load_balancing": _state(Title("load-balancing"), 0),
                "ready": _state(Title("ready"), 0),
                "backup": _state(Title("backup"), 0),
                "passive_backup": _state(Title("passive-backup"), 0),
                "waiting": _state(Title("waiting"), 1),
                "syncing": _state(Title("syncing"), 1),
                "in_maintenance": _state(Title("in-maintenance"), 1),
                "partner_in_maintenance": _state(Title("partner-in-maintenance"), 1),
                "communication_recovery": _state(Title("communication-recovery"), 2),
                "partner_down": _state(Title("partner-down"), 2),
                "terminated": _state(Title("terminated"), 2),
            },
        ),
    )


def _heartbeat_levels() -> DictElement:
    return _age_levels(
        Title("Age of the oldest peer heartbeat"),
        300.0,
        900.0,
        Help(
            "Kea exchanges heartbeats every ten seconds by default, but the "
            "value reaches Checkmk through the portal API, so allow for polling "
            "lag on top. IPv6 heartbeats reported as the epoch zero sentinel "
            "are ignored rather than counted as decades stale."
        ),
    )


def _form_ha_node() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox DHCP high availability node"),
        elements={
            "heartbeat_levels": _heartbeat_levels(),
            "node_states": _ha_node_states(),
        },
    )


rule_spec_infoblox_csp_ha_node = CheckParameters(
    name="infoblox_csp_ha_node",
    title=Title("Infoblox DHCP high availability node"),
    topic=TOPIC,
    parameter_form=_form_ha_node,
    condition=HostCondition(),
)


def _form_ha_group() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox DHCP high availability group"),
        elements={
            "heartbeat_levels": _heartbeat_levels(),
            "node_states": _ha_node_states(),
            "group_states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Map group status to monitoring state"),
                    elements={
                        "ok": _state(Title("ok"), 0),
                        "degraded": _state(Title("degraded"), 1),
                        "error": _state(Title("error"), 2),
                        "down": _state(Title("down"), 2),
                    },
                ),
            ),
        },
    )


rule_spec_infoblox_csp_ha_group = CheckParameters(
    name="infoblox_csp_ha_group",
    title=Title("Infoblox DHCP high availability group"),
    topic=TOPIC,
    parameter_form=_form_ha_group,
    condition=HostAndItemCondition(item_title=Title("HA group name")),
)


# ---------------------------------------------------------------------------
# IP utilisation, shared by ranges, subnets, address blocks and IP spaces
# ---------------------------------------------------------------------------
def _form_ip_utilization() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox IP address utilisation"),
        help_text=Help(
            "Applies to DHCP ranges, subnets, address blocks and IP spaces. "
            "Two separate level sets are used because objects containing no "
            "DHCP range are allocation records rather than pools. An ISP link "
            "allocation sits at one hundred percent by design, so alarming on "
            "it produces an alert nobody can clear. Whether an object contains "
            "a pool is derived from the parent reference on each DHCP range, "
            "with no extra API call."
        ),
        elements={
            "levels_pool": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Utilisation levels for objects with a DHCP pool"),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
                ),
            ),
            "levels_static": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Utilisation levels for allocation records"),
                    help_text=Help(
                        "Objects with no DHCP range inside them. Left unset by "
                        "default on purpose."
                    ),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(90.0, 98.0)),
                ),
            ),
            "free_levels_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on free address count"),
                    help_text=Help(
                        "A percentage alone treats a hundred address range and "
                        "a four thousand address range identically. At eighty "
                        "percent the first has twenty addresses left and the "
                        "second has eight hundred. An absolute floor catches "
                        "the small ranges that a percentage misses."
                    ),
                    form_spec_template=Integer(unit_symbol="addresses"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(value=(25, 10)),
                ),
            ),
            "abandoned_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Levels on abandoned address percentage"),
                    help_text=Help(
                        "Abandoned leases indicate address conflicts or "
                        "misbehaving clients rather than exhaustion, so they "
                        "get their own threshold."
                    ),
                    form_spec_template=Float(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(10.0, 25.0)),
                ),
            ),
        },
    )


rule_spec_infoblox_csp_ip_utilization = CheckParameters(
    name="infoblox_csp_ip_utilization",
    title=Title("Infoblox IP address utilisation"),
    topic=TOPIC,
    parameter_form=_form_ip_utilization,
    condition=HostAndItemCondition(item_title=Title("Range, subnet or IP space")),
)


# ---------------------------------------------------------------------------
# DNS
# ---------------------------------------------------------------------------
def _form_dns_zones() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox DNS zones"),
        elements={
            "disabled_state": _state(
                Title("State when zones are disabled"),
                1,
                Help("A disabled zone stops answering queries."),
            ),
            "warning_state": _state(
                Title("State when zones report warnings"),
                1,
                Help("Zone level warnings raised by Infoblox itself."),
            ),
        },
    )


rule_spec_infoblox_csp_dns_zones = CheckParameters(
    name="infoblox_csp_dns_zones",
    title=Title("Infoblox DNS zones"),
    topic=TOPIC,
    parameter_form=_form_dns_zones,
    condition=HostCondition(),
)


def _form_dns_view() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox DNS view configuration"),
        help_text=Help(
            "Asserts that DNSSEC settings on a view match what you expect. "
            "Leave an assertion unset to report the value without judging it."
        ),
        elements={
            "expect": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Expected settings"),
                    elements={
                        "dnssec_enabled": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("DNSSEC"),
                                elements=[
                                    SingleChoiceElement(
                                        name="enabled", title=Title("Enabled")
                                    ),
                                    SingleChoiceElement(
                                        name="disabled", title=Title("Disabled")
                                    ),
                                ],
                                prefill=DefaultValue("enabled"),
                            ),
                        ),
                        "dnssec_enable_validation": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("DNSSEC validation"),
                                elements=[
                                    SingleChoiceElement(
                                        name="enabled", title=Title("Enabled")
                                    ),
                                    SingleChoiceElement(
                                        name="disabled", title=Title("Disabled")
                                    ),
                                ],
                                prefill=DefaultValue("enabled"),
                            ),
                        ),
                        "dnssec_validate_expiry": DictElement(
                            required=False,
                            parameter_form=SingleChoice(
                                title=Title("DNSSEC expiry validation"),
                                elements=[
                                    SingleChoiceElement(
                                        name="enabled", title=Title("Enabled")
                                    ),
                                    SingleChoiceElement(
                                        name="disabled", title=Title("Disabled")
                                    ),
                                ],
                                prefill=DefaultValue("enabled"),
                            ),
                        ),
                    },
                ),
            ),
            "mismatch_state": _state(Title("State on a mismatch"), 1),
        },
    )


rule_spec_infoblox_csp_dns_view = CheckParameters(
    name="infoblox_csp_dns_view",
    title=Title("Infoblox DNS view configuration"),
    topic=TOPIC,
    parameter_form=_form_dns_view,
    condition=HostAndItemCondition(item_title=Title("DNS view")),
)


# ---------------------------------------------------------------------------
# Threat Defense
# ---------------------------------------------------------------------------
def _form_security_policy() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox security policy"),
        elements={
            "expected_default_action": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Expected default action"),
                    help_text=Help(
                        "For example action_allow or action_block. Leave unset "
                        "to report the value without judging it."
                    ),
                ),
            ),
            "mismatch_state": _state(Title("State on a mismatch"), 1),
            "legacy_feed_state": _state(
                Title("State when the policy references legacy feeds"), 1
            ),
        },
    )


rule_spec_infoblox_csp_security_policy = CheckParameters(
    name="infoblox_csp_security_policy",
    title=Title("Infoblox security policy"),
    topic=TOPIC,
    parameter_form=_form_security_policy,
    condition=HostAndItemCondition(item_title=Title("Security policy")),
)


def _form_threat_feeds() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox threat feeds"),
        elements={
            "expected_minimum": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Expected minimum number of feeds"),
                    help_text=Help(
                        "Catches feeds being removed from a tenant. Leave unset "
                        "to report the count without judging it."
                    ),
                    prefill=DefaultValue(1),
                ),
            ),
            "shortfall_state": _state(Title("State when below the minimum"), 1),
            "legacy_state": _state(
                Title("State when legacy feeds are present"),
                0,
                Help(
                    "Legacy feeds still function. Raise this if you are "
                    "migrating away from them and want visibility."
                ),
            ),
        },
    )


rule_spec_infoblox_csp_threat_feeds = CheckParameters(
    name="infoblox_csp_threat_feeds",
    title=Title("Infoblox threat feeds"),
    topic=TOPIC,
    parameter_form=_form_threat_feeds,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Tenant rollups
# ---------------------------------------------------------------------------
def _form_hosts_summary() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox tenant host rollup"),
        elements={
            "not_online_state": _state(
                Title("State when any server is not online"), 2
            ),
        },
    )


rule_spec_infoblox_csp_hosts_summary = CheckParameters(
    name="infoblox_csp_hosts_summary",
    title=Title("Infoblox tenant host rollup"),
    topic=TOPIC,
    parameter_form=_form_hosts_summary,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Service availability per type
# ---------------------------------------------------------------------------
def _form_service_availability() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox service availability by type"),
        help_text=Help(
            "One service per deployed service type, showing how many instances "
            "of it are online across the whole tenant. This mirrors the Service "
            "Availability tile in the portal dashboard and complements the per "
            "server checks, which each see one instance and cannot express "
            "'DNS is fine on one node and down on the other'."
        ),
        elements={
            "degraded_state": _state(
                Title("State when any instance of the type is not online"),
                2,
            ),
            "desired_state_mismatch": _state(
                Title("State when an instance is not in its desired state"),
                1,
                Help("An instance asked to run that is not, or the reverse."),
            ),
            "version_mismatch_state": _state(
                Title("State when instances run different versions"),
                0,
                Help(
                    "Infoblox applies updates asynchronously, so instances of "
                    "the same type routinely differ for a short window during a "
                    "rollout. Defaults to OK for that reason."
                ),
            ),
        },
    )


rule_spec_infoblox_csp_service_availability = CheckParameters(
    name="infoblox_csp_service_availability",
    title=Title("Infoblox service availability by type"),
    topic=TOPIC,
    parameter_form=_form_service_availability,
    condition=HostAndItemCondition(item_title=Title("Service type")),
)


# ---------------------------------------------------------------------------
# External networks
# ---------------------------------------------------------------------------
def _form_external_network() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox external networks"),
        help_text=Help(
            "External networks are the public address ranges registered against "
            "the tenant so that queries arriving from them are attributed to "
            "it. An address whose approval has not completed is registered but "
            "not yet in effect, which is why this is a check rather than pure "
            "inventory."
        ),
        elements={
            "unapproved_state": _state(
                Title("State when an address is not approved"),
                1,
                Help(
                    "Approval statuses treated as approved are AUTO_VERIFIED, "
                    "VERIFIED and APPROVED. Anything else counts as pending."
                ),
            ),
            "expected_minimum": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Expected minimum number of networks"),
                    help_text=Help(
                        "Catches a network list being deleted. Leave unset to "
                        "report the count without judging it."
                    ),
                    prefill=DefaultValue(1),
                ),
            ),
            "shortfall_state": _state(Title("State when below the minimum"), 1),
        },
    )


rule_spec_infoblox_csp_external_network = CheckParameters(
    name="infoblox_csp_external_network",
    title=Title("Infoblox external networks"),
    topic=TOPIC,
    parameter_form=_form_external_network,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Active DNS Forwarding Proxies
# ---------------------------------------------------------------------------
def _form_dfp_summary() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox active DNS Forwarding Proxies"),
        help_text=Help(
            "Counts how many configured proxies are actually running, by "
            "correlating the proxy configurations against the tenant service "
            "list. A proxy can be fully configured while the service on its "
            "server is stopped."
        ),
        elements={
            "inactive_state": _state(
                Title("State when a configured proxy is not active"), 2
            ),
            "expected_forwarding_policy": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Expected forwarding policy"),
                    help_text=Help(
                        "Asserted across every proxy, so a single "
                        "misconfigured one is visible. For example "
                        "ib_cloud_first. Leave unset to report the policies in "
                        "use without judging them."
                    ),
                ),
            ),
            "mismatch_state": _state(
                Title("State when a proxy has an unexpected forwarding policy"), 1
            ),
        },
    )


rule_spec_infoblox_csp_dfp_summary = CheckParameters(
    name="infoblox_csp_dfp_summary",
    title=Title("Infoblox active DNS Forwarding Proxies"),
    topic=TOPIC,
    parameter_form=_form_dfp_summary,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Anycast
# ---------------------------------------------------------------------------
_ANYCAST_STATUS_HELP = Help(
    "Infoblox reports Active, Degraded or Inactive. Any other value is "
    "reported as UNKNOWN rather than guessed at."
)


def _anycast_status_states() -> DictElement:
    return DictElement(
        required=False,
        parameter_form=Dictionary(
            title=Title("Map reported status to monitoring state"),
            help_text=_ANYCAST_STATUS_HELP,
            elements={
                "active": _state(Title("Active"), 0),
                "degraded": _state(Title("Degraded"), 1),
                "inactive": _state(Title("Inactive"), 2),
            },
        ),
    )


def _form_anycast() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox anycast configuration"),
        help_text=Help(
            "Anycast exists so that losing one advertiser is survivable, so the "
            "operational question is how many advertisers remain rather than "
            "whether the configuration is nominally healthy. This check counts "
            "advertising member hosts itself, because the reported status does "
            "not distinguish losing one member from losing all but one. "
            "Note the boundary of what can be verified here. The portal reports "
            "whether it believes a host is advertising a route. It does not "
            "prove the route reached the upstream router, nor that clients can "
            "reach the anycast address. Pair this with an active DNS check "
            "against the anycast address to confirm the path end to end."
        ),
        elements={
            "reduced_redundancy_state": _state(
                Title("State when some but not all hosts are advertising"),
                1,
                Help(
                    "Service continues, redundancy is reduced. Worth knowing "
                    "before the last advertiser goes too."
                ),
            ),
            "no_active_state": _state(
                Title("State when no host is advertising"),
                2,
                Help("The anycast address is unreachable through this configuration."),
            ),
            "minimum_active": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Minimum advertising hosts required"),
                    help_text=Help(
                        "Set this where a specific number of advertisers is "
                        "needed to carry the load, rather than merely more than "
                        "zero. Leave unset to use the full membership as the "
                        "expected count."
                    ),
                    unit_symbol="hosts",
                    prefill=DefaultValue(2),
                ),
            ),
            "below_minimum_state": _state(
                Title("State when below the required minimum"), 2
            ),
            "unconfigured_state": _state(
                Title("State when the configuration has not been applied"),
                1,
                Help(
                    "A configuration can exist without having been pushed to "
                    "its hosts, in which case nothing is being advertised."
                ),
            ),
            "status_states": _anycast_status_states(),
        },
    )


rule_spec_infoblox_csp_anycast = CheckParameters(
    name="infoblox_csp_anycast",
    title=Title("Infoblox anycast configuration"),
    topic=TOPIC,
    parameter_form=_form_anycast,
    condition=HostAndItemCondition(item_title=Title("Anycast configuration")),
)


def _form_anycast_node() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox anycast node"),
        help_text=Help(
            "One service per anycast configuration a NIOS-X server belongs to, "
            "reporting whether that particular server is advertising. A server "
            "can be a member of several configurations, for example one "
            "fronting DNS and another fronting DNS forwarding, and each is "
            "reported separately."
        ),
        elements={
            "status_states": _anycast_status_states(),
            "config_status_state": _state(
                Title("State applied to the configuration wide status"),
                0,
                Help(
                    "The overall status of the configuration is shown here for "
                    "context and defaults to not affecting this service, since "
                    "the tenant level anycast check already alerts on it."
                ),
            ),
        },
    )


rule_spec_infoblox_csp_anycast_node = CheckParameters(
    name="infoblox_csp_anycast_node",
    title=Title("Infoblox anycast node"),
    topic=TOPIC,
    parameter_form=_form_anycast_node,
    condition=HostAndItemCondition(item_title=Title("Anycast configuration")),
)
