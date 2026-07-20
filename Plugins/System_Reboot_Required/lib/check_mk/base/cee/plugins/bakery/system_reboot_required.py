#!/usr/bin/env python3
# system_reboot_required - CheckMK Agent Bakery plugin
#
# Copyright (C) 2026  Sher Zaman - FirmaTrust (szaman@iceconsulting.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pathlib import Path
from typing import Any

from .bakery_api.v1 import (
    OS,
    FileGenerator,
    Plugin,
    register,
)


def get_system_reboot_required_files(conf: Any) -> FileGenerator:
    # conf is the value of the AgentConfig ruleset. A dict (possibly empty)
    # deploys the plugin; the "do not deploy" choice never reaches here.
    interval = None
    if isinstance(conf, dict):
        raw_interval = conf.get("interval")
        if raw_interval:
            interval = int(raw_interval)

    yield Plugin(
        base_os=OS.LINUX,
        source=Path("system_reboot_required"),
        target=Path("system_reboot_required"),
        interval=interval,
    )


register.bakery_plugin(
    name="system_reboot_required",
    files_function=get_system_reboot_required_files,
)
