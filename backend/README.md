# PhotoShare Backend

Multi-tenant SaaS Django backend for private church media platform.

## Overview

This backend is designed for multi-tenant architecture where each church operates as an isolated tenant with their own data and media storage while sharing the same application infrastructure.

## Tech Stack

- **Django 5.0.7** - Web framework
- **Django REST Framework 3.15.2** - API framework
- **PostgreSQL** - Primary database (multi-tenant with tenant isolation)
- **JWT (SimpleJWT)** - Authentication system
- **CORS Headers** - Frontend integration support

## Key Architecture Features

### Multi-Tenancy
- **Tenant Isolation**: Each church's data is completely isolated
- **Shared Infrastructure**: Common codebase and infrastructure
- **Scalable Design**: Designed to support hundreds of church tenants

### Security
- JWT-based authentication with token refresh
- CORS configured for React frontend
- Tenant-aware permissions (to be implemented)
- Secure password validation

## Project Structure

```
backend/
├── photoshare_backend/     # Main Django project
│   ├── settings.py        # Comprehensive configuration
│   ├── urls.py           # API routing
│   └── ...
├── core/                 # Shared functionality across tenants
├── tenants/             # Multi-tenant management
├── requirements.txt     # Python dependencies
└── manage.py           # Django management script
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Django Core
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL required)
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# CORS (React frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Database Setup

1. Install PostgreSQL
2. Create database: `createdb photoshare_dev`
3. Update `DATABASE_URL` in `.env`
4. Run migrations: `python manage.py migrate`

## Development Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Database Migration**
   ```bash
   python manage.py migrate
   ```

4. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Authentication
- `POST /api/auth/token/` - Obtain JWT token pair
- `POST /api/auth/token/refresh/` - Refresh access token

### API Structure (Future Implementation)
- `/api/v1/core/` - Shared functionality
- `/api/v1/tenants/` - Tenant management
- `/api/v1/churches/{church_id}/` - Church-specific resources

## Multi-Tenant Strategy

### Current Configuration
- **TENANT_MODEL**: Will point to `tenants.Tenant`
- **SHARED_APPS**: Common functionality (auth, admin, tenants)
- **TENANT_APPS**: Isolated per-tenant (core, media, users)

### Next Steps for Multi-Tenancy
1. Implement Tenant and Domain models
2. Add tenant-aware middleware
3. Create tenant-specific routing
4. Implement tenant isolation in queries

## Development Guidelines

### Tenant Isolation Rules
- **Never write queries without tenant filtering**
- **Always include tenant context in API views**
- **Use tenant-aware permissions**
- **Validate tenant access on all operations**

### Code Organization
- `core/` - Functionality shared across tenants
- `tenants/` - Multi-tenant management logic
- Future apps should be tenant-aware by default

## Next Implementation Steps

1. **Tenant Models** - Tenant and Domain models with proper relationships
2. **Authentication Views** - Custom JWT views with tenant context
3. **Middleware** - Tenant resolution and context injection
4. **Permissions** - Tenant-aware permission classes
5. **Media Management** - Tenant-isolated file storage

---

**Note**: This backend is configured but does not yet contain business logic, models, or authentication views. It provides the foundation for a secure, scalable multi-tenant architecture.