# system_reboot_required - CheckMK Agent Bakery ruleset
#
# Copyright (C) 2026  Sher Zaman - FirmaTrust (sher_zaman[at]outlook[dot]com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("System Reboot Required (Linux)"),
        help_text=Help(
            "Deploy the system_reboot_required agent plugin to Linux hosts via "
            "the Agent Bakery. The plugin detects pending reboots on Debian, "
            "Ubuntu, Kali, RHEL, CentOS, Rocky Linux, AlmaLinux, Fedora and "
            "SUSE/openSUSE."
        ),
        elements={
            "interval": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Execution interval"),
                    label=Label("Run asynchronously every"),
                    help_text=Help(
                        "If set, the plugin runs asynchronously at this interval "
                        "instead of on every agent poll. Detection involves "
                        "package manager queries, so an interval of a few "
                        "minutes is recommended on busy hosts. If unset, the "
                        "plugin runs synchronously with each agent execution."
                    ),
                    displayed_magnitudes=[
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                    ],
                    prefill=DefaultValue(300.0),
                ),
                required=False,
            ),
        },
    )


rule_spec_system_reboot_required_bakery = AgentConfig(
    name="system_reboot_required",
    title=Title("System Reboot Required (Linux)"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form,
)
