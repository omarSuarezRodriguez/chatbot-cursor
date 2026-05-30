# Restaurant WhatsApp Chatbot SaaS

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