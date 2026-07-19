#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Checkmk check plugin: Windows DHCP failover relationships
#
# Author: Sher Zaman (FirmaTrust)
# License: GPLv2
#
# Consumes the <<<dhcp_failover>>> section produced by the Windows agent
# plugin dhcp_failover.ps1 and creates one service per failover relationship.
#
# Agent section format (sep 124):
#   name|state|mode|partner_server|server_role|scope_count|scope1,scope2,...
# or, on query failure:
#   __query_error__|<message>

from dataclasses import dataclass, field

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

# Microsoft DHCP failover states considered transitional (resynchronization
# and startup phases) as opposed to conflict/error states.
_TRANSITIONAL_STATES = {
    "init",
    "startup",
    "recover",
    "recoverwait",
    "recoverdone",
}

_DEFAULT_PARAMETERS = {
    "state_normal": 0,
    "state_communication_interrupted": 1,
    "state_partner_down": 2,
    "state_transitional": 1,
    "state_other": 2,
}


@dataclass(frozen=True)
class FailoverRelationship:
    state: str
    mode: str
    partner_server: str
    server_role: str
    scope_count: int
    scopes: tuple = ()


@dataclass(frozen=True)
class Section:
    relationships: dict = field(default_factory=dict)
    query_error: str = ""


def parse_dhcp_failover(string_table: StringTable) -> Section:
    relationships = {}
    query_error = ""

    for line in string_table:
        if not line:
            continue

        if line[0] == "__query_error__":
            query_error = line[1] if len(line) > 1 else "Unknown query error"
            continue

        if len(line) < 6:
            continue

        name, state, mode, partner, role, scope_count = line[:6]
        scopes = tuple(s for s in line[6].split(",") if s) if len(line) > 6 else ()

        try:
            count = int(scope_count)
        except ValueError:
            count = len(scopes)

        relationships[name] = FailoverRelationship(
            state=state,
            mode=mode,
            partner_server=partner,
            server_role=role,
            scope_count=count,
            scopes=scopes,
        )

    return Section(relationships=relationships, query_error=query_error)


def discover_dhcp_failover(section: Section) -> DiscoveryResult:
    for name in section.relationships:
        yield Service(item=name)


def _state_for(state_name: str, params: dict) -> State:
    normalized = state_name.lower()
    if normalized == "normal":
        return State(params["state_normal"])
    if normalized == "communicationinterrupted":
        return State(params["state_communication_interrupted"])
    if normalized == "partnerdown":
        return State(params["state_partner_down"])
    if normalized in _TRANSITIONAL_STATES:
        return State(params["state_transitional"])
    return State(params["state_other"])


def check_dhcp_failover(item: str, params: dict, section: Section) -> CheckResult:
    relationship = section.relationships.get(item)

    if relationship is None:
        if section.query_error:
            yield Result(
                state=State.UNKNOWN,
                summary=f"DHCP failover query failed: {section.query_error}",
            )
        # Otherwise yield nothing: the service goes stale and Checkmk
        # reports it as vanished, which is the correct signal when a
        # relationship has been deleted on the server.
        return

    yield Result(
        state=_state_for(relationship.state, params),
        summary=f"State: {relationship.state}",
    )

    yield Result(state=State.OK, summary=f"Mode: {relationship.mode}")
    yield Result(state=State.OK, summary=f"Partner: {relationship.partner_server}")

    if relationship.server_role:
        yield Result(state=State.OK, summary=f"Role: {relationship.server_role}")

    yield Result(
        state=State.OK,
        summary=f"Scopes: {relationship.scope_count}",
        details="Scopes in this relationship: "
        + (", ".join(relationship.scopes) if relationship.scopes else "none"),
    )
    yield Metric("dhcp_failover_scopes", relationship.scope_count)


agent_section_dhcp_failover = AgentSection(
    name="dhcp_failover",
    parse_function=parse_dhcp_failover,
)

check_plugin_dhcp_failover = CheckPlugin(
    name="dhcp_failover",
    service_name="DHCP Failover %s",
    discovery_function=discover_dhcp_failover,
    check_function=check_dhcp_failover,
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_ruleset_name="dhcp_failover",
)
