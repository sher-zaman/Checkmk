#!/usr/bin/env python3
"""Server side call configuration for the Infoblox CSP special agent.

Author:  Sher Zaman (sher[at]sherz[dot]dev, https://sherz.dev)
Repo:    https://github.com/sher-zaman/Checkmk
License: GPL-2.0-only
"""

from cmk.server_side_calls.v1 import (
    noop_parser,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _agent_arguments(params, host_config):
    args = []

    base_url = params.get("base_url")
    if base_url:
        args += ["--base-url", str(base_url).rstrip("/")]

    # The key is passed as a command argument with unsafe(). Secret objects
    # cannot be delivered over stdin, and passing the object without unsafe()
    # hands the agent a password store reference rather than the key itself.
    api_key = params.get("api_key")
    if api_key is not None:
        args += ["--api-key", api_key.unsafe()]

    # Isolates this tenant's configuration cache from any other tenant
    # monitored from the same site.
    args += ["--cache-scope", host_config.name]

    if "timeout" in params:
        args += ["--timeout", str(params["timeout"])]

    if params.get("no_cert_check"):
        args.append("--no-cert-check")

    prefix = params.get("host_prefix")
    if prefix:
        args += ["--host-prefix", str(prefix)]

    if params.get("skip_config_tier"):
        args.append("--skip-config-tier")

    if "config_ttl" in params:
        args += ["--config-ttl", str(int(params["config_ttl"]))]

    yield SpecialAgentCommand(command_arguments=args)


special_agent_infoblox_csp = SpecialAgentConfig(
    name="infoblox_csp",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
