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
_BYTES_PER_SEC = Unit(IECNotation("B/s"))
_IOPS = Unit(DecimalNotation("IO/s"))
_COUNT = Unit(DecimalNotation(""))
_SECONDS = Unit(TimeNotation())
_WATT = Unit(DecimalNotation("W"))
_FARAD = Unit(DecimalNotation("F"))
_OHM = Unit(DecimalNotation("Ohm"))
_VOLT = Unit(DecimalNotation("V"))

# --------------------------------------------------------------------- fans
metric_dell_me5_fan_speed = Metric(
    name="fan_speed",
    title=Title("Fan speed"),
    unit=_RPM,
    color=Color.BLUE,
)

# ---------------------------------------------------------- unwritable cache
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

# -------------------------------------------------------------- disk groups
metric_dell_me5_dg_job_percent = Metric(
    name="dell_me5_dg_job_percent",
    title=Title("Disk group job completion"),
    unit=_PERCENT,
    color=Color.CYAN,
)

# ------------------------------------------------------------------ volumes
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

metric_dell_me5_volume_throughput = Metric(
    name="dell_me5_volume_throughput",
    title=Title("Volume throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.BLUE,
)

metric_dell_me5_volume_read_throughput = Metric(
    name="dell_me5_volume_read_throughput",
    title=Title("Volume read throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.GREEN,
)

metric_dell_me5_volume_write_throughput = Metric(
    name="dell_me5_volume_write_throughput",
    title=Title("Volume write throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.ORANGE,
)

metric_dell_me5_volume_iops = Metric(
    name="dell_me5_volume_iops",
    title=Title("Volume IOPS"),
    unit=_IOPS,
    color=Color.BLUE,
)

metric_dell_me5_volume_read_iops = Metric(
    name="dell_me5_volume_read_iops",
    title=Title("Volume read IOPS"),
    unit=_IOPS,
    color=Color.GREEN,
)

metric_dell_me5_volume_write_iops = Metric(
    name="dell_me5_volume_write_iops",
    title=Title("Volume write IOPS"),
    unit=_IOPS,
    color=Color.ORANGE,
)

metric_dell_me5_volume_read_cache_hit_ratio = Metric(
    name="dell_me5_volume_read_cache_hit_ratio",
    title=Title("Volume read cache hit ratio"),
    unit=_PERCENT,
    color=Color.GREEN,
)

metric_dell_me5_volume_write_cache_hit_ratio = Metric(
    name="dell_me5_volume_write_cache_hit_ratio",
    title=Title("Volume write cache hit ratio"),
    unit=_PERCENT,
    color=Color.ORANGE,
)

# -------------------------------------------------------------------- disks
metric_dell_me5_ssd_life_left_percent = Metric(
    name="dell_me5_ssd_life_left_percent",
    title=Title("SSD life left"),
    unit=_PERCENT,
    color=Color.GREEN,
)

metric_dell_me5_disk_throughput = Metric(
    name="dell_me5_disk_throughput",
    title=Title("Disk throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.BLUE,
)

metric_dell_me5_disk_iops = Metric(
    name="dell_me5_disk_iops",
    title=Title("Disk IOPS"),
    unit=_IOPS,
    color=Color.CYAN,
)

metric_dell_me5_disk_queue_depth = Metric(
    name="dell_me5_disk_queue_depth",
    title=Title("Disk queue depth"),
    unit=_COUNT,
    color=Color.PURPLE,
)

metric_dell_me5_disk_smart_errors = Metric(
    name="dell_me5_disk_smart_errors",
    title=Title("SMART events"),
    unit=_COUNT,
    color=Color.RED,
)

metric_dell_me5_disk_media_errors = Metric(
    name="dell_me5_disk_media_errors",
    title=Title("Media errors"),
    unit=_COUNT,
    color=Color.ORANGE,
)

metric_dell_me5_disk_nonmedia_errors = Metric(
    name="dell_me5_disk_nonmedia_errors",
    title=Title("Non-media errors"),
    unit=_COUNT,
    color=Color.YELLOW,
)

metric_dell_me5_disk_bad_blocks = Metric(
    name="dell_me5_disk_bad_blocks",
    title=Title("Bad blocks"),
    unit=_COUNT,
    color=Color.RED,
)

metric_dell_me5_disk_block_reassigns = Metric(
    name="dell_me5_disk_block_reassigns",
    title=Title("Block reassignments"),
    unit=_COUNT,
    color=Color.PURPLE,
)

metric_dell_me5_disk_spinup_retries = Metric(
    name="dell_me5_disk_spinup_retries",
    title=Title("Spin-up retries"),
    unit=_COUNT,
    color=Color.BLUE,
)

metric_dell_me5_disk_io_timeouts = Metric(
    name="dell_me5_disk_io_timeouts",
    title=Title("I/O timeouts"),
    unit=_COUNT,
    color=Color.CYAN,
)

metric_dell_me5_disk_no_response = Metric(
    name="dell_me5_disk_no_response",
    title=Title("No-response events"),
    unit=_COUNT,
    color=Color.GREEN,
)

# --------------------------------------------------------------- host ports
metric_dell_me5_hostport_throughput = Metric(
    name="dell_me5_hostport_throughput",
    title=Title("Host port throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.BLUE,
)

metric_dell_me5_hostport_iops = Metric(
    name="dell_me5_hostport_iops",
    title=Title("Host port IOPS"),
    unit=_IOPS,
    color=Color.GREEN,
)

metric_dell_me5_hostport_latency = Metric(
    name="dell_me5_hostport_latency",
    title=Title("Host port average response time"),
    unit=_SECONDS,
    color=Color.ORANGE,
)

metric_dell_me5_hostport_read_latency = Metric(
    name="dell_me5_hostport_read_latency",
    title=Title("Host port read response time"),
    unit=_SECONDS,
    color=Color.CYAN,
)

metric_dell_me5_hostport_write_latency = Metric(
    name="dell_me5_hostport_write_latency",
    title=Title("Host port write response time"),
    unit=_SECONDS,
    color=Color.YELLOW,
)

metric_dell_me5_hostport_queue_depth = Metric(
    name="dell_me5_hostport_queue_depth",
    title=Title("Host port queue depth"),
    unit=_COUNT,
    color=Color.PURPLE,
)

# --------------------------------------------------------- system performance
metric_dell_me5_system_iops = Metric(
    name="dell_me5_system_iops",
    title=Title("System IOPS"),
    unit=_IOPS,
    color=Color.BLUE,
)

metric_dell_me5_system_read_iops = Metric(
    name="dell_me5_system_read_iops",
    title=Title("System read IOPS"),
    unit=_IOPS,
    color=Color.GREEN,
)

metric_dell_me5_system_write_iops = Metric(
    name="dell_me5_system_write_iops",
    title=Title("System write IOPS"),
    unit=_IOPS,
    color=Color.ORANGE,
)

metric_dell_me5_system_throughput = Metric(
    name="dell_me5_system_throughput",
    title=Title("System throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.BLUE,
)

metric_dell_me5_system_read_throughput = Metric(
    name="dell_me5_system_read_throughput",
    title=Title("System read throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.GREEN,
)

metric_dell_me5_system_write_throughput = Metric(
    name="dell_me5_system_write_throughput",
    title=Title("System write throughput"),
    unit=_BYTES_PER_SEC,
    color=Color.ORANGE,
)

metric_dell_me5_system_latency = Metric(
    name="dell_me5_system_latency",
    title=Title("System average response time"),
    unit=_SECONDS,
    color=Color.PURPLE,
)

metric_dell_me5_system_read_latency = Metric(
    name="dell_me5_system_read_latency",
    title=Title("System read response time"),
    unit=_SECONDS,
    color=Color.GREEN,
)

metric_dell_me5_system_write_latency = Metric(
    name="dell_me5_system_write_latency",
    title=Title("System write response time"),
    unit=_SECONDS,
    color=Color.ORANGE,
)

metric_dell_me5_controller_a_cpu_load = Metric(
    name="dell_me5_controller_a_cpu_load",
    title=Title("Controller A CPU load"),
    unit=_PERCENT,
    color=Color.BLUE,
)

metric_dell_me5_controller_b_cpu_load = Metric(
    name="dell_me5_controller_b_cpu_load",
    title=Title("Controller B CPU load"),
    unit=_PERCENT,
    color=Color.CYAN,
)

# ------------------------------------------------------------ supercapacitor
metric_dell_me5_supercap_charge_percent = Metric(
    name="dell_me5_supercap_charge_percent",
    title=Title("Supercapacitor charge"),
    unit=_PERCENT,
    color=Color.GREEN,
)

metric_dell_me5_supercap_capacitance = Metric(
    name="dell_me5_supercap_capacitance",
    title=Title("Supercapacitor capacitance"),
    unit=_FARAD,
    color=Color.BLUE,
)

metric_dell_me5_supercap_resistance = Metric(
    name="dell_me5_supercap_resistance",
    title=Title("Supercapacitor internal resistance"),
    unit=_OHM,
    color=Color.ORANGE,
)

metric_dell_me5_supercap_pack_voltage = Metric(
    name="dell_me5_supercap_pack_voltage",
    title=Title("Supercapacitor pack voltage"),
    unit=_VOLT,
    color=Color.PURPLE,
)

# --------------------------------------------------------------- enclosures
metric_dell_me5_enclosure_power = Metric(
    name="dell_me5_enclosure_power",
    title=Title("Enclosure power"),
    unit=_WATT,
    color=Color.ORANGE,
)

# ------------------------------------------------------- snapshots/schedules
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
    unit=_SECONDS,
    color=Color.CYAN,
)

metric_dell_me5_schedule_overdue = Metric(
    name="dell_me5_schedule_overdue",
    title=Title("Schedule overdue by"),
    unit=_SECONDS,
    color=Color.RED,
)

metric_dell_me5_schedule_last_run_age = Metric(
    name="dell_me5_schedule_last_run_age",
    title=Title("Time since last scheduled run"),
    unit=_SECONDS,
    color=Color.BLUE,
)

# ------------------------------------------------------------- health alerts
metric_dell_me5_health_alerts = Metric(
    name="dell_me5_health_alerts",
    title=Title("Unresolved health alerts"),
    unit=_COUNT,
    color=Color.RED,
)


# ===========================================================================
# Graphs
# ===========================================================================

graph_dell_me5_unwritable_cache = Graph(
    name="dell_me5_unwritable_cache",
    title=Title("ME5 unwritable cache per controller"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=[
        "dell_me5_unwritable_cache_a_percent",
        "dell_me5_unwritable_cache_b_percent",
    ],
)

graph_dell_me5_system_iops = Graph(
    name="dell_me5_system_iops",
    title=Title("ME5 system IOPS"),
    simple_lines=[
        "dell_me5_system_read_iops",
        "dell_me5_system_write_iops",
        "dell_me5_system_iops",
    ],
)

graph_dell_me5_system_throughput = Graph(
    name="dell_me5_system_throughput",
    title=Title("ME5 system throughput"),
    simple_lines=[
        "dell_me5_system_read_throughput",
        "dell_me5_system_write_throughput",
        "dell_me5_system_throughput",
    ],
)

graph_dell_me5_system_latency = Graph(
    name="dell_me5_system_latency",
    title=Title("ME5 system response time"),
    simple_lines=[
        "dell_me5_system_read_latency",
        "dell_me5_system_write_latency",
        "dell_me5_system_latency",
    ],
)

graph_dell_me5_controller_cpu = Graph(
    name="dell_me5_controller_cpu",
    title=Title("ME5 controller CPU load"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=[
        "dell_me5_controller_a_cpu_load",
        "dell_me5_controller_b_cpu_load",
    ],
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

graph_dell_me5_volume_iops = Graph(
    name="dell_me5_volume_iops",
    title=Title("ME5 volume IOPS"),
    simple_lines=[
        "dell_me5_volume_read_iops",
        "dell_me5_volume_write_iops",
        "dell_me5_volume_iops",
    ],
)

graph_dell_me5_volume_throughput = Graph(
    name="dell_me5_volume_throughput",
    title=Title("ME5 volume throughput"),
    simple_lines=[
        "dell_me5_volume_read_throughput",
        "dell_me5_volume_write_throughput",
        "dell_me5_volume_throughput",
    ],
)

graph_dell_me5_volume_cache_hits = Graph(
    name="dell_me5_volume_cache_hits",
    title=Title("ME5 volume cache hit ratio"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=[
        "dell_me5_volume_read_cache_hit_ratio",
        "dell_me5_volume_write_cache_hit_ratio",
    ],
)

graph_dell_me5_disk_errors = Graph(
    name="dell_me5_disk_errors",
    title=Title("ME5 disk error counters"),
    simple_lines=[
        "dell_me5_disk_smart_errors",
        "dell_me5_disk_media_errors",
        "dell_me5_disk_nonmedia_errors",
        "dell_me5_disk_bad_blocks",
        "dell_me5_disk_block_reassigns",
        "dell_me5_disk_spinup_retries",
        "dell_me5_disk_io_timeouts",
        "dell_me5_disk_no_response",
    ],
)

graph_dell_me5_supercapacitor = Graph(
    name="dell_me5_supercapacitor",
    title=Title("ME5 supercapacitor condition"),
    simple_lines=[
        "dell_me5_supercap_capacitance",
        "dell_me5_supercap_resistance",
        "dell_me5_supercap_pack_voltage",
    ],
)


# ===========================================================================
# Perfometers
# ===========================================================================

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

perfometer_dell_me5_supercap_charge = Perfometer(
    name="dell_me5_supercap_charge_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["dell_me5_supercap_charge_percent"],
)

perfometer_dell_me5_enclosure_power = Perfometer(
    name="dell_me5_enclosure_power",
    focus_range=FocusRange(Closed(0), Closed(1000)),
    segments=["dell_me5_enclosure_power"],
)
