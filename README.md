# Restaurant WhatsApp Chatbot SaaS

v0.1


Sistema conversacional productivo para restaurantes sobre **Flask + Twilio WhatsApp + Google Sheets**, con flujo editable en JSON.

## Arquitectura

```
/app
  app.py                 # Flask + webhook Twilio POST /bot
  config.py
  core/
    state_manager.py     # Estado por WaId
    parser.py            # Parser NL de pedidos
    flow_engine.py       # Motor que interpreta restaurant_flow.json
  services/
    menu_service.py
    order_service.py
    reservation_service.py
    user_service.py
  integrations/
    google_sheets.py
  utils/
    validators.py
/flows
  restaurant_flow.json   # Flujo conversacional editable
```

## Requisitos

- Python 3.11+
- Cuenta Twilio con WhatsApp Sandbox o número aprobado
- Google Cloud Service Account con acceso a Google Sheets API
- ngrok (desarrollo local)

## Instalación

```bash
cd "Chatbot cursor"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Google Sheets

1. Crea un Spreadsheet con estas pestañas (se crean automáticamente si no existen):
   - **MENU**: id, nombre, precio, categoria, disponible
   - **USERS**: wa_id, name, last_seen
   - **ORDERS**: order_id, wa_id, items, total, status, timestamp
   - **RESERVATIONS**: reservation_id, wa_id, personas, fecha, hora, status

2. Coloca el JSON de la service account en `credentials/google-service-account.json`.

3. Comparte el spreadsheet con el email de la service account.

4. Configura `GOOGLE_SPREADSHEET_ID` en `.env`.

> Sin credenciales, el bot funciona en modo demo con menú local y persistencia en memoria.

## Twilio + ngrok

1. Inicia el servidor:

```bash
python run.py
```

2. Expón el puerto:

```bash
ngrok http 5000
```

3. En Twilio Console → WhatsApp Sandbox → Webhook:

```
POST https://<tu-subdominio>.ngrok.io/bot
```

## Comandos globales (siempre activos)

| Comando    | Acción                    |
|-----------|---------------------------|
| menu      | Ver menú                  |
| pedido    | Iniciar pedido            |
| reservar  | Iniciar reserva           |
| inicio    | Reiniciar flujo           |
| cancelar  | Cancelar proceso actual   |

## Personalización del flujo

Edita `flows/restaurant_flow.json` sin tocar Python. Recarga en caliente:

```bash
curl -X POST http://localhost:5000/bot/reload-flow
```

## Simulación local

```bash
python scripts/simulate_conversation.py
```

## Endpoint principal

- `POST /bot` — Webhook Twilio (MessagingResponse XML)
- `GET /health` — Health check

## Parser de pedidos

Entiende lenguaje natural:

- `2 pizzas hawaianas y una coca cola`
- `quiero pizza, hamburguesa y 2 aguas`
- `quita la coca cola`
- `cambia pizza por hamburguesa`

## Estado por usuario

```python
{
  "wa_id": {
    "flow": "idle | order | reservation",
    "step": "node_id",
    "data": { "cart": [], "reservation": {} }
  }
}
```

Persistencia opcional en `data/user_states.json`.

## Producción inicial

- Usa un WSGI server (`gunicorn`, `waitress`)
- Mueve estado a Redis para multi-instancia
- Protege `/bot/reload-flow` con auth
- Rota credenciales y usa HTTPS permanente (no solo ngrok)







Respuesta cursor:


Chatbot de restaurante — sistema listo
Se construyó un SaaS conversacional productivo con la arquitectura que pediste. El workspace estaba vacío; todo el sistema se generó desde cero.

Estructura del proyecto
/app
  app.py                      → Flask + POST /bot (Twilio)
  config.py
  core/
    state_manager.py          → Estado por WaId (thread-safe + persistencia)
    parser.py                 → Parser NL de pedidos
    flow_engine.py            → Motor que interpreta el JSON
  services/
    menu_service.py
    order_service.py
    reservation_service.py
    user_service.py
  integrations/
    google_sheets.py          → MENU, USERS, ORDERS, RESERVATIONS
  utils/
    validators.py
/flows
  restaurant_flow.json        → Flujo editable sin tocar Python
/scripts
  simulate_conversation.py    → Simulación multi-usuario
run.py
requirements.txt
.env.example
README.md
Capacidades implementadas
Feature	Estado
Menú dinámico desde Google Sheets
✅
Carrito con parser NL
✅
Reservas paso a paso
✅
Usuarios auto-registrados
✅
Pedidos persistentes en ORDERS
✅
Reservas persistentes en RESERVATIONS
✅
Estado por WaId
✅
Comandos globales (menu, pedido, reservar, inicio, cancelar)
✅
Flujo 100% driven por JSON
✅
Webhook Twilio con MessagingResponse
✅
Modo demo sin credenciales
✅
Parser inteligente
Entiende mensajes como:

2 pizza hawaiana, 1 coca cola
2 pizzas hawaianas y una coca cola
quita la coca cola
cambia pizza hawaiana por hamburguesa clasica
Cómo ponerlo en marcha
cd "c:\Users\Usuario\Desktop\Chatbot cursor"
venv\Scripts\activate
copy .env.example .env
python run.py
En otra terminal:

ngrok http 5000
Configura en Twilio Console → WhatsApp → Webhook:

POST https://<tu-ngrok>.ngrok.io/bot
Google Sheets
Crea un spreadsheet y pon su ID en .env → GOOGLE_SPREADSHEET_ID
Coloca la service account en credentials/google-service-account.json
Comparte el sheet con el email de la service account
Las pestañas MENU, USERS, ORDERS y RESERVATIONS se crean solas si no existen.

Personalizar conversación
Edita flows/restaurant_flow.json y recarga sin reiniciar:

curl -X POST http://localhost:5000/bot/reload-flow
Simular localmente
python scripts/simulate_conversation.py
Arquitectura clave
FlowEngine: interpreta restaurant_flow.json; la lógica de negocio vive en acciones (show_menu, capture_order, save_reservation, etc.)
StateManager: { flow, step, data } por usuario, con persistencia opcional en data/user_states.json
Comandos globales: siempre activos; el usuario nunca queda bloqueado
Navegación: cada respuesta incluye las opciones menu, pedido, reservar, inicio, cancelar
Sin credenciales de Google, el bot funciona en modo demo con menú local para desarrollo y pruebas.

¿Quieres que configuremos el .env con tus credenciales de Twilio/Google, o que añadamos multi-restaurante (multi-tenant SaaS)?
























###############################################################
###############################################################
v0.2


Prompt generado en chatgpt:

# MODO ARQUITECTO SENIOR - MEJORA INCREMENTAL DEL SISTEMA

Actúa como un Principal Software Architect especializado en:

* Python
* Flask
* Twilio WhatsApp
* Sistemas conversacionales
* Motores de pedidos
* SaaS para restaurantes

Tu misión NO es reconstruir el proyecto.

Tu misión es EVOLUCIONAR el proyecto actual manteniendo compatibilidad total.

---

# REGLA CRÍTICA

Antes de modificar cualquier archivo:

1. Analiza toda la arquitectura existente.
2. Identifica dependencias.
3. Identifica contratos de entrada y salida.
4. Identifica flujos de conversación.
5. Identifica estados.
6. Identifica posibles puntos de ruptura.

NO debes romper nada existente.

Toda mejora debe ser incremental.

---

# OBJETIVO

Mejorar significativamente la experiencia del cliente, la robustez del parser y la operación del restaurante.

---

# MEJORA 1 - LOG DE ERRORES DEL PARSER

Crear un sistema de auditoría.

Cada vez que el parser:

* no entienda un mensaje
* detecte ambigüedad
* entre en fail-safe
* retorne needs_clarification

Debe registrarse automáticamente.

Guardar:

* timestamp
* teléfono del cliente
* mensaje original
* motivo del fallo
* score obtenido
* estado del parser

Crear log_parser_errors.

El sistema nunca debe detenerse por errores de logging.

---

# MEJORA 2 - SOPORTE PERFECTO DE CONECTORES

Mejorar el parser para interpretar correctamente:

* y
* e
* &
* *
* comas

Ejemplos:

2 hamburguesas y 1 agua

2 hamburguesas, 1 agua

2 hamburguesas & 1 agua

hamburguesa + agua

Todos deben producir el mismo resultado.

---

# MEJORA 3 - MOTOR DE INTERPRETACIÓN AVANZADO

Aumentar la tolerancia a errores.

Debe aceptar:

* errores ortográficos
* palabras repetidas
* texto desordenado
* cantidades mezcladas

Ejemplos:

peeedido dos hamburgesas y una coca

quiero una hambrguesa con una gaseoza

2 hamburguesas agua 3 papas

Objetivo:

Maximizar recall sin aumentar falsos positivos.

---

# MEJORA 4 - MEMORIA DE CLIENTES

Crear persistencia básica de clientes.

Guardar:

* teléfono
* nombre
* dirección
* fecha última compra
* último pedido

Cuando vuelva:

Hola {nombre}, bienvenido nuevamente.

---

# MEJORA 5 - REPETIR PEDIDO ANTERIOR

Si existe historial:

Ofrecer:

¿Deseas repetir tu pedido anterior?

Si responde sí:

Reconstruir automáticamente el carrito.

---

# MEJORA 6 - SOLICITAR NOMBRE

Al finalizar un pedido nuevo:

Solicitar nombre.

Objetivo:

Mejorar identificación y futuras compras.

No solicitarlo nuevamente si ya existe.

---

# MEJORA 7 - SOLICITAR DIRECCIÓN

Si es domicilio:

Solicitar dirección.

Guardar para futuras compras.

Si ya existe:

Preguntar si desea usar la dirección guardada.

---

# MEJORA 8 - ENTREGA O RECOGIDA

Antes de finalizar:

Preguntar:

¿Deseas:

1. Domicilio
2. Recoger en tienda?

Guardar la respuesta.

---

# MEJORA 9 - DETECCIÓN DE CONTEXTO

El sistema debe distinguir:

* saludo
* nueva conversación
* pedido en progreso
* pedido finalizado

Ejemplos:

hola

buenas

qué tal

No deben iniciar un pedido automáticamente.

---

# MEJORA 10 - MENSAJE DE BIENVENIDA MEJORADO

Enviar dos mensajes separados:

Mensaje 1:

Saludo.

Mensaje 2:

Opciones disponibles.

Ejemplo:

1. Menú
2. Hacer pedido

---

# MEJORA 11 - BOTÓN VOLVER AL INICIO

Mantener una sola opción:

Volver al inicio.

Si existe pedido activo:

Preguntar:

¿Estás seguro de abandonar tu pedido actual?

Sí / No

---

# MEJORA 12 - NOTIFICACIONES AL ADMIN

Agregar configuración en app.py:

ADMIN_WHATSAPP_NUMBER

Cuando un cliente confirme un pedido:

Enviar automáticamente al administrador:

* cliente
* teléfono
* dirección
* pedido
* total

---

# MEJORA 13 - CONFIRMACIÓN DEL ADMIN

El administrador debe responder:

CONFIRMAR

o equivalente.

Mientras no confirme:

Mantener pedido pendiente.

---

# MEJORA 14 - RECORDATORIOS AUTOMÁTICOS

Si el administrador no responde:

Reenviar recordatorio cada 5 minutos.

Límite:

1 hora.

Después:

Detener recordatorios.

Registrar evento.

---

# MEJORA 15 - COMPATIBILIDAD TOTAL

No romper:

* Flask
* Twilio
* Flow Engine
* Order Service
* Parser API
* Google Sheets
* Estado conversacional

Todos los contratos existentes deben seguir funcionando.

---

# ENTREGABLE OBLIGATORIO

Antes de modificar código:

Explicar:

1. Archivos a modificar.
2. Motivo de cada cambio.
3. Riesgos identificados.
4. Cómo se evita romper compatibilidad.

Al finalizar:

Generar un resumen:

FUNCIONALIDADES AGREGADAS

* ...
* ...
* ...

RIESGOS MITIGADOS

* ...
* ...

ARCHIVOS MODIFICADOS

* ...
* ...

COMPATIBILIDAD VERIFICADA

* Parser
* Flask
* Twilio
* Flow Engine
* Order Service
* Persistencia

No asumir que algo funciona.

Verificarlo y muestrame todas las mejoras incrementales que hiciste



Respuesta de  cursor al finalizar la ejecución del prompt:

FUNCIONALIDADES AGREGADAS
Mejora 1 — Auditoría del parser (log_parser_errors)
Registro JSONL en data/parser_errors.jsonl (configurable).
Campos: timestamp, teléfono, mensaje, motivo, score, estado, unknown.
Se activa en fail-safe, needs_clarification, segmentos desconocidos.
Nunca detiene el flujo si falla el log.
Mejora 2 — Conectores
Soporte: y, e, ,, &, +, * (mismo resultado equivalente).
14 pruebas automáticas en python -m app.core.parser (14/14 OK).
Mejora 3 — Motor de interpretación
Typos: hambrguesa, gaseoza, plurales, texto desordenado.
Desambiguación por tokens distintivos (p. ej. hawaiana vs margarita).
Corrección de palabras pegadas sin perder espacios.
Mejora 4 — Memoria de clientes
USERS ampliado: name, address, last_order_date, last_order_json.
UserService.get_profile, save_name, save_address.
Mejora 5 — Repetir pedido anterior
Al volver con historial: “¿Deseas repetir tu pedido anterior?”
Si responde sí → reconstruye el carrito y va a revisión.
Mejora 6 — Solicitar nombre
Nodo order_customer_name si no hay nombre guardado.
No vuelve a pedirlo si ya existe.
Mejora 7 — Dirección (domicilio)
Nodo order_address con dirección guardada (“¿usar la guardada?”).
Mejora 8 — Entrega o recogida
Nodo order_delivery → domicilio o recoger en tienda.
Mejora 9 — Detección de contexto
Saludos (hola, buenas, qué tal) en order_start no inician pedido; invitan a ordenar.
Mejora 10 — Bienvenida en dos mensajes
dual_message en start: saludo + menú de opciones (2 burbujas Twilio).
Mejora 11 — Volver al inicio con confirmación
Con carrito activo, inicio pregunta si abandonar el pedido (sí/no).
Mejora 12 — Notificaciones al admin
ADMIN_WHATSAPP_NUMBER en config.py / .env.example.
Al guardar pedido → notificación con cliente, teléfono, dirección, pedido, total.
Mejora 13 — Confirmación del admin
Admin escribe CONFIRMAR ORD-XXXXXXXX → pedido confirmed + aviso al cliente.
Mejora 14 — Recordatorios automáticos
Cada 5 min al admin si sigue pending (máx. 1 h).
Evento registrado en el mismo log de auditoría.
Mejora 15 — Compatibilidad
API pública del parser intacta (apply_message, parse_order, format_cart, etc.).
Flujo reservas y comandos globales sin cambios breaking.
RIESGOS MITIGADOS
Parser no inventa productos (menú dinámico + QA).
Logging envuelto en try/except (no tumba Flask).
Twilio outbound opcional (si no hay credenciales, solo log).
Admin aislado por número (mismo webhook /bot).
Sheets sin conexión → modo demo en memoria.
ARCHIVOS MODIFICADOS
Archivo	Cambio
app/config.py
Admin, Twilio, rutas de log, intervalos
app/core/parser.py
Logging, conectores +/*, fixes matching, 14 tests
app/utils/validators.py
Saludos, domicilio, confirmación admin
app/integrations/google_sheets.py
Perfil cliente, pedidos extendidos, pending/confirm
app/services/user_service.py
Memoria de cliente
app/services/order_service.py
wa_id en parse, metadata en save
app/services/admin_service.py
Nuevo — notify, confirm, reminders
app/core/flow_engine.py
Flujo completo UX + admin hooks
flows/restaurant_flow.json
Nodos delivery/address/name, bienvenida dual
app/app.py
Admin routing, multi-mensaje, scheduler
scripts/simulate_conversation.py
Constructor actualizado
.env.example
Variables admin/Twilio/log
COMPATIBILIDAD VERIFICADA
Sistema	Estado
Parser
python -m app.core.parser → 14/14 OK
Flask
create_app() carga sin error
Twilio
Multi-message() en TwiML; admin en mismo webhook
Flow Engine
Pedido completo probado: captura → revisión → entrega → nombre → guardado
Order Service
parse_order_text / save_order compatibles
Persistencia
State JSON + demo users/orders en memoria
Configuración necesaria en .env
ADMIN_WHATSAPP_NUMBER=whatsapp:+57XXXXXXXXXX
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
PARSER_ERROR_LOG_PATH=data/parser_errors.jsonl
El admin confirma con: CONFIRMAR ORD-XXXXXXXX

Flujo de pedido actualizado
pedido → captura NL → revisión → sí → tipo entrega → (dirección si domicilio) → (nombre si falta) → guardado (pending) → notificación admin
Tu mensaje largo con comas ya se interpreta correctamente (verificado en sesiones anteriores y en la suite de 14 tests). Si quieres, el siguiente paso puede ser probar el flujo completo por WhatsApp con ADMIN_WHATSAPP_NUMBER configurado.





##################################################################################################################################
v0.3

Prompt generado con chat gpt:






*****Respuesta de cursor*








##################################################################################################################################