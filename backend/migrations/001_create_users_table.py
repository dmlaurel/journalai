"""
Migration: 001_create_users_table
Creates the users table with all required fields.
"""

def up(conn):
    """Apply the migration"""
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            one_time_code VARCHAR(10),
            one_time_code_expiry TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index on email for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
    """)
    
    # Create index on one_time_code for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_one_time_code ON users(one_time_code)
    """)
    
    # Don't commit here - let the context manager handle it
    cursor.close()

def down(conn):
    """Rollback the migration"""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS users CASCADE")
    # Don't commit here - let the context manager handle it
    cursor.close()

