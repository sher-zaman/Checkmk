#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# dell_powervault_me5 - Graphing definitions
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# Pool capacity (fs_used / fs_size) and sensor temperature (temp) reuse
# Checkmk's built-in metric names and inherit the stock graphs and
# perfometers. The metrics below are the plugin-specific ones.
#
from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    TimeNotation,
    Unit,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

_PERCENT = Unit(DecimalNotation("%"))
_RPM = Unit(DecimalNotation("RPM"))
_BYTES = Unit(IECNotation("B"))
_COUNT = Unit(DecimalNotation(""))

metric_dell_me5_fan_speed = Metric(
    name="fan_speed",
    title=Title("Fan speed"),
    unit=_RPM,
    color=Color.BLUE,
)

metric_dell_me5_unwritable_cache_percent = Metric(
    name="dell_me5_unwritable_cache_percent",
    title=Title("Unwritable cache"),
    unit=_PERCENT,
    color=Color.RED,
)

metric_dell_me5_unwritable_cache_a_percent = Metric(
    name="dell_me5_unwritable_cache_a_percent",
    title=Title("Unwritable cache (controller A)"),
    unit=_PERCENT,
    color=Color.ORANGE,
)

metric_dell_me5_unwritable_cache_b_percent = Metric(
    name="dell_me5_unwritable_cache_b_percent",
    title=Title("Unwritable cache (controller B)"),
    unit=_PERCENT,
    color=Color.YELLOW,
)

metric_dell_me5_dg_job_percent = Metric(
    name="dell_me5_dg_job_percent",
    title=Title("Disk group job completion"),
    unit=_PERCENT,
    color=Color.CYAN,
)

metric_dell_me5_volume_allocated_bytes = Metric(
    name="dell_me5_volume_allocated_bytes",
    title=Title("Volume allocated size"),
    unit=_BYTES,
    color=Color.GREEN,
)

metric_dell_me5_volume_fill_percent = Metric(
    name="dell_me5_volume_fill_percent",
    title=Title("Volume thin fill"),
    unit=_PERCENT,
    color=Color.PURPLE,
)

metric_dell_me5_ssd_life_left_percent = Metric(
    name="dell_me5_ssd_life_left_percent",
    title=Title("SSD life left"),
    unit=_PERCENT,
    color=Color.GREEN,
)

metric_dell_me5_snapshot_count = Metric(
    name="dell_me5_snapshot_count",
    title=Title("Snapshot count"),
    unit=_COUNT,
    color=Color.BLUE,
)

metric_dell_me5_snapshot_bytes = Metric(
    name="dell_me5_snapshot_bytes",
    title=Title("Snapshot data"),
    unit=_BYTES,
    color=Color.ORANGE,
)

metric_dell_me5_snapshot_age = Metric(
    name="dell_me5_snapshot_age",
    title=Title("Newest snapshot age"),
    unit=Unit(TimeNotation()),
    color=Color.CYAN,
)

_BYTES_PER_SEC = Unit(IECNotation("B/s"))

metric_dell_me5_hostport_throughput = Metric(
    name="dell_me5_hostport_throughput",
    title=Title("Host port throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.BLUE,
)

metric_dell_me5_hostport_iops = Metric(
    name="dell_me5_hostport_iops",
    title=Title("Host port IOPS"),
    unit=Unit(DecimalNotation("IO/s")),
    color=Color.GREEN,
)

metric_dell_me5_hostport_latency = Metric(
    name="dell_me5_hostport_latency",
    title=Title("Host port average response time"),
    unit=Unit(TimeNotation()),
    color=Color.ORANGE,
)

metric_dell_me5_hostport_read_latency = Metric(
    name="dell_me5_hostport_read_latency",
    title=Title("Host port read response time"),
    unit=Unit(TimeNotation()),
    color=Color.CYAN,
)

metric_dell_me5_hostport_write_latency = Metric(
    name="dell_me5_hostport_write_latency",
    title=Title("Host port write response time"),
    unit=Unit(TimeNotation()),
    color=Color.YELLOW,
)

metric_dell_me5_hostport_queue_depth = Metric(
    name="dell_me5_hostport_queue_depth",
    title=Title("Host port queue depth"),
    unit=Unit(DecimalNotation("")),
    color=Color.PURPLE,
)

graph_dell_me5_hostport_latency = Graph(
    name="dell_me5_hostport_latency",
    title=Title("ME5 host port response time"),
    simple_lines=[
        "dell_me5_hostport_read_latency",
        "dell_me5_hostport_write_latency",
        "dell_me5_hostport_latency",
    ],
)

graph_dell_me5_unwritable_cache = Graph(
    name="dell_me5_unwritable_cache",
    title=Title("ME5 unwritable cache per controller"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=[
        "dell_me5_unwritable_cache_a_percent",
        "dell_me5_unwritable_cache_b_percent",
    ],
)

perfometer_dell_me5_fan_speed = Perfometer(
    name="fan_speed",
    focus_range=FocusRange(Closed(0), Closed(12000)),
    segments=["fan_speed"],
)

perfometer_dell_me5_ssd_life_left = Perfometer(
    name="dell_me5_ssd_life_left_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["dell_me5_ssd_life_left_percent"],
)
