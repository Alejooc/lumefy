# Lumefy

Plataforma SaaS con:
- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: Angular
- Base de datos: PostgreSQL

## Requisitos
- Git
- Docker Desktop (con engine corriendo)

## Instalacion con Docker (recomendada)

### 1. Clonar repositorio
```bash
git clone https://github.com/Alejooc/lumefy.git
cd lumefy
```

### 2. Configurar variables de entorno del backend
```bash
# Windows PowerShell
Copy-Item backend\.env.example backend\.env

# Linux/macOS
cp backend/.env.example backend/.env
```

Para Docker, deja estos valores en `backend/.env`:
```env
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=lumefy_db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/lumefy_db
```

### 3. Levantar servicios
```bash
docker compose up -d --build
```

### 4. Verificar contenedores
```bash
docker compose ps
docker compose logs db --tail=100
docker compose logs backend --tail=100
```

### 5. Ejecutar migraciones de base de datos
```bash
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic upgrade head
```

### 6. Cargar datos iniciales
```bash
docker compose exec backend python seed_roles.py
docker compose exec backend python seed_saas.py
docker compose exec backend python ensure_admin_role.py
```

### 7. Acceso
- Frontend: `http://localhost:4200`
- Backend: `http://localhost:8000`
- Docs API: `http://localhost:8000/docs`
- Usuario inicial:
  - Email: `admin@lumefy.com`
  - Password: `admin123`

## Comandos utiles de DB y Alembic

### Estado de migraciones
```bash
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic heads
docker compose exec backend python -m alembic history -i
```

### Subir/Bajar version
```bash
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m alembic downgrade -1
```

### Entrar a PostgreSQL dentro del contenedor
```bash
docker compose exec db psql -U postgres -d lumefy_db
```

### Ver tablas
```sql
\dt
```

### Ver version aplicada por Alembic
```sql
SELECT * FROM alembic_version;
```

## Flujo cuando agregues un nuevo modulo (estructura DB)

Siempre que cambies modelos:

1. Crear o editar modelos SQLAlchemy en `backend/app/models/`.
2. Generar migracion:
```bash
docker compose exec backend python -m alembic revision --autogenerate -m "add modulo_x"
```
3. Revisar el archivo generado en `backend/alembic/versions/`.
4. Aplicar migracion:
```bash
docker compose exec backend python -m alembic upgrade head
```
5. Probar API y frontend.
6. Subir al repositorio:
- Cambios en modelos
- Nueva migracion Alembic
- Seeds si agregaste datos iniciales requeridos

## Instalacion en otro equipo

En un equipo nuevo solo necesitas:

1. Clonar repo.
2. Configurar `backend/.env` para Docker (host `db`).
3. Levantar:
```bash
docker compose up -d --build
```
4. Migrar DB:
```bash
docker compose exec backend python -m alembic upgrade head
```
5. Cargar seeds:
```bash
docker compose exec backend python seed_roles.py
docker compose exec backend python seed_saas.py
```

## Troubleshooting rapido

### Error Docker pipe `dockerDesktopLinuxEngine`
Docker Desktop no esta iniciado. Abre Docker Desktop y espera `Engine running`.

### `alembic` no encontrado
Ejecuta con modulo Python:
```bash
python -m alembic ...
```
o dentro del contenedor backend:
```bash
docker compose exec backend python -m alembic ...
```

### Error de conexion DB en local
Si ejecutas fuera de Docker, en `backend/.env` usa `127.0.0.1` en lugar de `db`.

