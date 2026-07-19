#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Checkmk Bakery plugin: DHCP failover monitoring (Windows)
#
# Author: Sher Zaman (FirmaTrust)
# License: GPLv2
#
# Deploys agents/windows/plugins/dhcp_failover.ps1 to Windows hosts matched
# by the "DHCP failover monitoring (Windows)" agent rule.

from pathlib import Path
from typing import Any, Dict

from .bakery_api.v1 import (
    OS,
    FileGenerator,
    Plugin,
    register,
)


def get_dhcp_failover_files(conf: Dict[str, Any]) -> FileGenerator:
    if not conf.get("deploy", True):
        return

    yield Plugin(
        base_os=OS.WINDOWS,
        source=Path("dhcp_failover.ps1"),
        target=Path("dhcp_failover.ps1"),
    )


register.bakery_plugin(
    name="dhcp_failover",
    files_function=get_dhcp_failover_files,
)
