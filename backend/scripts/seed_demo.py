"""Manual entry point for the demo-data seed (also runs automatically on
app startup in demo mode — see app/main.py). Useful for re-seeding a
fresh DB or for CI without booting the whole server.

Usage:  python scripts/seed_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.demo_seed import run_seed  # noqa: E402

if __name__ == "__main__":
    result = run_seed()
    if result["already_seeded"]:
        print("Demo data already present — nothing to do.")
    else:
        print("Demo data seeded.")
    print(f"  Login email:    {result['email']}")
    print(f"  Login password: {result['password']}")
    print(f"  Organization:   {result['organization']}")
