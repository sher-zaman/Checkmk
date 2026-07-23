#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# dell_powervault_me5 - Server side call for the special agent
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
from cmk.server_side_calls.v1 import (
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _agent_arguments(params, host_config):
    args = [
        "--host", host_config.primary_ip_config.address,
        "--user", params["user"],
        # .unsafe() substitutes the real password into the argument so the
        # agent can compute the SHA-256 login hash. Passing the Secret object
        # itself would hand the agent a masked password-store reference.
        "--password", params["password"].unsafe(),
    ]

    timeout = params.get("timeout")
    if timeout is not None:
        args += ["--timeout", str(timeout)]

    if params.get("verify_ssl"):
        args.append("--verify-ssl")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_dell_powervault_me5 = SpecialAgentConfig(
    name="dell_powervault_me5",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
