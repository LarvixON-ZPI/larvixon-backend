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

### 2. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 3. Run Server

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

### Python Unittest

Run the standalone unittest suite:

```bash
python -m unittest -v -s ./tests -p "*_test.py"
```

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
