# Lumefy: evaluación de preparación para producción

Fecha: 5 de septiembre de 2026. Revisión del repositorio: `edcf3f8`.

## Dictamen

**Mi estimación global es 66 % de preparación para una operación comercial estable.** El proyecto tiene una base funcional importante y puede sostener una etapa de lanzamiento con acompañamiento, pero aún necesita cerrar procesos comerciales, proteger operaciones destructivas y demostrar los flujos críticos en un entorno integrado.

Estar desplegado confirma que el sistema arranca y es accesible; no demuestra por sí solo que pagos, devoluciones, suscripciones y recuperación ante fallos estén resueltos. Tampoco significa que debas rehacer el proyecto: la prioridad es completar y estabilizar lo que ya existe.

Este porcentaje es un juicio técnico orientativo, **no cobertura de código, probabilidad de éxito, certificación de seguridad ni porcentaje exacto de funcionalidades terminadas**. Confianza media para código; baja para el estado real del servidor. Una banda razonable de incertidumbre es de unos ±10 puntos, no un intervalo estadístico.

### Cómo se calculó

Se valoran cinco dimensiones con igual peso dentro de cada área: funcionalidad principal, cierre de flujos, controles de datos y acceso, validación automatizada y autonomía operativa. Escala: 0 = sin evidencia; 25 = inicial; 50 = parcial/manual; 75 = implementado con brechas; 100 = completo y demostrado. Se permiten valores intermedios por juicio técnico. Lo no validado limita la nota, pero no se presenta automáticamente como función inexistente.

| Área | Función principal | Cierre de flujos | Controles | Validación | Autonomía | Nota | Peso global |
|---|---:|---:|---:|---:|---:|---:|---:|
| Storefront | 90 | 70 | 80 | 55 | 65 | **72 %** | 30 % |
| Administración de empresa | 90 | 75 | 65 | 50 | 70 | **70 %** | 30 % |
| Dueño del SaaS | 70 | 40 | 60 | 35 | 45 | **50 %** | 25 % |
| Infraestructura y operación | 85 | 75 | 80 | 70 | 60 | **74 %** | 15 % |

Resultado: `72 × 0,30 + 70 × 0,30 + 50 × 0,25 + 74 × 0,15 = 66,2`, redondeado de manera orientativa a **~66 %**. Las notas priorizan un SaaS comercial operable, no la cantidad de pantallas. Si el modelo inicial es cobro manual y soporte directo, algunas automatizaciones pueden esperar.

## Alcance y resultados comprobados

Se revisaron rutas, componentes y servicios de Angular y Next, endpoints y modelos del backend, pruebas, Docker Compose, workflow de despliegue y documentación operativa. Se ejecutaron localmente:

| Validación | Resultado |
|---|---|
| Backend: `python -m unittest discover -s tests -p 'test_*.py'` | **171 tests aprobados** |
| Angular: `npm.cmd test -- --watch=false` | **12 tests aprobados en 12 archivos** |
| Angular: `npm.cmd run lint` | Aprobado |
| Angular: `npm.cmd run build` | Aprobado con advertencias de tamaños de estilos |
| Storefront: `npm.cmd run lint` | Aprobado |
| Storefront: `npm.cmd run build` | Aprobado, incluido TypeScript |

Las pruebas Angular advierten que el builder de aplicación actual no es el soportado por el builder de tests y que `polyfills.ts` se incluye sin comprobación de tipos. No impidieron aprobar, pero conviene corregir la configuración. El build Angular genera 1,41 MB iniciales sin comprimir, ~302 kB estimados de transferencia, con siete advertencias de presupuesto de estilos.

**No se inspeccionó el sitio desplegado ni el VPS**, no se realizó compra real, no se midieron rendimiento móvil ni concurrencia, no se ejecutaron migraciones/restauraciones ni auditorías actuales de dependencias. Tampoco se comprobó que el SHA desplegado coincida con esta revisión o que el último CI esté verde. Los builds usaron las dependencias locales existentes, no una instalación limpia. La revisión no es una auditoría exhaustiva de seguridad ni de cada módulo ERP.

## Lo que ya tienes y no hace falta reconstruir

- **Storefront:** catálogo, búsqueda y filtros, colecciones, producto con variantes, carrito, checkout, cuentas, recuperación de contraseña, contacto, newsletter, páginas, sitemap y robots. Hay configuración de envíos, pasarelas y dominios.
- **Editor de tienda:** home, producto, colección, búsqueda, carrito y páginas; existen documentos de tema, previsualización y publicación. No es únicamente una maqueta.
- **Pagos e inventario:** hay creación de pedidos con clave de idempotencia, bloqueos de inventario, reserva y liberación por cancelación, consulta de estado y callbacks de proveedores. No corresponde marcar “falta implementar stock” como si no existiera.
- **Administración de empresa:** catálogo, usuarios, clientes, sucursales, inventario, compras, ventas, POS, devoluciones, facturas, logística, reportes, CRM e integraciones tienen rutas e implementación. Su presencia no equivale a certificación funcional completa.
- **Dueño del SaaS:** empresas, onboarding, planes, estados y vencimientos, usuarios globales, acceso de soporte por impersonación, notificaciones, CMS, configuración y salud del sistema.
- **Operación:** CI con pruebas y builds, validación de migraciones, imágenes por revisión, workers, outbox, health checks, rotación de logs, scripts de backup y documentación de rollback.

Evidencia principal: `frontend_mantis/src/app/app-routing.module.ts`, `frontend_mantis/src/app/modules/apps/ecommerce.routes.ts`, `backend/app/api/v1/api.py`, `backend/app/api/v1/endpoints/storefront.py`, `.github/workflows/deploy.yml`, `docker-compose.prod.yml`.

## Prioridades inmediatas por estar ya en producción

P0 = atender de inmediato; P1 = siguiente ciclo de estabilización; P2 = mejora posterior. “Confirmado” significa observado en código; “validar” significa que no se ha demostrado el comportamiento completo; “propuesta” es una mejora de producto.

### P0-01 — Proteger el historial frente al borrado de catálogo [confirmado]

**Hallazgo:** el borrado físico masivo elimina relaciones que incluyen líneas de venta y factura. La interfaz incluso informa que conservará encabezados sin esas líneas. `/bulk-delete-all` invoca la purga con el permiso general `manage_inventory`. No ejecuté estas operaciones.

Evidencia: `backend/app/api/v1/endpoints/products.py`, funciones `_purge_products_physically`, `_purge_catalog_dependencies`, `bulk_delete_all_products` y `purge_all_products`; `frontend_mantis/src/app/modules/products/product-list/product-list.component.ts`, mensaje “BORRAR TODO”.

- [ ] Conservar documentos históricos al retirar productos: archivar o bloquear purga cuando exista historial.
- [ ] Sacar la limpieza destructiva del flujo cotidiano; si se conserva para datos de prueba, exigir permiso específico, controles del servidor y alcance explícito.
- [ ] Probar que retirar un producto no cambia el detalle ni los importes históricos de ventas, compras y facturas.

**Criterio de cierre:** un usuario de inventario no puede destruir detalle histórico mediante las rutas masivas; los documentos mantienen sus líneas y trazabilidad.

### P0-02 — Demostrar una venta completa [validar]

- [ ] Compra en móvil con la pasarela que realmente uses: aprobado, rechazado, pendiente y abandono.
- [ ] Repetir envío del checkout y webhook: un solo pedido y un único efecto en stock.
- [ ] Comprar la última unidad desde dos sesiones: nunca vender ambas.
- [ ] Confirmar importe, moneda, descuento, impuesto y envío entre checkout, pedido y proveedor.
- [ ] Cerrar navegador antes del retorno: el pago debe actualizarse por servidor.
- [ ] Completar preparación, despacho, entrega y cancelación; comprobar correo y estado de cuenta.

Evidencia de implementación: `backend/app/api/v1/endpoints/storefront.py`; pruebas en `backend/tests/test_storefront_validations.py`. Hay controles existentes, pero estas pruebas no sustituyen la compra integrada con proveedor y PostgreSQL reales.

**Criterio de cierre:** registrar IDs, importes, estados y stock antes/después en un entorno de pruebas equivalente. No usar pedidos de clientes para ensayos destructivos.

### P0-03 — Verificar recuperación y monitoreo reales [validar]

- [ ] Comprobar backup reciente de base **y archivos**, réplica fuera del servidor y acceso a la clave de cifrado guardada aparte.
- [ ] Restaurar en entorno aislado y verificar pedidos, usuarios, imágenes y credenciales descifrables.
- [ ] Probar que una alerta llega a un responsable ante caída, cola detenida, disco lleno o backup antiguo.
- [ ] Confirmar revisión desplegada y resultado del pipeline correspondiente.

Evidencia: `docs/production-operations.md`, `scripts/backup-production.sh`, `.github/workflows/deploy.yml`. **Los procedimientos existen; falta verificar su ejecución efectiva**, no escribirlos desde cero.

## Storefront: qué falta cerrar

| ID / prioridad | Estado y brecha | Trabajo y criterio de cierre |
|---|---|---|
| SF-01 / P1 | Validar: pedidos pendientes sin callback | Definir expiración por medio de pago y conciliación periódica. No se identificó un worker dedicado a caducar checkouts pendientes. Un abandono debe liberar reserva según política, sin cancelar una transferencia válida por error. |
| SF-02 / P1 | Parcial: devoluciones y reembolso online | Ya hay devoluciones ERP y reversión de saldo a crédito. No se encontró un flujo completo para solicitar devolución desde la cuenta y ejecutar/registrar reembolso de pasarela. Conectar solicitud, aprobación, movimiento físico, devolución monetaria y notificación; admitir reembolso manual trazable al inicio. |
| SF-03 / P1 | Validar: calidad de compra móvil | Probar navegación, variantes, teclado, errores de formularios, recarga de carrito, doble clic y recuperación de conexión en dispositivos reales. Sin compra móvil completa no dar por cerrado el checkout. |
| SF-04 / P1 | Validar: proveedores habilitados | Verificar cada proveedor que se ofrezca en la tienda con sus credenciales y callbacks. La existencia de campos de configuración no acredita homologación. Mantener visibles solo los medios comprobados. |
| SF-05 / P2 | Confirmado: reseñas incompletas | La ficha muestra contenido de estado vacío y un botón de reseña sin manejador de envío. Ocultar la sección hasta necesitarla, o implementar envío, moderación y publicación vinculada al producto. |
| SF-06 / P1 | Validar: contenido final | Revisar páginas publicadas, contacto, envíos, cambios, privacidad, enlaces, SEO e imágenes por tienda. Los mecanismos existen; no se comprobó la configuración de cada comercio. No constituye revisión legal. |
| SF-07 / P2 | Propuesta: recuperación comercial | Si el negocio lo necesita, añadir carrito abandonado, seguimiento de conversión y comunicaciones con preferencias del cliente. No es requisito para la primera venta. |

Evidencias: `backend/app/api/v1/endpoints/storefront.py` (`_cancel_storefront_sale_and_release_reservation`, callbacks y rutas `account`), `backend/app/workers/`, `backend/app/api/v1/endpoints/returns.py`, `storefront_nextmerce/src/components/ShopDetails/index.tsx` (bloque `reviews`).

## Panel administrador de empresa: qué falta cerrar

| ID / prioridad | Estado y brecha | Trabajo y criterio de cierre |
|---|---|---|
| AD-01 / P1 | Implementado: gestión visual de cupones | Panel CRUD conectado a `storefront_coupons.py`, con lista, creación, vigencia, compra mínima, desactivación y aplicación server-side en checkout. Falta validarlo con una tienda y PostgreSQL reales. |
| AD-02 / P1 | Propuesta sobre módulos existentes: operación ecommerce más directa | Reutilizar ventas y logística para una vista de pedidos online con filtros por tienda, pago y despacho, detalle de intentos y acciones permitidas. No hace falta construir otro motor de pedidos. Cierre: gestionar una compra completa desde el panel sin SQL. |
| AD-03 / P1 | Validar: integridad transversal ERP | Probar compra → recepción → stock → venta → despacho → devolución, incluyendo variantes y sucursales. Comparar cantidades y saldos; comprobar que repetir una acción no duplica efectos. |
| AD-04 / P1 | Validar: roles y dos empresas | Probar API y UI con administrador, vendedor y bodeguero; repetir sobre IDs ajenos. Ya hay `PermissionChecker` y pruebas de aislamiento, pero falta demostrar los flujos principales integrados. |
| AD-05 / P1 | Confirmado: facturación SaaS informativa | El tenant ve plan, vencimiento y estado, pero el historial de pagos es un mensaje fijo. Mostrar cobros/comprobantes reales cuando exista el registro SaaS y un camino claro para renovar. |
| AD-06 / P2 | Propuesta: consumo de plan visible | Mostrar uso frente al límite de usuarios, productos, sucursales, tiendas y apps antes de bloquear una operación. El backend ya tiene comprobaciones de límites. |
| AD-07 / P2 | Propuesta: puesta en marcha guiada | Checklist por tienda: datos, catálogo, stock, envíos, pago, dominio y compra de prueba. Cierre: un nuevo comercio puede publicar sin intervención del desarrollador. |
| AD-08 / P2 | Confirmado: deuda de validación frontend | Los 12 tests Angular son escasos para el alcance; el test POS inspeccionado solo comprueba creación de componente. Cubrir los flujos reales de venta, edición y permisos, y corregir advertencias de builder/estilos. |
| AD-09 / P1 | Implementado: promociones por alcance | Nuevo módulo para crear promociones porcentuales por colección o producto publicado, con vigencia, prioridad y activación. El precio se resuelve después de la lista de precios en catálogo y checkout; falta validar la migración y compra end-to-end contra PostgreSQL. |

Evidencias: `backend/app/api/v1/endpoints/storefront_coupons.py`, `backend/app/api/v1/endpoints/storefront_promotions.py`, `backend/app/services/storefront_promotions.py`, `frontend_mantis/src/app/modules/apps/ecommerce/ecommerce-promotions.component.ts`, `frontend_mantis/src/app/modules/apps/ecommerce.routes.ts`, `frontend_mantis/src/app/modules/billing/billing-list/billing-list.component.html`, `backend/app/core/plan_limits.py`, `backend/tests/test_tenant_isolation.py`, `frontend_mantis/src/app/modules/pos/pos.spec.ts`.

## Panel del dueño del SaaS: mayor brecha funcional

### SA-01 / P1 — Cobros y ciclo de suscripción [confirmado parcial]

Tienes administración de planes, estado y vencimiento. **No está cerrado el cobro SaaS:** el historial del tenant dice explícitamente que aparecerá cuando se integre el proveedor. Los pagos del storefront son cobros de los comercios a sus compradores; no sustituyen el cobro de Lumefy a sus empresas.

- [ ] Registro de cobros por empresa, periodo, importe, moneda, referencia y comprobante.
- [ ] Renovación trazable, historial de cambios de plan y fechas coherentes.
- [ ] Si se automatiza: checkout del plan, webhook idempotente, renovación, fallos, reintentos y cancelación.
- [ ] Avisos de vencimiento y política explícita para gracia, suspensión y reactivación.
- [ ] Pantalla de cartera: próximo a vencer, vencido, pagado y pendiente de validar.

**MVP aceptable:** cobro manual, comprobante verificable, renovación auditada y avisos. La recurrencia automática puede venir después. Cierre: una empresa paga y renueva con evidencia visible para ambas partes, sin editar la base.

### SA-02 / P1 — Corregir indicadores del negocio [confirmado]

`backend/app/api/v1/endpoints/admin.py:read_admin_stats` calcula MRR como empresas PRO × 49 y ENTERPRISE × 199. No toma el precio configurable de `Plan`, moneda, periodicidad o estado real de suscripción. FREE se calcula por diferencia del total, por lo que puede incluir otras situaciones o planes. El dashboard consume estos números.

- [ ] Retirar los precios de ejemplo y agrupar dinámicamente por planes existentes.
- [ ] Distinguir ingresos cobrados de ingreso recurrente contratado/estimado.
- [ ] Definir moneda y normalización de periodicidad; excluir estados según definición explícita.
- [ ] Añadir vencidos, activaciones y cancelaciones; churn y cohortes después de disponer de historial confiable.

**Cierre:** cambiar precio o crear un plan nuevo se refleja correctamente; un dato estimado se etiqueta como tal y no se presenta como caja cobrada.

### SA-03 / P1 — Trazabilidad de soporte y cambios globales [confirmado parcial]

La impersonación ya existe. En `admin_users.py` el token emitido identifica al usuario destino mediante `sub`, sin incorporar al operador original; no se observan escrituras explícitas de auditoría en las rutas revisadas de impersonación, empresas y planes. La marca de origen en el navegador no sustituye un registro del servidor.

- [ ] Guardar operador real, usuario/empresa destino, motivo, comienzo y fin de sesión de soporte.
- [ ] Mantener ambos actores en las acciones realizadas durante esa sesión.
- [ ] Registrar antes/después de plan, vencimiento, estado y configuración crítica.
- [ ] Mostrar historial filtrable desde el panel SaaS.

**Cierre:** se puede responder quién cambió un plan o modificó datos mediante soporte, cuándo y por qué. No basta con el usuario suplantado.

### SA-04 / P1 — Política de suspensión y límites [validar]

Existe `PlanLimitChecker`, aplicado a recursos concretos, y separación de acceso por empresa. Falta una matriz de aceptación que demuestre el comportamiento en todos los módulos: qué puede consultar o exportar un cliente vencido, qué se bloquea y qué ocurre con su tienda pública. No se afirma que hoy todos los módulos permitan saltar restricciones.

**Cierre:** pruebas con ACTIVE, PAST_DUE, SUSPENDED, CANCELED y vencimiento pasado en UI y API; la respuesta coincide con la política comercial y no deja pedidos en un estado imposible de atender.

### SA-05 / P1 — Protección de la cuenta dueña [no localizada / propuesta]

No se encontró implementación de MFA/TOTP en las búsquedas realizadas. Incorporar segundo factor para superadministradores, recuperación controlada y gestión/revocación de sesiones. Si ya existe protección externa en el proxy o proveedor de identidad, documentarla y verificarla antes de duplicar trabajo.

### SA-06 / P2 — Centro operativo [propuesta]

Ya hay salud del sistema, estadísticas y workers. Añadir una vista accionable de empresas con problemas: dominio pendiente, correo fallido, integración detenida, pagos atascados y respaldo atrasado. Enlazar errores y reintentos seguros. No es necesario construir observabilidad completa desde cero ni esperar a tener esta pantalla para configurar alertas externas.

## Pruebas que faltan para subir la confianza

La suite actual es una buena base. Varias pruebas inspeccionadas usan mocks; `test_storefront_checkout.py` prueba principalmente normalización de apariencia. No confundir su nombre con una compra completa. No se encontró script de tests del storefront ni suite de navegador en el workflow revisado.

- [ ] E2E de compra con PostgreSQL aislado y proveedor en pruebas: aprobado/rechazado/pendiente y callback repetido.
- [ ] Concurrencia por última unidad e idempotencia de creación de pedido.
- [ ] Dos tenants y roles limitados recorriendo ventas, inventario, archivos y editor.
- [ ] Alta de empresa → plan → usuarios → tienda → dominio → primera venta.
- [ ] Renovación → vencimiento → suspensión → reactivación según política.
- [ ] Devolución parcial/total y correspondencia entre stock, saldo y reembolso.
- [ ] Restauración y rollback ensayados fuera de producción.
- [ ] Carga y navegación móvil con catálogo representativo; fijar límites de respuesta y errores según tráfico esperado.

## Orden recomendado de ejecución

1. **Ahora:** proteger la purga de catálogo, comprobar respaldo recuperable y alertas, ejecutar la compra integrada y revisar pedidos pendientes existentes.
2. **Siguiente ciclo:** corregir MRR, trazabilidad de soporte, cobro SaaS manual completo y política de suspensión. Cerrar estados de pago/cancelación y reembolsos operativos.
3. **Después:** cupones en panel, vista operativa de pedidos, onboarding, consumo de plan y pruebas E2E repetibles.
4. **Al estabilizar:** automatizar recurrencia, recuperación comercial, reseñas y métricas avanzadas si aportan valor al negocio.

No asigno fechas cerradas: dependen del volumen de producción, proveedor de pago y complejidad de datos. Cerrar P0 reduce riesgo; sumar pantallas P2 no compensa dejar P0 abiertos. Recalcular el porcentaje usando la misma matriz después de adjuntar evidencias de cierre.

## Documentación que conviene actualizar

`docs/storefront_mvp_checklist.md` aún presenta stock y conciliación como pendientes amplios y describe Addi en una etapa anterior. El código actual ya contiene reserva/liberación y callbacks adicionales. Actualizarlo distinguiendo implementación y validación real para evitar repetir trabajo.

`README.md` documenta credenciales iniciales de desarrollo. No se comprobó que se utilicen en producción; verificar que el despliegue siga las instrucciones y secretos de `docs/production-operations.md`.

## Conclusión práctica

El storefront y el administrador están bastante más avanzados que el negocio SaaS automatizado. La mayor necesidad no es seguir agregando módulos: es asegurar la venta completa, conservar el historial, cobrar y renovar empresas con trazabilidad, y poder recuperar el servicio. Este informe deja pendientes explícitos sin dar por probada la operación que no se inspeccionó.

