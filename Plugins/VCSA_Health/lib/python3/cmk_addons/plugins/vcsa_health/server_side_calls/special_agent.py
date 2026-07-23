#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Server-side call configuration for the VCSA health special agent.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)


def _commands_function(params, host_config: HostConfig):
    args: list[str | Secret] = [
        "--username",
        params["username"],
        "--timeout",
        str(params.get("timeout", 30)),
    ]
    if params.get("no_cert_check"):
        args.append("--no-cert-check")

    # The password is stored in the Checkmk password store and referenced by
    # ID in the rule. unsafe() makes Checkmk resolve the reference to the
    # actual value in this argument before the agent runs, which a standalone
    # agent requires (passing the Secret directly would hand the agent a
    # password-store reference that it cannot resolve without Checkmk-internal
    # APIs). The resolved value is visible in the process table while the agent
    # runs; this is the standard behaviour for third-party special agents.
    args.extend(["--password", params["password"].unsafe()])
    args.append(host_config.primary_ip_config.address or host_config.name)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_vcsa_health = SpecialAgentConfig(
    name="vcsa_health",
    parameter_parser=noop_parser,
    commands_function=_commands_function,
)
