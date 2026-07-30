#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Metric, graph and perfometer definitions for the VCSA health plugin.
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License: GPL-2.0-only

from cmk.graphing.v1 import graphs, Title
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer

UNIT_PERCENT = Unit(DecimalNotation("%"))
UNIT_BYTES = Unit(IECNotation("B"))
UNIT_TIME = Unit(TimeNotation())
UNIT_BANDWIDTH = Unit(IECNotation("B/s"))
UNIT_PER_SEC = Unit(DecimalNotation("/s"), StrictPrecision(1))
# Packet errors and drops are reported by the appliance as per-sample counts
# (errors_per_sample, drops_per_sample), not as rates, so they must not carry
# a "/s" label.
UNIT_PER_SAMPLE = Unit(DecimalNotation(""), StrictPrecision(1))
UNIT_PAGES_PER_SEC = Unit(DecimalNotation("pages/s"), StrictPrecision(1))
# Clock drift is typically sub-second, so TimeNotation would round it to
# zero. A decimal seconds unit keeps the resolution that matters.
UNIT_SECONDS = Unit(DecimalNotation("s"), StrictPrecision(2))
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))

metric_vcsa_cpu_util = Metric(
    name="vcsa_cpu_util",
    title=Title("VCSA CPU utilization"),
    unit=UNIT_PERCENT,
    color=Color.BLUE,
)

metric_vcsa_mem_util = Metric(
    name="vcsa_mem_util",
    title=Title("VCSA memory utilization"),
    unit=UNIT_PERCENT,
    color=Color.GREEN,
)

metric_vcsa_cpu_steal = Metric(
    name="vcsa_cpu_steal",
    title=Title("VCSA CPU steal"),
    unit=UNIT_PERCENT,
    color=Color.RED,
)

metric_vcsa_swap_page_rate = Metric(
    name="vcsa_swap_page_rate",
    title=Title("VCSA swap page rate"),
    unit=UNIT_PAGES_PER_SEC,
    color=Color.DARK_ORANGE,
)

# Memory used and total in bytes. Note the appliance metric names are
# counterintuitive: mem.usage is the percentage, while mem.util and mem.total
# are byte counts in kb. These two carry the byte values.
metric_vcsa_mem_used = Metric(
    name="vcsa_mem_used",
    title=Title("VCSA memory used"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

metric_vcsa_mem_total = Metric(
    name="vcsa_mem_total",
    title=Title("VCSA memory total"),
    unit=UNIT_BYTES,
    color=Color.DARK_GREEN,
)

graph_vcsa_memory = graphs.Graph(
    name="vcsa_memory",
    title=Title("VCSA memory utilization"),
    simple_lines=["vcsa_mem_util"],
)

# Used as a filled area against total as a line, so headroom is visible
# directly rather than inferred from a percentage.
graph_vcsa_memory_bytes = graphs.Graph(
    name="vcsa_memory_bytes",
    title=Title("VCSA memory used and total"),
    compound_lines=["vcsa_mem_used"],
    simple_lines=["vcsa_mem_total"],
)

# CPU utilization and steal share a unit and a service, so they belong on one
# graph: utilization shows how busy the appliance is, steal shows how much CPU
# the host denied it. Reading them together is what distinguishes a busy
# appliance from a starved one.
graph_vcsa_cpu = graphs.Graph(
    name="vcsa_cpu",
    title=Title("VCSA CPU utilization and steal"),
    simple_lines=["vcsa_cpu_util", "vcsa_cpu_steal"],
)

metric_vcsa_fs_used_percent = Metric(
    name="vcsa_fs_used_percent",
    title=Title("VCSA filesystem used"),
    unit=UNIT_PERCENT,
    color=Color.PURPLE,
)

metric_vcsa_fs_used = Metric(
    name="vcsa_fs_used",
    title=Title("VCSA filesystem used space"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

metric_vcsa_backup_age = Metric(
    name="vcsa_backup_age",
    title=Title("VCSA backup age"),
    unit=UNIT_TIME,
    color=Color.BROWN,
)

metric_vcsa_cert_remaining = Metric(
    name="vcsa_cert_remaining",
    title=Title("VCSA certificate remaining validity"),
    unit=UNIT_TIME,
    color=Color.YELLOW,
)

perfometer_vcsa_cpu_util = Perfometer(
    name="vcsa_cpu_util",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["vcsa_cpu_util"],
)

perfometer_vcsa_mem_util = Perfometer(
    name="vcsa_mem_util",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["vcsa_mem_util"],
)

perfometer_vcsa_fs_used_percent = Perfometer(
    name="vcsa_fs_used_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["vcsa_fs_used_percent"],
)

perfometer_vcsa_backup_age = Perfometer(
    name="vcsa_backup_age",
    focus_range=FocusRange(Closed(0), Open(180000)),
    segments=["vcsa_backup_age"],
)

perfometer_vcsa_cert_remaining = Perfometer(
    name="vcsa_cert_remaining",
    focus_range=FocusRange(Closed(0), Open(7776000)),
    segments=["vcsa_cert_remaining"],
)

metric_vcsa_update_check_age = Metric(
    name="vcsa_update_check_age",
    title=Title("VCSA time since last update check"),
    unit=UNIT_TIME,
    color=Color.LIGHT_PURPLE,
)

perfometer_vcsa_update_check_age = Perfometer(
    name="vcsa_update_check_age",
    focus_range=FocusRange(Closed(0), Open(2592000)),
    segments=["vcsa_update_check_age"],
)

metric_vcsa_root_password_remaining = Metric(
    name="vcsa_root_password_remaining",
    title=Title("VCSA root password remaining validity"),
    unit=UNIT_TIME,
    color=Color.ORANGE,
)

perfometer_vcsa_root_password_remaining = Perfometer(
    name="vcsa_root_password_remaining",
    focus_range=FocusRange(Closed(0), Open(7776000)),
    segments=["vcsa_root_password_remaining"],
)

metric_vcsa_ntp_servers_reachable = Metric(
    name="vcsa_ntp_servers_reachable",
    title=Title("VCSA reachable NTP servers"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_vcsa_dns_servers = Metric(
    name="vcsa_dns_servers",
    title=Title("VCSA configured DNS servers"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_vcsa_time_drift = Metric(
    name="vcsa_time_drift",
    title=Title("VCSA clock drift"),
    unit=UNIT_SECONDS,
    color=Color.PURPLE,
)

# vCenter database usage by category. No default thresholds are set on these
# because the appliance does not document what the percentage is relative to.
metric_vcsa_db_stats_util = Metric(
    name="vcsa_db_stats_util",
    title=Title("VCSA database stats usage"),
    unit=UNIT_PERCENT,
    color=Color.BLUE,
)

metric_vcsa_db_events_util = Metric(
    name="vcsa_db_events_util",
    title=Title("VCSA database events usage"),
    unit=UNIT_PERCENT,
    color=Color.GREEN,
)

metric_vcsa_db_alarms_util = Metric(
    name="vcsa_db_alarms_util",
    title=Title("VCSA database alarms usage"),
    unit=UNIT_PERCENT,
    color=Color.ORANGE,
)

metric_vcsa_db_tasks_util = Metric(
    name="vcsa_db_tasks_util",
    title=Title("VCSA database tasks usage"),
    unit=UNIT_PERCENT,
    color=Color.PURPLE,
)

metric_vcsa_db_stats_hourly = Metric(
    name="vcsa_db_stats_hourly",
    title=Title("VCSA database hourly stats size"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_BLUE,
)

metric_vcsa_db_stats_daily = Metric(
    name="vcsa_db_stats_daily",
    title=Title("VCSA database daily stats size"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_vcsa_db_stats_monthly = Metric(
    name="vcsa_db_stats_monthly",
    title=Title("VCSA database monthly stats size"),
    unit=UNIT_BYTES,
    color=Color.DARK_BLUE,
)

metric_vcsa_db_stats_yearly = Metric(
    name="vcsa_db_stats_yearly",
    title=Title("VCSA database yearly stats size"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)

graph_vcsa_db_usage = graphs.Graph(
    name="vcsa_db_usage",
    title=Title("VCSA database usage by category"),
    simple_lines=[
        "vcsa_db_stats_util",
        "vcsa_db_events_util",
        "vcsa_db_alarms_util",
        "vcsa_db_tasks_util",
    ],
)

# Retention tiers stacked, so a too-high statistics level shows up as the
# hourly tier dominating the total.
graph_vcsa_db_stats_retention = graphs.Graph(
    name="vcsa_db_stats_retention",
    title=Title("VCSA database statistics by retention tier"),
    compound_lines=[
        "vcsa_db_stats_hourly",
        "vcsa_db_stats_daily",
        "vcsa_db_stats_monthly",
        "vcsa_db_stats_yearly",
    ],
)

# Per-interface network metrics
metric_vcsa_if_in = Metric(
    name="vcsa_if_in",
    title=Title("VCSA interface throughput in"),
    unit=UNIT_BANDWIDTH,
    color=Color.GREEN,
)

metric_vcsa_if_out = Metric(
    name="vcsa_if_out",
    title=Title("VCSA interface throughput out"),
    unit=UNIT_BANDWIDTH,
    color=Color.BLUE,
)

metric_vcsa_if_in_packets = Metric(
    name="vcsa_if_in_packets",
    title=Title("VCSA interface packet rate in"),
    unit=UNIT_PER_SEC,
    color=Color.LIGHT_GREEN,
)

metric_vcsa_if_out_packets = Metric(
    name="vcsa_if_out_packets",
    title=Title("VCSA interface packet rate out"),
    unit=UNIT_PER_SEC,
    color=Color.LIGHT_BLUE,
)

metric_vcsa_if_in_errors = Metric(
    name="vcsa_if_in_errors",
    title=Title("VCSA interface errors in (per sample)"),
    unit=UNIT_PER_SAMPLE,
    color=Color.RED,
)

metric_vcsa_if_out_errors = Metric(
    name="vcsa_if_out_errors",
    title=Title("VCSA interface errors out (per sample)"),
    unit=UNIT_PER_SAMPLE,
    color=Color.DARK_RED,
)

metric_vcsa_if_in_drops = Metric(
    name="vcsa_if_in_drops",
    title=Title("VCSA interface drops in (per sample)"),
    unit=UNIT_PER_SAMPLE,
    color=Color.ORANGE,
)

metric_vcsa_if_out_drops = Metric(
    name="vcsa_if_out_drops",
    title=Title("VCSA interface drops out (per sample)"),
    unit=UNIT_PER_SAMPLE,
    color=Color.DARK_ORANGE,
)

# Bidirectional graphs: outbound values are mirrored below the axis, which
# makes traffic patterns easier to read than two lines in the same direction.
graph_vcsa_if_throughput = graphs.Bidirectional(
    name="vcsa_if_throughput",
    title=Title("VCSA interface throughput"),
    lower=graphs.Graph(
        name="vcsa_if_throughput_out",
        title=Title("VCSA interface throughput out"),
        compound_lines=["vcsa_if_out"],
    ),
    upper=graphs.Graph(
        name="vcsa_if_throughput_in",
        title=Title("VCSA interface throughput in"),
        compound_lines=["vcsa_if_in"],
    ),
)

graph_vcsa_if_packets = graphs.Bidirectional(
    name="vcsa_if_packets",
    title=Title("VCSA interface packet rate"),
    lower=graphs.Graph(
        name="vcsa_if_packets_out",
        title=Title("VCSA interface packet rate out"),
        compound_lines=["vcsa_if_out_packets"],
    ),
    upper=graphs.Graph(
        name="vcsa_if_packets_in",
        title=Title("VCSA interface packet rate in"),
        compound_lines=["vcsa_if_in_packets"],
    ),
)

graph_vcsa_if_errors = graphs.Graph(
    name="vcsa_if_errors_drops",
    title=Title("VCSA interface errors and drops"),
    simple_lines=[
        "vcsa_if_in_errors",
        "vcsa_if_out_errors",
        "vcsa_if_in_drops",
        "vcsa_if_out_drops",
    ],
)

perfometer_vcsa_if_throughput = Perfometer(
    name="vcsa_if_throughput",
    focus_range=FocusRange(Closed(0), Open(12500000)),
    segments=["vcsa_if_in", "vcsa_if_out"],
)
