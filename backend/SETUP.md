# Quick Setup Guide

## Local Development Setup

### 1. Set Up Local PostgreSQL Database

**Option A: Using Docker (Recommended)**
```bash
docker run --name journalai-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=journalai \
  -p 5432:5432 \
  -d postgres:14
```

**Option B: Using System PostgreSQL**
```bash
# Install PostgreSQL (if not installed)
brew install postgresql@14  # macOS
# or
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian

# Create database
createdb journalai
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database Configuration (for local development)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=journalai
DB_USER=postgres
DB_PASSWORD=postgres

# Flask Secret Key (generate a random string)
SECRET_KEY=your_secret_key_here

# Add your other environment variables from env_template.txt
# (Gmail API keys, Twilio, etc.)
```

### 3. Install Dependencies

```bash
cd backend
source venv/bin/activate  # or create a new venv
pip install -r requirements.txt
```

### 4. Run Migrations

```bash
python run_migrations.py
```

This will:
- Create the `users` table
- Create indexes for better performance
- Track applied migrations

### 5. Start the Backend Server

```bash
python app.py --local
```

The server will run on `http://localhost:5000`

## Testing the Login Flow

### 1. Create a Test User

You'll need to manually insert a test user into the database:

```bash
psql -h localhost -U postgres -d journalai
```

Then:
```sql
INSERT INTO users (email, first_name, last_name) 
VALUES ('test@example.com', 'Test', 'User');
```

### 2. Test Login

1. Open the frontend (`frontend/index.html` in a browser)
2. Click "Log In" button (top right)
3. Enter the email: `test@example.com`
4. Check your email for the 6-digit code
5. Enter the code to log in
6. You should see your profile page

## Render.com Deployment

### 1. Set Up PostgreSQL on Render

1. Go to your Render dashboard
2. Create a new PostgreSQL database
3. Note the `DATABASE_URL` - Render provides this automatically

### 2. Configure Environment Variables

In your Render service settings, set:
- `DATABASE_URL` - Automatically provided by Render when you link the database
- `SECRET_KEY` - Generate a random string
- Other required variables (Gmail API keys, etc.)

### 3. Automatic Migrations on Deploy

**Option 1: Build Command (Recommended)**
- Set Build Command: `pip install -r requirements.txt && python run_migrations.py`
- Set Start Command: `python app.py`

**Option 2: Startup Script**
Create `start.sh`:
```bash
#!/bin/bash
python run_migrations.py
python app.py
```

Make it executable and set Start Command to: `./start.sh`

### 4. Manual Migration (if needed)

If you need to run migrations manually on Render:

1. Use Render's Shell feature in the dashboard
2. Run: `python run_migrations.py`

## Database Schema

The `users` table has the following structure:

- `id` - SERIAL PRIMARY KEY (auto-incrementing)
- `email` - VARCHAR(255) UNIQUE NOT NULL
- `first_name` - VARCHAR(255)
- `last_name` - VARCHAR(255)
- `one_time_code` - VARCHAR(10) (temporary, for login)
- `one_time_code_expiry` - TIMESTAMP (expires after 15 minutes)
- `created_at` - TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at` - TIMESTAMP DEFAULT CURRENT_TIMESTAMP

## Troubleshooting

### Database Connection Issues

1. Verify PostgreSQL is running:
   ```bash
   docker ps  # for Docker
   psql -l    # for system PostgreSQL
   ```

2. Check environment variables are set correctly

3. Test connection:
   ```bash
   psql -h localhost -U postgres -d journalai
   ```

### Migration Issues

1. Check if migrations table exists:
   ```sql
   SELECT * FROM schema_migrations;
   ```

2. If a migration fails, check the logs for errors

3. To re-run a migration, you'd need to manually remove it from `schema_migrations` table

### Email Not Sending

1. Verify Gmail API credentials are set in `.env`
2. Check that `GMAIL_REFRESH_TOKEN` is valid
3. Ensure email service is configured correctly

