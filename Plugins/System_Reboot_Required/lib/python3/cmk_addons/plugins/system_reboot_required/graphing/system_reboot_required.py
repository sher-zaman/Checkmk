# system_reboot_required - CheckMK graphing definitions
#
# Copyright (C) 2026  Sher Zaman - FirmaTrust (szaman@iceconsulting.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, Metric, TimeNotation, Unit
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer

UNIT_TIME = Unit(TimeNotation())

metric_system_reboot_pending_age = Metric(
    name="system_reboot_pending_age",
    title=Title("Pending reboot age"),
    unit=UNIT_TIME,
    color=Color.ORANGE,
)

perfometer_system_reboot_pending_age = Perfometer(
    name="system_reboot_pending_age",
    focus_range=FocusRange(Closed(0), Open(172800.0)),
    segments=["system_reboot_pending_age"],
)
