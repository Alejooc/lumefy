# Diagramas de Arquitectura de Lumefy

## 1. Alcance

Los diagramas incluidos en este documento corresponden exclusivamente a:

- `frontend_mantis`
- `backend`
- PostgreSQL

## 2. Arquitectura general

```mermaid
flowchart LR
    U[Usuario]
    FE[Frontend Angular\nfrontend_mantis]
    API[Backend FastAPI\nbackend]
    DB[(PostgreSQL)]

    U --> FE
    FE -->|HTTP REST| API
    API -->|SQLAlchemy / Alembic| DB
```

## 3. Arquitectura logica del frontend

```mermaid
flowchart TD
    A[AppRoutingModule]
    L1[LandingLayout]
    L2[GuestLayout]
    L3[AdminLayout]
    G1[AuthGuard]
    G2[GuestGuard]
    G3[SuperuserGuard]

    A --> L1
    A --> L2
    A --> L3
    A --> G1
    A --> G2
    A --> G3

    L3 --> M1[Dashboard]
    L3 --> M2[Productos]
    L3 --> M3[Categorias]
    L3 --> M4[Inventario]
    L3 --> M5[Compras]
    L3 --> M6[Ventas]
    L3 --> M7[Devoluciones]
    L3 --> M8[Logistica]
    L3 --> M9[Clientes]
    L3 --> M10[Usuarios]
    L3 --> M11[Reportes]
    L3 --> M12[Administracion]
    L3 --> M13[Apps]
```

## 4. Arquitectura logica del backend

```mermaid
flowchart TD
    Main[app.main]
    Router[app.api.v1.api]
    Endpoints[Endpoints REST]
    Core[Core\nconfig auth middleware rate_limit]
    Services[Services\nemail export pdf]
    Models[Models SQLAlchemy]
    Schemas[Schemas Pydantic]
    DB[(PostgreSQL)]

    Main --> Router
    Router --> Endpoints
    Endpoints --> Core
    Endpoints --> Services
    Endpoints --> Models
    Endpoints --> Schemas
    Models --> DB
```

## 5. Flujo de autenticacion

```mermaid
sequenceDiagram
    participant U as Usuario
    participant FE as Frontend Angular
    participant BE as FastAPI
    participant DB as PostgreSQL

    U->>FE: Ingresa credenciales
    FE->>BE: POST /api/v1/login
    BE->>DB: Valida usuario
    DB-->>BE: Datos del usuario
    BE-->>FE: Token / sesion
    FE-->>U: Acceso a modulos segun rol
```

## 6. Flujo de consumo de modulos

```mermaid
sequenceDiagram
    participant U as Usuario
    participant FE as Modulo Angular
    participant S as Servicio Angular
    participant API as Endpoint FastAPI
    participant DB as PostgreSQL

    U->>FE: Solicita operacion
    FE->>S: Ejecuta accion
    S->>API: Llamado HTTP
    API->>DB: Consulta o actualizacion
    DB-->>API: Resultado
    API-->>S: Respuesta JSON
    S-->>FE: Datos procesados
    FE-->>U: Vista actualizada
```

## 7. Modulos funcionales identificados

### Frontend

- autenticacion
- dashboard
- productos
- categorias
- inventario
- compras
- ventas
- devoluciones
- logistica
- clientes
- usuarios
- auditoria
- reportes
- administracion
- apps

### Backend API

- `login`
- `products`
- `categories`
- `inventory`
- `pos`
- `companies`
- `reports`
- `clients`
- `users`
- `roles`
- `audit`
- `suppliers`
- `purchases`
- `pricelists`
- `sales`
- `admin`
- `plans`
- `branches`
- `logistics`
- `brands`
- `units-of-measure`
- `upload`
- `dashboard`
- `system`
- `search`
- `notifications`
- `apps`
- `storefront`
- `stock-take`
- `returns`

