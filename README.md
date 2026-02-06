# Lumefy SaaS Platform

Lumefy is a multi-tenant business management SaaS (Inventory, POS, CRM, ERP) built with modern technologies.

## Architecture

- **Frontend**: Angular 17+ (Mantis Template structure)
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy (Async) + Alembic (Migrations)
- **Infrastructure**: Docker & Docker Compose

## Quick Start (Docker)

The easiest way to run the project is using Docker Compose.

1. **Build and Start Services**
   ```bash
   docker-compose up --build -d
   ```

2. **Run Database Migrations**
   Once the containers are running, apply the initial database schema:
   ```bash
   docker-compose exec backend alembic revision --autogenerate -m "Initial_migration"
   docker-compose exec backend alembic upgrade head
   ```

3. **Access the Application**
   - **Frontend**: http://localhost:4200
   - **Backend API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs

## Local Development Setup

### Backend

1. Navigate to backend directory:
   ```bash
   cd backend
   ```
2. Create virtual environment and install dependencies:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
3. Run with Uvicorn:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start development server:
   ```bash
   ng serve
   ```

## Project Structure

```
c:/Angular/lumefy/
├── backend/            # FastAPI Application
│   ├── app/
│   │   ├── api/        # API Endpoints
│   │   ├── core/       # Config, Security, DB
│   │   ├── models/     # SQLAlchemy Models
│   │   └── schemas/    # Pydantic Schemas
│   ├── alembic/        # Migration Scripts
│   └── requirements.txt
├── frontend/           # Angular Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/       # Guards, Interceptors, Services
│   │   │   ├── features/   # Business Modules (Auth, Dashboard, POS)
│   │   │   └── shared/     # Generic Components
│   └── package.json
└── docker-compose.yml  # Container Orchestration
```
