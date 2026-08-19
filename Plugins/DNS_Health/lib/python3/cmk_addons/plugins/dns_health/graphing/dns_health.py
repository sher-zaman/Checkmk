#!/usr/bin/env python3
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# Metric names are prefixed with the package name rather than a company name.
# Checkmk ships roughly a thousand built-in metrics and unprefixed names
# collide silently, and a company prefix would read oddly on someone else's
# site. Renaming later would need translation entries to keep history.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    Metric,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer

UNIT_TIME = Unit(TimeNotation())
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))

metric_dns_health_query_time = Metric(
    name="dns_health_query_time",
    title=Title("DNS query time"),
    unit=UNIT_TIME,
    color=Color.BLUE,
)

metric_dns_health_record_count = Metric(
    name="dns_health_record_count",
    title=Title("Records returned"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

graph_dns_health_query_time = Graph(
    name="dns_health_query_time",
    title=Title("DNS query time"),
    simple_lines=["dns_health_query_time"],
    minimal_range=MinimalRange(0, 0.5),
)

graph_dns_health_record_count = Graph(
    name="dns_health_record_count",
    title=Title("Records returned"),
    simple_lines=["dns_health_record_count"],
    minimal_range=MinimalRange(0, 10),
)

# Slowest of the authoritative servers, since that is what a resolver would
# wait for in the worst case. Observed variance on identical queries is roughly
# ten to one, so this is a trend indicator and thresholds on it are a bad idea.
perfometer_dns_health_query_time = Perfometer(
    name="dns_health_query_time",
    focus_range=FocusRange(Closed(0), Open(0.25)),
    segments=["dns_health_query_time"],
)
