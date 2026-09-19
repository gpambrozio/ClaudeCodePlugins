# Slimming Internals

Read this when something does not behave as expected, when a number needs
explaining, or when the daemon catalog has to be refreshed from upstream.

## Contents

- [How the overrides work](#how-the-overrides-work)
- [Persistence by iOS version](#persistence-by-ios-version)
- [Slimming without a reboot](#slimming-without-a-reboot)
- [What the managed allowlist protects](#what-the-managed-allowlist-protects)
- [How the transitions are applied](#how-the-transitions-are-applied)
- [Measurement method](#measurement-method)
- [Troubleshooting](#troubleshooting)
- [Refreshing the catalog from upstream](#refreshing-the-catalog-from-upstream)

## How the overrides work

Slimming writes `launchctl disable system/<label>` entries into the simulator's
own launchd database, executed inside the simulator via
`xcrun simctl spawn <udid> launchctl ...`. A disable override blocks the next
bootstrap of that job; it does not stop a job that is already running, which is
why a full slim reboots the simulator afterwards.

`launchctl print-disabled system` reads the state back. Recent launchd prints
`"com.apple.x" => disabled`; older builds print `=> true`/`=> false`. A label
absent from that output is enabled.

Nothing on the host Mac is modified. The state belongs to one simulator and
travels with it only through this plugin's own operations - not through
`simctl clone`, and not when a simulator is moved to another Mac.

## Persistence by iOS version

| Runtime | `launchctl disable` accepted | Survives reboot |
|---|---|---|
| iOS 17.x, 18.3 | yes | **no** - comes back stock |
| iOS 18.5+ | yes | yes |

This is the trap worth knowing: on older runtimes every command reports success
and the simulator silently returns to stock at the next boot. `sim-slim.py`
refuses those runtimes before booting or changing anything, rather than claiming
a win it cannot deliver, and points at `--no-reboot`. After a supported slim it
reads the overrides back post-reboot and fails if any were lost.

## Slimming without a reboot

`sim-slim.py --no-reboot` disables each daemon and then `launchctl bootout`s it,
so the process stops immediately and cannot respawn - no shutdown/boot cycle.

- On iOS 18.5+ this is simply the faster path; the overrides are stored too, so
  the next boot comes up slim as well.
- On iOS 17.x/18.3 it is the only way to slim at all, and the state ends with
  the boot session. Re-run it after every boot.

Live slimming only moves toward more-disabled. Managed daemons already disabled
beyond the current profile are left alone, because re-enabling one live would
require bootstrapping the job again; `sim-slim-off.py` restores them with a
reboot.

This is also the answer for `xcodebuild` parallel testing, which creates a fresh
stock clone per worker in the `testing` device set and deletes them when the run
ends. There is no device to slim ahead of time, so the clone has to be slimmed
after it boots - `sim-slim-status.py --all` will show them, since the scripts
scan both the default and `testing` sets.

## What the managed allowlist protects

Two sets govern every operation:

- **Slimmable**: the 170 labels a profile may disable.
- **Managed**: slimmable plus `com.apple.sharingd`, which is required for system
  share sheets and is therefore only ever transitioned *back* to enabled. It
  stays in the allowlist so a simulator slimmed by older tooling can be repaired.

Labels outside the managed set are never touched in either direction. That is
what keeps an unrelated tool's `launchctl disable` from being clobbered, and why
`sim-slim-verify.py` does not report such a daemon as drift.

The allowlist deliberately excludes core workflow daemons and the handful that
wedge a simulator when disabled. Adding labels to `slim-catalog.json` without
upstream verification risks a simulator that boots to a black screen.

## How the transitions are applied

Each transition is its own `xcrun simctl spawn <udid> launchctl <verb>
system/<label>` call, and they run eight at a time from a thread pool on the
host. The calls are spawn-latency bound rather than CPU bound - measured at
~1.16s each serially versus ~0.24s at eight-way concurrency - and a full slim is
~170 of them, so this is the difference between a multi-minute apply and one
that finishes in well under a minute. Anything that fails is retried on a later
pass (three total) rather than aborting the run, because the first pass races
the simulator's own startup work and a label that times out once usually
succeeds seconds later.

Concurrency lives on the host deliberately. simslim batches the same work into a
shell script running *inside* the simulator, which is cheaper still, but
`simctl spawn <udid> /bin/sh` fails outright on some runtimes (iOS 27.0 under
Xcode 27 returns `Invalid or missing Program/ProgramArguments` for any shell,
including `/bin/bash`). `launchctl` as the direct spawn target is the one form
that works everywhere, and a host thread pool recovers the parallelism without
depending on a shell being present.

If you ever do run a shell inside a simulator, one detail is load-bearing: dyld
strips `DYLD_ROOT_PATH` from the spawned shell's environment because `/bin/sh`
is a restricted platform binary, and a nested `launchctl` then aborts with
`DYLD_ROOT_PATH not set for simulator program`. `SIMULATOR_ROOT` carries the
same runtime root and does survive, so a script has to restore `DYLD_ROOT_PATH`
from it first.

Timeouts are layered: `--boot-timeout` (default 600s, or `SIM_SLIM_BOOT_TIMEOUT`)
bounds the whole reconfigure, `--spawn-timeout` (default 120s, or
`SIM_SLIM_SPAWN_TIMEOUT`) bounds a single transition. Right after a first boot
the simulator is saturated by its own startup work and individual spawns can
stall for minutes, which is why a stuck label becomes a retry rather than a
failed run.

For reference, on an M-series Mac with iOS 27.0: a full slim from stock runs
about 2m15s end to end, most of which is the two boots rather than the ~170
overrides.

## Measurement method

`sim-slim-measure.py` finds the simulator's `launchd_sim` via
`pgrep -f <udid>/data/var/run/launchd_bootstrap`, walks its process tree from
`ps -axo pid,ppid,%cpu,comm`, and sums each process's `phys_footprint` from
`top -l 1 -stats pid,mem`.

`phys_footprint` is the figure Activity Monitor's Memory column shows. It counts
compressed and swapped pages, so it stays accurate under the memory pressure
that matters here, where resident size reads misleadingly low. Summing `ps` RSS
instead would double-count, because RSS charges shared mappings to every process
that maps them.

The per-category memory estimates in the catalog are clean-boot medians on
iOS 26.5. They rank categories; they are **not additive** and will not predict a
total. Measure the simulator for that.

`sim-slim-status.py` counts managed launchd labels, not processes. A slim
simulator still runs required core services, system apps, and extensions, so its
process count never approaches zero and the two commands' numbers are not
comparable.

## Troubleshooting

**"simulator must be booted to read its state"** — the overrides live inside the
simulator's launchd, which only exists while it is booted. Boot it first;
`sim-slim.py` does this itself.

**"several simulators are booted, so the target is ambiguous"** — slimming
reboots a device, so the scripts refuse to guess. Pass `--udid`.

**"N launchd transitions failed after 3 passes"** — the simulator was too busy or
is wedged. Re-run `sim-slim.py`; it is idempotent and applies only the missing
difference. If it fails repeatedly, raise `--spawn-timeout`, or shut the
simulator down and try again from cold.

**"overrides did not survive the reboot"** — the runtime does not persist them.
Check `sim-slim-status.py`'s `persistent` field and use `--no-reboot`.

**A feature broke after slimming** — `sim-slim-doctor.py --requires <feature>`
names the disabled daemons behind it; re-slim with `--keep` or `--except`, or
run `sim-slim-off.py` to go back to stock.

**Memory crept back up** — something reset the overrides (erase, recreate, clone,
new runtime). Confirm with `sim-slim-status.py --all`, then re-slim.

**Simulator behaves strangely after slimming** — `sim-slim-off.py` restores it to
stock with a reboot. If it is wedged badly enough that launchctl no longer
responds, erase the simulator, which also clears the overrides.

## Refreshing the catalog from upstream

`scripts/slim-catalog.json` holds the categories, the feature map, the
per-daemon purpose descriptions, and the memory estimates. It is ported from
[simslim](https://github.com/MobAI-App/simslim) (MIT, Copyright (c) 2026
Interlap); the `source` object in the file records the upstream commit it came
from.

Upstream revises the allowlist as it learns which daemons are safe to disable
and which wedge a simulator, so refresh rather than hand-edit. With Go
available:

```bash
git clone --depth=1 https://github.com/MobAI-App/simslim /tmp/simslim
cat > /tmp/simslim/dump_catalog_test.go <<'EOF'
package simslim

import (
	"encoding/json"
	"os"
	"testing"
)

func TestDumpCatalog(t *testing.T) {
	out := map[string]any{
		"categories":          Categories,
		"features":            Features,
		"serviceDescriptions": serviceDescriptionByLabel,
	}
	b, _ := json.MarshalIndent(out, "", "  ")
	if err := os.WriteFile("/tmp/simslim-catalog.json", b, 0o644); err != nil {
		t.Fatal(err)
	}
}
EOF
cd /tmp/simslim && go test -run TestDumpCatalog .
```

Then merge `/tmp/simslim-catalog.json` into `slim-catalog.json`, keeping the
`source` object and updating its `commit`. The Python side reads the same field
names upstream emits (`approxMemoryMB`, `alwaysEnabled`, `serviceDescriptions`),
so a refresh is data-only.
