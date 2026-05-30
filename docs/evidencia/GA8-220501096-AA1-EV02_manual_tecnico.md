# Manual Tecnico GA8-220501096-AA1-EV02

## 1. Descripcion tecnica de la solucion

`Lumefy` es una plataforma SaaS orientada a operaciones comerciales. El sistema integra modulos administrativos, comerciales, de inventario, logistica, reportes y ecommerce.

Tecnologias principales:

- Frontend: Angular `21.0.3`
- Backend: FastAPI
- ORM: SQLAlchemy
- Migraciones: Alembic
- Base de datos: PostgreSQL `15`
- Contenedorizacion: Docker Compose

## 2. Estructura del proyecto

| Ruta | Contenido |
|---|---|
| `frontend_mantis/` | frontend Angular principal |
| `backend/` | API FastAPI, modelos, esquemas, seeds y pruebas |
| `docs/` | documentacion tecnica y de evidencia |
| `docker-compose.yml` | orquestacion local de backend y base de datos |

## 3. Configuracion tecnica

### 3.1 Backend

Variables identificadas en `backend/.env.example`:

- `POSTGRES_SERVER`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_PORT`
- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `PROJECT_NAME`
- `API_V1_STR`

Valores operativos observados en documentacion:

- API base: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/api/v1/openapi.json`
- Swagger UI: `http://localhost:8000/docs`
- Prefijo API: `/api/v1`

### 3.2 Frontend

- desarrollo: `npm start`
- build: `npm run build`
- URL local: `http://localhost:4200`

## 4. Instalacion y puesta en marcha

### 4.1 Clonacion

```powershell
git clone https://github.com/Alejooc/lumefy.git
cd lumefy
```

### 4.2 Configuracion backend

```powershell
Copy-Item backend\.env.example backend\.env
```

### 4.3 Despliegue local con Docker

```powershell
docker compose up -d --build
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python seed_roles.py
docker compose exec backend python seed_saas.py
docker compose exec backend python ensure_admin_role.py
```

### 4.4 Ejecucion local del frontend

```powershell
cd frontend_mantis
npm install
npm start
```

## 5. Configuracion de base de datos

Motor identificado:

- PostgreSQL `15`

Configuracion documentada:

- host Docker: `db`
- puerto: `5432`
- base por defecto: `lumefy_db`
- usuario por defecto: `postgres`

Cadena de conexion observada:

```text
postgresql+asyncpg://postgres:postgres@db:5432/lumefy_db
```

## 6. Modulos backend por componente

| Componente | Archivo principal |
|---|---|
| autenticacion | `backend/app/api/v1/endpoints/login.py` |
| productos | `backend/app/api/v1/endpoints/products.py` |
| categorias | `backend/app/api/v1/endpoints/categories.py` |
| inventario | `backend/app/api/v1/endpoints/inventory.py` |
| conteos | `backend/app/api/v1/endpoints/stock_take.py` |
| POS | `backend/app/api/v1/endpoints/pos.py` |
| clientes | `backend/app/api/v1/endpoints/clients.py` |
| proveedores | `backend/app/api/v1/endpoints/suppliers.py` |
| compras | `backend/app/api/v1/endpoints/purchases.py` |
| ventas | `backend/app/api/v1/endpoints/sales.py` |
| devoluciones | `backend/app/api/v1/endpoints/returns.py` |
| reportes | `backend/app/api/v1/endpoints/reports.py` |
| auditoria | `backend/app/api/v1/endpoints/audit.py` |
| usuarios | `backend/app/api/v1/endpoints/users.py` |
| roles | `backend/app/api/v1/endpoints/roles.py` |
| apps | `backend/app/api/v1/endpoints/apps.py` |
| ecommerce | `backend/app/api/v1/endpoints/storefront.py` |

## 7. Modulos frontend por componente

| Componente | Ruta base |
|---|---|
| admin | `frontend_mantis/src/app/modules/admin` |
| apps | `frontend_mantis/src/app/modules/apps` |
| audit | `frontend_mantis/src/app/modules/audit` |
| branches | `frontend_mantis/src/app/modules/branches` |
| brands | `frontend_mantis/src/app/modules/brands` |
| categories | `frontend_mantis/src/app/modules/categories` |
| clients | `frontend_mantis/src/app/modules/clients` |
| company | `frontend_mantis/src/app/modules/company` |
| inventory | `frontend_mantis/src/app/modules/inventory` |
| logistics | `frontend_mantis/src/app/modules/logistics` |
| pos | `frontend_mantis/src/app/modules/pos` |
| products | `frontend_mantis/src/app/modules/products` |
| profile | `frontend_mantis/src/app/modules/profile` |
| purchasing | `frontend_mantis/src/app/modules/purchasing` |
| reports | `frontend_mantis/src/app/modules/reports` |
| returns | `frontend_mantis/src/app/modules/returns` |
| sales | `frontend_mantis/src/app/modules/sales` |
| settings | `frontend_mantis/src/app/modules/settings` |
| units-of-measure | `frontend_mantis/src/app/modules/units-of-measure` |
| users | `frontend_mantis/src/app/modules/users` |

## 8. Entradas y salidas tecnicas

### 8.1 Entrada

- formularios Angular
- parametros de ruta
- parametros query
- payload JSON
- archivos multipart
- autenticacion por token bearer

### 8.2 Salida

- respuestas JSON
- exportaciones
- archivos PDF
- archivos compilados del frontend
- documentacion OpenAPI

## 9. Pruebas y validaciones

Pruebas automatizadas ejecutadas:

- `backend/tests/test_client_validations.py`
- `backend/test_security.py`

Resultado:

- pruebas unitarias backend: `7/7 OK`
- hash de seguridad: exitoso

Pruebas funcionales manuales apoyadas:

- coleccion Postman generada desde OpenAPI
- documentacion de endpoints por modulo

## 10. Ambientes

Documentos complementarios disponibles:

- `docs/ambientes_desarrollo_pruebas.md`
- `docs/diagramas_arquitectura_lumefy.md`
- `docs/postman/GUIA_EVIDENCIA_POSTMAN.md`

## 11. Mantenimiento tecnico

Para cambios estructurales en base de datos:

```powershell
docker compose exec backend python -m alembic revision --autogenerate -m "descripcion"
docker compose exec backend python -m alembic upgrade head
```

Para regenerar la coleccion Postman:

```powershell
cd backend
.\venv\Scripts\python.exe ..\docs\generate_postman_assets.py
```
