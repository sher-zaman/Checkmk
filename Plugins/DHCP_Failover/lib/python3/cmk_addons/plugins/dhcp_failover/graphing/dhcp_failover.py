#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Checkmk graphing: Windows DHCP failover relationships
#
# Author:   Sher Zaman
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# License:  GPL-2.0-only

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, Unit

metric_dhcp_failover_scopes = Metric(
    name="dhcp_failover_scopes",
    title=Title("Scopes in failover relationship"),
    unit=Unit(DecimalNotation("")),
    color=Color.BLUE,
)
