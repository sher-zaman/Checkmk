#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
###############################################################################
# fortiswitch_health - Graphing definitions
###############################################################################
# Author: Sher Zaman (sher_zaman@outlook.com), FirmaTrust
###############################################################################
#
# CPU (util), memory (mem_used_percent) and temperature (temp) use
# Checkmk's built-in metric names and inherit the stock graphs and
# perfometers. Only the fan speed metric is plugin-specific.
#
from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, Unit
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

metric_fortiswitch_fan_speed_percent = Metric(
    name="fortiswitch_fan_speed_percent",
    title=Title("Fan speed"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)

graph_fortiswitch_fan_speed = Graph(
    name="fortiswitch_fan_speed",
    title=Title("FortiSwitch fan speed"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=["fortiswitch_fan_speed_percent"],
)

perfometer_fortiswitch_fan_speed = Perfometer(
    name="fortiswitch_fan_speed_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["fortiswitch_fan_speed_percent"],
)

metric_fortiswitch_sfp_rx_dbm = Metric(
    name="fortiswitch_sfp_rx_dbm",
    title=Title("RX power"),
    unit=Unit(DecimalNotation("dBm")),
    color=Color.GREEN,
)

metric_fortiswitch_sfp_tx_dbm = Metric(
    name="fortiswitch_sfp_tx_dbm",
    title=Title("TX power"),
    unit=Unit(DecimalNotation("dBm")),
    color=Color.ORANGE,
)

metric_fortiswitch_sfp_temp = Metric(
    name="fortiswitch_sfp_temp",
    title=Title("Transceiver temperature"),
    unit=Unit(DecimalNotation("°C")),
    color=Color.RED,
)

metric_fortiswitch_sfp_voltage = Metric(
    name="fortiswitch_sfp_voltage",
    title=Title("Supply voltage"),
    unit=Unit(DecimalNotation("V")),
    color=Color.PURPLE,
)

metric_fortiswitch_sfp_bias = Metric(
    name="fortiswitch_sfp_bias",
    title=Title("Laser bias current"),
    unit=Unit(DecimalNotation("mA")),
    color=Color.CYAN,
)

graph_fortiswitch_sfp_power = Graph(
    name="fortiswitch_sfp_power",
    title=Title("SFP optical power"),
    simple_lines=["fortiswitch_sfp_tx_dbm", "fortiswitch_sfp_rx_dbm"],
)

perfometer_fortiswitch_sfp_rx = Perfometer(
    name="fortiswitch_sfp_rx_dbm",
    focus_range=FocusRange(Closed(-25), Closed(5)),
    segments=["fortiswitch_sfp_rx_dbm"],
)
