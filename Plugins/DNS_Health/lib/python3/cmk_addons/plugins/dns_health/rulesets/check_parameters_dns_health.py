#!/usr/bin/env python3
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# States are stored as names rather than integers so that no import of
# ServiceState is required. A form spec import that is unavailable on one
# supported version fails at rule migration time during installation, which is
# a difficult failure to diagnose from the GUI.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)

_STATE_ELEMENTS = [
    SingleChoiceElement(name="ok", title=Title("OK")),
    SingleChoiceElement(name="warn", title=Title("WARN")),
    SingleChoiceElement(name="crit", title=Title("CRIT")),
]


def _state_choice(title: Title, prefill: str, help_text: Help | None = None) -> SingleChoice:
    return SingleChoice(
        title=title,
        help_text=help_text,
        elements=_STATE_ELEMENTS,
        prefill=DefaultValue(prefill),
    )


def _record_type_states() -> Dictionary:
    """Every record type is listed with its default visible in the form. One
    rule therefore covers all types on a host, rather than requiring a separate
    rule per record type to express different behaviour."""
    return Dictionary(
        title=Title("State when a record changes"),
        help_text=Help(
            "NS defaults to CRIT because an unexpected nameserver change has no "
            "routine explanation: either the DNS provider was moved, which is "
            "planned work, or the domain was taken over. Everything else defaults "
            "to WARN because those records move for ordinary reasons, such as CDN "
            "changes, mail migrations, and vendor verification records being added "
            "to TXT. Set a type to OK to record and display its changes without "
            "alarming."
        ),
        elements={
            "A": DictElement(required=True, parameter_form=_state_choice(Title("A"), "warn")),
            "AAAA": DictElement(
                required=True, parameter_form=_state_choice(Title("AAAA"), "warn")
            ),
            "MX": DictElement(
                required=True, parameter_form=_state_choice(Title("MX"), "warn")
            ),
            "TXT": DictElement(
                required=True, parameter_form=_state_choice(Title("TXT"), "warn")
            ),
            "NS": DictElement(
                required=True, parameter_form=_state_choice(Title("NS"), "crit")
            ),
            "SOA": DictElement(
                required=True, parameter_form=_state_choice(Title("SOA"), "warn")
            ),
            "CNAME": DictElement(
                required=True, parameter_form=_state_choice(Title("CNAME"), "warn")
            ),
            "PTR": DictElement(
                required=True, parameter_form=_state_choice(Title("PTR"), "warn")
            ),
        },
    )


def _records_form() -> Dictionary:
    return Dictionary(
        title=Title("DNS record drift"),
        help_text=Help(
            "On the first run the current values are recorded as the baseline and "
            "the service reports OK, stating that a baseline was recorded so that a "
            "reset is visible in the service history rather than silent. Later runs "
            "compare against that baseline and report only what was added or "
            "removed."
        ),
        elements={
            "change_states": DictElement(
                required=True, parameter_form=_record_type_states()
            ),
            "hold_duration": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("How long a detected change keeps alarming"),
                    help_text=Help(
                        "A detected change holds the old baseline and keeps alarming "
                        "for this long, then the new values are accepted and the "
                        "service returns to OK. Accepting immediately risks the "
                        "alarm being missed entirely, since it would clear on the "
                        "next check. Never accepting means every legitimate change, "
                        "including routine TXT additions, has to be cleared by hand. "
                        "If the change is reverted during the window the service "
                        "returns to OK on its own with no intervention."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="after",
                            title=Title("Accept after a period"),
                            parameter_form=Dictionary(
                                elements={
                                    "days": DictElement(
                                        required=True,
                                        parameter_form=Integer(
                                            title=Title("Days"),
                                            unit_symbol="days",
                                            prefill=DefaultValue(7),
                                        ),
                                    )
                                }
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="never",
                            title=Title("Never accept automatically"),
                            parameter_form=Dictionary(elements={}),
                        ),
                        CascadingSingleChoiceElement(
                            name="immediate",
                            title=Title("Accept immediately, alarm for one check only"),
                            parameter_form=Dictionary(elements={}),
                        ),
                    ],
                    prefill=DefaultValue("after"),
                ),
            ),
            "state_vanished": DictElement(
                required=True,
                parameter_form=_state_choice(
                    Title("State when all records of a type disappear"),
                    "crit",
                    Help(
                        "Records existing and then being gone entirely is the most "
                        "serious content change, so this is separate from the "
                        "per-type setting above and defaults to CRIT."
                    ),
                ),
            ),
            "state_nxdomain": DictElement(
                required=True,
                parameter_form=_state_choice(
                    Title("State when the domain no longer exists"),
                    "crit",
                    Help(
                        "NXDOMAIN where a baseline previously existed. This is a live "
                        "condition rather than a change, so it keeps alarming for as "
                        "long as it lasts and is not subject to the period above."
                    ),
                ),
            ),
            "state_diverged": DictElement(
                required=True,
                parameter_form=_state_choice(
                    Title("State when authoritative servers disagree"),
                    "warn",
                    Help(
                        "The nameservers returned different answers for the same "
                        "record type, which means one of them is serving stale data. "
                        "The baseline is held while this lasts, since accepting "
                        "either answer would flap. Also a live condition and not "
                        "subject to the period above."
                    ),
                ),
            ),
            "ignore_soa_serial": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Ignore the SOA serial"),
                    label=Label("Compare every SOA field except the serial"),
                    help_text=Help(
                        "The serial increments on every zone edit, so comparing it "
                        "against a stored value alarms on routine changes. Serial "
                        "formats also differ between providers, some counting up and "
                        "some encoding a date, so it is not interpreted. Turn this "
                        "off only to alarm on any zone edit at all."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
        },
    )


def _delegation_form() -> Dictionary:
    return Dictionary(
        title=Title("DNS zone delegation"),
        help_text=Help(
            "Compares the nameserver set published by the parent zone against the "
            "set the zone publishes for itself, and checks that glue addresses match "
            "an independent resolution of each nameserver name. A disagreement means "
            "some resolvers may be directed at a server that no longer answers for "
            "the domain."
        ),
        elements={
            "state_ns_mismatch": DictElement(
                required=True,
                parameter_form=_state_choice(
                    Title("State when the parent and zone nameserver sets differ"),
                    "warn",
                ),
            ),
            "state_glue_mismatch": DictElement(
                required=True,
                parameter_form=_state_choice(
                    Title("State when glue addresses do not match"),
                    "warn",
                    Help(
                        "Nameservers with no glue published, which is normal for "
                        "out-of-bailiwick nameservers, are not treated as a fault. "
                        "Only IPv4 glue is verified."
                    ),
                ),
            ),
        },
    )


rule_spec_dns_health_records = CheckParameters(
    name="dns_health_records",
    title=Title("DNS record drift"),
    topic=Topic.NETWORKING,
    parameter_form=_records_form,
    condition=HostAndItemCondition(item_title=Title("Record type")),
)

rule_spec_dns_health_delegation = CheckParameters(
    name="dns_health_delegation",
    title=Title("DNS zone delegation"),
    topic=Topic.NETWORKING,
    parameter_form=_delegation_form,
    condition=HostCondition(),
)
