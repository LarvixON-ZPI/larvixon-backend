<!-- markdownlint-disable MD041 -->

[![Django CI](https://github.com/LarvixON-ZPI/larvixon-backend/actions/workflows/django.yml/badge.svg)](https://github.com/LarvixON-ZPI/larvixon-backend/actions/workflows/django.yml)

# Larvixon Backend

REST API backend for the Larvixon larval behavior analysis system. Built with Django REST Framework and includes comprehensive user account management and video analysis tracking.

## Features

- **User Authentication**: Registration, login, logout with JWT tokens
- **User Profile Management**: Extended profile information and preferences
- **Video Analysis Tracking**: History and results of larval video analyses
- **User Feedback System**: Allow users to provide feedback on analysis results
- **Comprehensive API Documentation**: Auto-generated Swagger/OpenAPI docs
- **Test Suite**: Both Django tests and unittest implementations

## Tech Stack

- **Backend Framework**: Django 5.2.5
- **API Framework**: Django REST Framework
- **Authentication**: JWT tokens (djangorestframework-simplejwt)
- **Documentation**: drf-spectacular (Swagger/OpenAPI)
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Testing**: Django TestCase + Python unittest

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/LarvixON-ZPI/larvixon-backend.git
cd larvixon-backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate
# OR on macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Local DB Setup

This project uses **PostgreSQL** for its database. You have two options:

#### Option A: Using Docker (Recommended - See Section 3)

Skip to section 3 to run both the application and PostgreSQL using Docker. This is the easiest way to get started.

#### Option B: Manual PostgreSQL Setup

If you prefer to run PostgreSQL locally without Docker, follow these steps:

##### 2.1 Install and Start PostgreSQL

Install PostgreSQL using your system's package manager (e.g., Homebrew, EDB Installer). Ensure the server is running on the default port (`5432`).

##### 2.2 Create the Database and User

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then access your PostgreSQL command line (`psql`) and run these commands, replacing the credentials with the values from your `.env` file:

```sql
CREATE DATABASE larvixon_local_db;

CREATE USER larvixon_user WITH PASSWORD 'localpassword';

GRANT ALL PRIVILEGES ON DATABASE larvixon_local_db TO larvixon_user;

ALTER ROLE larvixon_user CREATEDB;

-- It might be necessary to set the user as the owner of the default public schema 
\c larvixon_local_db;
ALTER SCHEMA public OWNER TO larvixon_user;
GRANT ALL ON SCHEMA public TO larvixon_user;
```

example `.env` file:

```bash
DATABASE_URL=postgres://larvixon_user:localpassword@localhost:5433/larvixon_local_db
```

### 2.3 Seed Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed database
python manage.py seed
python manage.py seed_substances
```

#### Configuring Social Authentication

For Google Login add in `.env`

```bash
GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
GOOGLE_SECRET="YOUR_GOOGLE_SECRET_KEY"
```

And fill it with your own keys from <https://console.cloud.google.com>

### 3. Run Server

#### Option A: Using Docker

The easiest way to run the application with PostgreSQL is using Docker:

```bash
cp .env.example .env
```

Edit .env and update the values if needed

##### Development mode

```bash
docker-compose up -d

# The application will automatically run migrations
# To create a superuser and seed the database:
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py seed
docker-compose exec web python manage.py seed_substances
```

The server will start at `http://127.0.0.1:8000`

##### Production mode

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# The application will automatically run migrations
# To create a superuser and seed the database:
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py seed
docker-compose exec web python manage.py seed_substances
```

You should then make requests to:
nginx: <http://localhost:8080/>

Direct backend access: <http://localhost:8000/>
Useful for testing/debugging

#### Option B: Local Development

```bash
python manage.py runserver
```

The server will start at `http://127.0.0.1:8000`

## API Documentation

### Swagger UI

- **Main Swagger UI**: <http://127.0.0.1:8000/>
- **Alternative URL**: <http://127.0.0.1:8000/api/docs/>
- **ReDoc**: <http://127.0.0.1:8000/api/redoc/>
- **OpenAPI Schema**: <http://127.0.0.1:8000/api/schema/>

### Admin Interface

- **Django Admin**: <http://127.0.0.1:8000/admin/>

## Testing

### Django Tests

Run the comprehensive Django test suite:

```bash
python manage.py test
```

### CI/CD pipelines

Recommended to install [nektos/act](https://github.com/nektos/act) and Docker Desktop.

then run:

```sh
act --workflows ".github/workflows/django.yml" \
    --job build \
    -P ubuntu-latest=catthehacker/ubuntu:act-22.04
```

Just ubuntu-latests results in this issue: <https://github.com/nektos/act/issues/251>

## Production Deployment

For production deployment:

1. Set `DEBUG = False` in settings
2. Configure proper database (PostgreSQL)
3. Set up proper SECRET_KEY
4. Configure static files serving
5. Use production WSGI server (Gunicorn)
6. Set up HTTPS with proper CORS settings

## Contributing

1. Follow Django/DRF best practices
2. Add Swagger documentation to new endpoints
3. Write comprehensive tests for new features
4. Try to follow [Conventional Commit Messages](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13)
5. Use Python Black formatter and ensure type checking is set as Standard or higher

## Recommended tooling

### Python

Using version 3.12.6

Test GitHub workflows locally with nektos/act

VSCode with extensions like Pylance, GitHub Local Actions
