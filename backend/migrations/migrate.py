"""
Simple migration runner for database migrations.
"""
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db_connection
import importlib.util

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_migration_files():
    """Get all migration files in order"""
    migrations_dir = Path(__file__).parent
    migration_files = sorted([
        f for f in migrations_dir.iterdir() 
        if f.name.startswith('0') and f.name.endswith('.py') and f.name != '__init__.py'
    ])
    return migration_files

def get_applied_migrations(conn):
    """Get list of applied migrations from database"""
    cursor = conn.cursor()
    
    # Create migrations tracking table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Don't commit here - will be committed when connection is used
    
    # Get applied migrations
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
    applied = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return applied

def mark_migration_applied(conn, version):
    """Mark a migration as applied"""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT (version) DO NOTHING",
        (version,)
    )
    # Don't commit here - let the context manager handle it
    cursor.close()

def run_migration(migration_file):
    """Run a single migration file"""
    migration_name = migration_file.stem
    
    # Load the migration module
    spec = importlib.util.spec_from_file_location(migration_name, migration_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if not hasattr(module, 'up'):
        raise ValueError(f"Migration {migration_name} does not have an 'up' function")
    
    logger.info(f"Running migration: {migration_name}")
    
    with get_db_connection() as conn:
        module.up(conn)
        mark_migration_applied(conn, migration_name)
        # Context manager will commit automatically
    
    logger.info(f"Migration {migration_name} applied successfully")

def run_all_migrations():
    """Run all pending migrations"""
    migration_files = get_migration_files()
    
    with get_db_connection() as conn:
        applied_migrations = get_applied_migrations(conn)
    
    pending_migrations = [
        f for f in migration_files 
        if f.stem not in applied_migrations
    ]
    
    if not pending_migrations:
        logger.info("No pending migrations")
        return
    
    logger.info(f"Found {len(pending_migrations)} pending migration(s)")
    
    for migration_file in pending_migrations:
        try:
            run_migration(migration_file)
        except Exception as e:
            logger.error(f"Failed to run migration {migration_file.stem}: {str(e)}")
            raise

if __name__ == '__main__':
    try:
        run_all_migrations()
        logger.info("All migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

