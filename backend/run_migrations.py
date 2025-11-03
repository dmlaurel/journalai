#!/usr/bin/env python3
"""
Run database migrations.
This script can be used both locally and on Render.
"""
import sys
import os
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from migrations.migrate import run_all_migrations

if __name__ == '__main__':
    try:
        print("Running database migrations...")
        run_all_migrations()
        print("✓ All migrations completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}", file=sys.stderr)
        sys.exit(1)

