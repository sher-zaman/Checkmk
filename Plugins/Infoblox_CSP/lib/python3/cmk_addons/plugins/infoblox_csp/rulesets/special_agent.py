#!/usr/bin/env python3
"""Special agent ruleset for the Infoblox Cloud Services Portal.

Author:  Sher Zaman (sher[at]sherz[dot]dev, https://sherz.dev)
Repo:    https://github.com/sher-zaman/Checkmk
License: GPL-2.0-only
"""

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    String,
    migrate_to_password,
)
from cmk.rulesets.v1.form_specs.validators import (
    LengthInRange,
    MatchRegex,
    NumberInRange,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _form_special_agent() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox Cloud Services Portal (CSP)"),
        help_text=Help(
            "Collects NIOS-X server health, DDI service state, DHCP high "
            "availability and IPAM utilisation from the Infoblox Cloud "
            "Services Portal REST API. Each NIOS-X server is reported as a "
            "piggyback host, so a Checkmk host must exist for every server "
            "with a name matching its display name in the portal."
        ),
        elements={
            "api_key": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("API key"),
                    help_text=Help(
                        "A user or service API key from the portal. The key "
                        "inherits the role of the account it belongs to, so a "
                        "read only account is sufficient and recommended."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "base_url": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Realm base URL"),
                    help_text=Help(
                        "Leave unset for the United States realm. Other realms "
                        "use a different host name, for example "
                        "https://csp.eu.infoblox.com"
                    ),
                    prefill=DefaultValue("https://csp.infoblox.com"),
                    custom_validate=(
                        MatchRegex(
                            regex=r"^https://[A-Za-z0-9.-]+/?$",
                            error_msg=Message(
                                "Enter an https URL with no path, "
                                "for example https://csp.infoblox.com"
                            ),
                        ),
                    ),
                ),
            ),
            "host_prefix": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Piggyback host name prefix"),
                    help_text=Help(
                        "Prepended to every piggyback host name. Useful when a "
                        "single site monitors more than one tenant, because "
                        "server display names are not guaranteed unique across "
                        "tenants and identical names would silently merge into "
                        "one host. Include the separator, for example "
                        "'alector-'. Changing this later renames every "
                        "piggyback host and orphans its services and history, "
                        "so treat it as a set once decision. Checkmk also "
                        "offers a more capable native alternative in the Host "
                        "name translation for piggybacked hosts rule set, "
                        "under Setup, Agents, Agent access rules, which "
                        "supports regular expressions, domain stripping and "
                        "explicit mapping. Use whichever suits; this field "
                        "exists because applying the prefix in the agent means "
                        "the piggyback files are written with the final name."
                    ),
                    custom_validate=(
                        LengthInRange(max_value=32),
                        MatchRegex(
                            regex=r"^[A-Za-z0-9._-]*$",
                            error_msg=Message(
                                "Only letters, digits, dot, underscore "
                                "and hyphen are allowed"
                            ),
                        ),
                    ),
                ),
            ),
            "config_ttl": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Configuration cache lifetime"),
                    help_text=Help(
                        "Health endpoints are queried on every cycle and are "
                        "never cached. Configuration and inventory endpoints, "
                        "such as DNS zones, security policies and threat "
                        "feeds, are queried on this interval and emitted as "
                        "cached sections. Raise it on large tenants, lower it "
                        "while making configuration changes. Set to 0 to query "
                        "everything on every cycle."
                    ),
                    unit_symbol="s",
                    prefill=DefaultValue(3600),
                    custom_validate=(NumberInRange(min_value=0, max_value=86400),),
                ),
            ),
            "skip_config_tier": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Health endpoints only"),
                    label=Label("Skip all configuration and inventory endpoints"),
                    help_text=Help(
                        "Reduces the agent to five API calls per cycle. "
                        "Services derived from configuration endpoints will go "
                        "stale and then vanish on the next discovery."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Per request timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(30),
                    custom_validate=(NumberInRange(min_value=1, max_value=300),),
                ),
            ),
            "no_cert_check": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Disable certificate verification"),
                    label=Label("Do not verify the TLS certificate"),
                    help_text=Help(
                        "Only needed behind an intercepting proxy. The portal "
                        "presents a publicly trusted certificate, so leaving "
                        "verification enabled is correct in almost all cases."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


rule_spec_infoblox_csp = SpecialAgent(
    name="infoblox_csp",
    title=Title("Infoblox Cloud Services Portal (CSP)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_special_agent,
)
