# Recuperacion Del Panel Admin

## Ejecucion Por Bloques

Cada bloque se cierra solo despues de revisar contratos frontend/backend, corregir los fallos encontrados, probar el flujo y ejecutar las verificaciones tecnicas aplicables.

### Bloque 1: Acceso Y Base Visual

- [x] Instalar dependencias, compilar y ejecutar lint del panel.
- [x] Configurar API local, CORS y arranque reproducible de backend/base de datos.
- [x] Normalizar dashboard, POS y ecommerce al lenguaje visual Mantis.
- [x] Validar login, registro, recuperación y restablecimiento por API; validar login Angular hacia dashboard.
- [x] Corregir limpieza de sesión, retorno de ruta y carga del contexto de empresa.
- [x] Unificar iconografía del panel en Feather/Mantis y eliminar dependencias visuales no cargadas.
- [x] Normalizar banner global, detalle de apps y tablero logístico para usar tokens Mantis en lugar de gradientes, sombras y paletas paralelas.

### Bloque 2: Catalogo E Inventario

- [x] Validar categorías, marcas, unidades y productos: crear, editar, buscar y eliminar.
- [x] Validar movimientos IN/OUT, toma física, historial y saldo de inventario.
- [x] Corregir aislamiento multiempresa en movimientos y tomas físicas.

### Bloque 3: Operacion Comercial

- [x] Validar compra, recepción y actualización de inventario.
- [x] Corregir validación de relaciones en compras y ventas.
- [x] Validar ciclo de venta, transiciones de estado y ajuste de inventario.
- [x] Corregir prevención de sobredevoluciones acumuladas.
- [x] Instalar y validar POS: apertura, cobro, stock y cierre de caja.

### Bloque 4: Administracion, SaaS Y Calidad

- [ ] Validar usuarios, roles, permisos y protección de rutas administrativas.
- [ ] Validar empresas, sucursales, planes, límites y facturación.
- [ ] Validar apps instalables, configuración, auditoría, notificaciones y salud del sistema.
- [ ] Validar reportes y exportaciones con datos de prueba.
- [ ] Revisar errores HTTP, aislamiento multiempresa y pruebas automatizadas de backend.
- [ ] Actualizar la documentación de operación local.

### Bloque 5: Storefront Y Despliegue

- [ ] Compilar, revisar y corregir el storefront NextMerce contra la API validada.
- [ ] Validar navegación pública, catálogo, carrito, checkout y autenticación de cliente.
- [ ] Separar servicios en composición de producción: backend, admin, storefront, nginx y persistencia.
- [ ] Configurar GitHub Actions por rutas y despliegue seguro al VPS.
- [ ] Documentar variables, migraciones, rollback y procedimiento de despliegue.

## Regla De Trabajo

- Mantener Mantis como fuente de verdad visual del panel.
- No agregar gradientes, paletas paralelas, sombras decorativas ni componentes visuales nuevos sin una necesidad de producto validada.
- No mezclar una correccion visual con cambios de API, base de datos o reglas de negocio.
- Cada tarea debe compilar y, cuando aplique, incluir una prueba manual del flujo afectado.

## Fase 0: Base De Trabajo

- [x] Instalar dependencias exactas del panel con `npm ci`.
- [x] Confirmar que `npm run build` compila el panel.
- [x] Ejecutar `npm run lint` y registrar los errores reales.
- [ ] Definir un usuario, empresa y sucursal de prueba reproducibles para validacion manual.
- [x] Documentar las variables de entorno necesarias para ejecutar Angular contra la API local.

**Criterio de aceptacion:** cualquier desarrollador puede levantar el panel y reproducir la validacion basica sin configuracion implícita.

Configuracion actual: desarrollo usa `http://localhost:8000/api/v1`; produccion usa `/api/v1` y requiere que nginx enrute ese prefijo al backend.

Nota: `BACKEND_CORS_ORIGINS` debe declararse como un arreglo JSON en `backend/.env`, no como una lista separada por comas.

Bootstrap local validado: iniciar PostgreSQL y backend, ejecutar `alembic upgrade head`, ejecutar `seed_saas.py` y crear la primera empresa mediante `POST /register`. `seed_roles.py` requiere que ya exista una empresa, por lo que no sirve como primer paso sobre una base vacia.

## Fase 1: Recuperacion Visual Mantis

- [x] Normalizar el dashboard para usar tokens Bootstrap/Mantis.
- [x] Normalizar POS para usar superficies, bordes y estados del tema.
- [x] Normalizar ecommerce: resumen, navegacion, pagos y configuracion.
- [x] Revisar los modulos restantes que usen colores hardcodeados, gradientes o `!important` para eliminar solo los estilos que rompan el lenguaje Mantis.
- [ ] Revisar el shell admin: sidebar, navbar, breadcrumb, tablas, formularios y responsive en escritorio y movil.
- [ ] Decidir por separado el destino de la landing publica Angular; no forma parte del panel admin ni tiene una referencia Mantis versionada.

**Criterio de aceptacion:** las rutas administrativas usan los componentes y tokens de Mantis de forma consistente; no existe una segunda identidad visual dentro del admin.

## Fase 2: Acceso Y Contexto De Empresa

- [ ] Probar login, cierre de sesion y persistencia de sesion despues de recargar.
- [x] Confirmar login Angular contra la API local y redireccion al dashboard.
- [ ] Probar registro, recuperacion y restablecimiento de contraseña.
- [x] Verificar por API registro, restablecimiento con token y login con la nueva contraseña.
- [ ] Validar guards de autenticacion, invitado y superusuario.
- [ ] Validar que empresa, plan y sucursal activos se cargan antes de consultar modulos dependientes.
- [ ] Corregir respuestas de error para que el usuario reciba mensajes accionables y no errores tecnicos crudos.

**Criterio de aceptacion:** un usuario autorizado entra al panel, conserva el contexto correcto y no puede abrir rutas fuera de sus permisos.

## Fase 3: Catalogo E Inventario

- [ ] Probar listado, busqueda, creacion, edicion y eliminacion de categorias.
- [x] Verificar por API el ciclo de categoria, marca y unidad de medida.
- [ ] Probar listado, creacion, edicion, imagenes, variantes e importacion de productos.
- [x] Verificar por API crear, editar, buscar y eliminar un producto relacionado con categoria, marca y unidad.
- [ ] Probar unidades de medida, marcas y listas de precios.
- [ ] Probar movimientos, historial, ajustes y toma fisica de inventario.
- [x] Verificar por API entrada, salida y ajuste por toma fisica; el saldo final coincide con el conteo aplicado.
- [x] Verificar que inventario y tomas fisicas rechazan productos o sucursales de otra empresa.
- [ ] Verificar que existencias y precios coinciden entre API, formularios y listas.

**Criterio de aceptacion:** un producto completo puede crearse, tener stock y aparecer correctamente en todos los modulos que lo consumen.

## Fase 4: Operacion Comercial

- [ ] Probar clientes y proveedores: listado, formulario y detalle.
- [ ] Probar compras y recepciones; confirmar que actualizan inventario.
- [x] Verificar por API una compra, su recepción y la actualización de existencias.
- [ ] Probar POS: apertura, busqueda, carrito, descuento, pago, recibo y cierre.
- [x] Instalar `pos_module` y verificar por API apertura, cobro, descuento de existencias y cierre de caja.
- [ ] Probar ventas, devoluciones y sus ajustes de inventario/contabilidad.
- [x] Verificar por API venta, transiciones de estado, devolución aprobada y prevención de sobredevolución.
- [ ] Probar reportes y exportaciones con datos de prueba.

**Criterio de aceptacion:** una compra seguida de una venta y una devolucion deja inventario, totales y auditoria en estados coherentes.

## Fase 5: Administracion Y SaaS

- [ ] Probar usuarios, roles y permisos desde el panel superusuario.
- [ ] Probar empresas, planes, facturacion y limites por plan.
- [ ] Probar notificaciones, auditoria, salud del sistema y estadisticas de base de datos.
- [ ] Revisar que modulos incompletos se oculten del menu o muestren estado no disponible.

**Criterio de aceptacion:** las funciones administrativas no exponen acciones que fallen o datos de otra empresa.

## Fase 6: Contrato Backend Y Calidad

- [ ] Para cada error funcional encontrado, registrar ruta frontend, endpoint, payload esperado, respuesta real y causa.
- [ ] Agregar pruebas de API para los flujos corregidos antes de cambiar otros modulos.
- [ ] Eliminar scripts, logs y artefactos generados que no sean parte de la aplicacion.
- [ ] Actualizar README con los tres servicios actuales: backend, panel admin y storefront.

**Criterio de aceptacion:** los flujos corregidos tienen una verificacion repetible y el repositorio no mezcla artefactos temporales con codigo productivo.

## Fase 7: Storefront Y Deploy

- [ ] Recuperar el storefront por separado, respetando NextMerce como referencia visual.
- [ ] Conectar storefront solo a endpoints ya validados del backend.
- [ ] Crear compose de produccion para backend, admin, storefront, nginx y persistencia.
- [ ] Configurar GitHub Actions con despliegue por cambios de carpeta.

**Criterio de aceptacion:** cada servicio se construye y despliega de manera reproducible sin afectar los demas.
