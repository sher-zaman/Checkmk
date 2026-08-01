#!/usr/bin/env python3
"""Discovery ruleset for Infoblox CSP network objects.

Author:  Sher Zaman (sher[at]sherz[dot]dev, https://sherz.dev)
Repo:    https://github.com/sher-zaman/Checkmk
License: GPL-2.0-only
"""

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import DiscoveryParameters, Topic


def _form_network_discovery() -> Dictionary:
    return Dictionary(
        title=Title("Infoblox subnet and address block discovery"),
        help_text=Help(
            "DHCP ranges are always discovered, because that is where address "
            "exhaustion actually happens, and the IP space rollup covers the "
            "tenant as a whole. Subnets and address blocks are off by default "
            "for two reasons. Most of them are allocation records rather than "
            "pools, and address blocks aggregate their child subnets and ranges, "
            "so one subnet filling up would alarm three times. Enable them if "
            "you want per subnet visibility. Every object remains in the "
            "hardware and software inventory whether discovered or not."
        ),
        elements={
            "discover": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Discover subnets and address blocks"),
                    label=Label("Create a service per subnet and address block"),
                    prefill=DefaultValue(False),
                ),
            ),
            "minimum_addresses": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Minimum size to discover"),
                    help_text=Help(
                        "Objects with fewer total addresses than this are "
                        "skipped. A /32 NAT record holds one address and reads "
                        "one hundred percent forever, which is the kind of "
                        "permanent alert that teaches people to ignore Checkmk."
                    ),
                    unit_symbol="addresses",
                    prefill=DefaultValue(4),
                    custom_validate=(NumberInRange(min_value=0, max_value=65536),),
                ),
            ),
        },
    )


rule_spec_infoblox_csp_network_discovery = DiscoveryParameters(
    name="infoblox_csp_network_discovery",
    title=Title("Infoblox subnet and address block discovery"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_network_discovery,
)
