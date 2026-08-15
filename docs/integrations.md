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
      "inventory": { "path": "/inventory", "data_path": "items" }
    },
    "field_map": {
      "product.external_id": "id",
      "product.name": "name",
      "product.sku": "sku",
      "product.price": "price",
      "product.cost": "cost",
      "inventory.external_id": "product_id",
      "inventory.sku": "sku",
      "inventory.quantity": "quantity"
    }
  }
}
```

Cuando `pagination.enabled` es `false`, Lumefy hace una sola solicitud. Cuando es `true`, reemplaza o agrega los parámetros de página en cada solicitud y continúa hasta encontrar una página vacía, una página menor al tamaño configurado, metadatos de páginas/total devueltos por el proveedor, `last_page`/`total` configurados o el límite `max_pages`.

Cada elemento de `GET /api/v1/integrations/sources/{id}/runs` incluye el estado operativo en `details.progress`. Sus campos principales son `stage` (`STARTING`, `FETCHING`, `PROCESSING`, `COMPLETED` o `FAILED`), `percent`, `message`, `current`, `total`, `page`, `pages_total`, `items_received`, `items_total` e `items_failed`. El panel consulta este historial mientras la ejecución está en cola o en curso y conserva el último resultado al terminar.

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

## Vista previa / debug

El botón **Ver previa / debug** ejecuta una consulta de solo lectura al endpoint de productos y, si está configurado, al de inventario. Solo consulta la primera página, muestra la URL sin credenciales, el estado HTTP, el mapeo que usaría la sincronización y una muestra del JSON original. No crea ni actualiza productos, inventario, vínculos o ejecuciones de sincronización.

El botón **Mapeo pendiente** analiza una muestra y propone rutas como `product_id`, `variants[].sku`, `images[]` y `variants[].properties[]`. El usuario puede editar las rutas y confirmar el perfil. Los campos principales se guardan en las entidades normalizadas; especificaciones, propiedades, proveedor y otros campos se conservan en atributos JSON y en el payload original.

## Próxima evolución

La tabla de vínculos ya es genérica por `entity_type`, por lo que se pueden añadir conectores para categorías, clientes, pedidos y proveedores sin cambiar el núcleo de productos. Las siguientes mejoras recomendadas son cursor pagination, sincronización incremental, webhooks y conectores específicos dentro del marketplace de apps.
