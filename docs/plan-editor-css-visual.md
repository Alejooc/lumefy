# Evolución del editor visual de estilos

## Alcance actual

La sección **Código personalizado** permite añadir contenido HTML presentacional o una integración externa mediante enlace. El contenido se guarda dentro del documento visual de la tienda correspondiente y se filtran scripts, formularios, estilos en línea, eventos y URLs inseguras.

El modo de integración utiliza un `iframe` aislado y acepta HTTPS. En desarrollo también permite enlaces HTTP de `localhost`, `127.0.0.1` y `::1` para que el preview local funcione con puertos.

## Próximas fases

### Fase 1 — Estilos visuales estructurados

Agregar a cada sección un panel **Diseño** con controles seguros y reutilizables:

- ancho del contenido y alineación;
- fondo, color de texto y color de títulos usando el tema;
- separación superior e inferior;
- bordes, radio y sombra;
- visibilidad por dispositivo.

Los valores deben ser tokens controlados, no CSS libre. Así se conserva la identidad visual del tema y se evita que una sección rompa el resto de la tienda.

### Fase 2 — Selector de elementos

El modo selector debe identificar la sección y, progresivamente, sus elementos editables —título, imagen, botón, lista o tarjeta—. Al tocar un elemento, el inspector abrirá sus propiedades de contenido y diseño en el mismo contexto.

Cada elemento tendrá un identificador estable dentro de su sección. La selección y los estilos viajarán en el documento de la tienda, sin compartir configuraciones entre empresas.

### Fase 3 — CSS avanzado opcional

Si se requiere personalización avanzada, se puede añadir un panel para CSS por tienda, siempre con estas reglas:

- alcance automático bajo un atributo único de la tienda o sección;
- límite de tamaño y validación antes de guardar;
- bloqueo de `@import`, scripts, URLs ejecutables y selectores que intenten salir del alcance;
- vista previa y publicación independientes;
- historial y rollback del documento anterior.

No se debe permitir CSS global sin alcance ni código JavaScript desde este editor. Para integraciones externas se mantiene el bloque de contenido integrado.

## Criterios de aceptación

- Un cliente puede ajustar la apariencia sin conocer CSS.
- Los colores predeterminados del tema siguen siendo la base visual.
- Un cambio de una empresa nunca aparece en otra.
- El preview muestra el resultado antes de publicar.
- Un documento inválido no se guarda ni se publica.
- Cada versión publicada puede revertirse desde el historial.
