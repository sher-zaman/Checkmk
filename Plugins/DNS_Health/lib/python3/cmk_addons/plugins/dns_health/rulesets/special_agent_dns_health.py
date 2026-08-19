#!/usr/bin/env python3
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    String,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("DNS Health"),
        help_text=Help(
            "Queries a domain's authoritative nameservers directly and reports "
            "record contents and delegation consistency. The nameserver list is "
            "taken from the parent zone's delegation rather than from the domain "
            "itself, so an altered NS record cannot redirect the check to servers "
            "of its own choosing. No agent is deployed on any host."
        ),
        elements={
            "domain": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Domain"),
                    help_text=Help(
                        "Leave empty to use the host name, which is the normal "
                        "arrangement: one host per monitored domain."
                    ),
                    field_size=FieldSize.MEDIUM,
                    prefill=DefaultValue(""),
                ),
            ),
            "record_types": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Record types to monitor"),
                    help_text=Help(
                        "One service is created per selected type. CNAME and PTR "
                        "are off by default because neither is valid at a domain "
                        "apex, so on a host named after the domain they would "
                        "always be empty. Select them when monitoring a specific "
                        "subdomain instead."
                    ),
                    elements=[
                        MultipleChoiceElement(name="A", title=Title("A, IPv4 address")),
                        MultipleChoiceElement(
                            name="AAAA", title=Title("AAAA, IPv6 address")
                        ),
                        MultipleChoiceElement(name="MX", title=Title("MX, mail exchange")),
                        MultipleChoiceElement(
                            name="TXT", title=Title("TXT, SPF, DKIM and verification")
                        ),
                        MultipleChoiceElement(name="NS", title=Title("NS, nameservers")),
                        MultipleChoiceElement(
                            name="SOA", title=Title("SOA, start of authority")
                        ),
                        MultipleChoiceElement(
                            name="CNAME", title=Title("CNAME, canonical name")
                        ),
                        MultipleChoiceElement(name="PTR", title=Title("PTR, reverse DNS")),
                    ],
                    prefill=DefaultValue(["A", "AAAA", "MX", "TXT", "NS", "SOA"]),
                ),
            ),
            "check_delegation": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Check zone delegation"),
                    label=Title("Compare the parent delegation against the zone"),
                    help_text=Help(
                        "Creates the DNS Zone Delegation service, which compares the "
                        "nameserver set published by the parent zone against the set "
                        "the zone publishes for itself, and verifies glue addresses. "
                        "The parent is queried in either case, because the record "
                        "checks need the nameserver list, so turning this off saves "
                        "no queries and only removes the service."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "resolver": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Query this resolver instead"),
                    help_text=Help(
                        "Optional. By default the authoritative nameservers are "
                        "queried directly, which reports what the domain publishes. "
                        "Naming a resolver here reports what that resolver's cache "
                        "holds instead, which can lag a change by up to the record's "
                        "TTL. Useful for split-horizon setups or for verifying an "
                        "internal resolver. Delegation checking is not possible in "
                        "this mode and the service is not created."
                    ),
                    field_size=FieldSize.SMALL,
                    prefill=DefaultValue(""),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Timeout per query"),
                    unit_symbol="s",
                    help_text=Help(
                        "Query times vary by an order of magnitude on identical "
                        "queries, so a generous value avoids spurious timeouts."
                    ),
                    prefill=DefaultValue(5),
                ),
            ),
            "retries": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Retries per query"),
                    help_text=Help(
                        "A single lost UDP packet should not produce an alarm."
                    ),
                    prefill=DefaultValue(2),
                ),
            ),
            "deadline": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Total time budget"),
                    unit_symbol="s",
                    help_text=Help(
                        "The agent gives up and emits whatever it has collected once "
                        "this is reached, rather than being killed by the agent "
                        "timeout and producing nothing at all. Keep it below the "
                        "Checkmk agent timeout, which defaults to 60 seconds."
                    ),
                    prefill=DefaultValue(45),
                ),
            ),
        },
    )


rule_spec_dns_health = SpecialAgent(
    name="dns_health",
    title=Title("DNS Health"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
)
