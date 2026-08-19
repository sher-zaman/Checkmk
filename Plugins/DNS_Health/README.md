# DNS Health

Checkmk extension for monitoring DNS record drift and zone delegation by querying a domain's authoritative nameservers directly.

## Attribution

The 3.x `dns_record_monitor` extension this replaces was written by Waqar Ahmed. This is a rewrite rather than a patch: the collection method, service layout, state handling and package name all changed. The original active check remains the origin of the idea and of the record drift approach.

## Changes in this fork

- Rewritten as a special agent with one service per record type, replacing a single active check that reported every type in one service and exceeded Checkmk's output limit on domains with many records.
- Records are read from the authoritative nameservers rather than the local resolver, so a change is visible immediately rather than after the record's TTL expires.
- The nameserver list is taken from the parent zone's delegation, so an altered NS record cannot redirect the check to servers of its own choosing.
- Every nameserver is queried and the agreed answer used, so a single briefly stale server is not reported as a change.
- Records that existed and are now gone are reported CRIT. In 3.x this case returned before the baseline comparison and reported OK.
- The SOA serial is masked by default, since it increments on every zone edit and previously alarmed on routine changes.
- Output shows only what was added and removed, rather than the entire stored baseline.
- TXT character strings are joined before comparison, so a record's wire-format split point no longer appears as a change.
- Baselines are held in the Checkmk value store rather than in files named after the domain, which could collide between similarly named domains.
- Response codes are read, so NXDOMAIN, SERVFAIL and an empty answer are no longer indistinguishable.

## Why this exists

Checkmk can tell you a name resolves, but nothing built in tells you whether the answer is the one you published, or whether it changed overnight, which is the question that matters when a domain is hijacked, a migration is half finished, or a registrar change silently breaks delegation. The design decision that makes this reliable is where the nameserver list comes from: it is read from the parent zone's delegation rather than from the domain's own NS records, because taking it from the zone would mean trusting the thing being monitored, and every nameserver is then queried so the answer they agree on is what gets compared.

## What it monitors

- **Record drift**: one service per record type, comparing current values against a baseline and reporting only what was added or removed. A record set that existed and is now empty, a domain that has stopped existing, and disagreement between authoritative servers are each handled as separate conditions rather than folded into a generic change.
- **Zone delegation**: the nameserver set published by the parent zone against the set the domain publishes for itself, plus verification of the glue addresses the parent hands out against an independent resolution of each nameserver name.

CNAME and PTR are available but off by default, since neither is valid at a domain apex. The extension works with no ruleset configuration: record types default to A, AAAA, MX, TXT, NS and SOA, the domain defaults to the host name, and every state has a working default.

## Example services

```
DNS Records A                      OK    2 records, unchanged
DNS Records AAAA                   OK    2 records, unchanged
DNS Records MX                     OK    1 record, unchanged
DNS Records NS                     OK    2 records, unchanged
DNS Records SOA                    OK    1 record, unchanged, serial 2412000000
DNS Records TXT                    OK    10 records, unchanged
DNS Zone Delegation                OK    Parent (com) and zone agree on 2 nameservers, Glue verified on 2 nameservers
```

All services report OK on a domain whose records match the recorded baseline. A
changed record reports the difference rather than the full record set, for
example `Changed: 1 added, 0 removed`, at CRIT for NS and WARN for other types
by default.

## Graphing

- **DNS Records**: query time of the slowest authoritative server, and number of records returned, on separate graphs, with a perfometer on query time.

Query time is a trend indicator only, since variance on identical queries runs to roughly a factor of ten, so thresholds on it produce permanent noise.

Services with no metrics: DNS Zone Delegation.

## Data source

DNS queries only, over UDP with TCP fallback when a response does not fit. Per record type, one query to each authoritative nameserver. Once per run, one query to a nameserver of the parent zone for the delegation and glue, and one resolution per nameserver name for the glue comparison.

## Requirements

- Checkmk 2.4.0 or later, up to 2.5
- Outbound UDP and TCP port 53 from the Checkmk site to the internet. TCP is required for domains whose TXT records exceed what fits in a UDP response.
- No agent on any host, and no credentials.

## Installation

1. Install the package via **Setup > Extension packages > Upload package**.
2. Create the host with "Checkmk agent / API integrations" set to "Configured API integrations, no Checkmk agent", naming the host after the domain to be monitored, then add a rule under **Setup > Agents > Other integrations** titled **DNS Health**. The rule selects which record types to monitor, default A, AAAA, MX, TXT, NS and SOA, and carries the delegation toggle, an optional resolver override, and query timeout, retries and time budget. The domain field can be left empty to use the host name.
3. Run a service discovery on the host.

## Conflicts and supersedes

**Important:** this extension replaces `dns_record_monitor` 3.x. Remove that package before installing this one. Its rules cannot be migrated automatically, because the rule changed from an active check to a special agent, so any 3.x rules must be recreated. Service names and items have both changed, so rediscovery is required and 3.x services will appear as vanished.

## Configuration

- **DNS record drift**: state per record type when a record changes, default CRIT for NS and WARN for all others; how long a change keeps alarming before the new values are accepted, default 7 days; state when all records of a type disappear, default CRIT; state on NXDOMAIN, default CRIT; state when authoritative servers disagree, default WARN; and whether to mask the SOA serial, default on because it increments on every zone edit.
- **DNS zone delegation**: state when the parent and zone nameserver sets differ, and state when glue does not match, both default WARN.

No ruleset configuration is required beyond the collection rule created during installation. Every check ships with working defaults.

## Validated

Validated against production domains hosted on Cloudflare and GoDaddy DNS, covering counter-style and date-style SOA serial formats, record sets of more than twenty TXT entries requiring TCP fallback, and domains publishing no AAAA records.

## Version history

- **4.0.0**: rewritten as a special agent, renamed from `dns_record_monitor`. One service per record type, authoritative queries with the nameserver list taken from the parent delegation, agreed-answer comparison across nameservers, zone delegation and glue checking, diff-only output, per-type states, a configurable acceptance period for detected changes, SOA serial masking, TXT string joining, response code handling, and baselines held in the value store. Service names and items changed, so rediscovery is required.

## Author

Sher Zaman

- Email: sher[at]sherz[dot]dev
- Website: https://sherz.dev
- LinkedIn: https://www.linkedin.com/in/sher-zaman-95b008114/

## License

GPL-2.0-only. See the repository [LICENSE.md](../../LICENSE.md).
