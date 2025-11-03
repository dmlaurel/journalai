# Connecting to PostgreSQL with pgAdmin 4

## Connection Details

Based on your PostgreSQL installation, use these settings:

- **Host**: `localhost` (or `127.0.0.1`)
- **Port**: `5432` (default PostgreSQL port)
- **Database**: `journalai`
- **Username**: `duncanabbot` (your macOS username)
- **Password**: (likely empty, or check your PostgreSQL setup)

## Steps to Connect in pgAdmin 4

1. **Open pgAdmin 4**

2. **Add a New Server**:
   - Right-click on "Servers" in the left panel
   - Select "Register" → "Server..."

3. **General Tab**:
   - **Name**: `JournalAI Local` (or any name you prefer)

4. **Connection Tab**:
   - **Host name/address**: `localhost`
   - **Port**: `5432`
   - **Maintenance database**: `postgres` (or `journalai`)
   - **Username**: `duncanabbot`
   - **Password**: 
     - If you haven't set a password, try leaving it blank first
     - If that doesn't work, you may need to set a password (see below)

5. **Advanced Tab** (optional):
   - **DB restriction**: `journalai` (to only show this database)

6. **Click "Save"**

## Troubleshooting Password Issues

If you get a password error, you have a few options:

### Option 1: Check if password is required
```bash
# Try connecting via command line first
psql -d journalai -U duncanabbot
```

If this works without a password, pgAdmin should work with an empty password too.

### Option 2: Set a password for your user
```bash
# Connect to PostgreSQL
psql -U duncanabbot -d postgres

# Set a password
ALTER USER duncanabbot WITH PASSWORD 'your_password_here';

# Exit
\q
```

Then use that password in pgAdmin.

### Option 3: Use the postgres superuser
If you have a `postgres` superuser:
- **Username**: `postgres`
- **Password**: (whatever you set during installation)

## Alternative: Find Connection Details

You can also check your connection details by looking at your environment:
```bash
# Check PostgreSQL socket location
pg_config --socketdir

# Check if PostgreSQL is running
pg_isready

# List databases (to verify connection works)
psql -l
```

## Default macOS PostgreSQL Socket

If connecting via socket instead of TCP/IP:
- **Host**: leave empty or use `localhost`
- **Port**: `5432`
- Or use the socket path: `/tmp` (default for Homebrew PostgreSQL)

## Verify Connection

Once connected, you should see:
- The `journalai` database in the left panel
- Expand it to see:
  - Schemas → public → Tables → `users`
  - Schemas → public → Tables → `schema_migrations`

You can then browse tables, run queries, and manage your database!

