# Database Migrations

This document explains how to set up and run database migrations for the Journie application.

## Local Development Setup

### 1. Install PostgreSQL

**macOS (using Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Or use Docker (recommended):**
```bash
docker run --name journalai-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=journalai \
  -p 5432:5432 \
  -d postgres:14
```

### 2. Create Database

If not using Docker, create the database:
```bash
createdb journalai
```

Or connect as postgres user:
```bash
psql -U postgres -c 'CREATE DATABASE journalai;'
```

### 3. Configure Environment Variables

Create a `.env` file in the `backend/` directory with:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=journalai
DB_USER=postgres
DB_PASSWORD=postgres
```

### 4. Install Dependencies

Make sure you have the required Python packages:
```bash
cd backend
pip install -r requirements.txt
```

### 5. Run Migrations

```bash
python run_migrations.py
```

## Render.com Deployment

### Automatic Migration on Deploy

To automatically run migrations when deploying to Render, add a build command that runs migrations before starting the app.

1. **Option 1: Add to Build Command** (Recommended)
   - In your Render service settings, set the Build Command to:
   ```bash
   pip install -r requirements.txt && python run_migrations.py
   ```
   - Set the Start Command to:
   ```bash
   python app.py
   ```

2. **Option 2: Use a Startup Script**
   - Create a `start.sh` script:
   ```bash
   #!/bin/bash
   python run_migrations.py
   python app.py
   ```
   - Make it executable: `chmod +x start.sh`
   - Set Start Command to: `./start.sh`

### Environment Variables on Render

Make sure these are set in your Render service:
- `DATABASE_URL` - Automatically provided by Render when you link a PostgreSQL database
- `SECRET_KEY` - Generate a random string for Flask sessions
- Other required variables (Gmail API keys, etc.)

### Manual Migration on Render

If you need to run migrations manually on Render:

1. SSH into your Render service (if available)
2. Or use Render's Shell feature in the dashboard
3. Run: `python run_migrations.py`

## Migration Files

Migrations are stored in `backend/migrations/` directory:
- `001_create_users_table.py` - Creates the users table

Each migration file should have:
- `up(conn)` function - Applies the migration
- `down(conn)` function - Rolls back the migration (optional)

## Creating New Migrations

1. Create a new file in `migrations/` directory:
   - Format: `002_<description>.py`
   - Example: `002_add_phone_number.py`

2. Add the migration functions:
   ```python
   def up(conn):
       cursor = conn.cursor()
       cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)")
       conn.commit()
       cursor.close()
   
   def down(conn):
       cursor = conn.cursor()
       cursor.execute("ALTER TABLE users DROP COLUMN phone_number")
       conn.commit()
       cursor.close()
   ```

3. The migration system will automatically detect and run it.

## Troubleshooting

### Connection Issues
- Verify PostgreSQL is running: `psql -l` or `docker ps`
- Check environment variables are set correctly
- Test connection: `psql -h localhost -U postgres -d journalai`

### Migration Already Applied
- The system tracks applied migrations in `schema_migrations` table
- If a migration shows as already applied, it won't run again
- To re-run, you'd need to manually remove from `schema_migrations` table

### Database Locked
- Close any open connections to the database
- Check for long-running queries: `SELECT * FROM pg_stat_activity;`

