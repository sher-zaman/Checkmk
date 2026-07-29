#!/usr/bin/python
'''Deployment ruleset for DFS state plugin.'''
# -*- encoding: utf-8; py-indent-offset: 4 -*-

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _valuespec_agent_config_dfs_state():
    return Dictionary(
        title=Title("DFS state plugin"),
        help_text=Help(
            "This plugin checks the DFS state."
        ),
        elements={
            "deploy": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Deploy plugin for DFS state plugin"),
                ),
                required=True,
            ),
        },
    )


rule_spec_agent_config_dfs_state = AgentConfig(
    title=Title("DFS state plugin"),
    topic=Topic.WINDOWS,
    name="dfs_state",
    parameter_form=_valuespec_agent_config_dfs_state,
)