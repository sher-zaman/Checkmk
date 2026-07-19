#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Checkmk graphing: Windows DHCP failover relationships
#
# Author: Sher Zaman (FirmaTrust)
# License: GPLv2

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, Unit

metric_dhcp_failover_scopes = Metric(
    name="dhcp_failover_scopes",
    title=Title("Scopes in failover relationship"),
    unit=Unit(DecimalNotation("")),
    color=Color.BLUE,
)
