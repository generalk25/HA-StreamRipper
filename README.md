# HA-StreamRipper

A Home Assistant custom integration for the StreamRipper media
conversion farm. It mirrors the coordinator's state into Home
Assistant and exposes its levers as switches.

## Discovery

The streamripper coordinator announces itself on the LAN over
mDNS as `_streamripper._tcp`. With this integration installed,
Home Assistant offers to set it up the moment the announcement
is seen — no address to type. Discovery carries only the
address and a stable instance id; the setup form still asks for
the coordinator's API token, which is never advertised.

If mDNS does not reach Home Assistant on your network, add the
integration manually (Settings → Devices & Services → Add
Integration → StreamRipper) with the coordinator's host, port
(9595 by default), and API token.

## Entities

One device, **StreamRipper**, carrying:

- **Job** — the running job's name, or `Idle`, with phase,
  progress, the runner state and the passive jobs' states as
  attributes
- **Workers Online** — how many fleet workers are fresh, with
  each worker's state and mode as attributes
- **Worker \<name\>** — one sensor per worker (the coordinator
  itself included): its state, with everything the
  coordinator reports as attributes — the current job's step
  and file, % done, from/to codecs, active/passive mode with
  its percent pair and effective limit, cores in the fire,
  the efficiency index and grade, class, stream-only, holds
  and their reasons, host vitals (CPU, temperature, memory,
  load), scratch space, all-time GB transcoded with its
  medal rank, claim tallies, the bench, and the mode
  schedule (raw and as a readable line)
- **Worker \<name\> Progress** — % done with the current job,
  as a graphable number
- **Worker \<name\> Throughput** — average GB/hr over the
  trailing 24 hours of completed work
- **Schedules** — plan runs scheduled for later: how many
  are pending, when the next one fires, and the list
- **Pending Steps** — plan steps waiting in the worker pool
- **Failure Review** — genuine failures waiting for a
  dismiss/requeue decision
- **Language Review** — language verdicts waiting on review
- **Deletion Queue** — files inside their deletion fuse window
- **Running** (binary) — on while any job runs
- **Jobs Paused** (binary) — on while the jobs brake is set
- **Pause Jobs** (switch) — the jobs brake itself: turning it
  on cancels the running job and holds schedules and the
  top-up; turning it off resumes. Passive jobs are governed by
  their own switches and are deliberately not held by this
  brake — a checked passive job is its own opt-in
- **Passive Analyze / Normalize / Save Space** (switches) —
  the per-job passive checkmarks: a passive job starts itself
  when the runner is free and its cadence is due, and never
  cancels another job to do so

## Installation

- **HACS**: add this repository as a custom repository
  (category: Integration), install StreamRipper, restart Home
  Assistant.
- **Manual**: copy `custom_components/streamripper` into your
  Home Assistant `config/custom_components/` directory and
  restart.

## Notes

State is polled every 15 seconds. The coordinator's status read
can take a few seconds while a job preview is scanning the
library; the integration allows for that and keeps the last
good state rather than flapping.
