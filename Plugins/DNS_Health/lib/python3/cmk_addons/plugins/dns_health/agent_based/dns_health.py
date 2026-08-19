#!/usr/bin/env python3
# Author:   Sher Zaman
# Company:  FirmaTRUST | Managed IT and Cybersecurity
# Email:    sher[at]sherz[dot]dev
# Website:  https://sherz.dev
# LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/
# Repo:     https://github.com/sher-zaman/Checkmk
#
# All state lives here rather than in the agent. Baselines are held in the
# Checkmk value store, which is scoped per service and per item, so no files
# are written and no filenames can collide between domains.

from __future__ import annotations

import json
import time
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    get_value_store,
    render,
)

# Types where an unexpected change has no routine explanation. Everything else
# moves for ordinary reasons: CDN changes, mail migrations, and the constant
# churn of vendor verification records in TXT.
DEFAULT_CHANGE_STATES = {
    "A": 1,
    "AAAA": 1,
    "MX": 1,
    "TXT": 1,
    "NS": 2,
    "SOA": 1,
    "CNAME": 1,
    "PTR": 1,
}

# A long TXT set would otherwise push the service output past what Checkmk
# will store. alector.com already carries 24 records.
MAX_DIFF_LINES = 25

# How long a detected change keeps alarming before the new values are accepted
# as the baseline. Holding indefinitely means every legitimate change needs
# manual intervention, and accepting immediately means the alarm can be missed
# entirely. A window gives an alert that cannot be missed and still self-heals.
# None means never accept automatically.
DEFAULT_HOLD_SECONDS = 7 * 24 * 3600

# The ruleset stores states as names rather than integers, because
# cmk.rulesets.v1.form_specs.ServiceState is not guaranteed present across the
# supported range and a bad import breaks ruleset migration at install time.
# Both forms are accepted here so defaults and rule values behave identically.
_STATE_NAMES = {"ok": 0, "warn": 1, "crit": 2, "unknown": 3}


def _count(n: int, word: str, plural: str | None = None) -> str:
    """Service summaries are public-facing on every check, so "1 record(s)" is
    not acceptable output. Zero reads as "No records" rather than "0 records"."""
    many = plural or word + "s"
    if n == 0:
        return f"No {many}"
    if n == 1:
        return f"1 {word}"
    return f"{n} {many}"


def _as_state(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value if 0 <= value <= 3 else default
    if isinstance(value, str):
        return _STATE_NAMES.get(value.strip().lower(), default)
    return default


def _hold_seconds(params: dict[str, Any]) -> float | None:
    """Accepts the cascading ruleset value, a plain number of seconds, or None
    meaning never accept automatically."""
    value = params.get("hold_duration", DEFAULT_HOLD_SECONDS)
    if value is None:
        return None
    if isinstance(value, bool):
        return float(DEFAULT_HOLD_SECONDS)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (tuple, list)) and len(value) == 2:
        kind, inner = value
        if kind == "never":
            return None
        if kind == "immediate":
            return 0.0
        if kind == "after":
            days = inner.get("days", 7) if isinstance(inner, dict) else inner
            try:
                return float(days) * 86400.0
            except (TypeError, ValueError):
                return float(DEFAULT_HOLD_SECONDS)
    return float(DEFAULT_HOLD_SECONDS)


def _parse_json_section(string_table: StringTable) -> dict[str, Any] | None:
    if not string_table:
        return None
    blob = "".join(part for row in string_table for part in row)
    if not blob.strip():
        return None
    try:
        parsed = json.loads(blob)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


agent_section_dns_health_records = AgentSection(
    name="dns_health_records",
    parse_function=_parse_json_section,
)

agent_section_dns_health_delegation = AgentSection(
    name="dns_health_delegation",
    parse_function=_parse_json_section,
)


# --------------------------------------------------------------- record drift


def discover_dns_health_records(section: dict[str, Any] | None) -> DiscoveryResult:
    if not section:
        return
    for rtype in sorted(section.get("types", {})):
        yield Service(item=rtype)


def _strip_soa_serial(records: list[str]) -> list[str]:
    """The SOA serial increments on every zone edit, so comparing it to a
    stored value alarms on routine changes. Formats also vary by provider,
    counter style on some, date style on others, so it is masked rather than
    interpreted."""
    out = []
    for rec in records:
        parts = rec.split()
        if len(parts) >= 7:
            parts[2] = "<serial>"
            out.append(" ".join(parts))
        else:
            out.append(rec)
    return out


def _diff(baseline: list[str], current: list[str]) -> tuple[list[str], list[str]]:
    b, c = set(baseline), set(current)
    return sorted(c - b), sorted(b - c)


def check_dns_health_records(
    item: str, params: dict[str, Any], section: dict[str, Any] | None
) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data from agent")
        return

    if section.get("error"):
        yield Result(state=State.UNKNOWN, summary=str(section["error"]))
        return

    entry = section.get("types", {}).get(item)
    if entry is None:
        yield Result(state=State.UNKNOWN, summary="Record type not in agent output")
        return

    change_states = params.get("change_states") or DEFAULT_CHANGE_STATES
    ignore_serial = params.get("ignore_soa_serial", True)
    state_vanished = _as_state(params.get("state_vanished"), 2)
    state_nxdomain = _as_state(params.get("state_nxdomain"), 2)
    state_diverged = _as_state(params.get("state_diverged"), 1)

    rcodes = entry.get("rcodes") or []
    agreed = entry.get("agreed")
    diverged = bool(entry.get("diverged"))
    answered = entry.get("servers_answered", 0)
    queried = entry.get("servers_queried", 0)

    store = get_value_store()
    baseline = store.get("baseline")

    # Measurement failure, not a content finding. Nothing is compared and the
    # baseline is left untouched, because an unreachable server must never be
    # allowed to overwrite a known-good baseline with nothing.
    if answered == 0:
        errs = {
            s.get("error")
            for s in entry.get("per_server", {}).values()
            if s.get("error")
        }
        detail = "; ".join(sorted(e for e in errs if e)) or "no server answered"
        yield Result(
            state=State.UNKNOWN,
            summary=f"No authoritative answer ({_count(queried, 'server')} queried)",
            details=detail,
        )
        return

    if diverged:
        # Servers disagree. Report it and hold the baseline: re-recording here
        # would flap between the two answers on alternate runs.
        per = entry.get("per_server", {})
        lines = [
            f"{name}: {', '.join(d.get('records') or []) or '(none)'}"
            for name, d in sorted(per.items())
        ]
        yield Result(
            state=State(state_diverged),
            summary=f"Authoritative servers disagree on {item}, baseline held",
            details="\n".join(lines),
        )
        yield from _metrics(entry)
        return

    if "NXDOMAIN" in rcodes:
        if baseline is not None:
            yield Result(
                state=State(state_nxdomain),
                summary="Domain does not exist (NXDOMAIN), baseline existed",
            )
        else:
            yield Result(state=State.OK, summary="Domain does not exist (NXDOMAIN)")
        yield from _metrics(entry)
        return

    current = list(agreed or [])
    compare_current = current
    compare_baseline = baseline
    if item == "SOA" and ignore_serial:
        compare_current = _strip_soa_serial(current)
        if baseline is not None:
            compare_baseline = _strip_soa_serial(list(baseline))

    if baseline is None:
        # Stated explicitly rather than reported as a bare OK, so that a
        # baseline being re-recorded after a host rebuild or item change is a
        # visible event in the service history rather than a silent reset.
        store["baseline"] = current
        yield Result(
            state=State.OK,
            summary=f"Baseline recorded on this run, {_count(len(current), 'record')}",
            details=_record_block(current),
        )
        yield from _metrics(entry)
        return

    if compare_current == list(compare_baseline):
        # Drift that has gone away, because someone reverted the change during
        # the hold window. No manual step needed.
        if store.get("pending_since") is not None:
            store["pending_since"] = None
        extra = ""
        if item == "SOA" and ignore_serial:
            serial = _serial_of(entry)
            extra = f", serial {serial}" if serial is not None else ""
        yield Result(
            state=State.OK,
            summary=f"{_count(len(current), 'record')}, unchanged{extra}",
            details=_record_block(current),
        )
        yield from _metrics(entry)
        return

    added, removed = _diff(list(compare_baseline), compare_current)

    # Age of this drift. Set on first sighting and kept until the change is
    # either accepted or reverted, so a second change during the window still
    # diffs against the last accepted baseline and shows cumulative drift.
    now = time.time()
    pending_since = store.get("pending_since")
    if pending_since is None:
        pending_since = now
        store["pending_since"] = now
    age = max(0.0, now - pending_since)

    hold = _hold_seconds(params)
    expired = hold is not None and age >= hold

    vanished = current == [] and list(baseline)

    if vanished:
        base_state = State(state_vanished)
        n_gone = len(baseline)
        headline = (
            f"The only {item} record has disappeared"
            if n_gone == 1
            else f"All {n_gone} {item} records have disappeared"
        )
        detail = _record_block(list(baseline), prefix="was: ")
    else:
        base_state = State(
            _as_state(
                change_states.get(item), DEFAULT_CHANGE_STATES.get(item, 1)
            )
        )
        headline = f"Changed: {len(added)} added, {len(removed)} removed"
        lines: list[str] = [f"+ {r}" for r in added[:MAX_DIFF_LINES]]
        lines += [f"- {r}" for r in removed[:MAX_DIFF_LINES]]
        hidden = max(0, len(added) - MAX_DIFF_LINES) + max(
            0, len(removed) - MAX_DIFF_LINES
        )
        if hidden:
            lines.append(f"... {_count(hidden, 'further difference')} not shown")
        detail = "\n".join(lines)

    if expired:
        # The window has run out. Accept the new values so the service can
        # return to OK, and say so plainly rather than going quiet, since the
        # transition from alarming to accepted is itself worth recording.
        store["baseline"] = current
        store["pending_since"] = None
        accepted = (
            f"{headline}, accepted as new baseline after {render.timespan(age)}"
            if age >= 60
            else f"{headline}, accepted as new baseline"
        )
        yield Result(state=State.OK, summary=accepted, details=detail)
        yield from _metrics(entry)
        return

    if age >= 60:
        headline = f"{headline}, pending for {render.timespan(age)}"

    yield Result(state=base_state, summary=headline, details=detail)
    yield from _metrics(entry)


def _serial_of(entry: dict[str, Any]) -> int | None:
    soa = entry.get("soa") or []
    for s in soa:
        if isinstance(s, dict) and "serial" in s:
            return s["serial"]
    return None


def _record_block(records: list[str], prefix: str = "") -> str:
    if not records:
        return "(none)"
    shown = records[:MAX_DIFF_LINES]
    out = [f"{prefix}{r}" for r in shown]
    if len(records) > len(shown):
        out.append(f"... {len(records) - len(shown)} more")
    return "\n".join(out)


def _metrics(entry: dict[str, Any]) -> CheckResult:
    """Query time is for trending only. Observed variance on identical queries
    is roughly ten to one, so thresholds on it would produce permanent noise.
    This is stated in the check manual as well."""
    times = [
        s["elapsed_ms"]
        for s in entry.get("per_server", {}).values()
        if s.get("elapsed_ms") is not None
    ]
    if times:
        yield Metric("dns_health_query_time", max(times) / 1000.0)
    agreed = entry.get("agreed")
    if agreed is not None:
        yield Metric("dns_health_record_count", float(len(agreed)))


check_plugin_dns_health_records = CheckPlugin(
    name="dns_health_records",
    service_name="DNS Records %s",
    sections=["dns_health_records"],
    discovery_function=discover_dns_health_records,
    check_function=check_dns_health_records,
    check_ruleset_name="dns_health_records",
    check_default_parameters={
        "change_states": DEFAULT_CHANGE_STATES,
        "ignore_soa_serial": True,
        "state_vanished": 2,
        "state_nxdomain": 2,
        "state_diverged": 1,
        "hold_duration": DEFAULT_HOLD_SECONDS,
    },
)


# ------------------------------------------------------------------ delegation


def discover_dns_health_delegation(section: dict[str, Any] | None) -> DiscoveryResult:
    if section:
        yield Service()


def check_dns_health_delegation(
    params: dict[str, Any], section: dict[str, Any] | None
) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No data from agent")
        return

    state_ns_mismatch = _as_state(params.get("state_ns_mismatch"), 1)
    state_glue_mismatch = _as_state(params.get("state_glue_mismatch"), 1)

    if section.get("error"):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Delegation could not be checked: {section['error']}",
        )
        return

    parent_ns = set(section.get("parent_ns") or [])
    zone_ns = set(section.get("zone_ns") or [])
    parent_zone = section.get("parent_zone") or "parent"

    if not parent_ns:
        yield Result(state=State.UNKNOWN, summary="Parent published no delegation")
        return

    problems = False

    if not zone_ns:
        yield Result(
            state=State.UNKNOWN,
            summary="Zone did not return its own NS records for comparison",
        )
    elif parent_ns == zone_ns:
        yield Result(
            state=State.OK,
            summary=f"Parent ({parent_zone.rstrip('.')}) and zone agree on "
            f"{_count(len(parent_ns), 'nameserver')}",
            details="\n".join(sorted(parent_ns)),
        )
    else:
        problems = True
        only_parent = sorted(parent_ns - zone_ns)
        only_zone = sorted(zone_ns - parent_ns)
        lines = [f"only at parent: {n}" for n in only_parent]
        lines += [f"only in zone: {n}" for n in only_zone]
        yield Result(
            state=State(state_ns_mismatch),
            summary=f"Delegation mismatch: {len(only_parent)} only at parent, "
            f"{len(only_zone)} only in zone",
            details="\n".join(lines),
        )

    # Glue is compared against an independent resolution of each nameserver
    # name. A null match means no glue was published, which is normal for
    # out-of-bailiwick nameservers and is not a fault.
    bad = [g for g in section.get("glue") or [] if g.get("match") is False]
    checked = [g for g in section.get("glue") or [] if g.get("match") is not None]

    if bad:
        problems = True
        lines = []
        for g in bad:
            lines.append(
                f"{g.get('name')}: parent glue "
                f"{', '.join(g.get('parent_glue') or []) or '(none)'} "
                f"but resolves to {', '.join(g.get('resolved') or []) or '(none)'}"
            )
        yield Result(
            state=State(state_glue_mismatch),
            summary=f"Glue mismatch on {_count(len(bad), 'nameserver')}",
            details="\n".join(lines),
        )
    elif checked:
        yield Result(
            state=State.OK, summary=f"Glue verified on {_count(len(checked), 'nameserver')}"
        )

    if not problems and not checked:
        yield Result(state=State.OK, summary="No glue published, nothing to verify")


check_plugin_dns_health_delegation = CheckPlugin(
    name="dns_health_delegation",
    service_name="DNS Zone Delegation",
    sections=["dns_health_delegation"],
    discovery_function=discover_dns_health_delegation,
    check_function=check_dns_health_delegation,
    check_ruleset_name="dns_health_delegation",
    check_default_parameters={
        "state_ns_mismatch": 1,
        "state_glue_mismatch": 1,
    },
)
