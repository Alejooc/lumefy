# Guia rapida para la evidencia

## Archivos generados
- `Lumefy.postman_collection.json`: coleccion lista para importar en Postman.
- `Lumefy.local.postman_environment.json`: ambiente local con `baseUrl` y `access_token`.
- `ENDPOINTS_Lumefy.md`: inventario de endpoints.
- `REPOSITORIO.txt`: enlace del repositorio.

## Instalacion de Postman
1. Descarga Postman desde `https://www.postman.com/downloads/`.
2. Instala la aplicacion.
3. Importa la coleccion y el environment generados en `docs/postman/`.

## Flujo de prueba recomendado
1. Levanta el backend en `http://localhost:8000`.
2. Ejecuta `POST /api/v1/login/access-token` con el usuario admin.
3. Guarda el token en `access_token`.
4. Prueba endpoints `GET` primero.
5. Luego prueba `POST`, `PUT` y `DELETE` con datos controlados.

## Sugerencia para video y pantallazos
- Muestra el login exitoso.
- Muestra minimo un `GET`, un `POST`, un `PUT` y un `DELETE`.
- Muestra el codigo de respuesta y el body.
- Toma pantallazos de cada prueba relevante y pegalos en tu documento.

## Nombre de carpeta sugerido
- `NOMBRE_APELLIDO_AA5_EV04`

## Credenciales iniciales segun README
- Email: `admin@lumefy.com`
- Password: `admin123`