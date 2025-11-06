"""
Migration: 004_change_approved_to_string
Changes the approved column from boolean to string type with allowed values:
PENDING_APPROVAL (default), APPROVED, REJECTED
"""

def up(conn):
    """Apply the migration"""
    cursor = conn.cursor()
    
    # Step 1: Add a new VARCHAR column for approved status
    cursor.execute("""
        ALTER TABLE users 
        ADD COLUMN approved_status VARCHAR(50)
    """)
    
    # Step 2: Set all existing values to 'PENDING_APPROVAL'
    cursor.execute("""
        UPDATE users 
        SET approved_status = 'PENDING_APPROVAL'
    """)
    
    # Step 3: Drop the old boolean column
    cursor.execute("""
        ALTER TABLE users 
        DROP COLUMN approved
    """)
    
    # Step 4: Rename the new column to 'approved'
    cursor.execute("""
        ALTER TABLE users 
        RENAME COLUMN approved_status TO approved
    """)
    
    # Step 5: Set NOT NULL constraint and default value
    cursor.execute("""
        ALTER TABLE users 
        ALTER COLUMN approved SET NOT NULL,
        ALTER COLUMN approved SET DEFAULT 'PENDING_APPROVAL'
    """)
    
    # Step 6: Add CHECK constraint to enforce allowed values
    cursor.execute("""
        ALTER TABLE users 
        ADD CONSTRAINT check_approved_status 
        CHECK (approved IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED'))
    """)
    
    # Step 7: Drop old index and recreate it (index name stays the same)
    cursor.execute("""
        DROP INDEX IF EXISTS idx_users_approved
    """)
    
    cursor.execute("""
        CREATE INDEX idx_users_approved ON users(approved)
    """)
    
    # Don't commit here - let the context manager handle it
    cursor.close()

def down(conn):
    """Rollback the migration"""
    cursor = conn.cursor()
    
    # Step 1: Drop the CHECK constraint
    cursor.execute("""
        ALTER TABLE users 
        DROP CONSTRAINT IF EXISTS check_approved_status
    """)
    
    # Step 2: Add a new boolean column
    cursor.execute("""
        ALTER TABLE users 
        ADD COLUMN approved_boolean BOOLEAN
    """)
    
    # Step 3: Convert string values back to boolean
    # APPROVED -> true, everything else -> false
    cursor.execute("""
        UPDATE users 
        SET approved_boolean = CASE 
            WHEN approved = 'APPROVED' THEN TRUE 
            ELSE FALSE 
        END
    """)
    
    # Step 4: Drop the old string column
    cursor.execute("""
        ALTER TABLE users 
        DROP COLUMN approved
    """)
    
    # Step 5: Rename the new column to 'approved'
    cursor.execute("""
        ALTER TABLE users 
        RENAME COLUMN approved_boolean TO approved
    """)
    
    # Step 6: Set NOT NULL constraint and default value
    cursor.execute("""
        ALTER TABLE users 
        ALTER COLUMN approved SET NOT NULL,
        ALTER COLUMN approved SET DEFAULT FALSE
    """)
    
    # Step 7: Recreate the index
    cursor.execute("""
        DROP INDEX IF EXISTS idx_users_approved
    """)
    
    cursor.execute("""
        CREATE INDEX idx_users_approved ON users(approved)
    """)
    
    # Don't commit here - let the context manager handle it
    cursor.close()

