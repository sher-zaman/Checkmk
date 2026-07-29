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
DFS backlog check for Check_MK

Authors:    Kai Biebel
            Roger Ellenberger, roger.ellenberger@wagner.ch
Version:    1.3

"""

from __future__ import annotations
from enum import Enum, unique
from typing import List, NamedTuple, Tuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)


CHECK_NAME: str = 'dfs_backlog'


@unique
class DfsBacklogHealthLevels(Enum):
    WARN: int = 300
    CRIT: int = 1000

    @staticmethod
    def health_levels() -> Tuple:
        return (DfsBacklogHealthLevels.WARN.value, DfsBacklogHealthLevels.CRIT.value)

    @staticmethod
    def get_state(backlog_count: int) -> State:
        if backlog_count > DfsBacklogHealthLevels.CRIT.value:
            return State.CRIT
        elif backlog_count > DfsBacklogHealthLevels.WARN.value:
            return State.WARN
        elif backlog_count < 0:
            raise ValueError(f'Backlog count is negative! count={backlog_count}')

        return State.OK


class DfsReplication(NamedTuple):
    descr: str
    backlog_count: int
    disabled: bool = False

    @staticmethod
    def from_string_table(line: List[str]) -> DfsReplication:
        descr_raw: List[str] = line[0].rstrip(')').split(' ')

        share_name: str = descr_raw[0]
        direction: str = descr_raw[2]
        host: str = descr_raw[3]

        dfs_replica_descr: str = f'{share_name} {direction} {host}'
        backlog_count: int = 0
        disabled: bool = False

        if line[1] == 'NULL':
            disabled = True
        else:
            backlog_count = int(line[1])

        return DfsReplication(dfs_replica_descr, backlog_count, disabled)


def parse_dfs_backlog(string_table) -> List[DfsReplication]:
    """
    Example agent output:
        <<<dfs_backlog:sep(59)>>>
        FOO_DATA ( from foohost);0
        FOO_DATA ( to foohost);0
        Archive ( from foohost);0
        Archive ( to foohost);0

    Agent output is separated by a semicolon (ASCII char 59)

    Example string_table:
        [
            ['FOO_DATA ( from foohost)', '0'],
            ['FOO_DATA ( to foohost)', '0'],
            ['Archive ( from foohost)', '0'],
            ['Archive ( to foohost)', '0'],
        ]
    """
    return [DfsReplication.from_string_table(line) for line in string_table]


agent_section_dfs_backlog = AgentSection(
    name=CHECK_NAME,
    parse_function=parse_dfs_backlog,
)


def discover_dfs_backlog(section: List[DfsReplication]) -> DiscoveryResult:
    for replication in section:
        yield Service(item=replication.descr)


def check_dfs_backlog(item: str, section: List[DfsReplication]) -> CheckResult:
    for replication in section:
        if replication.descr == item:
            if replication.disabled:
                yield Result(state=State.OK, summary='DFSR Disabled')
            else:
                yield Result(state=DfsBacklogHealthLevels.get_state(replication.backlog_count),
                             summary=f'Backlog count: {replication.backlog_count}')
                yield Metric(name="count",
                             value=replication.backlog_count,
                             levels=DfsBacklogHealthLevels.health_levels())
            break

    else:
        yield Result(state=State.UNKNOWN, summary='item not found')


check_plugin_dfs_backlog = CheckPlugin(
    name=CHECK_NAME,
    service_name='DFS Backlog: %s',
    discovery_function=discover_dfs_backlog,
    check_function=check_dfs_backlog,
)
