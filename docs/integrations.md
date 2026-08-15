# Orígenes de datos e integraciones

Lumefy permite que cada empresa configure sus propios orígenes de datos REST desde el panel en **Orígenes de datos**.

## Primera versión

La primera versión soporta:

- Autenticación Bearer, API key o sin autenticación.
- Prueba de conexión.
- Importación manual de productos y precios.
- Importación manual de inventario.
- Mapeo de campos mediante rutas JSON (`data.items.0.sku`).
- Detección automática de campos con confianza y confirmación manual del perfil.
- Catálogos simples y catálogos con variantes, imágenes, atributos e inventario por variante.
- Relación estable entre el ID externo y el producto de Lumefy.
- Historial de ejecuciones y errores.

Las credenciales se almacenan usando el cifrado de credenciales existente en Lumefy y no se devuelven al frontend.

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

Cuando `pagination.enabled` es `false`, Lumefy hace una sola solicitud. Cuando es `true`, reemplaza o agrega los parámetros de página en cada solicitud y continúa hasta encontrar una página vacía, una página menor al tamaño configurado, `last_page`/`total` si se configuran, o el límite `max_pages`.

## Vista previa / debug

El botón **Ver previa / debug** ejecuta una consulta de solo lectura al endpoint de productos y, si está configurado, al de inventario. Solo consulta la primera página, muestra la URL sin credenciales, el estado HTTP, el mapeo que usaría la sincronización y una muestra del JSON original. No crea ni actualiza productos, inventario, vínculos o ejecuciones de sincronización.

El botón **Mapeo pendiente** analiza una muestra y propone rutas como `product_id`, `variants[].sku`, `images[]` y `variants[].properties[]`. El usuario puede editar las rutas y confirmar el perfil. Los campos principales se guardan en las entidades normalizadas; especificaciones, propiedades, proveedor y otros campos se conservan en atributos JSON y en el payload original.

## Próxima evolución

La tabla de vínculos ya es genérica por `entity_type`, por lo que se pueden añadir conectores para variantes, categorías, clientes, pedidos y proveedores sin cambiar el núcleo de productos. La siguiente etapa recomendada es mover la sincronización manual a workers programados, agregar cursor pagination/webhooks y después registrar conectores específicos dentro del marketplace de apps.
