import os
import psycopg2
import logging
from psycopg2 import pool
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Connection pool (will be initialized on first use)
_connection_pool = None

def get_db_connection_string():
    """
    Get database connection string based on environment.
    - Local: Uses DATABASE_URL from .env or defaults to localhost
    - Render: Uses DATABASE_URL from environment (provided by Render)
    """
    # Check if we have a DATABASE_URL (used by Render.com)
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Render.com provides DATABASE_URL in format: postgres://user:pass@host:port/dbname
        # But psycopg2 expects postgresql:// (not postgres://)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        logger.info("Using DATABASE_URL from environment (Render.com)")
        return database_url
    
    # Local development - construct from individual components or use local defaults
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'journalai')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    
    conn_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    logger.info(f"Using local database connection: {db_host}:{db_port}/{db_name}")
    return conn_string

def _init_connection_pool():
    """Initialize the connection pool"""
    global _connection_pool
    if _connection_pool is None:
        conn_string = get_db_connection_string()
        try:
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # min connections
                10,  # max connections
                conn_string
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {str(e)}")
            raise
    return _connection_pool

@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Uses connection pool for efficiency.
    """
    pool = _init_connection_pool()
    conn = None
    try:
        conn = pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        if conn:
            pool.putconn(conn)

