#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Server-side call configuration for the VCSA health special agent.
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
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

    # The bare Secret is passed rather than Secret.unsafe(). Checkmk replaces it
    # with a password store reference at the process level, so the plaintext
    # credential never appears in argv or in the process table. The agent
    # resolves that reference in its own memory via the password store.
    args.extend(["--secret-id", params["password"]])
    args.append(host_config.primary_ip_config.address or host_config.name)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_vcsa_health = SpecialAgentConfig(
    name="vcsa_health",
    parameter_parser=noop_parser,
    commands_function=_commands_function,
)
