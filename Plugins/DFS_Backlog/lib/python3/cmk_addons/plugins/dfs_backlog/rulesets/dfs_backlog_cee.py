#!/usr/bin/python
'''Deployment ruleset for DFS Backlog plugin.'''
# -*- encoding: utf-8; py-indent-offset: 4 -*-

from cmk.rulesets.v1 import Title, Label, Help
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _valuespec_agent_config_dfs_backlog():
    return Dictionary(
        title=Title("DFS Backlog plugin"),
        help_text=Help(
            "This plugin checks the DFS backlog."
        ),
        elements={
            "deploy": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Deploy plugin for DFS Backlog plugin"),
                ),
                required=True,
            ),
        },
    )


rule_spec_agent_config_dfs_backlog = AgentConfig(
    title=Title("DFS Backlog plugin"),
    topic=Topic.WINDOWS,
    name="dfs_backlog",
    parameter_form=_valuespec_agent_config_dfs_backlog,
)