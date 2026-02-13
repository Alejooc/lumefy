# <p align="center">🚀 Lumefy: Ilumina tu Negocio 💡</p>

<p align="center">
  <b>La plataforma SaaS todo-en-uno para el emprendedor moderno.</b><br>
  <i>Escalable. Modular. Diseñado para Crecer.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Made%20with-Love%20%26%20Code-ff69b4?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Framework-FastAPI%20%2B%20Angular-blueviolet?style=for-the-badge" />
  <img src="https://img.shields.io/github/v/release/Alejooc/lumefy?style=for-the-badge&color=orange" />
</p>

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

*   **Git**: [Descargar](https://git-scm.com/)
*   **Docker Desktop** (para instalación recomendada): [Descargar](https://www.docker.com/products/docker-desktop/)
*   **Node.js v18+** (solo para instalación manual): [Descargar](https://nodejs.org/)
*   **Python 3.10+** (solo para instalación manual): [Descargar](https://www.python.org/)

---

## 🚀 Opción 1: Instalación Rápida con Docker (Recomendada)

La forma más fácil de probar Lumefy sin configurar entornos locales complejos.

### 1. Clonar el repositorio
```bash
git clone https://github.com/Alejooc/lumefy.git
cd lumefy
```

### 2. Configurar entorno
Copia la configuración de ejemplo:
```bash
# Windows (PowerShell)
copy backend\.env.example backend\.env

# Linux / Mac
cp backend/.env.example backend/.env
```

### 3. Iniciar servicios
```bash
docker-compose up -d --build
```
*Espera unos minutos mientras se descargan las imágenes y se construye el frontend.*

### 4. Inicializar base de datos
Ejecuta estos comandos una sola vez para crear las tablas y datos iniciales:
```bash
# Aplicar migraciones
docker-compose exec backend alembic upgrade head

# Crear roles y usuario administrador
docker-compose exec backend python seed_roles.py

# (Opcional) Cargar datos SaaS y de prueba
docker-compose exec backend python seed_saas.py
```

### 5. ¡Listo! 
Accede a la plataforma en: http://localhost:4200
*   **Usuario**: `admin@lumefy.com`
*   **Contraseña**: `admin123`

---

## 🛠️ Opción 2: Instalación Manual (Desarrollo)

Si prefieres ejecutar todo en tu máquina local para desarrollo.

### 1. Backend (FastAPI)

Navega a la carpeta del backend y crea un entorno virtual:
```bash
cd backend
python -m venv venv

# Activar entorno:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

Instala las dependencias:
```bash
pip install -r requirements.txt
```

Configura las variables de entorno:
1.  Copia `.env.example` a `.env`.
2.  Edita `.env` y asegúrate de tener una base de datos PostgreSQL corriendo localmente.
3.  Actualiza `POSTGRES_SERVER` a `localhost` (y credenciales según tu DB local).

Inicia el servidor y migraciones:
```bash
# Migraciones
alembic upgrade head

# Semillas
python seed_roles.py

# Iniciar servidor
uvicorn app.main:app --reload
```
*El backend estará en: http://localhost:8000*

### 2. Frontend (Angular)

En una nueva terminal, navega a la carpeta del frontend:
```bash
cd frontend_mantis
```

Instala dependencias (Angular 17+):
```bash
npm install
```

Inicia el servidor de desarrollo:
```bash
npm start
```
*El frontend estará en: http://localhost:4200*

---

## 🏗️ Estructura del Proyecto

*   `/backend` - API REST con FastAPI, SQLAlchemy y Alembic.
*   `/frontend_mantis` - Aplicación SPA con Angular y plantilla Mantis.
*   `/docker-compose.yml` - Orquestación de contenedores.

## 🤝 Contribuir
¡Las contribuciones son bienvenidas! Por favor abre un Issue o Pull Request para mejoras.

---
<p align="center">Construido con ✨ por Alejooc</p>
