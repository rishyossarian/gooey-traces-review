#!/usr/bin/env python3
"""Restore annotations.json / suggestions.json from a backup made by 'Reset for demo'.

Usage:
  python3 restore_backup.py                # lists available backup timestamps
  python3 restore_backup.py 20260914_135256  # restores that timestamp
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "error_discovery_data"
BACKUPS = DATA / "backups"


def list_timestamps():
    stamps = sorted({p.stem.split(".", 1)[1] for p in BACKUPS.glob("*.json")})
    return stamps


def main():
    if not BACKUPS.exists() or not any(BACKUPS.glob("*.json")):
        print("No backups found in error_discovery_data/backups/")
        return

    if len(sys.argv) < 2:
        print("Available backup timestamps:")
        for ts in list_timestamps():
            print(" ", ts)
        print("\nRun again as: python3 restore_backup.py <timestamp>")
        return

    ts = sys.argv[1]
    restored = False
    for name in ("annotations", "suggestions"):
        src = BACKUPS / f"{name}.{ts}.json"
        if src.exists():
            shutil.copy(src, DATA / f"{name}.json")
            print(f"Restored {name}.json from {src.name}")
            restored = True
    if not restored:
        print(f"No backup files found for timestamp {ts}")


if __name__ == "__main__":
    main()
