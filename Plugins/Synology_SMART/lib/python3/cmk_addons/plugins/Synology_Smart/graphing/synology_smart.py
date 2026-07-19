#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# synology_smart - metrics and graphs
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, TimeNotation, Unit

_COUNT = Unit(DecimalNotation(""))

metric_synology_smart_reallocated = Metric(
    name="synology_smart_reallocated",
    title=Title("Reallocated sectors"),
    unit=_COUNT,
    color=Color.RED,
)

metric_synology_smart_pending = Metric(
    name="synology_smart_pending",
    title=Title("Current pending sectors"),
    unit=_COUNT,
    color=Color.ORANGE,
)

metric_synology_smart_offline_uncorrectable = Metric(
    name="synology_smart_offline_uncorrectable",
    title=Title("Offline uncorrectable sectors"),
    unit=_COUNT,
    color=Color.PURPLE,
)

metric_synology_smart_reported_uncorrect = Metric(
    name="synology_smart_reported_uncorrect",
    title=Title("Reported uncorrectable errors"),
    unit=_COUNT,
    color=Color.BROWN,
)

metric_synology_smart_udma_crc = Metric(
    name="synology_smart_udma_crc",
    title=Title("UDMA CRC errors"),
    unit=_COUNT,
    color=Color.BLUE,
)

metric_synology_smart_power_on_hours = Metric(
    name="synology_smart_power_on_hours",
    title=Title("Powered on"),
    unit=Unit(TimeNotation()),
    color=Color.GREEN,
)

graph_synology_smart_errors = Graph(
    name="synology_smart_errors",
    title=Title("SMART error counters"),
    simple_lines=[
        "synology_smart_reallocated",
        "synology_smart_pending",
        "synology_smart_offline_uncorrectable",
        "synology_smart_udma_crc",
        "synology_smart_reported_uncorrect",
    ],
    optional=[
        "synology_smart_reported_uncorrect",
    ],
    minimal_range=MinimalRange(0, 10),
)
