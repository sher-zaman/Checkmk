#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
"""Agent Bakery plugin for the DFS state check.

Original DFS state check by Allan GooD <allan.cassaro@gmail.com>.
MKP packaging by Roger Ellenberger (WagnerAG).

Checkmk 2.4 compatibility fixes by Sher Zaman:
  * Migrated from the removed pre-2.3 bakery API
    (cmk.base.api.bakery.constants / .function_types, BakeryPlugin)
    to the supported register.bakery_plugin / .bakery_api.v1 API.
    The old imports raised ModuleNotFoundError at bake time, which the
    bakery swallowed silently, so the "deploy" toggle never emitted a file.
  * Windows source now resolves from local/share/check_mk/agents/windows/plugins/
    (the location Plugin(source=...) expects for OS.WINDOWS), instead of the
    non-standard agent_based/ directory used previously.
"""

from pathlib import Path
from typing import Any

from .bakery_api.v1 import OS, Plugin, register, FileGenerator


def get_dfs_state_files(conf: dict[str, Any]) -> FileGenerator:
    """Yield the Windows agent plugin when the deploy toggle is enabled."""
    if not conf.get("deploy"):
        return

    yield Plugin(base_os=OS.WINDOWS, source=Path("dfs_state.ps1"))


register.bakery_plugin(
    name="dfs_state",
    files_function=get_dfs_state_files,
)
