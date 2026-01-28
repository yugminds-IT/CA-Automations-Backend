#!/usr/bin/env python3
"""
Wait for PostgreSQL to be reachable before starting the app.
Used in production (e.g. Coolify) when DB may not be ready at container start.
Exits 0 when ready, 1 after max retries.
"""
from __future__ import annotations

import os
import sys
import time


def _norm_url(url: str) -> str:
    url = url.strip()
    url = url.replace("postgres://", "postgresql://", 1)
    # Raw psycopg expects postgresql://; strip +psycopg if present
    if "postgresql+psycopg://" in url:
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("wait_for_db: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    url = _norm_url(url)

    max_attempts = int(os.getenv("DB_WAIT_MAX_ATTEMPTS", "30"))
    delay = int(os.getenv("DB_WAIT_DELAY_SECONDS", "2"))
    connect_timeout = int(os.getenv("DB_WAIT_CONNECT_TIMEOUT", "5"))

    import psycopg

    for attempt in range(1, max_attempts + 1):
        try:
            with psycopg.connect(url, connect_timeout=connect_timeout) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            print(f"wait_for_db: database ready (attempt {attempt}/{max_attempts})")
            return
        except Exception as e:
            print(f"wait_for_db: attempt {attempt}/{max_attempts} failed: {e}", file=sys.stderr)
            if attempt >= max_attempts:
                print("wait_for_db: max attempts reached, giving up", file=sys.stderr)
                sys.exit(1)
            time.sleep(delay)
    sys.exit(1)


if __name__ == "__main__":
    main()
