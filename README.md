# <p align="center"> <img src="https://via.placeholder.com/200x80?text=LUMEFY" alt="Lumefy Logo" width="200" /> </p>

<p align="center">
  <b>The Unified SaaS Solution for Modern Business Management</b><br>
  <i>Inventory • POS • CRM • ERP • Multi-Tenant Architecture</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Angular-DD0031?style=flat-square&logo=angular&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/LICENSE-MIT-green?style=flat-square" />
</p>

---

## ⚡ Quick Start (Docker)

The fastest way to deploy the entire stack is using **Docker Compose**.

1. **Clone & Configure**
   ```bash
   git clone https://github.com/Alejooc/lumefy.git
   cd lumefy
   cp backend/.env.example backend/.env
   ```

2. **Launch Services**
   ```bash
   docker-compose up --build -d
   ```

3. **Initialize Database**
   ```bash
   docker-compose exec backend alembic upgrade head
   docker-compose exec backend python seed_roles.py
   ```

---

## 🏗️ Architecture

Lumefy is built on a modern, decoupled architecture designed for high availability and scalability.

```mermaid
graph LR
    User([User Agent]) -->|Frontend:4200| Angular[Angular SPA]
    Angular -->|REST API| FastAPI[FastAPI Backend:8000]
    FastAPI -->|Async Engine| Postgres[(PostgreSQL)]
    FastAPI -->|Schemas| Pydantic[Pydantic Models]
    FastAPI -->|Auth| JWT[JWT Bearer Token]
```

---

## 🛠️ Detailed Installation

### Backend (FastAPI)
The backend requires Python 3.11+.

1. **Virtual Environment**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate # Windows
   pip install -r requirements.txt
   ```
2. **Environment Variables**
   Create a `.env` file with the following:
   ```env
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_SERVER=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=lumefy
   SECRET_KEY=super-secret-key-change-me
   ```
3. **Run Dev Server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend (Angular)
The frontend uses the premium **Mantis Template**.

1. **Install Deps**
   ```bash
   cd frontend_mantis
   npm install
   ```
2. **Launch**
   ```bash
   npm start # Runs on http://localhost:4200
   ```

---

## 🛡️ Role-Based Access Control (RBAC)
Lumefy uses a structured permission system stored as `JSONB` for flexibility.

| Role | Permissions | Description |
| :--- | :--- | :--- |
| **ADMIN** | `{"all": true}` | Full system access |
| **MANAGER** | `{"manage_users": true, ...}` | Store-level operations |
| **CASHIER** | `{"pos_access": true, ...}` | Selling and inventory view |

---

## 🧩 Modularity
Each module is designed to be isolated yet integrated:
- **`app/api/v1/`**: Versioned API endpoints.
- **`app/models/`**: Domain models with SQLAlchemy.
- **`src/app/modules/`**: Feature-based Angular modules.

---

## 🔧 Troubleshooting

- **CORS Errors**: Ensure `BACKEND_CORS_ORIGINS` in your `.env` includes your development URL.
- **Migration Issues**: If `alembic upgrade head` fails, verify your PostgreSQL connection string in `.env`.
- **Node Modules**: If the frontend fails to build, try `npm cache clean --force` followed by a fresh `npm install`.

---

<p align="center">
  <b>Developed by the Lumefy Engineering Team</b>
</p>
