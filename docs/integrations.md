# Orígenes de datos e integraciones

Lumefy permite que cada empresa configure sus propios orígenes de datos REST desde el panel en **Orígenes de datos**.

## Alcance actual

La primera versión soporta:

- Autenticación Bearer, API key o sin autenticación.
- Prueba de conexión.
- Importación manual de catálogo (productos, variantes, imágenes y precios), separada del inventario.
- Importación de inventario manual o automática por intervalo.
- Mapeo de campos mediante rutas JSON (`data.items.0.sku`).
- Detección automática de campos con confianza y confirmación manual del perfil.
- Catálogos simples y catálogos con variantes, imágenes, atributos e inventario por variante.
- Relación estable entre el ID externo y el producto de Lumefy.
- Historial de ejecuciones y errores.
- Progreso persistido por ejecución: etapa, porcentaje, página actual, registros recibidos/procesados y fallos.
- Diagnóstico por registro: conteo de causas y hasta 100 ejemplos seguros en `details.error_counts` y `details.error_samples`.
- Reintentos limitados con backoff para `429`, `5xx`, timeouts y errores de conexión; las respuestas JSON tienen un límite de tamaño configurable.
- Cada cambio real de inventario crea un movimiento `ADJ` con existencia anterior, nueva, diferencia y referencia de la ejecución.
- Cola duradera en PostgreSQL y recuperación de ejecuciones interrumpidas.
- Una sola ejecución concurrente por origen y una sola solicitud activa por tipo.

Las credenciales se almacenan usando el cifrado de credenciales existente en Lumefy y no se devuelven al frontend.
Los encabezados personalizados también se cifran de forma recursiva. Por defecto, el conector rechaza localhost, redes privadas, direcciones reservadas y redirecciones a otro host para reducir el riesgo de SSRF. Un entorno privado controlado puede habilitarse explícitamente con `INTEGRATION_ALLOW_PRIVATE_NETWORKS=true`.

## Configuración equivalente por API

```json
{
  "name": "Proveedor mayorista",
  "provider_key": "custom_rest",
  "source_type": "REST",
  "base_url": "https://api.proveedor.com",
  "auth_type": "bearer",
  "credentials": { "token": "TOKEN_DEL_PROVEEDOR" },
  "configuration": {
    "endpoints": {
      "products": {
        "path": "/api/external/products",
        "data_path": "data",
        "pagination": {
          "enabled": true,
          "type": "page",
          "page_param": "page",
          "per_page_param": "per_page",
          "per_page": 50,
          "start_page": 1,
          "max_pages": 1000
        }
      },
      "inventory": {
        "path": "/api/external/inventory",
        "data_path": "data",
        "batch": {
          "enabled": true,
          "query_param": "skus",
          "size": 100
        }
      }
    },
    "field_map": {
      "product.external_id": "id",
      "product.name": "name",
      "product.sku": "sku",
      "product.brand.name": "brand_name",
      "product.weight": "weight",
      "product.volume": "volume",
      "product.price": "price",
      "product.cost": "cost",
      "inventory.external_id": "product_id",
      "inventory.sku": "sku",
      "inventory.quantity": "stock"
    }
  }
}
```

En el catálogo, la marca se homologa por nombre dentro de la empresa: si ya
existe se reutiliza y si no existe se crea automáticamente. El identificador
externo de la marca, cuando el proveedor lo envía, queda guardado en los
atributos del producto para trazabilidad. También se sincronizan los campos
físicos y operativos disponibles (`weight` en kg, `volume` en litros,
`tax_rate`, `min_stock`, `product_type`, `track_inventory`, `tracking_type`,
`sale_ok`, `purchase_ok`, `unit_name` y `purchase_unit_name`), incluyendo
alias habituales en español como `marca`, `peso`, `volumen`, `iva` y
`stock_minimo`. Las unidades se homologan por nombre o abreviatura dentro de
la empresa y se crean cuando el proveedor envía una unidad nueva.

Las imágenes del catálogo se descargan al volumen persistente local del VPS y
se sirven desde Lumefy. El nombre del archivo se calcula a partir del origen y
la URL externa, por lo que repetir el catálogo reutiliza la copia existente.
Una descarga fallida no reemplaza una copia local válida; la URL externa queda
guardada en `product.attributes.external_image_urls` para poder reintentarla en
la siguiente sincronización.

Cuando `pagination.enabled` es `false`, Lumefy hace una sola solicitud. Cuando es `true`, reemplaza o agrega los parámetros de página en cada solicitud y continúa hasta encontrar una página vacía, una página menor al tamaño configurado, metadatos de páginas/total devueltos por el proveedor, `last_page`/`total` configurados o el límite `max_pages`.

Para endpoints de inventario que reciben varios SKU (por ejemplo `GET /api/external/inventory?skus=THO12306,THO12362`), activa `batch.enabled`. Lumefy toma los SKU vinculados durante la sincronización de catálogo, los divide en lotes y reemplaza dinámicamente el parámetro `skus`; el tamaño se limita a 100 aunque la configuración indique un valor mayor. La respuesta esperada puede envolver los registros en `data`, con `sku` como identificador y `stock` como cantidad. Las cantidades negativas se normalizan a cero antes de guardarse.

Cada elemento de `GET /api/v1/integrations/sources/{id}/runs` incluye el estado operativo en `details.progress`. Sus campos principales son `stage` (`STARTING`, `FETCHING`, `PROCESSING`, `COMPLETED` o `FAILED`), `percent`, `message`, `current`, `total`, `page`, `pages_total`, `items_received`, `items_total` e `items_failed`. El panel consulta este historial mientras la ejecución está en cola o en curso y conserva el último resultado al terminar.

Cuando una ejecución termina con alertas, `details.error_counts` agrupa causas como
`product_not_found`, `quantity_invalid`, `stock_below_reserved` o
`company_mismatch`. `details.error_samples` contiene solo identificadores
acotados (por ejemplo, SKU o ID externo), nunca el payload completo ni las
credenciales. Esto permite corregir el mapeo o el catálogo sin revisar miles de
registros manualmente.

Las peticiones al proveedor reintentan automáticamente los errores transitorios
con backoff y respetan `Retry-After` cuando está disponible. Los valores por
defecto son dos reintentos, 0,5 segundos iniciales, máximo 8 segundos y 20 MB
por respuesta JSON. Se pueden ajustar con `INTEGRATION_RETRY_ATTEMPTS`,
`INTEGRATION_RETRY_BASE_SECONDS`, `INTEGRATION_RETRY_MAX_SECONDS` e
`INTEGRATION_MAX_RESPONSE_BYTES`.

## Catálogo, inventario y programación

Las ejecuciones manuales se agregan a la cola y responden inmediatamente con HTTP `202`:

- `POST /api/v1/integrations/sources/{id}/sync/catalog`
- `POST /api/v1/integrations/sources/{id}/sync/inventory`

El endpoint anterior `POST /sync` se conserva temporalmente como compatibilidad y encola una ejecución completa. Los clientes nuevos deben usar los endpoints separados.

La programación del inventario se actualiza con:

```http
PUT /api/v1/integrations/sources/{id}/inventory-schedule
Content-Type: application/json

{
  "mode": "AUTOMATIC",
  "interval_minutes": 15
}
```

El intervalo permitido está entre 5 y 1440 minutos. En modo `MANUAL`, `interval_minutes` se guarda como `null`. El servicio `integration-sync-worker` encola los orígenes vencidos y procesa catálogo e inventario sin bloquear las peticiones web. El inventario usa una identidad única por empresa, producto, variante, sucursal y almacén, por lo que repetir un payload actualiza la existencia en vez de duplicarla.

La sincronización de inventario trata la respuesta del proveedor como una
fotografía de existencia física: normaliza valores negativos a cero y no reduce
una existencia por debajo de `reserved_quantity`. Cuando la fotografía es
válida y cambia el valor, se registra un ajuste auditable; las ventas y compras
continúan generando sus propios movimientos `OUT`/`IN`.

## Vista previa / debug

El botón **Ver previa / debug** ejecuta una consulta de solo lectura al endpoint de productos y, si está configurado, al de inventario. Solo consulta la primera página, muestra la URL sin credenciales, el estado HTTP, el mapeo que usaría la sincronización y una muestra del JSON original. No crea ni actualiza productos, inventario, vínculos o ejecuciones de sincronización.

El botón **Mapeo pendiente** analiza una muestra y propone rutas como `product_id`, `variants[].sku`, `images[]` y `variants[].properties[]`. El usuario puede editar las rutas y confirmar el perfil. Los campos principales se guardan en las entidades normalizadas; especificaciones y propiedades se conservan en atributos JSON y en el payload original. Cuando llegan `provider_id`/`supplier_id` o `provider_name`/`supplier_name`, el catálogo homologa el proveedor existente o lo crea automáticamente y guarda la relación en el producto.

## Próxima evolución

La tabla de vínculos ya es genérica por `entity_type`, por lo que se pueden añadir conectores para categorías, clientes, pedidos y proveedores sin cambiar el núcleo de productos. Las siguientes mejoras recomendadas son cursor pagination, sincronización incremental, webhooks y conectores específicos dentro del marketplace de apps.
