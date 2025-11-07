"""
Quick script to check a user's approval status in the database.
"""
import os
import sys
from dotenv import load_dotenv
from src.db import get_db_connection
from src.auth import get_user_by_email

load_dotenv()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_user_approval.py <email>")
        sys.exit(1)
    
    email = sys.argv[1].lower().strip()
    
    print(f"Checking approval status for: {email}")
    print("=" * 60)
    
    # Check via function
    user_data = get_user_by_email(email)
    if user_data:
        print(f"Via get_user_by_email():")
        print(f"  Approval: {user_data.get('approved')}")
        print(f"  Type: {type(user_data.get('approved'))}")
    else:
        print("User not found via get_user_by_email()")
    
    # Check directly in database
    print("\nDirect database query:")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, approved, approved::text
                FROM users 
                WHERE email = %s
            """, (email,))
            user = cursor.fetchone()
            cursor.close()
            
            if user:
                print(f"  ID: {user[0]}")
                print(f"  Email: {user[1]}")
                print(f"  Approved (raw): {user[2]}")
                print(f"  Approved (text): {user[3]}")
                print(f"  Type: {type(user[2])}")
            else:
                print("  User not found in database")
    except Exception as e:
        print(f"  Error querying database: {e}")
    
    # List all users with their approval status
    print("\n" + "=" * 60)
    print("All users in database:")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, approved
                FROM users 
                ORDER BY id
            """)
            users = cursor.fetchall()
            cursor.close()
            
            for user in users:
                print(f"  ID {user[0]}: {user[1]} - {user[2]}")
    except Exception as e:
        print(f"  Error querying database: {e}")

