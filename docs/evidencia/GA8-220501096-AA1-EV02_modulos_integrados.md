# Evidencia de Producto GA8-220501096-AA1-EV02

## 1. Identificacion

- Proyecto: `Lumefy`
- Repositorio fuente: `https://github.com/Alejooc/lumefy.git`
- Arquitectura: frontend Angular + backend FastAPI + base de datos PostgreSQL
- Estado de integracion evidenciado: frontend y backend integrados por consumo REST sobre `/api/v1`

## 2. Objetivo de la evidencia

Documentar los modulos integrados del sistema, los componentes entregables, los datos de entrada y salida por modulo, las pruebas realizadas, los ambientes usados y los artefactos tecnicos asociados a la entrega.

## 3. Requerimientos y aprobaciones

El repositorio contiene implementacion funcional de los modulos y documentos tecnicos de apoyo, pero no contiene actas formales de aprobacion de requerimientos dentro del arbol versionado.

Para la entrega se recomienda anexar por fuera del repositorio:

- acta de aprobacion de requerimientos
- documento de alcance funcional aprobado
- evidencia de validacion por instructor o cliente

## 4. Modulos integrados identificados

La integracion se evidencia en dos capas:

- Frontend `frontend_mantis/src/app/modules`
- Backend `backend/app/api/v1/endpoints`

### 4.1 Modulos funcionales principales

| Modulo | Frontend | Backend | Proposito |
|---|---|---|---|
| Autenticacion | paginas de login y recuperacion | `login.py`, `users.py` | acceso, token, recuperacion de credenciales |
| Dashboard | `dashboard`, `admin/dashboard` | `dashboard.py` | metricas y estado general |
| Productos | `products` | `products.py`, `upload.py` | catalogo, variantes, importacion |
| Categorias | `categories` | `categories.py` | clasificacion de productos |
| Marcas | `brands` | `brands.py` | gestion de marcas |
| Inventario | `inventory` | `inventory.py`, `stock_take.py` | existencias, movimientos, conteos |
| Compras | `purchasing` | `purchases.py`, `suppliers.py`, `pricelists.py` | proveedores, ordenes, recepcion |
| Ventas | `sales`, `pos` | `sales.py`, `pos.py` | pedidos, estados, punto de venta |
| Devoluciones | `returns` | `returns.py` | registro y aprobacion de devoluciones |
| Clientes | `clients` | `clients.py` | gestion comercial y cartera |
| Usuarios y roles | `users`, `profile` | `users.py`, `roles.py`, `admin_users.py` | seguridad, permisos, perfil |
| Sucursales | `branches` | `branches.py` | organizacion operativa |
| Unidades de medida | `units-of-measure` | `units_of_measure.py` | normalizacion de catalogo |
| Logistica | `logistics` | `logistics.py` | empaque, picking, tablero logistico |
| Reportes | `reports` | `reports.py` | indicadores y consultas analiticas |
| Configuracion empresa | `company`, `settings` | `companies.py`, `system.py`, `admin.py`, `notifications.py`, `notification_admin.py` | parametrizacion, salud, mensajeria |
| Apps y ecommerce | `apps` | `apps.py`, `storefront.py` | extensiones, storefront y canal ecommerce |
| Auditoria | `audit` | `audit.py` | trazabilidad de acciones |
| Busqueda y sistema | interfaces transversales | `search.py`, `system.py` | soporte transversal del sistema |

## 5. Integracion entre modulos

La aplicacion integrada sigue este flujo:

1. El usuario interactua con un componente Angular del modulo funcional.
2. El componente usa servicios HTTP para consumir la API FastAPI.
3. La API valida autenticacion, permisos y reglas de negocio.
4. Los modelos SQLAlchemy persisten y consultan datos en PostgreSQL.
5. La respuesta JSON vuelve al frontend para actualizar la vista.

## 6. Datos de entrada y salida por modulo

La siguiente matriz resume entradas y salidas funcionales por modulo. Los endpoints detallados quedan documentados en `docs/postman/ENDPOINTS_Lumefy.md`.

| Modulo | Datos de entrada | Datos de salida |
|---|---|---|
| Autenticacion | correo, contrasena, email de recuperacion, nueva contrasena | token, datos de usuario, mensajes de recuperacion |
| Dashboard | filtros de fechas y contexto del usuario | indicadores, alertas, salud del sistema |
| Productos | nombre, SKU, precio, categoria, marca, stock, imagenes, variantes | producto creado/actualizado, listados, exportaciones |
| Categorias | nombre, descripcion, estado | categoria registrada o actualizada |
| Marcas | nombre, estado | marca registrada o actualizada |
| Inventario | producto, sucursal, cantidades, tipo de movimiento, observacion | kardex, existencias, movimiento confirmado |
| Compras | proveedor, items, cantidades, costos, estados, recepcion | orden de compra, estado, PDF, recepcion |
| Ventas | cliente, items, impuestos, descuentos, metodo de pago, estado | venta, estado, PDF, checkout, comprobante |
| Devoluciones | venta origen, productos devueltos, motivo, decision | devolucion registrada, aprobada o rechazada |
| Clientes | identificacion, nombre, telefono, email, direccion, cupo, actividades | cliente, estado de cuenta, pagos, actividades, estadisticas |
| Usuarios y roles | datos de usuario, rol, permisos, password | usuario creado/actualizado, roles, permisos activos |
| Sucursales | nombre, direccion, contacto | sucursal creada/actualizada |
| Unidades de medida | nombre, abreviatura | unidad creada/actualizada |
| Logistica | paquetes, tipos de paquete, movimientos en tablero, items de picking | paquete, tablero logistico, actualizacion de picking |
| Reportes | rangos de fecha, filtros por categoria, sucursal o estado | reportes consolidados, resumenes y exportaciones |
| Configuracion empresa | datos fiscales, ajustes, mensajes, mantenimiento, broadcast | configuraciones activas, confirmaciones de cambio |
| Apps y ecommerce | catalogo app, instalacion, dominio, navegacion, colecciones, pagos | app instalada/configurada, storefront publico, catalogo publico |
| Auditoria | filtros por usuario, modulo o fecha | logs de auditoria |

## 7. Componentes y acoplamiento tecnico

### 7.1 Frontend

- Enrutamiento y guardas para acceso por rol.
- Formularios reactivos para captura y validacion.
- Componentes de lista, formulario y detalle por modulo.
- Servicios HTTP para intercambio con la API.

### 7.2 Backend

- Routers FastAPI por modulo.
- Esquemas Pydantic para entrada y salida.
- Modelos SQLAlchemy para persistencia.
- Servicios auxiliares para PDF, exportacion y correo.
- Middleware de mantenimiento y rate limiting.

## 8. Pruebas realizadas y resultado

### 8.1 Pruebas backend ejecutadas en el entorno local

Pruebas automatizadas ejecutadas sobre `backend/venv`:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultado observado:

- 7 pruebas ejecutadas
- 7 pruebas aprobadas
- tiempo aproximado: `0.062s`

Cobertura validada por estas pruebas:

- validacion de creacion de clientes
- rechazo de NIT invalido
- rechazo de telefono invalido
- rechazo de cupo de credito negativo
- saneamiento de campos opcionales vacios
- validacion de actividades de clientes
- validacion de pagos en cartera

Prueba tecnica adicional ejecutada:

```powershell
.\venv\Scripts\python.exe test_security.py
```

Resultado observado:

- generacion exitosa de hash de contrasena

### 8.2 Pruebas funcionales API

Se genero una coleccion Postman desde el OpenAPI real del backend:

- `docs/postman/Lumefy.postman_collection.json`
- `docs/postman/Lumefy.local.postman_environment.json`
- `docs/postman/ENDPOINTS_Lumefy.md`

Cobertura documentada:

- `173` paths de API detectados
- autenticacion, consultas, inserciones, actualizaciones y eliminaciones

### 8.3 Pruebas frontend

Se identifica compilado listo en `frontend_mantis/dist`, lo cual evidencia integracion funcional del frontend con el backend.

En el repositorio tambien existen archivos `*.spec.ts` en modulos como:

- usuarios
- clientes
- categorias
- POS

No se ejecutaron pruebas Angular en esta sesion, por lo que deben reportarse como pendientes de corrida formal si se quieren anexar resultados numericos.

## 9. Archivos ejecutables y compilados

Se identifican como artefactos entregables:

- `frontend_mantis/dist`: compilado del frontend
- `backend/start.bat`: arranque local del backend
- `docker-compose.yml`: orquestacion de servicios
- `backend/Dockerfile`: construccion del contenedor backend

## 10. Control de versiones

El proyecto se encuentra bajo control de versiones Git.

- remoto configurado: `origin`
- URL: `https://github.com/Alejooc/lumefy.git`

## 11. Conclusiones

El sistema evidencia integracion real entre sus modulos de negocio, autenticacion, operacion, administracion y analitica. La integracion se soporta en una API FastAPI centralizada, consumida por el frontend Angular, con persistencia en PostgreSQL.

Para cerrar la entrega academica solo faltaria anexar, si la evidencia lo exige en formato formal:

- actas de aprobacion de requerimientos
- capturas de pruebas funcionales
- video de demostracion
- URL publica de despliegue si existe fuera del repositorio
