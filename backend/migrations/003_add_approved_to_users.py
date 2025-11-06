"""
Migration: 003_add_approved_to_users
Adds an approved boolean column to the users table, defaulting to false.
"""

def up(conn):
    """Apply the migration"""
    cursor = conn.cursor()
    
    # Add approved column to users table with default value of false
    cursor.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS approved BOOLEAN NOT NULL DEFAULT FALSE
    """)
    
    # Create index on approved for faster lookups when filtering by approval status
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_approved ON users(approved)
    """)
    
    # Don't commit here - let the context manager handle it
    cursor.close()

def down(conn):
    """Rollback the migration"""
    cursor = conn.cursor()
    
    # Drop index first
    cursor.execute("""
        DROP INDEX IF EXISTS idx_users_approved
    """)
    
    # Drop approved column
    cursor.execute("""
        ALTER TABLE users 
        DROP COLUMN IF EXISTS approved
    """)
    
    # Don't commit here - let the context manager handle it
    cursor.close()

