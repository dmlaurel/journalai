# Connecting to PostgreSQL with pgAdmin 4

This guide covers connecting to both your **Render.com database** and **local database** using pgAdmin 4.

---

## Connecting to Render.com Database

### Step 1: Get Your Connection Details from Render

1. **Go to your Render Dashboard**: https://dashboard.render.com
2. **Navigate to your PostgreSQL database** (not the web service)
3. **Click on your database** to open its details
4. **Look for the "Connections" section** - you'll see:
   - **Internal Database URL** (for services on Render)
   - **External Database URL** (for connecting from outside Render, like pgAdmin)

### Step 2: Parse the Connection String

Render provides a connection string in this format:
```
postgres://username:password@hostname:port/database_name
```

Or if you see it in your environment variables:
```
postgresql://username:password@hostname:port/database_name
```

**Extract these values:**
- **Host**: The hostname (e.g., `dpg-xxxxx-a.oregon-postgres.render.com`)
- **Port**: Usually `5432` (check the connection string)
- **Database**: The database name (e.g., `journalai_xxxx`)
- **Username**: The username from the connection string
- **Password**: The password from the connection string

### Step 3: Enable External Connections (if needed)

Some Render databases require you to enable external connections:

1. In your Render database dashboard
2. Look for **"Connections"** or **"Network"** settings
3. Enable **"Allow connections from outside"** or similar option
4. You may need to add your IP address to an allowlist (or allow all IPs for development)

### Step 4: Connect in pgAdmin 4

1. **Open pgAdmin 4**

2. **Add a New Server**:
   - Right-click on "Servers" in the left panel
   - Select "Register" → "Server..."

3. **General Tab**:
   - **Name**: `JournalAI Render` (or any name you prefer)

4. **Connection Tab**:
   - **Host name/address**: The hostname from your Render connection string
     - Example: `dpg-xxxxx-a.oregon-postgres.render.com`
   - **Port**: `5432` (or the port from your connection string)
   - **Maintenance database**: Usually `postgres` (or the database name from your connection string)
   - **Username**: The username from your Render connection string
   - **Password**: The password from your Render connection string
   - ✅ **Check "Save password"** if you want pgAdmin to remember it

5. **SSL Tab** (Important for Render):
   - **SSL mode**: Select `Require` or `Prefer`
     - Render databases require SSL connections
   - If you get SSL errors, try:
     - **SSL mode**: `Require`
     - Or check "Allow self-signed certificates"

6. **Advanced Tab** (optional):
   - **DB restriction**: Your database name (to only show this database)

7. **Click "Save"**

### Alternative: Get Connection String from Environment

If you have access to your Render service environment variables, you can also get the connection string there:

1. Go to your Render service (not the database)
2. Click on "Environment" tab
3. Look for `DATABASE_URL` variable
4. Parse it as described above

The format is typically:
```
postgres://[username]:[password]@[hostname]:[port]/[database_name]
```

### Troubleshooting Render Connection Issues

**Issue: "Connection refused" or "Can't connect"**
- ✅ Make sure external connections are enabled in Render
- ✅ Check that your IP address is allowed (or allow all IPs)
- ✅ Verify the hostname and port are correct
- ✅ Try using the **External Database URL** from Render (not the internal one)

**Issue: "SSL required" or SSL errors**
- ✅ Set SSL mode to `Require` in pgAdmin
- ✅ Try `Prefer` if `Require` doesn't work
- ✅ Check "Allow self-signed certificates" if needed

**Issue: "Authentication failed"**
- ✅ Double-check username and password from the connection string
- ✅ Make sure you're using the External Database URL credentials
- ✅ Try regenerating the database password in Render if needed

**Issue: "Database does not exist"**
- ✅ Use `postgres` as the maintenance database
- ✅ Check the database name in the connection string

---

## Connecting to Local Database

### Connection Details

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

