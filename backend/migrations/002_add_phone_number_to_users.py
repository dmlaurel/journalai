"""
Migration: 002_add_phone_number_to_users
Adds a phone_number column to the users table.
"""

def up(conn):
    """Apply the migration"""
    cursor = conn.cursor()
    
    # Add phone_number column to users table
    cursor.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)
    """)
    
    # Create index on phone_number for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number)
    """)
    
    # Don't commit here - let the context manager handle it
    cursor.close()

def down(conn):
    """Rollback the migration"""
    cursor = conn.cursor()
    
    # Drop index first
    cursor.execute("""
        DROP INDEX IF EXISTS idx_users_phone_number
    """)
    
    # Drop phone_number column
    cursor.execute("""
        ALTER TABLE users 
        DROP COLUMN IF EXISTS phone_number
    """)
    
    # Don't commit here - let the context manager handle it
    cursor.close()

