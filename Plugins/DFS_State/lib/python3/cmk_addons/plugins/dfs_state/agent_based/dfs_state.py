#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

"""
Check_MK plugin to check dfs state

Authors:    Allan GooD <allan.cassaro@gmail.com>
            Roger Ellenberger, roger.ellenberger@wagner.ch
Version:    2.0

"""

from __future__ import annotations
from enum import Enum
from typing import List, NamedTuple

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Result,
    Service,
    State,
)


class DfsStatus(Enum):
    ERROR = 5
    NORMAL = 4
    AUTO_RECOVER = 3
    INITIAL_SYNC = 2
    INITIALIZE = 1
    NOT_INITIALIZED = 0

    def get_description(self) -> str:
        descr = {
            0: 'DFS not initialized',
            1: 'DFS Initializing',
            2: 'DFS in Initial Sincronization',
            3: 'DFS in Auto Recover Operation',
            4: 'DFS in Normal Operation',
            5: 'DFS Error',
        }
        return descr[self.value]

    def get_cmk_state(self) -> State:
        if self.value == 0:
            return State.UNKNOWN
        if self.value in {1, 2, 3}:
            return State.WARN
        if self.value == 4:
            return State.OK
        if self.value == 5:
            return State.CRIT


class DfsShare(NamedTuple):
    replicated_folder_name: str
    replication_group_name: str
    state: DfsStatus

    @staticmethod
    def from_string_table(line) -> DfsShare:
        return DfsShare(
            replicated_folder_name=line[0],
            replication_group_name=line[1],
            state=DfsStatus(int(line[2]))
        )

    def get_result(self) -> Result:
        yield Result(
            state=self.state.get_cmk_state(),
            summary=f'State: {self.state.get_description()}, '
                    f'ReplicationGroup: {self.replication_group_name}',
        )


def parse_dfs_state(string_table) -> List[DfsShare]:
    """
    Output sample:
        <<<dfs_state>>>
        ReplicatedFolderName  ReplicationGroupName     State
        XXXXXXX               SRWXXXXXXX1-SVXXXXXXXX2  4
        XXXXXXX               SRXXXXXXXX1-SVXXXXXXXX2  4
        XXXXXXX               SRXXXXXXXX1-SVXXXXXXXX2  4
        XXXX                  SRXXXXXXXX1-SVXXXXXXXX2  4
    """
    return [DfsShare.from_string_table(line) for line in string_table
            if line[2].isdigit() and 0 <= int(line[2]) <= 5]  # only process valid data lines


agent_section_dfs_state = AgentSection(
    name='dfs_state',
    parse_function=parse_dfs_state,
)


def discover_dfs_state(section: List[DfsShare]) -> DiscoveryResult:
    for dfs_item in section:
        yield Service(item=dfs_item.replicated_folder_name)


def check_dfs_state(item: str, section: List[DfsShare]) -> CheckResult:
    for dfs_item in section:
        if dfs_item.replicated_folder_name == item:
            yield from dfs_item.get_result()
            return
    else:
        yield Result(state=State.UNKNOWN, summary='item not found')


check_plugin_dfs_state = CheckPlugin(
    name='dfs_state',
    service_name='DFS Share %s',
    discovery_function=discover_dfs_state,
    check_function=check_dfs_state,
)
