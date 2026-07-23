#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Metric, graph and perfometer definitions for the VCSA health plugin.
#
# Copyright (C) 2026 Sher Zaman <sher_zaman@outlook.com>
# License: GPL-2.0-only

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    TimeNotation,
    Unit,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer

UNIT_PERCENT = Unit(DecimalNotation("%"))
UNIT_BYTES = Unit(IECNotation("B"))
UNIT_TIME = Unit(TimeNotation())

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

metric_vcsa_swap_util = Metric(
    name="vcsa_swap_util",
    title=Title("VCSA swap utilization"),
    unit=UNIT_PERCENT,
    color=Color.ORANGE,
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

perfometer_vcsa_swap_util = Perfometer(
    name="vcsa_swap_util",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["vcsa_swap_util"],
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
