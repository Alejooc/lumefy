# Evidencia de producto GA7-220501096-AA3-EV02

## Portada

**Programa:** Analisis y Desarrollo de Software  
**Evidencia:** GA7-220501096-AA3-EV02 Modulos de software codificados y probados  
**Proyecto:** Lumefy  
**Modulo evaluado:** Clientes  
**Componentes incluidos:** `backend` y `frontend_mantis`  
**Aprendiz:** [Completar]  
**Ficha:** [Completar]  
**Instructor:** [Completar]  
**Fecha:** [Completar]

## Introduccion

Este documento presenta la evidencia funcional y tecnica del modulo de clientes del proyecto Lumefy, tomando en cuenta unicamente el backend desarrollado en FastAPI y la interfaz administrativa Mantis desarrollada en Angular. El objetivo es demostrar que el modulo fue codificado, validado y probado segun las necesidades funcionales del sistema, dejando trazabilidad de las historias de usuario, validaciones aplicadas y resultados esperados.

## Objetivo

Verificar que el modulo de clientes permite registrar, consultar, actualizar y gestionar informacion comercial y financiera de los clientes desde Mantis, apoyado por servicios backend validados y probados.

## Alcance

Este entregable cubre:

- Registro de clientes
- Consulta y busqueda de clientes
- Edicion de clientes
- Consulta de perfil del cliente
- Registro de interacciones
- Registro de abonos sobre saldo pendiente
- Validaciones de texto, numeros, longitudes y caracteres permitidos
- Evidencia de uso de versionamiento con Git

## Arquitectura evaluada

- Backend: `backend/app/api/v1/endpoints/clients.py`
- Validaciones backend: `backend/app/schemas/client.py`
- Validaciones de pagos: `backend/app/schemas/account_ledger.py`
- Interfaz Mantis: `frontend_mantis/src/app/modules/clients/`

## Historias de usuario y evidencias

### HU-01 Registrar cliente

**Descripcion:** Como usuario con permiso de gestion de clientes, deseo crear un cliente desde Mantis para asociarlo a ventas, seguimiento CRM y estado de cuenta.

**Ruta Mantis sugerida:** `/clients/new`

**Resultado esperado:**

- El sistema registra el cliente correctamente.
- El cliente aparece en el listado general.
- Los datos quedan disponibles en la vista detalle.

**Captura pendiente por agregar:** insertar pantallazo del formulario diligenciado y del mensaje de confirmacion.

### HU-02 Consultar y buscar clientes

**Descripcion:** Como usuario administrativo, deseo listar y filtrar clientes para ubicar rapidamente un registro por nombre o estado.

**Ruta Mantis sugerida:** `/clients`

**Resultado esperado:**

- El listado muestra los clientes registrados.
- La busqueda por texto filtra coincidencias.
- El filtro por estado muestra solo los registros correspondientes.

**Captura pendiente por agregar:** insertar pantallazo del listado y del filtro aplicado.

### HU-03 Editar cliente

**Descripcion:** Como usuario con permisos, deseo actualizar la informacion de un cliente para mantener datos comerciales correctos.

**Ruta Mantis sugerida:** `/clients/edit/{id}`

**Resultado esperado:**

- El sistema permite modificar nombre, identificacion, telefono, direccion, estado, notas y limite de credito.
- Los cambios se reflejan en la vista detalle y en el listado.

**Captura pendiente por agregar:** insertar pantallazo del formulario en modo edicion antes y despues de guardar.

### HU-04 Consultar perfil y estado de cuenta

**Descripcion:** Como usuario administrativo, deseo revisar la ficha del cliente para consultar saldo, historial, ventas y datos de contacto.

**Ruta Mantis sugerida:** `/clients/view/{id}`

**Resultado esperado:**

- Se visualiza el saldo pendiente.
- Se visualizan metricas comerciales y datos de contacto.
- Se visualiza el estado de cuenta y el historial de compras.

**Captura pendiente por agregar:** insertar pantallazo de la vista general y de la pestaña de estado de cuenta.

### HU-05 Registrar interaccion CRM

**Descripcion:** Como usuario, deseo guardar notas o interacciones del cliente para conservar el seguimiento comercial.

**Ruta Mantis sugerida:** `/clients/view/{id}` pestaña `Linea de Tiempo`

**Resultado esperado:**

- La interaccion queda registrada.
- La linea de tiempo muestra el nuevo evento.
- Se almacena el tipo de interaccion y su contenido.

**Captura pendiente por agregar:** insertar pantallazo del formulario de interaccion y de la linea de tiempo actualizada.

### HU-06 Registrar abono

**Descripcion:** Como usuario administrativo, deseo registrar un abono sobre la deuda del cliente para actualizar su saldo.

**Ruta Mantis sugerida:** `/clients/view/{id}` pestaña `Estado Financiero`

**Resultado esperado:**

- El sistema registra el pago.
- El saldo pendiente disminuye.
- El movimiento queda reflejado en el estado de cuenta.

**Captura pendiente por agregar:** insertar pantallazo del modal de abono y del estado de cuenta actualizado.

## Validaciones probadas

### Validaciones de texto

| Campo | Regla | Resultado esperado |
|---|---|---|
| Nombre | Obligatorio, minimo 2, maximo 120 caracteres | No permite guardar vacio ni excedido |
| Direccion | Maximo 180 caracteres | Rechaza valores demasiado largos |
| Notas | Maximo 500 caracteres | Rechaza textos extensos |
| Descripcion de interaccion | Obligatoria, minimo 3, maximo 500 | No permite texto vacio o muy corto |
| Descripcion de pago | Obligatoria, minimo 3, maximo 160 | No permite texto vacio o muy corto |

### Validaciones de numeros

| Campo | Regla | Resultado esperado |
|---|---|---|
| Limite de credito | Debe ser mayor o igual a 0 | No acepta numeros negativos |
| Monto de abono | Debe ser mayor a 0 | No acepta cero ni negativos |

### Validaciones de caracteres especiales

| Campo | Regla | Resultado esperado |
|---|---|---|
| Identificacion | Permite letras, numeros, espacios, punto, slash y guion | Rechaza caracteres como `#`, `@`, `*` |
| Telefono | Permite numeros, espacios, parentesis, `+` y guion | Rechaza letras u otros simbolos no validos |
| Email | Formato correo valido | Rechaza correos mal formados |

### Validaciones de longitud

| Campo | Regla |
|---|---|
| Identificacion | Maximo 30 caracteres |
| Telefono | Maximo 25 caracteres |
| Referencia de pago | Maximo 80 caracteres |

### Validaciones de fechas

En este modulo no se capturan fechas manualmente desde el formulario de clientes. Las fechas visibles en registro, linea de tiempo, ventas y estado de cuenta son generadas por el sistema, por lo que la validacion aplicada corresponde a la correcta visualizacion de fecha y hora en cada movimiento almacenado.

## Pruebas tecnicas ejecutadas

Se agrego una prueba automatizada para las validaciones del backend:

- Archivo: `backend/tests/test_client_validations.py`
- Comando de ejecucion:

```powershell
cd backend
venv\Scripts\python -m unittest discover -s tests -p "test_*.py" -v
```

**Cobertura funcional de la prueba automatizada:**

- Creacion valida de cliente
- Rechazo de identificacion con caracteres invalidos
- Rechazo de telefono invalido
- Rechazo de limite de credito negativo
- Normalizacion de campos opcionales vacios
- Validacion de contenido minimo en interacciones
- Validacion de monto, descripcion y referencia en pagos

## Registro sugerido para el video

Durante el video se recomienda mostrar este orden:

1. Ingreso al modulo de clientes en Mantis.
2. Creacion de un cliente valido.
3. Intento de creacion con datos invalidos.
4. Edicion del cliente.
5. Consulta del perfil del cliente.
6. Registro de una interaccion.
7. Registro de un abono.
8. Visualizacion del estado final en listado, linea de tiempo y estado de cuenta.

## Evidencia de versionamiento

Para soportar el uso de Git, agregar capturas de:

- `git status`
- `git log --oneline -5`
- commit relacionado con el modulo de clientes o con las validaciones

Comandos sugeridos:

```powershell
git status
git log --oneline -5
```

## Conclusiones

El modulo de clientes de Lumefy cumple con el objetivo de registrar y administrar informacion de clientes desde Mantis, respaldado por un backend con validaciones de negocio y de entrada. Las pruebas funcionales y tecnicas definidas permiten sustentar que el modulo fue codificado y probado, quedando listo para que se anexen las capturas y el video solicitados en la evidencia.
