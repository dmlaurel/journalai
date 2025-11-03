#!/bin/bash
# Script to set up local PostgreSQL database for development

set -e

echo "Setting up local PostgreSQL database..."

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed. Please install it first:"
    echo "  macOS: brew install postgresql@14"
    echo "  Ubuntu: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi

# Check if Docker is available (for easier PostgreSQL setup)
if command -v docker &> /dev/null; then
    echo "Docker detected. You can use Docker to run PostgreSQL:"
    echo ""
    echo "To start PostgreSQL with Docker:"
    echo "  docker run --name journalai-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=journalai -p 5432:5432 -d postgres:14"
    echo ""
    echo "To stop PostgreSQL:"
    echo "  docker stop journalai-postgres"
    echo ""
    echo "To remove the container:"
    echo "  docker rm journalai-postgres"
    echo ""
    read -p "Do you want to start PostgreSQL with Docker now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Check if container already exists
        if docker ps -a --format '{{.Names}}' | grep -q "^journalai-postgres$"; then
            echo "Container already exists. Starting it..."
            docker start journalai-postgres
        else
            echo "Creating and starting PostgreSQL container..."
            docker run --name journalai-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=journalai -p 5432:5432 -d postgres:14
            echo "Waiting for PostgreSQL to start..."
            sleep 3
        fi
        echo "PostgreSQL is running on localhost:5432"
        echo "Database: journalai"
        echo "User: postgres"
        echo "Password: postgres"
    fi
else
    echo "Docker is not installed. Using system PostgreSQL instead."
    echo ""
    echo "Please ensure PostgreSQL is running and create a database:"
    echo "  createdb journalai"
    echo ""
    echo "Or connect as postgres user and create:"
    echo "  psql -U postgres -c 'CREATE DATABASE journalai;'"
fi

echo ""
echo "Next steps:"
echo "1. Make sure your .env file has the database configuration:"
echo "   DB_HOST=localhost"
echo "   DB_PORT=5432"
echo "   DB_NAME=journalai"
echo "   DB_USER=postgres"
echo "   DB_PASSWORD=postgres"
echo ""
echo "2. Run migrations:"
echo "   python migrations/migrate.py"

