# Plan de App Store e integraciones instalables de Lumefy

## Estado de la decisión

Lumefy evolucionará el módulo visible de **Orígenes externos** hacia un sistema de aplicaciones instalables similar al App Store de Shopify.

La primera aplicación real de este sistema será **ElegantHome**. La funcionalidad actual de sincronización de productos, variantes, imágenes, precios e inventario se moverá a la experiencia de esta app. Posteriormente se agregará la integración de órdenes.

La infraestructura actual de `IntegrationSource` no se eliminará. Se conservará inicialmente como el motor interno de conexiones y sincronizaciones, pero dejará de presentarse al usuario como un módulo independiente.

### Progreso actual

- [x] ElegantHome registrado como app de primera parte en el catálogo.
- [x] `IntegrationSource` enlazable con la instalación de una app mediante `app_install_id`.
- [x] Las conexiones nuevas de ElegantHome requieren que la app esté instalada y activa.
- [x] Las conexiones heredadas de `custom_rest` se adoptan automáticamente al instalar ElegantHome.
- [x] La navegación de usuario dejó de mostrar Orígenes externos como módulo independiente.
- [x] La ruta anterior `/integrations` redirige a la configuración de conexiones de ElegantHome.
- [x] La sincronización actual de productos e inventario quedó accesible desde la app ElegantHome.
- [x] Implementar la primera importación de órdenes con detalle, homologación por SKU e idempotencia.
- [x] Preparar la exportación de ventas mediante `POST /api/external/orders`.
- [ ] Publicar la API para aplicaciones remotas de terceros.

Decisiones principales:

- **App**: define el conector, sus capacidades, versión y permisos solicitados.
- **Instalación**: representa que una empresa activó la app y aprobó determinados permisos.
- **Conexión**: guarda la cuenta, credenciales y configuración específica de esa empresa.
- **Entidad de negocio**: los productos, clientes, inventario y ventas continúan perteneciendo al núcleo de Lumefy.
- ElegantHome será una app reutilizable por cualquier empresa del SaaS; no habrá código ni configuración global cerrada para una sola empresa.

## Objetivos

1. Permitir que cada empresa descubra e instale aplicaciones desde la Tienda de Apps.
2. Reutilizar la misma app en múltiples empresas manteniendo aislamiento total de datos y credenciales.
3. Permitir una o varias conexiones por instalación cuando el proveedor lo requiera.
4. Controlar el acceso mediante permisos explícitos y verificables en el backend.
5. Encapsular la lógica particular de cada proveedor sin introducir condiciones específicas dentro del núcleo de ventas, productos o inventario.
6. Soportar inicialmente apps desarrolladas por Lumefy y, posteriormente, apps remotas desarrolladas por terceros.
7. Incorporar ElegantHome sin perder las configuraciones, vínculos ni historiales creados mediante Orígenes externos.

## Conceptos del sistema

| Concepto | Responsabilidad | Alcance |
| --- | --- | --- |
| `AppDefinition` | Nombre, publicador, versión, permisos, capacidades y configuración pública de una app | Global para toda la plataforma |
| `CompanyAppInstall` | Instalación, permisos aprobados, estado y configuración de la app | Una empresa |
| `IntegrationSource` / `AppConnection` | URL, autenticación, credenciales, mapeos y programación de una cuenta externa | Una empresa y una instalación |
| Conector | Código que traduce entre la API del proveedor y el modelo normalizado de Lumefy | Una app y versión |
| Servicios de dominio | Aplican las reglas reales de productos, inventario, clientes y ventas | Núcleo de Lumefy |
| Outbox y workers | Ejecutan sincronizaciones, webhooks, reintentos y trabajos duraderos | Infraestructura compartida |

## Arquitectura objetivo

```text
Tienda de Apps
    |
    +-- AppDefinition: ElegantHome
            |
            +-- CompanyAppInstall: Empresa A
            |       |
            |       +-- Conexión principal
            |       +-- Conexión secundaria (opcional)
            |
            +-- CompanyAppInstall: Empresa B
                    |
                    +-- Conexión principal

Conector ElegantHome
    |
    +-- Productos --------> Product / ProductVariant
    +-- Inventario -------> Inventory / InventoryMovement
    +-- Órdenes ----------> Sale / SaleItem
    +-- Clientes ---------> Client
    +-- Eventos ----------> Outbox / Webhooks / Workers
```

La app define **qué sabe hacer**. La instalación define **qué autorizó una empresa**. La conexión define **con qué cuenta y credenciales se ejecuta**.

## Tipos de aplicaciones

### Apps internas o de primera parte

Su código vive dentro de Lumefy y es mantenido por el equipo de la plataforma. ElegantHome comenzará como una app de primera parte.

Estas apps podrán utilizar directamente los servicios internos de dominio, pasando siempre por el contexto de empresa, instalación y permisos. No deberán insertar registros directamente en la base de datos ni duplicar las reglas de negocio.

### Apps remotas o de terceros

Su código vivirá en servidores del desarrollador. Accederán a Lumefy mediante una API pública, OAuth o tokens de instalación y webhooks firmados.

Las apps remotas se implementarán después de estabilizar la arquitectura con ElegantHome. En la primera versión no se permitirá cargar ni ejecutar código arbitrario de terceros dentro del backend principal.

## Permisos de las apps

Los permisos usarán la forma `recurso:acción`. Propuesta inicial:

```text
products:read
products:write
inventory:read
inventory:write
orders:read
orders:write
orders:cancel
customers:read
customers:write
payments:read
payments:write
webhooks:manage
```

No se ofrecerá `orders:delete` como permiso normal. Las órdenes confirmadas forman parte del historial comercial y deberán cancelarse, no borrarse.

Reglas de permisos:

- La app declara los permisos que solicita.
- La empresa ve y aprueba los permisos durante la instalación.
- `CompanyAppInstall.granted_scopes` guarda únicamente los permisos concedidos.
- Cada endpoint y operación interna valida el permiso requerido en el backend.
- La interfaz puede ocultar acciones no autorizadas, pero nunca será la única barrera de seguridad.
- Desinstalar o desactivar una app revoca sus tokens y detiene sus trabajos, pero no elimina automáticamente los productos, clientes u órdenes ya creados.

## Modelo de datos propuesto

### `app_definitions`

Se conservará el modelo actual y se preparará para incluir, cuando sea necesario:

- `publisher_name`
- `app_type`: `FIRST_PARTY` o `REMOTE`
- `visibility`: `PUBLIC`, `PRIVATE` o `UNLISTED`
- versión y estado de publicación
- permisos solicitados
- capacidades
- esquema de configuración
- URL de instalación, documentación y soporte
- información OAuth para apps remotas

En la primera fase se evitarán cambios que no sean necesarios para ElegantHome.

### `company_app_installs`

Se reutilizará el modelo actual para representar una instalación por empresa y app. Mantendrá:

- `company_id`
- `app_id`
- `is_enabled`
- `installed_version`
- `granted_scopes`
- secretos, tokens y datos OAuth cuando correspondan
- configuración general de la instalación
- estado de facturación
- usuario y fecha de instalación

### `integration_sources`

Se reutilizará inicialmente como tabla de conexiones. Se agregará:

- `app_install_id`: instalación propietaria de la conexión
- nombre de conexión visible para el usuario
- dirección de sincronización si se necesita: entrada, salida o ambas
- marcas de última sincronización por capacidad

`provider_key` continuará resolviendo el conector, por ejemplo `eleganthome`.

El nombre de tabla no se cambiará durante la primera fase para reducir el riesgo de migración. En código e interfaz se tratará como `AppConnection`. Un cambio físico de nombre podrá hacerse posteriormente si aporta valor.

### Vínculos de entidades externas

Los vínculos actuales de productos y variantes se conservarán. Para las órdenes se creará una relación explícita, inicialmente llamada `integration_order_links`, con:

- `company_id`
- `source_id`
- `sale_id`
- `external_order_id`
- `external_order_number`
- estado externo
- fecha externa de actualización
- última sincronización
- último error
- hash o metadatos seguros del payload

La restricción de idempotencia será:

```text
source_id + external_order_id = una sola orden interna
```

No se guardarán credenciales en payloads ni se expondrán datos personales completos en historiales de error.

### Origen de una venta

`Sale` deberá poder identificar su canal de origen:

```text
MANUAL
POS
STOREFRONT
EXTERNAL_APP
```

También podrá guardar la conexión que originó la orden. Los identificadores externos completos permanecerán en la tabla de vínculos para permitir que una venta se relacione posteriormente con más de un sistema.

`StorefrontOrder` continuará utilizándose exclusivamente para pedidos creados desde el ecommerce nativo de Lumefy.

## Contrato común de conectores

Cada conector implementará únicamente las capacidades que declare. Contrato conceptual:

```python
class AppConnector:
    async def test_connection(...): ...
    async def pull_products(...): ...
    async def pull_inventory(...): ...
    async def pull_orders(...): ...
    async def create_external_order(...): ...
    async def update_external_order(...): ...
    async def cancel_external_order(...): ...
    async def verify_webhook(...): ...
```

El núcleo invocará el conector mediante `provider_key` y capacidades, sin condiciones del tipo `if provider == "eleganthome"` dentro de los servicios generales.

Los conectores traducirán el payload particular del proveedor hacia modelos normalizados de Lumefy. Las validaciones, reservas de inventario y transiciones comerciales seguirán en los servicios del dominio.

## Aplicación ElegantHome

### Definición inicial

```json
{
  "slug": "eleganthome",
  "name": "ElegantHome",
  "publisher": "Lumefy",
  "version": "1.0.0",
  "app_type": "FIRST_PARTY",
  "requested_scopes": [
    "products:read",
    "products:write",
    "inventory:read",
    "inventory:write",
    "orders:read",
    "orders:write"
  ],
  "capabilities": [
    "catalog_sync",
    "inventory_sync",
    "order_import",
    "order_export",
    "webhooks"
  ],
  "setup_url": "/apps/installed/eleganthome"
}
```

La lista final de permisos se reducirá a los estrictamente necesarios para cada versión publicada.

### Pantalla de la app instalada

La ruta de ElegantHome reemplazará la experiencia independiente de Orígenes externos y tendrá:

```text
ElegantHome
    +-- Resumen
    +-- Conexiones
    +-- Productos
    +-- Inventario
    +-- Órdenes
    +-- Mapeos
    +-- Historial y errores
    +-- Configuración
```

Configuración esperada por conexión:

- nombre de conexión
- URL de API
- método de autenticación
- credenciales cifradas
- sincronización de productos activada o desactivada
- sincronización de inventario activada o desactivada
- importación de órdenes activada o desactivada
- exportación de órdenes activada o desactivada
- sucursal y bodega de cumplimiento
- programación de sincronizaciones
- mapeo de campos y estados
- configuración de webhook

## Flujo de productos e inventario

La lógica existente será reutilizada dentro de la app ElegantHome:

```text
Usuario instala ElegantHome
    -> crea una conexión
    -> prueba credenciales
    -> revisa y confirma el mapeo
    -> sincroniza catálogo
    -> sincroniza inventario
    -> consulta historial y errores desde la app
```

Los productos e inventarios seguirán siendo entidades normales de Lumefy. No existirán tablas de productos independientes para cada app.

## Flujo de órdenes entrantes

```text
ElegantHome envía un webhook o Lumefy ejecuta polling
    -> se verifica autenticidad e idempotencia
    -> se encola el evento
    -> el conector normaliza la orden
    -> se resuelve cliente, producto, variante y bodega
    -> el servicio de ventas valida y crea la Sale
    -> se reserva inventario según la política definida
    -> se guarda integration_order_link
    -> se emiten eventos y se registra el resultado
```

Modelo normalizado mínimo:

```text
ExternalOrder
    external_id
    external_number
    status
    payment_status
    currency
    customer
    shipping_address
    items[]
        external_product_id
        external_variant_id
        sku
        quantity
        unit_price
        discount
```

Si una línea no puede homologarse con un producto o variante, la orden quedará en una bandeja de integración pendiente y no reservará inventario hasta ser corregida. La política inicial propuesta es `PENDING_MAPPING` en lugar de descartar la orden o crear silenciosamente productos incorrectos.

## Flujo de órdenes salientes

```text
Sale alcanza el estado configurado
    -> se escribe un evento en el outbox
    -> el worker selecciona la instalación y conexión destino
    -> el conector crea o actualiza la orden externa
    -> se guarda el identificador externo
    -> se registra éxito o reintento
```

La clave de idempotencia considerará como mínimo:

```text
source_id + sale_id + operación
```

Los errores transitorios usarán reintentos con espera progresiva. Los errores de validación quedarán visibles para intervención del usuario y no se reintentarán indefinidamente.

## API de plataforma para apps remotas

Cuando se habiliten apps de terceros, Lumefy ofrecerá una API estable y común. Las apps no tendrán endpoints privados creados directamente sobre tablas internas.

Recursos previstos:

```text
GET  /platform/v1/products
GET  /platform/v1/inventory
GET  /platform/v1/orders
POST /platform/v1/orders
POST /platform/v1/orders/{id}/cancel
GET  /platform/v1/customers
POST /platform/v1/webhook-subscriptions
```

El token de instalación determinará el `company_id`; una app no podrá seleccionar libremente el tenant enviando un identificador de empresa.

La API incluirá versionado, límites de consumo, paginación, claves de idempotencia, auditoría y documentación para desarrolladores.

## Seguridad y aislamiento SaaS

Reglas obligatorias:

- Toda instalación y conexión pertenece a una empresa.
- La empresa se obtiene del usuario autenticado o del token de instalación, nunca de un valor confiado del payload.
- `app_install_id`, `source_id` y las entidades afectadas deben pertenecer a la misma empresa.
- Las credenciales se almacenan cifradas y nunca regresan completas al frontend.
- Los scopes se validan en backend para cada lectura o escritura.
- Los webhooks se firman, verifican, deduplican y procesan de forma asíncrona.
- Cada operación relevante deja un registro de auditoría.
- Se aplican límites por instalación para evitar abuso o saturación.
- Las apps no tienen acceso directo a la base de datos.
- Desinstalar una app revoca acceso y detiene sincronizaciones sin borrar el historial comercial.

## Experiencia de usuario objetivo

### Tienda de Apps

La ficha de ElegantHome mostrará:

- descripción y publicador
- versión
- capacidades
- permisos solicitados
- precio o inclusión en el plan
- botón de instalación
- documentación y soporte

### Instalación

```text
Instalar ElegantHome
    -> mostrar permisos solicitados
    -> aprobar instalación
    -> crear configuración inicial
    -> conectar cuenta
    -> probar conexión
    -> activar sincronizaciones
```

### Aplicaciones instaladas

Cada empresa verá únicamente sus instalaciones. Desde ElegantHome podrá administrar sus conexiones, sincronizaciones, mapeos, órdenes y errores.

El menú **Orígenes externos** se retirará de la navegación principal cuando la migración esté verificada. Durante una transición corta podrá redirigir a la app ElegantHome instalada.

## Migración desde Orígenes externos

La migración no eliminará datos.

1. Crear o actualizar `AppDefinition` para ElegantHome.
2. Detectar empresas con un `IntegrationSource` correspondiente a ElegantHome.
3. Crear una `CompanyAppInstall` de ElegantHome para cada empresa detectada.
4. Agregar y completar `app_install_id` en las conexiones existentes.
5. Conservar credenciales, configuración, mapeos, vínculos, horarios e historial de ejecuciones.
6. Mover la interfaz de conexión y sincronización a `/apps/installed/eleganthome`.
7. Mantener temporalmente los endpoints actuales como compatibilidad interna.
8. Redirigir o retirar la ruta visible de Orígenes externos después de validar la migración.
9. Hacer obligatorio `app_install_id` cuando ya no existan registros antiguos sin migrar.

## Fases de implementación

### Fase 1 — Unificar App Store y conexiones

- [x] Registrar ElegantHome como app de primera parte.
- [x] Definir scopes y capacidades iniciales.
- [x] Agregar `app_install_id` a `IntegrationSource` mediante migración segura.
- [ ] Crear el concepto de `AppConnection` en servicios y esquemas sin renombrar todavía la tabla.
- [x] Exigir que la app esté instalada y activa antes de crear o administrar una conexión de ElegantHome.
- [ ] Validar scopes en las operaciones de conexión y sincronización.
- [x] Crear la pantalla de app instalada para ElegantHome.
- [x] Incorporar la administración de conexiones dentro de esa pantalla.
- [x] Preparar la adopción de conexiones existentes.

### Fase 2 — Mover catálogo e inventario a ElegantHome

- [x] Reutilizar el motor actual de catálogo, variantes, imágenes, precios e inventario.
- [x] Resolver el conector mediante `provider_key=eleganthome`.
- [ ] Mover pruebas de conexión, previa, mapeo, sincronización y programación a la app.
- [ ] Mostrar historial, progreso y errores dentro de ElegantHome.
- [x] Mantener compatibilidad temporal con las rutas existentes.
- [ ] Validar que dos empresas puedan instalar ElegantHome sin compartir datos.
- [x] Retirar el menú visible de Orígenes externos.

### Fase 3 — Importar órdenes de ElegantHome

- [x] Definir el DTO normalizado de orden externa.
- [x] Crear `integration_order_links` y sus restricciones de idempotencia.
- [x] Agregar el origen de canal a `Sale`.
- [x] Extraer o consolidar un servicio de dominio para crear ventas desde cualquier canal.
- [x] Implementar homologación de cliente, producto, variante, precios y bodega.
- [x] Implementar la bandeja `PENDING_MAPPING`.
- [ ] Incorporar polling y/o webhook de órdenes según la API real de ElegantHome.
- [ ] Crear auditoría, métricas, reintentos y manejo de errores.
- [x] Proteger la repetición de la misma orden para que no duplique ventas ni reservas.

### Fase 4 — Exportar órdenes y sincronizar estados

- [ ] Publicar eventos comerciales mediante el outbox.
- [ ] Implementar creación idempotente de órdenes externas.
- [ ] Mapear estados de Lumefy y ElegantHome.
- [ ] Sincronizar cancelación, despacho, entrega y pagos según las capacidades disponibles.
- [ ] Implementar reintentos, intervención manual y trazabilidad.

### Fase 5 — Plataforma para desarrolladores externos

- [ ] Crear API pública versionada para apps.
- [ ] Implementar OAuth o tokens de instalación para apps remotas.
- [ ] Crear suscripciones y entregas de webhooks.
- [ ] Incorporar límites por instalación y métricas de consumo.
- [ ] Crear portal de desarrolladores, documentación y entorno de pruebas.
- [ ] Implementar versiones, revisión y publicación de apps.
- [ ] Definir políticas de privacidad, seguridad, soporte y facturación.

## Criterios de aceptación

- [ ] ElegantHome aparece en la Tienda de Apps y puede instalarse por empresa.
- [ ] Una empresa sin la app instalada no puede acceder a sus operaciones.
- [ ] Los permisos solicitados se muestran antes de instalar y se validan en backend.
- [ ] Dos empresas pueden instalar la misma app con credenciales y datos completamente aislados.
- [ ] Una instalación puede soportar múltiples conexiones sin duplicar la definición de la app.
- [ ] Las conexiones existentes se migran sin perder credenciales, mapeos ni historiales.
- [ ] Productos e inventario se sincronizan desde la pantalla de ElegantHome.
- [x] Una orden externa crea como máximo una `Sale` por conexión e identificador externo.
- [x] Los productos sin homologación dejan la orden pendiente y no alteran inventario.
- [ ] Las reservas y movimientos se ejecutan mediante los servicios normales de Lumefy.
- [ ] La desinstalación detiene el acceso y los trabajos sin borrar datos comerciales.
- [ ] Ninguna app puede consultar o modificar información de otra empresa.
- [ ] El usuario ya no necesita administrar ElegantHome desde un módulo separado de Orígenes externos.

## Decisiones pendientes antes de la fase de órdenes

- Método real de autenticación de la API de ElegantHome.
- Disponibilidad y formato de webhooks de órdenes.
- Si la primera versión importará órdenes, exportará órdenes o hará ambas cosas.
- Estado de Lumefy en el que una orden debe enviarse a ElegantHome.
- Política de precios: respetar el valor externo, recalcular con lista de precios o validar diferencias.
- Política de creación y homologación de clientes.
- Mapeo de estados de pago, preparación, despacho, entrega y cancelación.
- Tratamiento de devoluciones, reembolsos y órdenes parciales.
- Límite de conexiones y volumen de sincronización por plan.

## Fuera del alcance inicial

- Ejecutar código arbitrario subido por terceros dentro del backend de Lumefy.
- Marketplace público sin proceso de revisión.
- Facturación automática de desarrolladores externos.
- Microservicio independiente para cada conector.
- Eliminación irreversible de órdenes por parte de una app.
- Cambio inmediato del nombre físico de `integration_sources`.

## Resultado esperado

Al completar las primeras cuatro fases, ElegantHome será una app instalable y multiempresa que encapsula catálogo, inventario y órdenes. La infraestructura quedará preparada para agregar Shopify, WooCommerce, marketplaces, proveedores y ERPs mediante nuevos conectores, sin modificar el núcleo de Lumefy ni crear soluciones cerradas por empresa.
