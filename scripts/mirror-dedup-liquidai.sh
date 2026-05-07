#!/usr/bin/env bash
# Mirror dedup: Shared (archive) ↔ qbitOS — checksum discipline before deleting qbitOS copy.
#
# Usage:
#   LIQUID_DEDUP_DRY_RUN=1 ./scripts/mirror-dedup-liquidai.sh
#   ./scripts/mirror-dedup-liquidai.sh LFM2-2.6B-Transcript-GGUF
#
# Defaults (override with env):
#   MAC_BASE=/Volumes/MacBookPro/Users/Shared/03.models/01-ollama/hf-mirror/LiquidAI
#   QBIT_BASE=/Volumes/qbitOS/03.models/01-ollama/hf-mirror/LiquidAI

set -euo pipefail

MAC_BASE="${MAC_BASE:-/Volumes/MacBookPro/Users/Shared/03.models/01-ollama/hf-mirror/LiquidAI}"
QBIT_BASE="${QBIT_BASE:-/Volumes/qbitOS/03.models/01-ollama/hf-mirror/LiquidAI}"
DRY="${LIQUID_DEDUP_DRY_RUN:-1}"

die() { echo "error: $*" >&2; exit 1; }

[[ -d "$MAC_BASE" ]] || die "MAC_BASE missing: $MAC_BASE"
[[ -d "$QBIT_BASE" ]] || die "QBIT_BASE missing: $QBIT_BASE"

check_identical() {
	local name="$1"
	local a="$MAC_BASE/$name"
	local b="$QBIT_BASE/$name"
	if [[ ! -d "$a" ]]; then
		echo "SKIP $name (no Mac archive dir)"
		return 1
	fi
	if [[ ! -d "$b" ]]; then
		echo "SKIP $name (no qbitOS dir)"
		return 1
	fi
	if diff -qr "$a" "$b" >/dev/null 2>&1; then
		echo "IDENTICAL $name"
		return 0
	fi
	echo "DIFFER $name — do not auto-delete (inspect diff -qr)"
	return 2
}

remove_qbit() {
	local name="$1"
	local target="$QBIT_BASE/$name"
	if [[ "$DRY" == "1" ]]; then
		echo "DRY-RUN would: rm -rf \"$target\""
	else
		rm -rf "$target"
		echo "REMOVED $target"
	fi
}

if [[ $# -gt 0 ]]; then
	for name in "$@"; do
		if check_identical "$name"; then
			remove_qbit "$name"
		fi
	done
	exit 0
fi

echo "Scanning repos under qbitOS (set LIQUID_DEDUP_DRY_RUN=0 to actually delete IDENTICAL trees)..."
for path in "$QBIT_BASE"/*; do
	[[ -d "$path" ]] || continue
	name="$(basename "$path")"
	case "$name" in .* ) continue ;; esac
	if check_identical "$name"; then
		remove_qbit "$name"
	fi
done
