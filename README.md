TurnAI Full Utils - Cleaning Service API
A comprehensive FastAPI application for managing cleaning services with location-based matching, authentication, and payment integration.

Features
Core Functionality
Cleaner Registration: Register cleaners with location and payment details
Job Creation: Create cleaning jobs with AI-powered price estimation
Location-based Matching: Automatically assign jobs to nearby cleaners
Authentication: JWT-based authentication for secure access
Payment Integration: Stripe integration for payment processing
API Endpoints
Health & Support
GET /health - Application health check
GET /support - Support information
Authentication
POST /token - User login and JWT token generation
POST /cleaners/register - Register new cleaners
Job Management
POST /jobs/create - Create new cleaning jobs with photo analysis
Database Models
Cleaner
Personal information (name, location)
Authentication credentials
Payment integration (Stripe account)
Availability status
Rating system
Job
Job details and location
Price estimation
Status tracking
Cleaner assignment
Payment processing
Setup and Installation
Prerequisites
Python 3.11+
pip package manager
Installation Steps
Install Dependencies

pip install -r requirements.txt
Environment Configuration

export JWT_SECRET="your_secret_key"
export STRIPE_SECRET_KEY="your_stripe_key"
export DATABASE_URL="sqlite:///./turnai_full_utils.db"
Run the Application

uvicorn turnai_full_utils:app --host 0.0.0.0 --port 8000 --reload
API Documentation
Once running, visit http://localhost:8000/docs for interactive API documentation.

Usage Examples
Register a Cleaner
curl -X POST "http://localhost:8000/cleaners/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Cleaner",
    "lat": 40.7128,
    "lon": -74.0060,
    "password": "secure_password"
  }'
Authenticate
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=John Cleaner&password=secure_password"
Create a Job
curl -X POST "http://localhost:8000/jobs/create" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Clean 2-bedroom apartment",
    "lat": 40.7128,
    "lon": -74.0060
  }'
Key Features
AI-Powered Price Estimation
The application uses simulated AI analysis to estimate cleaning prices based on:

Base pricing structure
Image analysis (when photos are provided)
Cleanliness scoring
Market adjustments
Location-Based Matching
Uses Haversine distance calculation for accurate location matching
Finds available cleaners within a 25km radius
Prioritizes cleaners by rating and proximity
Security Features
JWT-based authentication
Password hashing with fallback mechanisms
CORS middleware for web integration
Request logging for monitoring
Technology Stack
FastAPI: Modern Python web framework
SQLAlchemy: Database ORM with SQLite support
Pydantic: Data validation and serialization
JWT: Authentication tokens
Stripe: Payment processing
Passlib: Password hashing
Uvicorn: ASGI server
Development
Running Tests
The application includes built-in health checks and endpoint validation.

Database
Uses SQLite by default with automatic table creation. Can be configured for PostgreSQL or other databases via the DATABASE_URL environment variable.

Logging
Application includes comprehensive logging for debugging and monitoring.

License
This project is part of the TurnAI cleaning service platform.
