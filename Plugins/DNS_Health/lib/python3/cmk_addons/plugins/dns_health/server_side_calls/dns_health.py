#!/usr/bin/env python3
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# Pure translation of rule values into arguments. Nothing is written to disk
# and no state is created here: this runs on every configuration render, so
# side effects would repeat every time and are shared across all hosts.

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from cmk.server_side_calls.v1 import (
    HostConfig,
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)

DEFAULT_TYPES = ["A", "AAAA", "MX", "TXT", "NS", "SOA"]


def _commands(
    params: Mapping[str, Any], host_config: HostConfig
) -> Iterable[SpecialAgentCommand]:
    # One host per domain is the intended arrangement, so the host name is the
    # default and the field can be left empty.
    domain = str(params.get("domain") or "").strip() or host_config.name

    rtypes = list(params.get("record_types") or DEFAULT_TYPES)
    args: list[str] = ["--domain", domain, "--types", ",".join(rtypes)]

    resolver = str(params.get("resolver") or "").strip()
    if resolver:
        args += ["--resolver", resolver]

    args += ["--timeout", str(params.get("timeout", 5))]
    args += ["--retries", str(params.get("retries", 2))]
    args += ["--deadline", str(params.get("deadline", 45))]

    if params.get("check_delegation", True) is False:
        args.append("--no-delegation")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_dns_health = SpecialAgentConfig(
    name="dns_health",
    parameter_parser=noop_parser,
    commands_function=_commands,
)
