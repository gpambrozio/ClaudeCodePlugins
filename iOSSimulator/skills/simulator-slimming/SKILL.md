---
name: simulator-slimming
version: 1.0.0
description: Cut an iOS or watchOS Simulator's memory roughly 3-4x by disabling the background daemons it does not need (Siri, Spotlight, photo analysis, iCloud sync, News, widgets), so many more simulators fit on one Mac. Use this skill whenever the user mentions simulators eating RAM, a Mac slowing down or swapping with simulators open, running many simulators or agents in parallel, parallel or CI test runs that are memory-bound, "slimming" a simulator, simslim, or asks how many simulators their machine can hold - even if they do not name a specific tool. Also use it for watchOS simulators and paired watch/phone pairs, to check what a slimmed simulator gave up, to confirm a feature a test needs (push, StoreKit, universal links, watch pairing) still works, or to restore a slimmed simulator to stock.
---

# Simulator Slimming

A freshly booted iOS Simulator starts around 180 background services - Siri, Spotlight indexing, photo analysis, News, wallpaper posters, iCloud sync. None of them matter for development, UI automation, or CI, and together they are most of the simulator's memory. Disabling them takes a simulator from roughly 3 GB to under 1 GB - measured here at 2.9 GB across 240 processes stock versus 620 MB across 80 slim - which is what decides how many simulators a Mac holds before it starts swapping.

**watchOS simulators slim too**, and are worth doing: a stock watch is not the small thing its screen suggests. Measured on watchOS 27, one went from 1315 MB across 178 processes to 554 MB across 79. A watch runs most of the same daemons a phone does plus its own `nano*` family - Mail, Photos, Weather, Messages mirrored from the phone - so the catalog covers both and a category means the same thing on either.

The mechanism is `launchctl disable system/<label>` run inside the simulator through `simctl spawn`. The overrides live in that one simulator's own launchd database, so nothing on the host Mac is touched and each simulator is independent.

## Prerequisites

- macOS with Xcode installed (simctl ships with full Xcode, not the Command Line Tools)
- Python 3 (pre-installed on macOS)
- **iOS 18.5 or newer**, or **watchOS 27 or newer**, for slimming that survives a reboot. Older runtimes accept every `launchctl disable` and then come back stock, so `sim-slim.py` refuses them and points at `--no-reboot`, which slims only the current boot session. (watchOS is gated where it is because that is what has been measured, not because earlier is known to fail.)
- tvOS and visionOS simulators are skipped entirely: their daemon sets have never been measured against this catalog, and the scripts will not find such a device.

## Running the Scripts

- Scripts live in `scripts/`, are executable, and print JSON on stdout
- Long operations write progress to stderr; pass `--quiet` to suppress it
- `--udid` / `--name` target a simulator; with neither, scripts use the booted one and refuse to guess when several are booted
- Run any script with `--help` for full argument documentation

## Decide Before Slimming

Slimming is a deliberate trade: memory back in exchange for features that stop working. Two questions settle almost every case.

**Is this simulator for automation, or for a person?** UI automation, CI, and agent-driven work want everything off. A simulator someone is manually exercising Photos or Siri in does not.

**What does the work under test actually need?** Ask before slimming rather than debugging a mysterious failure afterwards - a test that needs push notifications fails in ways that look exactly like an app bug once `apsd` is gone. `scripts/sim-slim-profiles.py` lists every category with the downside of turning it off, so the conversation can be concrete.

Slimming reboots the simulator. If it is running something the user cares about, say so first.

## Quick Start

```bash
# 1. See what a slim boot would turn off, and what that costs in capability
scripts/sim-slim-profiles.py

# 2. Preview the exact change for this simulator without touching it
scripts/sim-slim.py --dry-run

# 3. Slim it (boots, disables ~170 daemons, reboots slim)
scripts/sim-slim.py

# 4. Confirm the win
scripts/sim-slim-measure.py
```

Slimming takes roughly two minutes: it boots the simulator, applies the overrides, and reboots, and most of that is the two boots. `sim-slim.py` is idempotent, so re-running it only applies the missing difference.

## Script Reference

| Script | Purpose | Common Usage |
|--------|---------|--------------|
| `sim-slim.py` | Slim a simulator | `--except search`, `--keep com.apple.apsd`, `--dry-run` |
| `sim-slim-off.py` | Restore to stock | `--udid <udid>` |
| `sim-slim-status.py` | Is it still slim? | `--dropped`, `--all` |
| `sim-slim-profiles.py` | What a slim boot turns off | `--category siri`, `--find com.apple.apsd`, `--platform watchos` |
| `sim-slim-measure.py` | Real memory footprint | `--all`, `--processes` |
| `sim-slim-doctor.py` | Do required features still work? | `--requires push,storekit` |
| `sim-slim-verify.py` | Has the slim state drifted? | `--profile ci.json` |

`sim-slim-doctor.py` and `sim-slim-verify.py` exit non-zero on failure, which is what makes them usable as CI preflight steps.

## Keeping What the Work Needs

Three levers, from coarse to fine:

```bash
# Keep a whole category, e.g. Spotlight search
scripts/sim-slim.py --except search

# Keep one daemon, e.g. push notifications
scripts/sim-slim.py --keep com.apple.apsd

# Both, recorded in a file that can be committed alongside the project
scripts/sim-slim.py --profile ci.json
```

Categories overlap on purpose - a daemon several features need lives in each of their categories - so excepting any category that lists a daemon keeps it enabled.

A profile file is the single source of truth for its run and cannot be combined with `--except`/`--keep`, because a committed profile and an ad-hoc flag disagreeing about what "slim" means is exactly the drift `sim-slim-verify.py` exists to catch:

```json
{
  "name": "ci",
  "description": "UI test runs",
  "except": ["search", "store"],
  "keep": ["com.apple.apsd"]
}
```

Unknown fields, unknown category IDs, and labels no category disables are all rejected, so a typo fails loudly instead of quietly slimming more than intended.

### Mapping a need to a lever

When the user names a capability rather than a category, resolve it with the feature list rather than guessing at daemon names:

```bash
scripts/sim-slim-doctor.py --list                 # every known feature and its daemons
scripts/sim-slim-profiles.py --find com.apple.swcd  # which categories disable a daemon
```

The ones that bite most often: push needs `apsd` (`store`), StoreKit testing needs `storekitd` plus the Apple Media Services and Wallet daemons (`store`), universal links need `swcd` (`web`), and the Contacts, Photos, and Calendar pickers want their own categories (`pim`, `photos`).

`sim-slim-profiles.py` reads a device's platform from the device; with no device to read - which is every invocation of this one - pass `--platform watchos` to see what a watch would lose.

## Slimming a Paired Watch

A watch and the phone it is paired to are two simulators and slim independently, and one profile covers both: category IDs mean the same thing on either, so `--except health` keeps HealthKit on a phone and `healthd` *plus* the watch's `sleepd` on a watch.

Three things are specific to the watch, and all three are handled by the catalog rather than by the caller:

- **The pairing and the home screen are never disabled.** `nanoregistryd`, `nanoregistrylaunchd`, `Carousel`, `nanotimekitd`, `appconduitd` and the rest of that set are in the always-enabled list, so no profile can turn them off and a watch found with one disabled is repaired. A watch that loses its pairing is one no companion app installs onto, and the failure looks nothing like its cause.
- **WatchConnectivity lives in `connectivity`.** `com.apple.wcd` is shared with iOS and sits in that category on both sides, so a project whose phone and watch talk to each other excepts `connectivity` on both.
- **The watch's own apps are mirrored, not separate.** Mail, Photos, Weather, Messages and Wallet on a watch are the `nano*` daemons, and they are in `pim`, `photos`, `apps`, `messaging` and `store` alongside their phone equivalents.

```bash
scripts/sim-slim.py --udid <watch-udid> --profile ci.json
scripts/sim-slim-measure.py --all          # both halves of the pair
```

## Running Many Simulators

The point of slimming is fitting more simulators on one machine, so the fleet view is usually what the user actually wants:

```bash
scripts/sim-slim-status.py --all    # which simulators are slim
scripts/sim-slim-measure.py --all   # what the fleet costs right now
```

`sim-slim-measure.py` sums `phys_footprint` across each simulator's process tree - the figure Activity Monitor shows, counting compressed and swapped pages. Use it for "how much memory is this costing?" and `sim-slim-status.py` for "is my slimming still applied?"; they answer different questions and their numbers are not comparable.

## CI and Repeatable Setups

Commit a profile, apply it per run, and verify rather than assume:

```bash
scripts/sim-slim-verify.py --profile ci.json || scripts/sim-slim.py --profile ci.json
scripts/sim-slim-doctor.py --requires push,universal-links
```

Shared CI runners are slow enough to blow the default 10-minute budget mid-reconfigure. Raise it with `--boot-timeout 900` (or `SIM_SLIM_BOOT_TIMEOUT=900`), and `--spawn-timeout 300` when individual transitions stall on a cold first boot.

## When Slimming Comes Undone

The overrides are per-simulator state, and several ordinary actions silently reset it: `erase`, delete-and-recreate, "Erase All Content and Settings", `simctl clone` (clones are created stock), and any simulator from a newly installed runtime. Nothing fails loudly when this happens - the simulator just quietly runs heavy again - so when memory creeps back, check state before re-slimming:

```bash
scripts/sim-slim-status.py --all
scripts/sim-slim-verify.py --profile ci.json
```

## Reporting Results

The memory numbers are the reason the user asked, so lead with them and be concrete: measure before and after, and name what was given up. "Slimmed: 2.9 GB to 0.6 GB, 240 processes to 80. Siri, Spotlight, Photos analysis, and iCloud sync are off; push and universal links are still on." That is a decision the user can act on. A bare "done" is not.

## Additional Resources

- **`references/internals.md`** — how the overrides work, the persistence matrix by iOS version, troubleshooting, the measurement method, and how to refresh the daemon catalog from upstream

The daemon catalog, feature map, and category memory estimates are ported from [simslim](https://github.com/MobAI-App/simslim) (MIT, Copyright (c) 2026 Interlap), which established and verified this allowlist.
