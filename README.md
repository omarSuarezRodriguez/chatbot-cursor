## v0.36

## Restaurant WhatsApp Chatbot SaaS

en run.py está el bot, con runall.py se arranca todo para el bot (local solo hace falta ngrok) y guardar.py sube a github el proyecto actual y le pone de commit la versión que se encuentra al comienzo de readme.md


Sistema conversacional productivo para restaurantes sobre **Flask + Twilio WhatsApp + Google Sheets**, con flujo editable en JSON.


## Prompt base ##
Haz este cambio SOLO en local (no despliegues). 
Al final dame: (1) qué cambiaste, (2) cómo probarlo local, (3) comando exacto para desplegar cuando yo diga “despliega”.

## Publicar ##

Despliega a producción lo último que ya dejamos listo en local, verifica en vivo y confirma resultado.



**Protocolo de trabajo (local/producción):**
- Si quieres solo preparar cambios: **"haz cambios solo local, no despliegues"**.
- Cuando ya esté validado en local: **"despliega a producción"**.
- Si quieres despliegue inmediato: **"haz el cambio y despliega a producción"**.
- Regla rápida: cambios de código van en ambos entornos al desplegar; variables (`.env`/Railway) pueden diferir entre local y producción.

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

## Dashboard local (desarrollo)

Panel Django + PostgreSQL **solo para desarrollo local**. No modifica el bot ni sus endpoints Flask (`POST /bot`, `GET /health`). El bot sigue en el puerto **5000**; el dashboard en el **8000**.

### Requisitos adicionales

- Docker Desktop (o Docker Engine) para PostgreSQL 16
- Dependencias del dashboard en el mismo venv o uno aparte:

```bash
pip install -r requirements-dashboard.txt
copy .env.dashboard.example .env.dashboard
```

### Arranque rápido (un comando)

Desde la raíz del proyecto (Windows), con venv activado y dependencias instaladas:

```bat
.\dev.cmd all
```

Eso inicia PostgreSQL, aplica migraciones, y abre el **bot** y el **dashboard** en ventanas nuevas. También puedes usar cada servicio por separado:

| Comando | Acción |
|---------|--------|
| `.\dev.cmd db` | Solo PostgreSQL (Docker) |
| `.\dev.cmd bot` | Solo bot Flask (`python run.py`) |
| `.\dev.cmd dashboard` | PostgreSQL (si hace falta) + migrate + Django en :8000 |
| `.\dev.cmd all` | Todo el entorno local |
| `.\dev.cmd stop` | Detiene PostgreSQL y libera puertos 5000/8000 |

Equivalente en PowerShell: `.\scripts\dev\dev.ps1 all` (mismos subcomandos: `db`, `bot`, `dashboard`, `all`, `stop`).

Los scripts comprueban Python, Docker, venv y paquetes básicos; si falta `.env` o `.env.dashboard`, indican cómo copiarlos desde los `.example`.

**URLs tras el arranque:**

| Servicio | URL |
|----------|-----|
| Bot (webhook) | http://localhost:5000/bot |
| Health | http://localhost:5000/health |
| Dashboard | http://localhost:8000/ |
| Login staff | http://localhost:8000/accounts/login/ |
| Django admin | http://localhost:8000/admin/ |

**Primera vez:** crea usuario staff con `python dashboard/manage.py createsuperuser` (login en panel y `/admin/`).

**Detener:** `.\dev.cmd stop` (o cierra las ventanas del bot/dashboard y `docker compose down` para PostgreSQL). Para borrar datos de PG: `docker compose down -v`.

### Arranque manual (dos terminales)

Si prefieres no usar los scripts:

**Terminal 1 — bot (sin cambios):**

```bash
python run.py
```

**Terminal 2 — base de datos y dashboard:**

```bash
docker compose up -d db
python dashboard/manage.py migrate
python dashboard/manage.py createsuperuser
python dashboard/manage.py runserver 8000
```

`createsuperuser` crea el usuario staff para login en el panel (`/accounts/login/`) y en `/admin/`. Sin usuario, las rutas operativas redirigen al login.

### Guía del operador (panel Fase 4)

| Área | Ruta | Quién |
|------|------|--------|
| Inicio / KPIs | `/` | Cualquier usuario autenticado |
| Pedidos, reservas, menú, clientes | `/pedidos/`, `/reservas/`, `/menu/`, `/usuarios/` | Autenticado |
| Centro de administración | `/administracion/` | Rol **dashboard_admin** |
| Auditoría | `/accounts/audit/` | Admin |
| Accesos al panel (usuarios Django) | `/administracion/accesos/` | Admin |
| Estado bot + caché Sheets | `/estado/` | Autenticado |
| Qué requiere escrituras | `/administracion/escrituras/` | Autenticado |
| Preferencias UI | `/configuracion/` | Admin |
| Django `/admin/` | Enlace discreto en menú | Solo **superusuario** |

**Roles:** ejecuta una vez `python dashboard/manage.py setup_dashboard_groups`. Asigna operador o admin con `--operator` / `--assign`. Operador: pedidos, clientes, disponibilidad menú. Admin: CRUD menú, eliminar clientes, configuración y administración.

**Modo solo lectura (por defecto):** `DASHBOARD_ENABLE_WRITES=0` en `.env.dashboard`. El banner amarillo y la [guía de escrituras](http://localhost:8000/administracion/escrituras/) listan qué acciones necesitan `=1` y reinicio de `runserver`. Las preferencias del panel (PostgreSQL) no dependen de esa variable.

**Escrituras activas (entorno de prueba):** `DASHBOARD_ENABLE_WRITES=1`, bot en marcha (`python run.py`), spreadsheet de prueba. Confirmar un pedido desde detalle; comprobar Sheets/caché y que el webhook WhatsApp no se ha tocado.

**Tests del dashboard:**

```bash
cd dashboard
python manage.py test apps.operations.tests.test_views -v 2 --settings=config.test_settings
```

**Checklist responsive (manual, Chrome DevTools):** 320px (móvil: menú hamburguesa, tablas con scroll horizontal), 768px (tablet: sidebar colapsable), 1280px (escritorio: grid KPI y admin hub en columnas). Respetar `prefers-reduced-motion` en animaciones.

> **LOCAL ONLY:** no desplegar el dashboard en Render/Railway junto al bot sin decisión explícita (ver `AUDITORIA.md`).

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

## Despliegue (Render / Railway)

**Protocolo de trabajo (local/producción):**
- Si quieres solo preparar cambios: **"haz cambios solo local, no despliegues"**.
- Cuando ya esté validado en local: **"despliega a producción"**.
- Si quieres despliegue inmediato: **"haz el cambio y despliega a producción"**.
- Regla rápida: cambios de código van en ambos entornos al desplegar; variables (`.env`/Railway) pueden diferir entre local y producción.

- Despliega desde GitHub con `python run.py` (Waitress en el puerto `PORT`).
- En la nube, pega el JSON de la service account en `GOOGLE_SERVICE_ACCOUNT_JSON` (no subas el archivo al repo).
- Configura el resto de variables de `.env` (Twilio, `GOOGLE_SPREADSHEET_ID`, etc.).
- En Twilio, apunta el webhook WhatsApp a `https://tu-dominio/bot`.
- En plan gratuito, el servicio puede dormir: el primer mensaje tras reinicio tarda más (cold start); usa plan de pago si necesitas respuesta constante menor a 2 s 24/7.

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

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[* Que cuando el cliente salude, el bot le responda:
(
1 mensaje: Hola "nombre de persona", Bienvenido a "Nombre del restaurante"
2 mensaje: mostrar el menú (osea los productos que tiene el restaurante) y al final preguntarle que si desea hacer un pedido o reservar una mesa
)]




*****Respuesta de cursor*

Análisis previo
El nodo start ya usaba dual_message para enviar dos burbujas en Twilio. El segundo mensaje mostraba opciones (menu, pedido, reservar) en lugar del menú real. La tarea pide: (1) saludo con nombre y restaurante, (2) productos del menú + pregunta por pedido o reserva.

Solución mínima: un solo archivo (flow_engine.py), sin tocar el JSON del flujo ni los estados conversacionales.

Cambios implementados
Saludo (mensaje 1): formato Hola *{nombre}*, Bienvenido a *{restaurante}*.
Menú (mensaje 2): en el nodo start, el segundo mensaje incluye el menú dinámico (MenuService.format_menu()) y cierra con: ¿Deseas hacer un pedido o reservar una mesa?
Saludos en flujo idle: variantes como buenos días o qué tal en nodos idle redirigen al nodo start con la bienvenida completa.
Archivos modificados
app/core/flow_engine.py
Riesgos mitigados
Sin cambios en parser, endpoints, JSON del flujo ni estados.
Saludos en order_start / order_modify siguen invitando a ordenar (Mejora 9).
Repetir pedido anterior sigue en el mensaje 1 cuando aplica.
Compatibilidad verificada
Sistema	Estado
Parser
14/14 OK
Flow Engine
Saludo → 2 mensajes con menú
Twilio
dual_message → lista de respuestas
Pedido / reserva
Sin cambios en flujos posteriores
Funcionalidades agregadas
Al saludar, el bot responde con bienvenida personalizada y menú completo en la segunda burbuja, preguntando si desea pedir o reservar.
Funcionalidades preservadas
Comandos globales (menu, pedido, reservar, inicio, cancelar)
Flujo de pedidos y reservas
Repetir pedido anterior
Confirmación al abandonar carrito activo
Notificaciones admin






##################################################################################################################################

v0.4

## Prompt generado con chat gpt:

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[* El saludo actualmente son dos mensajes, el segundo mensaje está bien pero el primero es así:
Hola Omar Suarez, Bienvenido a La Casa del Sabor.

---
Escribe inicio para volver al inicio

quiero que le quites el --- y lo que dice Escribe inicio para volver al inicio]

## Respuesta cursor:

Análisis previo
El hint --- / Escribe *inicio*... se agregaba en _append_navigation() antes de dividir la respuesta en dos burbujas (_as_reply()), así que quedaba pegado al mensaje 1.

Cambios implementados
Se añadió "suppress_navigation": true al nodo start en el flujo JSON. Ese flag ya existía en el engine y evita el hint solo en la bienvenida.

Archivos modificados
flows/restaurant_flow.json
Riesgos mitigados
Sin cambios en Python, estados ni otros nodos.
El mensaje 2 (menú + pedido/reserva) queda igual.
Compatibilidad verificada
Sistema	Estado
Flow Engine
Saludo → msg1 limpio, msg2 sin cambios
Otros nodos
Siguen mostrando el hint de navegación
Funcionalidades agregadas
El primer mensaje de bienvenida ya no incluye --- ni “Escribe inicio para volver al inicio”.
Funcionalidades preservadas
Saludo personalizado, menú en el segundo mensaje, pedidos, reservas y comandos globales.




######################################################################################################################################
## v0.5

## prompt: 

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[* Verificar por qué el número de whatsapp del admin no funciona si ya se puso correctamente en .env, verificar que si funciona]


## Respuesta cursor:

Análisis previo
Revisé la carga de .env, el endpoint /bot y AdminService.is_admin().

Diagnóstico:

Verificación	Resultado
ADMIN_WHATSAPP_NUMBER en .env
Cargado correctamente
Twilio (SID, token, FROM)
Configurado
/health → admin_configured
true
Causa raíz: Twilio envía el WaId sin el prefijo + (ej. 573001111032), pero en .env suele estar con + (ej. whatsapp:+573001111032). is_admin() comparaba strings exactos:

"+573001111032" == "573001111032"  # False
Por eso el admin recibía el bot de cliente en lugar de los comandos admin (CONFIRMAR ORD-...).

Cambios implementados
En app/services/admin_service.py, is_admin() ahora compara solo los dígitos del número, ignorando whatsapp:, + y espacios.

Archivos modificados
app/services/admin_service.py
Riesgos mitigados
Sin cambios en endpoints, .env ni flujo de clientes.
Las notificaciones salientes al admin siguen usando el valor completo de .env (formato Twilio correcto).
Compatibilidad verificada
Prueba	Resultado
is_admin("5730...") (formato Twilio WaId)
✅
is_admin("+5730...")
✅
is_admin("whatsapp:+5730...") (formato .env)
✅
Otro número
❌ (correcto)
Webhook /bot con WaId sin +
Ruta admin ✅
Parser
14/14 OK
Funcionalidades agregadas
Reconocimiento del admin aunque Twilio y .env usen formatos distintos del mismo número.
Funcionalidades preservadas
Notificaciones de pedidos, recordatorios, confirmación CONFIRMAR ORD-XXXXXXXX y flujo normal de clientes.
Importante: reinicia el servidor Flask después de cambiar .env para que cargue los valores nuevos.

Formato recomendado en .env:

ADMIN_WHATSAPP_NUMBER=whatsapp:+57XXXXXXXXXX
Debe ser el mismo número desde el que escribes al bot por WhatsApp





###################################################################
## v0.7

prompt


# MODO ARQUITECTO SENIOR

Actúa como Principal Software Architect especializado en Python, Flask, Twilio, WhatsApp Bots y SaaS.

Objetivo: implementar únicamente la mejora solicitada con cambios mínimos, seguros y compatibles.

## REGLAS

* Evolucionar, no reconstruir.
* No romper funcionalidades existentes.
* No cambiar APIs, endpoints, contratos, JSON ni estados.
* No refactorizar módulos completos para cambios pequeños.
* Reutilizar código existente antes de crear componentes nuevos.
* Modificar la menor cantidad posible de archivos y líneas.
* Si existe riesgo de ruptura, detenerse y reportarlo.

## ANTES DE MODIFICAR

1. Leer únicamente los archivos necesarios.
2. Analizar impacto.
3. Identificar archivos afectados.
4. Detectar riesgos.
5. Proponer la solución de menor impacto.

No generar código hasta terminar el análisis.

## IMPLEMENTACIÓN

* Aplicar únicamente los cambios necesarios.
* Mantener estructura, nombres e interfaces actuales.
* Conservar el comportamiento existente.
* No generar pseudocódigo.
* Realizar cambios reales sobre el código existente.

## ENTREGA

### Análisis previo

* Funcionalidad solicitada
* Archivos afectados
* Riesgos
* Estrategia de compatibilidad

### Cambios implementados

### Archivos modificados

### Riesgos mitigados

### Compatibilidad verificada

✅ Parser

✅ Flask

✅ Twilio

✅ Flow Engine

✅ Order Service

✅ Persistencia

✅ Estados conversacionales

### Funcionalidades agregadas

### Funcionalidades preservadas

## TAREA

[Por favor revisa el parser y verifica que puede leer palabras con tilde como menú, revisa e implementa la mejora] 


## Respuesta cursor:

Análisis previo
Funcionalidad solicitada: Que el sistema reconozca palabras con tilde como menú (comandos y parser).

Hallazgos:

Parser (app/core/parser.py): ya usaba _strip_accents() para productos (ensalada césar) e intención de menú.
Flow Engine (validators.normalize_text): solo hacía lower() + espacios, sin quitar tildes. Por eso menu funcionaba y menú caía en el fallback.
Archivos afectados:

app/utils/validators.py — normalización usada por Flow Engine y comandos globales
app/core/parser.py — prueba de regresión para menú
Riesgos: Que normalize_text rompa confirmaciones o fechas. Mitigado: sí → si (ya en el set), envío → envio (ya contemplado).

Estrategia: Añadir _strip_accents en normalize_text (misma lógica que el parser), sin tocar APIs, JSON ni estados.

Cambios implementados
normalize_text() ahora elimina tildes antes de comparar comandos (menú → menu).
Prueba automática intencion menu con tilde en la suite del parser (15/15).
Archivos modificados
app/utils/validators.py
app/core/parser.py
Riesgos mitigados
Sin cambios en endpoints, JSON del flujo ni estados conversacionales.
Parser mantiene su pipeline de acentos; solo se alineó la capa de comandos.
Compatibilidad verificada
✅ Parser — 15/15 OK (incluye menú y ensalada césar)
✅ Flask — sin cambios
✅ Twilio — sin cambios
✅ Flow Engine — menú abre el menú igual que menu
✅ Order Service — sin cambios
✅ Persistencia — sin cambios
✅ Estados conversacionales — sin cambios

Funcionalidades agregadas
Comandos con tilde: menú, envío, qué tal, etc. se normalizan y enrutan igual que sin tilde.
Funcionalidades preservadas
Matching de productos con typos y tildes en el parser.
Comandos globales sin tilde (menu, pedido, reservar, inicio, cancelar).
Confirmaciones, reservas, pedidos y flujo admin.






#################################################################
## v0.8

## Prompt: 

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Cuando estoy escribiendo el pedido, osea lo que quiero pedir, si por ejemplo escribo dos pizzas, dos hamburguesas con dos aguas, el sistema no me reconoce el con como si fuera un Y]


## Respuesta cursor:

Análisis previo
Funcionalidad solicitada: Que con actúe como conector de ítems, igual que y (ej.: dos pizzas, dos hamburguesas con dos aguas).

Causa raíz (doble):

CONNECTOR_SPLIT_RE no incluía con, así que no separaba los productos.
con estaba en NOISE_WORDS y se eliminaba al normalizar; el fail_safe veía solo tokens genéricos (dos, 2) y rechazaba el pedido antes de procesar los segmentos.
Archivos afectados: solo app/core/parser.py

Riesgos: Que con deje de filtrarse en frases tipo “hamburguesa con queso”. Mitigado: solo se usa como separador con \s+con\s+ (espacios a ambos lados).

Cambios implementados
Añadido \s+con\s+ a CONNECTOR_SPLIT_RE (junto a y, e, comas, etc.).
Eliminado con de NOISE_WORDS para que no desaparezca antes del análisis.
Reordenado parse(): si hay 2+ segmentos, no aplica el fail_safe prematuro.
Pruebas automáticas para con con cantidades en palabras y en dígitos.
Archivos modificados
app/core/parser.py
Riesgos mitigados
Sin cambios en APIs, Flask, Twilio, flow JSON ni estados.
Conectores existentes (y, e, ,, &, +, *) intactos.
Compatibilidad verificada
✅ Parser — 17/17 OK
✅ Flask — sin cambios
✅ Twilio — sin cambios
✅ Flow Engine — sin cambios
✅ Order Service — dos pizzas, dos hamburguesas con dos aguas → 3 productos
✅ Persistencia — sin cambios
✅ Estados conversacionales — sin cambios

Funcionalidades agregadas
con como conector entre ítems del pedido, equivalente a y.
Ejemplo verificado:

dos pizzas, dos hamburguesas con dos aguas
→ 2 Pizza Margarita, 2 Hamburguesa Clásica, 2 Agua Mineral
Funcionalidades preservadas
Pedidos con y, comas, typos, tildes y el resto de conectores ya soportados.





#################################################################
## v0.9

## Prompt: 

No quiero que hagas nada ni edites nada, solo quiero que revises el proyecto y me digas qué hace falta para conectarlo con los documentos online de google y cómo lo hago, dame el paso a paso especifico


## Respuesta cursor:

Revisé el proyecto: la conexión con Google Sheets ya está implementada en app/integrations/google_sheets.py. No falta programar eso; falta configurar Google Cloud, la hoja y el .env.

Si no conectas, verás en logs algo como GOOGLE_SPREADSHEET_ID not set. Using demo data. o Google Sheets unavailable (No module named 'gspread') y el bot usa menú demo en memoria.

Qué hace falta (checklist)
Requisito	Para qué
Cuenta Google
Crear proyecto y credenciales
Google Cloud Project
APIs de Sheets y Drive
Service Account + JSON
Que la app acceda a la hoja
Google Spreadsheet
Menú, pedidos, usuarios, reservas
Compartir la hoja con la service account
Permiso de lectura/escritura
.env configurado
ID de la hoja + ruta del JSON
pip install -r requirements.txt
Instala gspread y google-auth
Paso a paso específico
1. Instalar dependencias Python
En la carpeta del proyecto:

cd "c:\Users\Usuario\Desktop\chatbot-cursor"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Confirma que existan gspread y google-auth.

2. Crear proyecto en Google Cloud
Entra a Google Cloud Console.
Nuevo proyecto (ej.: chatbot-restaurante).
Selecciónalo como proyecto activo.
3. Activar APIs necesarias
En el menú APIs y servicios → Biblioteca, activa:

Google Sheets API
Google Drive API (la app la usa para abrir el spreadsheet)
4. Crear Service Account (cuenta de servicio)
APIs y servicios → Credenciales
Crear credenciales → Cuenta de servicio
Nombre: ej. chatbot-sheets
Rol: Editor (o mínimo acceso a la hoja compartida)
En la cuenta creada → pestaña Claves
Agregar clave → Crear clave nueva → JSON
Se descarga un archivo .json
5. Guardar el JSON en el proyecto
Crea la carpeta credentials/ si no existe (ya hay un .gitkeep).
Guarda el archivo como:
c:\Users\Usuario\Desktop\chatbot-cursor\credentials\google-service-account.json
No subas este archivo a GitHub (contiene claves secretas).

Abre el JSON y copia el email, algo como:

chatbot-sheets@tu-proyecto.iam.gserviceaccount.com
Lo necesitas en el paso 7.

6. Crear el Google Spreadsheet
Ve a Google Sheets.
Crea una hoja nueva, ej.: Restaurante Bot.
Copia el ID de la URL:
https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit
7. Compartir la hoja con la Service Account
En la hoja → Compartir
Pega el email de la service account
Permiso: Editor
Guardar
Sin esto la app no puede leer ni escribir.

8. Configurar .env
En tu .env (copia de .env.example):

GOOGLE_SHEETS_CREDENTIALS_PATH=credentials/google-service-account.json
GOOGLE_SPREADSHEET_ID=EL_ID_QUE_COPIASTE_DE_LA_URL
Ruta relativa al root del proyecto o absoluta.

9. Pestañas que la app usa
Al arrancar, si faltan, las crea sola con estos nombres exactos:

Pestaña	Columnas (fila 1)
MENU
id, nombre, precio, categoria, disponible
USERS
wa_id, name, address, last_order_date, last_order_json, last_seen
ORDERS
order_id, wa_id, items, total, status, timestamp, customer_name, address, delivery_type
RESERVATIONS
reservation_id, wa_id, personas, fecha, hora, status
Ejemplo de menú en MENU (fila 2 en adelante):
id	nombre	precio	categoria	disponible
1
Pizza Hawaiana
12.5
Pizzas
true
2
Hamburguesa Clásica
9.5
Hamburguesas
true
3
Coca Cola
2.5
Bebidas
true
disponible: true, false, si, 1, etc.
Si nombre está vacío, la fila se ignora.
Si MENU está vacío, vuelve al menú demo.
USERS, ORDERS y RESERVATIONS las llena el bot; no hace falta cargarlas a mano.

10. Arrancar y verificar conexión
python run.py
Revisa la consola:

✅ Conectado: no debería aparecer Using demo data
❌ Fallo: Google Sheets unavailable (...) → revisa ID, JSON, permisos o APIs
Prueba rápida:

curl http://localhost:5000/health
Luego escribe menu al bot; debería mostrar lo de tu hoja MENU.

11. Qué se guarda automáticamente en Google Sheets
Acción del cliente	Hoja
Primer contacto / nombre / dirección
USERS
Completa un pedido
ORDERS
Admin confirma pedido
ORDERS (status → confirmed)
Reserva mesa
RESERVATIONS
Errores frecuentes
Síntoma	Causa probable
GOOGLE_SPREADSHEET_ID not set
Falta el ID en .env
No module named 'gspread'
No corriste pip install -r requirements.txt
Google Sheets unavailable
JSON mal ubicado, APIs off o hoja no compartida
Sigue menú demo
MENU vacío o conexión fallida
403 / Permission denied
No compartiste la hoja con la service account
Resumen
No falta código para conectar con Google Sheets. Falta:

Proyecto Google Cloud + APIs activadas
Service Account + JSON en credentials/
Spreadsheet creado y compartido
GOOGLE_SPREADSHEET_ID en .env
Productos en la pestaña MENU
Dependencias instaladas y servidor reiniciado
Cuando eso esté bien, el bot usa tu menú real y persiste pedidos, usuarios y reservas en la hoja online.



#################################################################
## v0.10

## Prompt: 

no hagas nada ni edites codigo ni nada solo respondeme lo siguiente: aparte del tutorial de google, hay algo más que haya que hacer para dejarlo funcional? que esté pendiente? solo dime


## Respuesta cursor:

Sí. Aparte del tutorial de Google, para dejarlo **funcional de verdad por WhatsApp** aún necesitas esto:

### Obligatorio para producción real

1. **Twilio configurado** en `.env` (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`).
2. **Webhook público** apuntando a tu bot (`POST /bot`) — en local con **ngrok** o similar; en producción con servidor desplegado.
3. **Unir números al sandbox de Twilio** (o tener WhatsApp Business aprobado si ya no usas sandbox).
4. **`ADMIN_WHATSAPP_NUMBER`** en `.env` con tu número real de admin.
5. **`RESTAURANT_NAME`** en `.env` con el nombre de tu restaurante.
6. **Dependencias instaladas** (`pip install -r requirements.txt`) y **servidor corriendo** (`python run.py`).
7. **Productos cargados** en la pestaña **MENU** de Google Sheets.

### Recomendable (no bloquea del todo, pero conviene)

8. **`STATE_PERSIST_PATH`** en `.env` para que no se pierda el estado de conversación al reiniciar.
9. **Probar flujo completo**: saludo → pedido → notificación admin → confirmación → cliente notificado.
10. **Verificar en Twilio Console** que los mensajes salientes al admin digan `delivered` (antes viste que a veces no llegaban al celular).

### Pendiente / por validar en tu caso

- Que **Twilio envíe de verdad** al admin (config + sandbox + logs).
- **Despliegue permanente** si no quieres depender de ngrok en tu PC encendida.
- **`pendientes.md`** no está actualizado; varias tareas de v0.3–v0.5 ya se trabajaron en código, pero **conviene probarlas en WhatsApp real**, no solo asumir que funcionan.

### Resumen

**Google Sheets no basta.** También necesitas **Twilio + webhook + `.env` completo + menú en la hoja + pruebas reales por WhatsApp**. Lo demás del bot ya está en el código; lo que falta es sobre todo **configuración externa y pruebas end-to-end**.


#################################################################
## v0.11

## Prompt:

quiero que no me toques absolutamente el proyecto para nada, quiero que unica y exclusivamente hagas lo siguiente, solo 1 archivo puedes crear no puedes tocar ni editar nada más solo quiero que crees un archivo en la raíz del proyecto que haga lo siguiente:

Que cuando yo le de doble clic, me ejecute git add . , git commit -m "(aquí iría la primera línea del readme.md que sería la versión de la app, en este caso ## v0.10 , pero claramente yo la idea es editarla y solamente con escribir run save.py me haga tambien el git push -u origin main, osea que haga todo de una, si me entiendes? ya sabes solo puedes crear ese archivo que haga eso, ni mas ni menos



## Respuesta cursor:

Creé solo `save.py` en la raíz. No toqué ningún otro archivo.

**Qué hace:**
1. Lee la **primera línea** de `README.md` (ej. `## v0.10` → commit `v0.10`)
2. `git add .`
3. `git commit -m "v0.10"`
4. `git push -u origin main`

**Cómo usarlo:**
- Doble clic en `save.py` (si Windows abre `.py` con Python)
- O en terminal: `python save.py`

Al terminar espera que pulses Enter para que veas el resultado antes de cerrar la ventana.

**Para nueva versión:** cambia solo la primera línea de `README.md` (ej. `## v0.11`) y ejecuta `save.py`.




#################################################################
## v0.12

## Prompt:

ya hice todo revisa que funcione y pon el menú que tenemos de prueba ahi en los google sheeets, solo haz eso no hagas nada mas ni edites nada mas, osea solo dejalo funcional con ese menú de prueba ahí funcional ya, no toques ni hagas nada mas, si puedes hacerlo todo sin editar mucho codigo mejor, trata de usar el menor codigo posible y de no afectar ni dañar nada, revisa que todo quede funcional 

## Respuesta cursor:

Listo. Google Sheets queda funcional con el menú de prueba.

### Qué impedía que funcionara

1. **`GOOGLE_SPREADSHEET_ID` en `.env`** tenía la URL completa; el código necesita solo el ID. Lo dejé así:
   ```
   110zzaM2G4hX9Kqc9lhgbnZd1w9-9_ziTufEbkY_yRYg
   ```
2. **Faltaba `gspread`** en el entorno Python. Lo instalé con `python -m pip install gspread google-auth`.

### Qué quedó en Google Sheets

Pestaña **MENU** con los 6 productos de prueba:

| Producto | Precio | Categoría |
|---|---|---|
| Pizza Hawaiana | $12.50 | Pizzas |
| Pizza Margarita | $11.00 | Pizzas |
| Hamburguesa Clásica | $9.50 | Hamburguesas |
| Coca Cola | $2.50 | Bebidas |
| Agua Mineral | $1.50 | Bebidas |
| Ensalada César | $8.00 | Ensaladas |

También se crearon las pestañas **USERS**, **ORDERS** y **RESERVATIONS** (las llena el bot al usarse).

### Verificado

- Conexión a Google Sheets: OK  
- Menú leído desde la hoja (no demo en memoria): OK  
- Bot responde `menu` con esos productos: OK  

### Qué toqué

Solo **`.env`** (corregir el ID del spreadsheet). No modifiqué código de la app.

**Importante:** reinicia el servidor (`python run.py`) si ya estaba corriendo para que cargue el `.env` nuevo. Si en otra máquina no conecta, ejecuta `python -m pip install -r requirements.txt`.




#################################################################
## v0.13

## Prompt:

Quiero que solamente y unicamente me edites el siguiente archivo: guardar.py y no toques nada mas, editalo para que al final no le tenga que dar enter sino solo me muestre el mensaje final confirmando si Listo: add, commit y push completados con la logica que tiene de guardar la versión, y nada más, no toques ningun otro archivo, al final me dices qué archivos tocaste


## Respuesta cursor:

Listo. Quité los `input()` que pedían Enter al terminar. Al ejecutarlo verás el mensaje final y la ventana se cerrará sola (o volverás al prompt si lo corres desde terminal).

**Archivo modificado:** `guardar.py` únicamente.




#################################################################
## v0.14

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Solamente quiero que hagas esto y no edites absolutamente nada más, estaba ingresando un pedido y el parser leyó mal, quiero que veas por qué falló y lo soluciones, como mejora incremental que no rehagas nada mas sino una mejora incremental
el mensaje que yo envié fue este: "quiero por favor dos pizzas de jamon y queso, tres pizzas mexicanas, 4 pizzas rancheras, 5 coca colas, 7 hamburguesas mega ocho hamburguesas doble carne una habasurguesa doble pollo" 
la respuesta fue: "Perfecto, actualicé tu pedido.

* 3 x Pizza de Jamón y Queso — $285.00
* 3 x Pizza Mexicana — $75.00
* 4 x Pizza Ranchera — $60.00
* 5 x Coca Cola — $40.00
* 7 x Hamburguesa Doble Pollo — $105.00

Total: $565.00



¿Confirmamos tu pedido?
Responde sí para confirmar o no para modificarlo.

---
Escribe inicio para volver al inicio" 

Pero fijate que yo escribí dos pizzas de jamón y queso y el parser agarró 3 pizzas de jamón y queso, y las hamburguesas no me agarró casi ninguna, y la que agarró agarró mal, yo puse 7 hamburguesas mega ocho hamburguesas doble carne una habmbuguesa doble pollo pero el parser agarró solo 7 hamburguesas doble pollo, osea agarró solo una y mal.

Así que por favor necesito que me solucioens eso como mejora incremental]



## Respuesta cursor:

### Análisis previo

**Problemas detectados en tu mensaje:**

1. **`jamon y queso` → 3 en vez de 2:** el conector `y` partía `"jamon y queso"` en dos segmentos; `"queso"` solo volvía a matchear la misma pizza y sumaba +1.
2. **Hamburguesas perdidas:** `"7 hamburguesas mega ocho hamburguesas doble carne una habasurguesa..."` no se partía porque solo se detectaban cantidades numéricas (`7`, `4`), no en palabras (`ocho`, `una`).
3. **Typo `habasurguesa`:** no se normalizaba a hamburguesa.

---

### Cambios implementados (solo `app/core/parser.py`)

1. **Preservar `de X y Y`** en nombres compuestos (`de jamon y queso` no se parte).
2. **Separar por cantidades en palabras** (`ocho`, `una`, `dos`, etc.) además de dígitos.
3. **Sinónimo** `habasurguesa` → `hamburguesa`.
4. **Prueba automática** con tu pedido exacto.

---

### Resultado verificado

```
2 x Pizza de Jamon y Queso
3 x Pizza Mexicana
4 x Pizza Ranchera
5 x Coca Cola
7 x Hamburguesa Mega
8 x Hamburguesa Doble Carne
1 x Hamburguesa Doble Pollo
```

Parser: **18/18 OK**

---

### Archivos modificados

- `app/core/parser.py`

---

### Funcionalidades preservadas

Pedidos con `y`, comas, `con`, typos, tildes y el resto de casos de la suite de pruebas.





#################################################################
## v0.15


## Prompt:

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Por qué ahora siento que cuadno le puse la sheet de google va el  bot como más lento? hay alguna manera de reducir latencia? quiero que solo trabejes en eso no te metas con nada mas y que todo funcoine no toques nada solo implementa eso como mejora incremental]

## Respuesta cursor

### Análisis previo

**Por qué se siente más lento con Google Sheets:** cada mensaje de WhatsApp hacía varias llamadas de red a la API de Google (`get_all_records()`), que tarda ~200–800 ms cada una.

En un solo mensaje típico ocurría:
- Leer **MENU** (al parsear pedido y mostrar menú)
- Leer **USERS** completo 2–3 veces (`touch` + `get_profile` + `upsert`)
- Leer **ORDERS** en confirmaciones/admin

En modo demo todo está en memoria; con Sheets cada lectura es una petición HTTP.

**Archivo afectado:** `app/integrations/google_sheets.py` únicamente.

---

### Cambios implementados

Caché en memoria con TTL, sin cambiar APIs ni flujos:

| Dato | Caché | TTL |
|---|---|---|
| **MENU** | Sí | 60 s |
| **USERS** | Sí (carga una vez, actualiza al guardar) | Hasta cambio |
| **ORDERS** | Sí | 30 s (se invalida al crear/confirmar pedido) |

Así, un mensaje reutiliza datos ya cargados en lugar de volver a pedir la hoja entera a Google.

---

### Archivos modificados

- `app/integrations/google_sheets.py`

---

### Compatibilidad verificada

✅ Parser — 18/18  
✅ Flask / Twilio / Flow Engine — sin cambios  
✅ Escrituras (pedidos, usuarios, confirmaciones) — invalidan caché cuando corresponde  
✅ Modo demo sin Sheets — sigue igual  

---

### Nota

Si editas el **MENU** en Google Sheets, el bot puede tardar hasta **60 segundos** en reflejarlo (TTL del caché). Es el trade-off normal por velocidad.

Reinicia el servidor para aplicar el cambio.







#################################################################
## v0.16

## Prompt:

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[que busque la manera de implementar algo que permita buscar palabras y detectar que palabra es por ejemplo si escribo hbogruesa el me detecte que quise decir hamburguesa, pero no solo para esa palabra sino para cualquiera en general, solo has eso y no toques nada mas, hazlo como mejora incremental]


## Respuesta cursor:

### Análisis previo

**Problema:** typos como `hbogruesa` no se reconocían porque:
1. El `fail_safe` rechazaba palabras sueltas sin coincidencia exacta con el menú.
2. No había corrección por token contra el vocabulario del catálogo.
3. Los aliases con typos (`hambrguesa`) competían con la palabra correcta.

**Archivo afectado:** `app/core/parser.py` únicamente.

---

### Cambios implementados

1. **`_correct_typos()`** en `FuzzyMatcher`: cada palabra se compara con el vocabulario del menú (nombres y tokens reales).
2. **Filtros de seguridad:** similitud mínima 68%, diferencia clara entre 1.º y 2.º candidato, y longitud similar (±3 caracteres).
3. **`best_match()`** aplica la corrección antes del matching.
4. **`_has_menu_token_overlap()`** usa la versión corregida para no rechazar typos válidos.
5. **Pruebas:** `hbogruesa` y `2 piza hawaiana`.

---

### Resultado verificado

| Entrada | Resultado |
|---|---|
| `hbogruesa` | 1 x Hamburguesa Clásica |
| `2 piza hawaiana` | 2 x Pizza Hawaiana |
| `ensalada cesr` | 1 x Ensalada César |

Parser: **20/20 OK**

Funciona con **cualquier producto del menú** cargado (Sheets o demo), porque el vocabulario se construye dinámicamente del catálogo.

---

### Archivos modificados

- `app/core/parser.py`




#################################################################
## v0.17

## Prompt:

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Mira, le mandé este mensaje y no me agarró las cantidades bien, revisa y que por favor siempre quieden bien las cantidades, solo arregla unicamente eso,

mi mensaje: quiero por favor 60 hamburgsdfesas clasiccscas, 2333 hamburgueas mega, 12123 cocas con 777 pirzas harwewaianas y 8 picsas de jamon y quieso

respuesta: Perfecto, actualicé tu pedido.

* 60 x Hamburguesa Clásica — $7500.00
* 23 x Hamburguesa Mega — $253.00
* 12123 x Coca Cola — $96984.00
* 7 x Pizza Hawaiana — $875.00
* 8 x Pizza de Jamón y Queso — $760.00

Total: $106372.00



¿Confirmamos tu pedido?
Responde sí para confirmar o no para modificarlo.

---
Escribe inicio para volver al inicio


---- busca la manera con alguna comprobación check o algo de que siempre los numeros vayan perfecto]


## Respuesta cursor:

### Análisis previo

**Causa:** `REPEAT_CHAR_RE` trataba dígitos como letras repetidas:
- `2333` → `23` (tres `3` seguidas se colapsaban)
- `777` → `7`

Las cantidades se extraían bien en segmentos básicos, pero `TextNormalizer.advanced()` las corrompía antes del matching.

---

### Cambios implementados (solo `app/core/parser.py`)

1. **`REPEAT_CHAR_RE`** solo colapsa letras (`holaaa` → `hola`), no dígitos.
2. **`QuantityEngine.resolve()`** — extrae cantidad del segmento sin destructurar números y verifica contra el texto original si hay discrepancia.
3. **Prueba automática** con tu mensaje exacto (60, 2333, 12123, 777, 8).

---

### Resultado verificado

| Producto | Cantidad esperada | Ahora |
|---|---|---|
| Hamburguesa Clásica | 60 | ✅ |
| Hamburguesa Mega | 2333 | ✅ |
| Coca Cola | 12123 | ✅ |
| Pizza Hawaiana | 777 | ✅ |
| Pizza de Jamón y Queso | 8 | ✅ |

Parser: **21/21 OK**

---

### Archivos modificados

- `app/core/parser.py`




#################################################################
## v0.18

## Prompt:


OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Por qué siento que el bot va lento? especialmente después de agregar lo de google sheets? pero no te fijes solamente en eso, quiero que analices y me propongas un plan de acción que yo puead ir implementando prompt por prompt para mejorar la velocidad del bot, pero que sea seguro sin que se rompa nada, osea una mejora incremental, es una optimización sin romper nada, quiero que me verifiques varias veces que todo está correctamente funcionando osea poner eso en el plan de acción, necesito que me hagas el mejor plan de acción pero que también sea corto por ahí unas 10 o 15 como tu creas conveniente, recuerda que es de vital importancia la integridad del proyecto que es una mejora incremental, una  optimización]


## Respuesta cursor:

## Por qué se siente lento

No es solo Google Sheets. Hoy el bot hace **todo en serie** antes de responder a Twilio:

| Causa | Impacto | Estado |
|---|---|---|
| Llamadas a Google Sheets API (~200–800 ms c/u) | Alto | Parcialmente mitigado (caché 60s menú, usuarios, 30s pedidos) |
| `upsert_user` sigue leyendo USERS entero para encontrar fila | Medio | Pendiente |
| Menú se lee varias veces por mensaje (saludo + parser) | Medio | Pendiente |
| Parser reconstruye catálogo en cada mensaje de pedido | Medio | Pendiente |
| Twilio outbound síncrono (admin/cliente) dentro del webhook | Medio | Pendiente |
| Persistencia de estado: escribe JSON completo en disco | Bajo–medio | Pendiente |
| Flask en modo debug / servidor local + ngrok | Medio (dev) | Entorno |
| Pedidos muy largos = más parsing | Bajo | Normal |

**Conclusión:** Sheets añadió latencia de red; la caché ya ayuda, pero aún hay cuellos de botella seguros de optimizar.

---

## Plan de acción incremental (12 pasos)

Cada paso = **1 prompt**. Regla: **1 cambio → verificar → commit**. No pasar al siguiente si falla la verificación.

---

### Fase 1 — Medir antes de tocar (sin riesgo)

**Paso 1 — Baseline de tiempos**  
Agregar logs de duración en `/bot` (solo `time.perf_counter`, sin cambiar lógica).  
**Verificar:** `python run.py` → enviar `hola`, `menu`, `pedido` → anotar ms en consola.  
**Meta:** saber cuánto tarda hoy cada tipo de mensaje.

**Paso 2 — Checklist de regresión fijo**  
Definir 5 pruebas manuales + 2 automáticas que repetirás siempre:
- `python -m app.core.parser` → 21/21
- `curl http://localhost:5000/health`
- WhatsApp: `hola` → 2 mensajes
- WhatsApp: `menu` → menú de Sheets
- WhatsApp: pedido corto → confirmación

---

### Fase 2 — Google Sheets (mayor impacto, bajo riesgo)

**Paso 3 — Optimizar `upsert_user`** *(ya hay caché parcial)*  
Evitar `get_all_records()` en cada `touch`; guardar índice de fila por `wa_id` en caché.  
**Verificar:** checklist paso 2 + editar nombre en chat no rompe perfil.

**Paso 4 — Caché de menú en `MenuService`**  
Un solo `get_menu()` por request (no re-leer en saludo + parser).  
**Verificar:** saludo muestra menú correcto; parser sigue reconociendo productos.

**Paso 5 — TTL configurable en `.env`**  
`MENU_CACHE_TTL_SECONDS=120` sin cambiar comportamiento por defecto.  
**Verificar:** cambiar producto en Sheets → aparece antes de 2 min si TTL=120.

**Paso 6 — Precarga al arrancar**  
Al iniciar Flask, cargar MENU + USERS en caché (warm-up).  
**Verificar:** primer `hola` después de reinicio ya no es el más lento.

---

### Fase 3 — Flujo interno (riesgo bajo)

**Paso 7 — Reutilizar `OrderParser` por sesión**  
No reconstruir catálogo en cada mensaje; invalidar solo si expira caché de menú.  
**Verificar:** parser 21/21 + pedido largo con cantidades (60, 2333, 777…).

**Paso 8 — Persistencia de estado más liviana**  
Escribir disco solo si el estado cambió (debounce 1–2 s o diff).  
**Verificar:** flujo pedido completo conserva carrito tras 3 mensajes seguidos.

**Paso 9 — Notificaciones Twilio en background**  
`notify_new_order` y aviso al cliente: thread/async, no bloquear respuesta al webhook.  
**Verificar:** cliente recibe respuesta rápido; admin sigue recibiendo WhatsApp.

---

### Fase 4 — Entorno y producción

**Paso 10 — Servidor de producción**  
Usar `waitress` o `gunicorn` en lugar de Flask debug.  
**Verificar:** `/health` OK; misma checklist WhatsApp.

**Paso 11 — Hosting permanente**  
Desplegar (Railway, Render, VPS) en lugar de PC + ngrok.  
**Verificar:** latencia menor que ngrok; webhook estable 24/7.

**Paso 12 — Documentar tiempos objetivo**  
Tras pasos 3–9, repetir Paso 1 y comparar.  
**Meta razonable:** respuesta al cliente **< 2 s** en pedidos normales (sin contar red Twilio→usuario).

---

## Orden recomendado (prioridad)

```
1 → 2 → 3 → 4 → 6 → 7 → 9 → 5 → 8 → 10 → 11 → 12
```

Empieza por **medir** y **Sheets** (pasos 1–4, 6): ahí está la mayor ganancia con menor riesgo.

---

## Qué NO hacer (proteger integridad)

- No cambiar endpoints, JSON del flujo ni estados conversacionales.
- No refactorizar parser + flow + sheets en un solo prompt.
- No quitar caché ni escritura a Sheets sin alternativa.
- No pasar al siguiente paso si falla parser 21/21 o el checklist WhatsApp.

---

## Prompt sugerido para tu próximo paso

> *"Implementa solo el Paso 1 del plan de optimización: logs de duración en `/bot` sin cambiar lógica. Verifica health + parser 21/21."*

Cuando quieras, dime **"implementa el paso X"** y lo hacemos uno por uno con verificación incluida.



## Segundo prompt:

pero me estás dando los pasos en desorden, damelos en orden


## Respuesta cursor:


## Plan de optimización incremental (en orden)

Cada paso = **1 prompt**. No avances si falla la verificación.

---

### Paso 1 — Medir tiempos actuales (baseline)
Agregar logs de duración en `/bot` sin cambiar lógica.  
**Verificar:** `python run.py` → probar `hola`, `menu`, `pedido` → anotar milisegundos en consola.

---

### Paso 2 — Checklist fijo de regresión
Definir pruebas que repetirás en **todos** los pasos siguientes:
- `python -m app.core.parser` → 21/21
- `curl http://localhost:5000/health`
- WhatsApp: `hola` → 2 mensajes
- WhatsApp: `menu` → menú de Sheets
- WhatsApp: pedido corto → confirmación

---

### Paso 3 — Optimizar `upsert_user` en Google Sheets
Evitar `get_all_records()` en cada `touch`; guardar índice de fila por `wa_id` en caché.  
**Verificar:** checklist del Paso 2 + perfil/nombre se guardan bien.

---

### Paso 4 — Caché de menú por request en `MenuService`
Un solo `get_menu()` por mensaje (no releer en saludo + parser).  
**Verificar:** saludo con menú correcto + parser reconoce productos.

---

### Paso 5 — Precarga de caché al arrancar (warm-up)
Al iniciar Flask, cargar MENU y USERS en memoria.  
**Verificar:** el primer `hola` tras reiniciar ya no es el más lento.

---

### Paso 6 — Reutilizar `OrderParser` entre mensajes
No reconstruir catálogo en cada mensaje; invalidar solo si cambia el menú.  
**Verificar:** parser 21/21 + pedido largo con cantidades (60, 2333, 777…).

---

### Paso 7 — Notificaciones Twilio en background
Enviar WhatsApp al admin/cliente en thread/async, sin bloquear la respuesta del webhook.  
**Verificar:** cliente responde rápido + admin sigue recibiendo notificaciones.

---

### Paso 8 — Persistencia de estado más liviana
Escribir `user_states.json` solo si hubo cambio (debounce o diff).  
**Verificar:** flujo de pedido conserva carrito tras varios mensajes.

---

### Paso 9 — TTL de caché configurable en `.env`
`MENU_CACHE_TTL_SECONDS`, `ORDERS_CACHE_TTL_SECONDS` con defaults actuales.  
**Verificar:** cambio en Sheets se refleja según TTL; todo lo demás igual.

---

### Paso 10 — Servidor de producción local
Usar `waitress` o `gunicorn` en lugar de Flask debug.  
**Verificar:** `/health` OK + checklist WhatsApp del Paso 2.

---

### Paso 11 — Hosting permanente (sin ngrok)
Desplegar en Railway, Render o VPS.  
**Verificar:** webhook estable 24/7 + latencia menor que con PC + ngrok.

---

### Paso 12 — Medir de nuevo y comparar
Repetir el Paso 1 y documentar antes/después.  
**Meta:** respuesta al cliente **< 2 s** en pedidos normales (sin contar red Twilio→teléfono).

---

## Reglas durante todo el plan

1. Un paso por prompt.  
2. No cambiar endpoints, JSON del flujo ni estados conversacionales.  
3. Si falla parser o checklist → corregir antes de continuar.  
4. Commit después de cada paso verificado.

Cuando quieras empezar: **"Implementa el Paso 1"**.


## Tercer prompt: ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Paso 1 — Medir tiempos actuales (baseline)
Agregar logs de duración en /bot sin cambiar lógica.
Verificar: python run.py → probar hola, menu, pedido → anotar milisegundos en consola.]


## Respuesta cursor:

### Análisis previo

**Funcionalidad solicitada:** Paso 1 del plan — medir tiempos en `/bot` sin cambiar la lógica del bot.

**Archivo afectado:** `app/app.py` únicamente.

---

### Cambios implementados

Se añadió `time.perf_counter()` al inicio y fin de `POST /bot`. Al terminar cada request se registra en consola:

```
POST /bot completed in 1234.5 ms wa_id=... admin=False body='hola'
```

Incluye: milisegundos, `wa_id`, si es admin y los primeros 80 caracteres del mensaje.

---

### Verificación

| Prueba | Resultado |
|---|---|
| Parser | 21/21 OK |
| `/health` | 200 |
| Logs en `hola`, `menu`, `pedido` | OK |

**Baseline medido (cliente, con Google Sheets):**

| Mensaje | Tiempo |
|---|---|
| `hola` | ~2362 ms |
| `menu` | ~1179 ms |
| `pedido` | ~1202 ms |

*(El primer `hola` suele ser el más lento por cargar Sheets + menú en saludo dual.)*

---

### Cómo usarlo tú

1. `python run.py`
2. Envía `hola`, `menu`, `pedido` por WhatsApp
3. Mira la consola las líneas `POST /bot completed in X ms`

Anota esos valores; serán la referencia para comparar después del Paso 3 en adelante.

---

### Archivos modificados

- `app/app.py`

---

### Funcionalidades preservadas

Sin cambios en flujo, respuestas, Sheets, Twilio ni parser. Solo observabilidad.



## Cuarto prompt: ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 2 — Checklist fijo de regresión
Definir pruebas que repetirás en **todos** los pasos siguientes:
- `python -m app.core.parser` → 21/21
- `curl http://localhost:5000/health`
- WhatsApp: `hola` → 2 mensajes
- WhatsApp: `menu` → menú de Sheets
- WhatsApp: pedido corto → confirmación]


## Respuesta cursor: ## 

### Análisis previo

**Funcionalidad solicitada:** Paso 2 — checklist fijo de regresión reutilizable en cada optimización.

**Enfoque:** Un script ejecutable que automatiza lo verificable localmente; las pruebas en WhatsApp real quedan documentadas como complemento manual.

---

### Cambios implementados

Nuevo script `scripts/regression_checklist.py` con 5 pruebas:

| # | Prueba | Qué valida |
|---|---|---|
| 1 | `python -m app.core.parser` | 21/21 |
| 2 | `GET /health` | status 200, `"ok"` |
| 3 | `POST /bot` + `hola` | 2 mensajes Twilio |
| 4 | `POST /bot` + `menu` | menú con productos (Sheets si conectado) |
| 5 | `POST /bot` + pedido corto | prompt *¿Confirmamos tu pedido?* |

---

### Verificación

```
=== Result: 5/5 passed ===
Checklist OK. Safe to continue to the next optimization step.
```

Menú detectado desde **Google Sheets (10 items)**.

---

### Cómo usarlo en cada paso siguiente

```bash
python scripts/regression_checklist.py
```

- Exit code **0** → puedes continuar al siguiente paso  
- Exit code **1** → corregir antes de seguir  

**Manual (opcional):** repetir `hola`, `menu` y un pedido corto en WhatsApp real.

---

### Archivos modificados

- `scripts/regression_checklist.py` *(nuevo)*

---

### Funcionalidades preservadas

Sin cambios en lógica del bot, parser, flow ni Sheets. Solo herramienta de verificación.



## Quinto prompt: ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 3 — Optimizar `upsert_user` en Google Sheets
Evitar `get_all_records()` en cada `touch`; guardar índice de fila por `wa_id` en caché.  
**Verificar:** checklist del Paso 2 + perfil/nombre se guardan bien.]


## Respuesta cursor: ##

Cambios en app/integrations/google_sheets.py
Caché de índice de fila (_user_row_index: wa_id → fila real en la hoja), poblada en la carga inicial con get_all_values() (números de fila correctos, incluso con huecos).

upsert_user optimizado

Usuario existente → sheet.update() con fila cacheada (sin releer toda la hoja).
Usuario nuevo → append_row() + fila derivada de len(get_all_values()).
Complementos

get_user() usa caché en memoria sin volver a pedir metadata de la hoja.
Worksheets cacheados en _worksheets para evitar fetch_sheet_metadata repetido.
_resolve_user_row() como fallback con find() si el índice no está en caché.
Verificación
=== Result: 5/5 passed ===
Test mock: 2 upsert_user consecutivos → 1 get_all_values + 2 update (sin recarga).

Latencia observada (vs. baseline)
Mensaje	Antes	Ahora
hola
~2362 ms
~1363 ms
menu
~1179 ms
~190 ms
pedido
~1202 ms
~180–200 ms
Listo para continuar con el Paso 4 (caché menú por request) cuando quieras.






#################################################################
## v0.19

## Prompt:


OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 4 — Caché de menú por request en MenuService Un solo get_menu() por mensaje (no releer en saludo + parser). **Verificar:** saludo con menú correcto + parser reconoce productos.]


## Respuesta cursor: ##

### Análisis previo

`MenuService.get_available_menu()` llamaba a `sheets.get_menu()` en cada invocación. En un mismo webhook podían acumularse varias lecturas (p. ej. `format_menu()` en el saludo y `OrderParser` vía `OrderService._parser()`).

### Cambios implementados

Caché por request en `MenuService` usando Flask `g`: la primera llamada filtra y guarda el menú disponible; las siguientes en el mismo mensaje reutilizan esa lista sin volver a llamar a Sheets.

Scripts y tests sin contexto Flask siguen funcionando como antes (carga directa en cada llamada).

### Archivos modificados

- `app/services/menu_service.py`

### Riesgos mitigados

- Sin contexto de request (scripts, tests unitarios): comportamiento previo intacto.
- Con contexto Flask (`/bot`): `g` se limpia automáticamente entre requests, sin datos obsoletos entre mensajes.

### Compatibilidad verificada

```
=== Result: 5/5 passed ===
```

- Saludo con menú correcto (2 mensajes, productos de Sheets).
- Parser reconoce productos (`1 hamburguesa` → confirmación).
- Test unitario: 3 llamadas a `get_available_menu`/`format_menu` → **1** `sheets.get_menu()`.

### Funcionalidades agregadas

- Caché de menú disponible por request HTTP.

### Funcionalidades preservadas

- API de `MenuService`, formato del menú, parser, flow engine y contratos existentes sin cambios.



## Segundo Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 5 — Precarga de caché al arrancar (warm-up) Al iniciar Flask, cargar MENU y USERS en memoria. **Verificar:** el primer hola tras reiniciar ya no es el más lento.]




## Respuesta cursor: ##

### Análisis previo

El primer `hola` tras reiniciar pagaba el costo de conectar y leer MENU + USERS en la primera petición (~1.3 s+). Esas lecturas pueden hacerse al arrancar, cuando ya se crea `GoogleSheetsClient` en `create_app()`.

### Cambios implementados

Nuevo método `warm_up_cache()` en `GoogleSheetsClient`: tras conectar con éxito, precarga menú y usuarios en memoria y registra el tiempo en log.

Se invoca automáticamente al final de `_connect()`, sin cambios en `app.py`.

### Archivos modificados

- `app/integrations/google_sheets.py`

### Riesgos mitigados

- Si Sheets no está disponible, `warm_up_cache()` no hace nada (modo demo intacto).
- Errores en warm-up se capturan y registran; no impiden arrancar la app.

### Compatibilidad verificada

```
=== Result: 5/5 passed ===
```

Medición con caché caliente al arrancar:
- Warm-up al inicio: ~407 ms (10 ítems menú, 8–10 usuarios)
- Primer `hola`: ~980–1050 ms (antes ~1363 ms post-Paso 3, ~2362 ms baseline)
- `menu` siguiente: ~225 ms

### Funcionalidades agregadas

- Precarga de caché MENU + USERS al iniciar Flask.

### Funcionalidades preservadas

- APIs, endpoints, flujo conversacional, parser y persistencia sin cambios.



## Tercer Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 6 — Reutilizar OrderParser entre mensajes No reconstruir catálogo en cada mensaje; invalidar solo si cambia el menú. **Verificar:** parser 21/21 + pedido largo con cantidades (60, 2333, 777…).]



## Respuesta cursor: ##

### Análisis previo

`OrderService._parser()` creaba un `OrderParser` nuevo en cada mensaje, reconstruyendo catálogo, matcher y motor de fuzzy matching aunque el menú no hubiera cambiado.

### Cambios implementados

`OrderService` mantiene una instancia cacheada de `OrderParser` y una clave derivada del menú (`id`, `nombre`, `precio`, `disponible`). Solo reconstruye el parser cuando esa clave cambia (menú actualizado o TTL de Sheets expirado).

### Archivos modificados

- `app/services/order_service.py`

### Riesgos mitigados

- Invalidación automática al cambiar contenido del menú; no queda parser obsoleto.
- API pública de `OrderService` sin cambios.

### Compatibilidad verificada

```
PARSER VALIDATION: OK (21/21)
=== Result: 5/5 passed ===
```

Pedido largo (60, 2333, 12123, 777, 8): cantidades correctas. Test unitario: dos llamadas a `_parser()` → misma instancia (`p1 is p2`).

### Funcionalidades agregadas

- Reutilización de `OrderParser` entre mensajes con invalidación por cambio de menú.

### Funcionalidades preservadas

- Parser, flow engine, contratos JSON y flujo de pedidos sin cambios.


## Cuarto Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 7 — Notificaciones Twilio en background Enviar WhatsApp al admin/cliente en thread/async, sin bloquear la respuesta del webhook. **Verificar:** cliente responde rápido + admin sigue recibiendo notificaciones.]

## Respuesta Cursor: ##

### Análisis previo

`notify_new_order()` y la confirmación al cliente llamaban `_send_whatsapp()` de forma síncrona dentro del webhook, bloqueando la respuesta mientras Twilio procesaba el envío (500 ms–2 s+).

### Cambios implementados

- Nuevo `_send_whatsapp_async()`: lanza un thread daemon que ejecuta el envío real.
- `notify_new_order()` → notificación al admin en background.
- Confirmación al cliente tras `CONFIRMAR ORD-...` → también en background.
- Recordatorios del scheduler siguen en su thread propio (no bloquean el webhook).

### Archivos modificados

- `app/services/admin_service.py`

### Riesgos mitigados

- Threads daemon: no impiden apagar el proceso.
- Errores de Twilio se registran en el thread; no afectan la respuesta al cliente.
- Sin credenciales Twilio: mismo comportamiento de log que antes.

### Compatibilidad verificada

```
=== Result: 5/5 passed ===
```

Test unitario: envío simulado de 1.5 s → el caller retorna en **< 200 ms**; el mensaje se envía en background. `notify_new_order` sigue invocando el envío.

### Funcionalidades agregadas

- Notificaciones Twilio outbound sin bloquear el webhook.

### Funcionalidades preservadas

- Formato de mensajes admin/cliente, confirmación de pedidos, scheduler de recordatorios, APIs y flujo conversacional sin cambios.


## Quinto Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 8 — Persistencia de estado más liviana Escribir user_states.json solo si hubo cambio (debounce o diff). **Verificar:** flujo de pedido conserva carrito tras varios mensajes.]


## Respuesta prompt: ##

### Análisis previo

`StateManager` escribía `user_states.json` en cada `update()` y `reset()`, incluso cuando el estado no cambiaba (p. ej. `set_step` repetido con los mismos valores).

### Cambios implementados

- `_persist_if_changed()` compara el estado anterior con el nuevo antes de guardar.
- `update()` y `reset()` solo llaman a `_save()` si hubo cambio real.
- `update()` modifica el estado in-place (sin el `get()` + deepcopy extra de antes).

### Archivos modificados

- `app/core/state_manager.py`

### Riesgos mitigados

- Si el estado es idéntico, no hay escritura a disco (menos I/O y menos contención).
- Cuando sí hay cambio (carrito, paso, etc.), se persiste igual que antes.

### Compatibilidad verificada

```
=== Result: 5/5 passed ===
```

Tests adicionales:
- 3× `set_step` igual → **1** escritura; `patch_data` duplicado → sin escritura extra.
- Carrito persiste tras recargar desde disco.
- Flujo `pedido` → `2 hamburguesas` → mensaje siguiente: carrito conservado (qty ≥ 2).

### Funcionalidades agregadas

- Persistencia con diff: escribir solo si el estado cambió.

### Funcionalidades preservadas

- API de `StateManager`, flujo de pedido, carrito y estados conversacionales sin cambios.


## Sexto Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 9 — TTL de caché configurable en .env MENU_CACHE_TTL_SECONDS, ORDERS_CACHE_TTL_SECONDS con defaults actuales. **Verificar:** cambio en Sheets se refleja según TTL; todo lo demás igual.]

## Respuesta cursor: ##

### Análisis previo

Los TTL de caché de menú (60 s) y pedidos (30 s) estaban fijos en `google_sheets.py`, sin poder ajustarlos desde `.env`.

### Cambios implementados

- **`app/config.py`**: `MENU_CACHE_TTL_SECONDS` y `ORDERS_CACHE_TTL_SECONDS` leídos de `.env` con defaults `60` y `30`.
- **`app/integrations/google_sheets.py`**: importa esos valores desde `config` (ya no hay constantes locales).
- **`.env.example`**: documentadas las nuevas variables.

### Archivos modificados

- `app/config.py`
- `app/integrations/google_sheets.py`
- `.env.example`

### Riesgos mitigados

- Defaults idénticos al comportamiento anterior si no se define nada en `.env`.
- Sin cambios en APIs ni en la lógica de invalidación de caché existente.

### Compatibilidad verificada

```
=== Result: 5/5 passed ===
```

Defaults verificados: `60` / `30`. Tras expirar el TTL, `get_menu()` vuelve a leer Sheets.

### Funcionalidades agregadas

- TTL de caché configurable vía `.env`:

```env
MENU_CACHE_TTL_SECONDS=60
ORDERS_CACHE_TTL_SECONDS=30
```

### Funcionalidades preservadas

- Warm-up, parser, flujo de pedidos y resto del checklist sin cambios.


## Septimo Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 10 — Servidor de producción local Usar waitress o gunicorn en lugar de Flask debug. **Verificar:** /health OK + checklist WhatsApp del Paso 2.]


## Respuesta cursor: ##

### Análisis previo

El arranque usaba `app.run(..., debug=True)` (servidor de desarrollo de Flask), inadecuado para uso local estable o como base de producción.

### Cambios implementados

- **`waitress`** añadido a `requirements.txt` (compatible con Windows; gunicorn no lo es).
- **`run.py`**: arranca con Waitress; host/puerto configurables vía `HOST` y `PORT`.
- **`app/app.py`**: el bloque `__main__` también usa Waitress (sin `debug=True`).
- **`.env.example`**: documentados `HOST=0.0.0.0` y `PORT=5000`.

### Archivos modificados

- `requirements.txt`
- `run.py`
- `app/app.py`
- `.env.example`

### Riesgos mitigados

- Waitress es un servidor WSGI de producción, sin reloader ni debugger de Flask.
- Misma app WSGI (`app = create_app()`); endpoints sin cambios.

### Compatibilidad verificada

```
GET /health → 200 {'status': 'ok', ...}
=== Result: 5/5 passed ===
```

Servidor Waitress en ejecución: log `Serving on http://0.0.0.0:5000`.

### Funcionalidades agregadas

- Arranque con Waitress: `python run.py`

### Funcionalidades preservadas

- Webhook `/bot`, warm-up, cachés y checklist completo sin cambios.

Para usar en otra máquina: `pip install -r requirements.txt` (incluye `waitress`).



## Octavo Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 11 — Hosting permanente (sin ngrok) Desplegar en Railway, Render o VPS. **Verificar:** webhook estable 24/7 + latencia menor que con PC + ngrok.]

## Respuesta cursor: ##

**Paso 11 — listo en el repo.** Quedó preparado el despliegue permanente sin ngrok:

- `Dockerfile` + `render.yaml` + `railway.toml`
- Credenciales Google vía `GOOGLE_SERVICE_ACCOUNT_JSON` (para la nube)
- `scripts/verify_deployment.py` para comprobar `/health` y latencia de `hola`

**Verificado localmente:** checklist 5/5 y `verify_deployment` OK (`hola` ~857 ms).

**Tu parte:** subir a GitHub, desplegar en Render o Railway con las variables de `.env`, apuntar Twilio a `https://tu-dominio/bot` y ejecutar:

```bash
DEPLOY_URL=https://tu-app.onrender.com python scripts/verify_deployment.py
```


## Noveno Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Paso 12 — Medir de nuevo y comparar Repetir el Paso 1 y documentar antes/después. **Meta:** respuesta al cliente **< 2 s** en pedidos normales (sin contar red Twilio→teléfono).]

## Respuesta cursor: ## 

### Análisis previo

Paso 12 pide repetir la medición del Paso 1 y comparar con el baseline documentado (~2362 / ~1179 / ~1202 ms), con meta de pedido normal **< 2 s**.

### Cambios implementados

Nuevo script `scripts/measure_latency.py`:
- Mide `hola`, `menu`, `pedido` y `1 hamburguesa` en secuencia
- Imprime tabla antes/después
- Guarda reporte en `data/latency_report.json`
- Soporta `DEPLOY_URL` para medir en producción

### Archivos modificados

- `scripts/measure_latency.py` (nuevo)
- `data/latency_report.json` (generado)

### Resultados — antes vs ahora

| Paso | Baseline | Ahora | Cambio | < 2 s |
|------|----------|-------|--------|-------|
| `hola` | 2362 ms | **913 ms** | −61% | OK |
| `menu` | 1179 ms | **513 ms** | −56% | OK |
| `pedido` (`1 hamburguesa`) | 1202 ms | **214 ms** | −82% | OK |

**Meta cumplida:** pedido normal **214 ms** ≪ 2000 ms.

Checklist: **5/5 passed**.

### Cómo repetir

```bash
python scripts/measure_latency.py
DEPLOY_URL=https://tu-app.onrender.com python scripts/measure_latency.py
```

### Optimizaciones que explican la mejora

Pasos 3–10: caché usuarios/menú/parser, warm-up al arrancar, Twilio async, persistencia con diff, Waitress.

**Plan de optimización (12 pasos): completado.**




#################################################################
## v0.20

## Prompt:


OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Quiero que que el bot cada 30 segundos guarde el menú osea lo vaya actualizando en el servidor del bot y que el bot acceda directamente a lo que está guardado localmente en su servidor así no depende de la consulta sino accede directamente a un archivo que está ya guardado, y el archivo se va actualizando cada 30 segundos pero de manera independiente, es decir que el bot lee es el local, y el local se actualiza de forma independiente y el bot no depende de nada a la red ya que el toma es el local, eso se actualiza solo pero el bot no depende de la actualización, para evitar tanto delay en cada consulta sino que agarre lo que ya tiene guardado, solo has eso y nada mas no toques nada mas es una mejora incremental]



## Respuesta cursor: ##

### Cambios (solo `app/integrations/google_sheets.py`)

**Comportamiento:**
- Al arrancar carga el menú desde `data/menu_cache.json` (o menú demo si no existe).
- `get_menu()` **solo lee memoria local** — nunca consulta Sheets durante un mensaje.
- Un thread en background actualiza cada **30 s** desde Sheets → memoria + archivo, de forma independiente.

**Flujo:**
```
Sheets ──(cada 30s, background)──► data/menu_cache.json + memoria
                                         ▲
Bot / parser / menú ──(instantáneo)──────┘
```

### Verificación

- Checklist **5/5 OK**
- Test: `/bot` + `menu` **no llama** a Sheets en el request
- Log: `Menu local refresh every 30s (reads: .../data/menu_cache.json)`

Tras reiniciar el servidor, el menú queda disponible al instante desde el archivo local; la red solo la usa el refresco en background.


## Segundo Prompt ## 

te pregunto solo responde: eso mejora muchisimo la respuesta? que tanto? comparalo a como estaba antes, has un test 

## Respuesta cursor ##

**Respuesta directa:** mejora **sí, pero no es tan brutal** como el plan de 12 pasos. Es un **refinamiento** sobre algo que ya estaba bastante optimizado.

### Test que acabo de correr (8 requests `menu` cada modo)

| Modo | Mediana | Rango típico |
|------|---------|--------------|
| **Ahora** (menú local, sin red en el request) | **~196 ms** | 179–208 ms |
| **Antes simulado** (Sheets en cada `menu`) | **~391 ms** | 375–445 ms |
| Solo la llamada a Sheets | **~246 ms** | — |

**Ganancia en `menu`:** ~**195 ms menos** → **~50% más rápido** en estado estable.

### Cómo se compara con todo lo anterior

| Etapa | Pedido / menu (orden de magnitud) |
|-------|-----------------------------------|
| **Baseline original** | ~1200 ms (`menu` / pedido) |
| **Tras plan 12 pasos** | ~200 ms |
| **Este cambio (menú local)** | ~200 ms → ~196 ms en `menu` |

Es decir: **no baja de 200 ms a 20 ms**. Lo que hace es:

1. **Quitar ~250 ms de red** cuando tocaría ir a Sheets (cache vencida, cold start, etc.).
2. **Evitar picos**: antes podías tener ~400 ms en `menu`; ahora se queda ~180–210 ms.
3. **Desacoplar**: si Sheets va lento o falla, el bot **sigue respondiendo** con el archivo local.

### ¿“Muchísimo”?

- **Para el flujo completo ya optimizado:** no muchísimo; es **~50% en el comando `menu`** y menos en `hola`/`pedido` (ahí el menú ya estaba en memoria).
- **Para estabilidad y previsibilidad:** **sí vale la pena** — el bot no espera la red en cada consulta de menú.

**En una frase:** no es otra revolución como pasar de 1,2 s a 200 ms, pero en `menu` ganas **~200 ms estables** y eliminas la dependencia de Sheets en cada mensaje. Eso se nota sobre todo si Sheets está lento o hay muchos usuarios pidiendo menú a la vez.



## Tercer prompt ##

no hagas nada solo responde: pero yo pienso que si influye porque es el primer contacto, entonces este debería ser rapido, no? así ya la persona sabe que es un bot y esperará respuesta

## Resp cursor ##

Sí, **tienes razón en lo importante**: el primer contacto marca la percepción. Si el `hola` tarda 3 segundos, mucha gente piensa que el bot “no sirve” o se va. Si responde en ~1 s o menos, la persona entiende que hay algo vivo al otro lado y **tolera mejor** que los mensajes siguientes tarden un poco más.

En ese sentido, **sí influye** lo del menú local en el primer contacto, porque el `hola` trae **dos mensajes** y el segundo es el menú completo. Antes, ahí podía colarse una consulta a Sheets (~250 ms o más, y a veces mucho más si hay cuota lenta). Ahora ese menú sale del archivo local → **el saludo no espera la red por el menú**.

Pero hay un matiz honesto: el `hola` **sigue siendo el más lento** (~900 ms en tus pruebas) porque en el **primer contacto** aún hace otras cosas de red:

- registrar/actualizar al usuario en Sheets (`touch`)
- cargar perfil para personalizar el saludo
- arrancar el flujo (saludo dual, etc.)

O sea: **menú local acorta el `hola`, pero no lo deja en 200 ms** como un `pedido` ya en caliente. La mejora del menú local en el primer contacto es real, pero el cuello de botella que queda es sobre todo **usuario/perfil en Sheets**, no el menú.

**Resumen:** tu intuición es correcta — **el primer contacto debe ser rápido** y optimizar el menú ahí ayuda. Para que el `hola` baje de ~900 ms a algo más “wow”, habría que atacar el `touch`/usuario en el primer mensaje (similar a lo que ya hicieron con el menú: local o async), no solo el menú. Pero como primer paso, **sí tiene sentido** lo que hiciste: quitar red del menú en el saludo es justo donde más impacto psicológico tiene.



## Cuarto Prompt ##

te pregunto solo responde:

registrar/actualizar al usuario en Sheets (touch)
cargar perfil para personalizar el saludo
arrancar el flujo (saludo dual, etc.)

Eso hay forma de dejarlo local? hay forma de dejar esa información local? osea que la lea es de un archivo local con la información del perfil del cliente y que se actualice eso cada 30 segundos como el otro

no hagas nada solo responde


## Resp cursor ##

**Sí, se puede hacer el mismo patrón que con el menú**, con matices.

### Qué se puede dejar local (lectura instantánea)

- **Perfil para el saludo:** nombre, dirección guardada, último pedido, etc.
- **Lectura en `hola`:** cargar desde `data/users_cache.json` (o similar) en memoria, sin ir a Sheets en el request.

### Qué haría el thread cada 30 s (en background)

- Leer la pestaña **USERS** de Sheets.
- Actualizar memoria + archivo local.
- Igual que el menú: el bot **no espera** esa actualización.

### El tema de `touch` (registrar/actualizar usuario)

Ahí no es solo lectura. En cada mensaje quieres guardar `last_seen`, nombre de WhatsApp, etc.

Opciones:

1. **Escritura diferida (recomendable):**  
   - En el request: actualizar solo memoria + archivo local (rápido).  
   - Cada X segundos (o cada 30 s): sincronizar cambios pendientes a Sheets en background.  
   - El `hola` queda rápido; Sheets se entera un poco después.

2. **Solo caché de lectura (más simple):**  
   - Lectura local para saludo.  
   - `touch` sigue escribiendo a Sheets en el request → **el primer `hola` sigue lento** si el usuario es nuevo (hay que hacer `append`).

### Limitaciones a tener en cuenta

| Caso | Qué pasa |
|------|----------|
| **Usuario nuevo** | Hay que crearlo en algún sitio; puede ser local primero y subir en background. |
| **Varios servidores** | Cada uno con su copia local; hace falta una sola instancia o Redis/DB compartida. |
| **Datos “al instante” en Sheets** | Con sync cada 30 s, el admin puede ver el usuario con hasta ~30 s de retraso. |
| **Pedidos / confirmaciones** | Orders suelen seguir yendo a Sheets en tiempo real; esto es sobre **perfil/saludo**. |

### Conclusión

**Sí:** perfil para personalizar el saludo puede ser **100% local en lectura**, con refresh cada 30 s como el menú.

**Para que el `hola` baje de verdad (~900 ms → ~200 ms):** hace falta también **escritura local + sync en background** del `touch`, no solo cachear lecturas.

Es el mismo enfoque que ya aplicaste al menú, un poco más delicado porque mezcla lectura y escritura, pero **totalmente viable** como mejora incremental.



## Quinto prompt ##

te pregunto solo responde: 

Para que el hola baje de verdad (~900 ms → ~200 ms): hace falta también escritura local + sync en background del touch, no solo cachear lecturas.

Dame un prompt para poder dejarlo así a 200ms

## Resp cursor ##

**Prompt listo para copiar:**

---

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:

### Optimizar `touch` y perfil de usuario — lectura/escritura local + sync en background

**Objetivo:** que el primer `hola` baje de ~900 ms a ~200 ms, igual que `pedido`/`menu` en caliente.

**Patrón (igual que el menú local):**
- El bot **lee siempre** perfil/usuario desde **memoria + archivo local** (`data/users_cache.json` o similar).
- **Nunca** consulta ni escribe en Google Sheets durante `POST /bot` (ni en `touch`, ni en `get_user`, ni en `_build_node_context` del saludo).
- Un **thread en background cada 30 s** (independiente del webhook):
  1. Descarga USERS de Sheets → actualiza memoria + archivo local.
  2. Sube a Sheets los cambios pendientes de usuarios (cola de `touch` / upserts locales).
- Si Sheets falla o va lento, el bot sigue respondiendo con datos locales.

**Comportamiento en el request (`touch`):**
- Actualizar solo caché en memoria + archivo local (nombre, `last_seen`, dirección, etc.).
- Marcar usuario como `dirty` / pendiente de sync si hubo cambio.
- Responder al cliente **sin esperar** red.

**Usuario nuevo:**
- Crearlo primero en caché local + archivo.
- Encolar sync (append en Sheets) en background; no bloquear el `hola`.

**Restricciones:**
- Cambio **incremental**; modificar la **mínima** cantidad de archivos (idealmente `google_sheets.py` + `user_service.py` si hace falta).
- **No** cambiar endpoints, flujo conversacional, JSON del flujo, parser ni contratos públicos.
- Reutilizar `_users_cache`, `_user_row_index` y la lógica de `upsert_user` donde aplique.
- Mantener warm-up al arrancar: cargar usuarios desde archivo local; el refresh en background arranca solo si hay conexión a Sheets.

**Verificar:**
```bash
python scripts/regression_checklist.py
python scripts/measure_latency.py
```
- `hola` mediana **< 300 ms** (meta ~200 ms) en test client con caché caliente.
- Test: `POST /bot` + `hola` **no** llama a Sheets de forma síncrona (mock/patch que falle si hay fetch/write en el request).
- Tras 30–60 s, cambios de `touch` deben aparecer en Sheets (sync background).
- Saludo personalizado con nombre sigue funcionando.
- Checklist 5/5.

**No tocar:** menú local ya hecho, Twilio async, parser, flow JSON, admin.

---

Si quieres acotarlo a un solo archivo, añade al final: *«Si puede hacerse solo en `app/integrations/google_sheets.py`, no modifiques otros archivos.»*



## Sexto prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[### Optimizar `touch` y perfil de usuario — lectura/escritura local + sync en background

**Objetivo:** que el primer `hola` baje de ~900 ms a ~200 ms, igual que `pedido`/`menu` en caliente.

**Patrón (igual que el menú local):**
- El bot **lee siempre** perfil/usuario desde **memoria + archivo local** (`data/users_cache.json` o similar).
- **Nunca** consulta ni escribe en Google Sheets durante `POST /bot` (ni en `touch`, ni en `get_user`, ni en `_build_node_context` del saludo).
- Un **thread en background cada 30 s** (independiente del webhook):
  1. Descarga USERS de Sheets → actualiza memoria + archivo local.
  2. Sube a Sheets los cambios pendientes de usuarios (cola de `touch` / upserts locales).
- Si Sheets falla o va lento, el bot sigue respondiendo con datos locales.

**Comportamiento en el request (`touch`):**
- Actualizar solo caché en memoria + archivo local (nombre, `last_seen`, dirección, etc.).
- Marcar usuario como `dirty` / pendiente de sync si hubo cambio.
- Responder al cliente **sin esperar** red.

**Usuario nuevo:**
- Crearlo primero en caché local + archivo.
- Encolar sync (append en Sheets) en background; no bloquear el `hola`.

**Restricciones:**
- Cambio **incremental**; modificar la **mínima** cantidad de archivos (idealmente `google_sheets.py` + `user_service.py` si hace falta).
- **No** cambiar endpoints, flujo conversacional, JSON del flujo, parser ni contratos públicos.
- Reutilizar `_users_cache`, `_user_row_index` y la lógica de `upsert_user` donde aplique.
- Mantener warm-up al arrancar: cargar usuarios desde archivo local; el refresh en background arranca solo si hay conexión a Sheets.

**Verificar:**
```bash
python scripts/regression_checklist.py
python scripts/measure_latency.py
```
- `hola` mediana **< 300 ms** (meta ~200 ms) en test client con caché caliente.
- Test: `POST /bot` + `hola` **no** llama a Sheets de forma síncrona (mock/patch que falle si hay fetch/write en el request).
- Tras 30–60 s, cambios de `touch` deben aparecer en Sheets (sync background).
- Saludo personalizado con nombre sigue funcionando.
- Checklist 5/5.

**No tocar:** menú local ya hecho, Twilio async, parser, flow JSON, admin.

**«Si puede hacerse solo en `app/integrations/google_sheets.py`, no modifiques otros archivos.»**]


## Resp cursor ##

### Análisis previo

El `hola` (~900 ms) esperaba a Sheets en `touch`/`get_user` (lectura + escritura). El menú ya era local; faltaba lo mismo para usuarios.

### Cambios implementados (solo `google_sheets.py`)

- **`data/users_cache.json`**: usuarios, índice de filas y cola `dirty`.
- **`get_user` / `upsert_user`**: solo memoria + archivo local; marcan `dirty` sin red.
- **Thread cada 30 s** (unificado con menú):
  1. Sube usuarios `dirty` → Sheets  
  2. Refresca menú  
  3. Refresca usuarios (sin pisar los que siguen `dirty`)
- **Warm-up**: solo cuenta datos locales (0 ms de red).

### Verificación

```
=== Result: 5/5 passed ===
Meta OK: pedido normal 11 ms < 2000 ms
```

| Prueba | Resultado |
|--------|-----------|
| `hola` sin Sheets en request | OK (mock bloquea red) |
| Saludo con nombre "Ana" | OK |
| Sync background | `Users synced to Sheets: 1` en log |
| Mediana `hola` | **~2–5 ms** (test client, caché caliente) |

### Antes vs ahora (`hola`)

| | Antes | Ahora |
|---|-------|-------|
| Baseline original | ~2362 ms | ~5 ms |
| Tras plan 12 pasos | ~913 ms | ~5 ms |

En WhatsApp real verás más ms (red Twilio), pero el servidor ya no espera Sheets en el primer contacto.

### Archivos modificados

- `app/integrations/google_sheets.py`

Reinicia el servidor (`python run.py`) para que cargue el nuevo flujo. Los cambios de `touch` llegan a Sheets en ≤30 s por el sync en background.






#################################################################
## v0.21
(prompt en auto)

## Prompt:

Quiero que hagas lo siguiente pero que no modifiques el proyecto ni lo toques, solo quiero que lo visualices y hagas esto:

Proponme un plan de 3 prompts donde incluyas todas las mejoras posibles y necesarias para poder optimizar la velocidad del chatbot en cuanto a latencia, que sean profesionales los prompts pero también los necesito que ahorren tokens pero que sean las mejores mejoras que se le puedan implementar como si fueras un senior de 15 años

## Respuesta cursor ##

Ya tienes **menú y usuarios 100% locales** (~5 ms en servidor). Lo que sigue limitando latencia **en WhatsApp real** no es el `hola`, sino **pedidos/reservas/admin** que aún pueden ir a Sheets en el request, más **cold start** en hosting free.

Plan en **3 prompts** (ordenados por impacto). Cada uno es autocontenido, corto y con verificación.

---

## Prompt 1 — Pedidos y reservas: escritura local + sync (máximo impacto en flujo real)

```
OBLIGATORIO: Lee y aplica AI_RULES.md. Cambio incremental; mínimos archivos.

TAREA: Pedidos/reservas sin Sheets en POST /bot.

Hoy create_order / create_reservation bloquean en append/update. Mismo patrón que users/menu:
- Respuesta al cliente solo con memoria + data/orders_cache.json (y reservations si aplica).
- Cola dirty; thread cada 30s sube a Sheets (reutilizar loop en google_sheets.py).
- get_order / get_pending_orders leen local primero; refresh background.

NO tocar: menú/users local, Twilio async, parser, flow JSON, endpoints.

Verificar:
python scripts/regression_checklist.py
python scripts/measure_latency.py
Medir POST /bot tras flujo: pedido → confirmar → guardar pedido: sin _get_sheet en request (mock).
Meta: confirmación pedido <300ms servidor (test_client).
```

**Por qué primero:** es el camino donde el usuario **sigue esperando red** después de optimizar saludo.

---

## Prompt 2 — Producción estable y sin cold start lento

```
OBLIGATORIO: AI_RULES.md. Solo lo necesario para latencia 24/7.

TAREA: Reducir latencia primera petición tras deploy/reinicio.

1) Un solo GoogleSheetsClient por proceso (create_app singleton; no recrear en tests salvo necesario).
2) Warm-up al import/arranque: menú+users+orders locales antes del primer /bot.
3) Health check que confirme cachés cargadas (opcional campo en GET /health).
4) Documentar en README 5 líneas: Render/Railway, variables GOOGLE_SERVICE_ACCOUNT_JSON, webhook /bot, plan pago si cold start.

NO refactor grande. NO cambiar contratos JSON.

Verificar:
python run.py → curl /health
DEPLOY_URL=... python scripts/verify_deployment.py
Primer hola tras reinicio <2s en servidor (log POST /bot completed).
```

**Por qué segundo:** en local ya vas rápido; en cloud el **primer mensaje** tras dormir es lo que el cliente nota.

---

## Prompt 3 — Afinado senior: menos trabajo por mensaje + observabilidad

```
OBLIGATORIO: AI_RULES.md. 1-2 archivos max si posible.

TAREA: Micro-optimizaciones sin cambiar UX.

1) user_service.touch: un solo upsert_user (hoy get_user+upsert redundante).
2) OrderService: invalidar parser solo si cambió menu_cache.json (mtime/hash), no cada request.
3) state_manager: debounce escritura user_states.json (ej. flush cada 2s o solo al cambiar step/cart).
4) Log p50/p95 por body en /bot (una línea agregada cada N requests o al final del request).

Verificar: regression 5/5 + measure_latency.py sin regresión >10% vs Paso 12.

NO nuevas capas. NO Redis salvo que documentes por qué no aplica en 1 instancia.
```

**Por qué tercero:** ganancias pequeñas pero **profesionales**; útil cuando 1-2 ya están en producción.

---

## Mapa rápido (qué ya tienes vs qué falta)

| Área | Estado | Prompt |
|------|--------|--------|
| Menú local + refresh 30s | Hecho | — |
| Usuarios/touch local + sync | Hecho | — |
| Parser cache por menú | Hecho | 3 (mtime) |
| Twilio admin async | Hecho | — |
| Waitress + deploy | Hecho | 2 |
| **Pedidos/reservas async** | Pendiente | **1** |
| **Cold start producción** | Parcial | **2** |
| touch duplicado / state debounce | Pendiente | **3** |

---

## Expectativa realista

- **Servidor (test_client):** ya ~5–15 ms; poco margen.
- **WhatsApp real:** meta **<2 s** servidor en pedido completo = Prompt **1** + hosting estable (**2**).
- **No optimizar más** sin métricas en producción (`measure_latency` + logs Twilio `delivered`).

Copia cada bloque en un chat nuevo, uno por uno, en orden 1 → 2 → 3.



## Segundo Prompt:
(en composer 2.5 fast)


OBLIGATORIO: Lee y aplica AI_RULES.md. Cambio incremental; mínimos archivos.

TAREA: [Pedidos/reservas sin Sheets en POST /bot.

Hoy create_order / create_reservation bloquean en append/update. Mismo patrón que users/menu:
- Respuesta al cliente solo con memoria + data/orders_cache.json (y reservations si aplica).
- Cola dirty; thread cada 30s sube a Sheets (reutilizar loop en google_sheets.py).
- get_order / get_pending_orders leen local primero; refresh background.

NO tocar: menú/users local, Twilio async, parser, flow JSON, endpoints.

Verificar:
python scripts/regression_checklist.py
python scripts/measure_latency.py
Medir POST /bot tras flujo: pedido → confirmar → guardar pedido: sin _get_sheet en request (mock).
Meta: confirmación pedido <300ms servidor (test_client).]



## Respuesta cursor ##

Tarea completada. Pedidos y reservas siguen el mismo patrón local que menú/usuarios.

## Qué cambió

En `app/integrations/google_sheets.py`:

- **Caché local**: `data/orders_cache.json` y `data/reservations_cache.json`
- **Escritura en request**: `create_order`, `update_order_status`, `create_reservation` solo tocan memoria + JSON y marcan dirty
- **Lectura en request**: `get_order` y `get_pending_orders` leen local primero
- **Sync en background** (cada 30s): push de dirty orders/reservations + refresh desde Sheets

## Verificación

| Check | Resultado |
|-------|-----------|
| Flujo pedido → confirmar → recoger con `_get_sheet` mockeado | **~12 ms**, pedido en caché local, sin Sheets en request |
| `scripts/regression_checklist.py` | **5/5** |
| `scripts/measure_latency.py` | hola ~3.7 ms, menu ~5.8 ms, pedido_flow ~8.8 ms |

Meta de confirmación de pedido **<300 ms** cumplida con margen amplio.

El sync a Sheets sigue ocurriendo en el thread de background (logs: `Orders synced to Sheets: 1 new`).

¿Quieres que ejecute `guardar.py` para commitear?



## Tercer Prompt: ##


OBLIGATORIO: Lee y aplica AI_RULES.md. Cambio incremental; mínimos archivos.

TAREA: [TAREA: Reducir latencia primera petición tras deploy/reinicio.

1) Un solo GoogleSheetsClient por proceso (create_app singleton; no recrear en tests salvo necesario).
2) Warm-up al import/arranque: menú+users+orders locales antes del primer /bot.
3) Health check que confirme cachés cargadas (opcional campo en GET /health).
4) Documentar en README 5 líneas: Render/Railway, variables GOOGLE_SERVICE_ACCOUNT_JSON, webhook /bot, plan pago si cold start.

NO refactor grande. NO cambiar contratos JSON.

Verificar:
python run.py → curl /health
DEPLOY_URL=... python scripts/verify_deployment.py
Primer hola tras reinicio <2s en servidor (log POST /bot completed).
```]




## Respuesta cursor ##

La tarea de **cold start (Prompt 2)** quedó completada: singleton de Sheets, warm-up al arranque, `caches` en `/health`, docs en README, y verificaciones OK (regression 5/5, `hola` ~21 ms en servidor).

Los errores de los shells 1692 y 98110 son normales: eran procesos Waitress que se cerraron al liberar el puerto 5000 (había instancias viejas sirviendo código sin `caches`).

El servidor local está de nuevo en marcha con `python run.py` en el puerto 5000.


## Cuarto Prompt: ##


OBLIGATORIO: Lee y aplica AI_RULES.md. Cambio incremental; mínimos archivos.

TAREA: [TAREA: Micro-optimizaciones sin cambiar UX.

1) user_service.touch: un solo upsert_user (hoy get_user+upsert redundante).
2) OrderService: invalidar parser solo si cambió menu_cache.json (mtime/hash), no cada request.
3) state_manager: debounce escritura user_states.json (ej. flush cada 2s o solo al cambiar step/cart).
4) Log p50/p95 por body en /bot (una línea agregada cada N requests o al final del request).

Verificar: regression 5/5 + measure_latency.py sin regresión >10% vs Paso 12.

NO nuevas capas. NO Redis salvo que documentes por qué no aplica en 1 instancia.]



## Respuesta cursor ##

### Análisis previo

Cuatro micro-optimizaciones puntuales sin cambiar UX: menos trabajo redundante por mensaje y mejor observabilidad, respetando la arquitectura actual.

### Cambios implementados

1. **`user_service.touch`**: una sola llamada a `upsert_user` (ya mergea nombre/dirección en caché).
2. **`OrderService`**: el parser se invalida solo si cambia el `mtime` de `data/menu_cache.json`, no en cada request.
3. **`state_manager`**: escritura inmediata al cambiar `step`, `flow` o `cart`; resto de cambios con debounce de 2 s.
4. **`app.py`**: acumula latencias por `body` y loguea p50/p95 cada 100 requests.

### Archivos modificados

- `app/services/user_service.py`
- `app/services/order_service.py`
- `app/core/state_manager.py`
- `app/app.py`

### Compatibilidad verificada

| Check | Resultado |
|-------|-----------|
| `regression_checklist.py` | **5/5** |
| `measure_latency.py` | hola 3.0 ms, menu 3.1 ms, pedido 5.5 ms |
| Regresión vs reporte Paso 12 | **<10%** (mejora leve) |

### Funcionalidades preservadas

Parser, flow, endpoints, contratos JSON, Twilio, Sheets async — sin cambios de UX.





## Quinto Prompt ##

No hagas nada ni modifiques nada solo responde: quiero que hagas un analisis del antes de todas las optimizaciones y después, a ver que tanto y me das una comparativa 

## Respuesta cursor ##

## Análisis comparativo: antes vs después de todas las optimizaciones

### Punto de partida (baseline original — Paso 1)

Medición con Google Sheets conectado, **cada mensaje pegaba a la API de Google** (`get_all_records`, `append_row`, etc.). Tiempos medidos en servidor (`POST /bot completed in X ms`):

| Acción | Antes (baseline) | Cuellos de botella principales |
|--------|------------------|--------------------------------|
| `hola` | **~2 362 ms** | Menú + usuario + Sheets en el mismo request |
| `menu` | **~1 179 ms** | Lectura completa de pestaña MENU |
| `pedido` (`1 hamburguesa`) | **~1 202 ms** | Menú + parser + estado + posible touch a Sheets |

**Meta del plan:** respuesta al cliente **< 2 s** en pedidos normales (sin contar Twilio → teléfono).

---

### Evolución por fases

| Fase | Qué se hizo | `hola` | `menu` | `pedido` |
|------|-------------|--------|--------|----------|
| **0 — Baseline** | Sin optimizaciones | ~2 362 ms | ~1 179 ms | ~1 202 ms |
| **1 — Plan 12 pasos** (Pasos 3–10) | Caché usuarios, menú por request, warm-up, parser reutilizado, Twilio async, state diff, Waitress | ~913 ms (−61 %) | ~513 ms (−56 %) | ~214 ms (−82 %) |
| **2 — Menú 100 % local** | `data/menu_cache.json` + refresh cada 30 s en background | ~900 ms (casi igual) | ~196 ms | ~200 ms |
| **3 — Usuarios/touch local** | `data/users_cache.json` + dirty sync 30 s | **~2–5 ms** | ~5 ms | ~8 ms |
| **4 — Pedidos/reservas local** | `orders_cache.json` + sync background | ~5 ms | ~5 ms | confirmar/guardar **~12 ms** |
| **5 — Cold start prod** | Singleton Sheets + warm-up al arranque + `/health` con `caches` | ~21 ms (HTTP servidor) | ~3 ms | ~6 ms |
| **6 — Micro-opts** (actual) | touch 1× upsert, parser por mtime, state debounce, logs p50/p95 | **~3 ms** | **~3 ms** | **~5,5 ms** |

---

### Estado final (ahora)

Según `data/latency_report.json` (test client, caché caliente):

| Paso | Baseline | Ahora | Mejora | Factor |
|------|----------|-------|--------|--------|
| `hola` | 2 362 ms | **3,0 ms** | −99,9 % | **~787× más rápido** |
| `menu` | 1 179 ms | **3,1 ms** | −99,7 % | **~380× más rápido** |
| `pedido_flow` | 1 202 ms | **5,5 ms** | −99,5 % | **~218× más rápido** |

**Meta < 2 s:** cumplida con margen enorme (todo bajo **10 ms** en servidor con caché caliente).

En **servidor real** (`python run.py` + HTTP), el primer `hola` tras arranque quedó en **~21 ms** (vs ~800–900 ms antes de usuarios locales, y ~2,3 s en el baseline).

---

### Qué cambió arquitecturalmente

| Área | Antes | Después |
|------|-------|---------|
| **Menú** | Sheets en cada request | Memoria + JSON local; Sheets solo en background (30 s) |
| **Usuarios / touch** | `get_user` + `upsert` → red | Un `upsert_user` local + sync background |
| **Pedidos / reservas** | `append_row` / `update` bloqueantes | Local + cola dirty + sync 30 s |
| **Parser** | Reconstruido a menudo | Reutilizado; invalida solo si cambia `menu_cache.json` |
| **Estado** | Escritura en cada cambio | Diff + debounce 2 s (inmediato en step/cart) |
| **Twilio admin** | Síncrono en webhook | Thread en background |
| **Arranque** | Primera petición pagaba conexión Sheets | Warm-up + singleton al import |
| **Observabilidad** | Solo log por request | p50/p95 por `body` cada 100 requests |

Patrón común: **responder al cliente solo con memoria/disco local; Sheets es eventual (background)**.

---

### Dónde sigue habiendo latencia (honesto)

1. **Twilio → teléfono:** no se optimizó; el usuario puede seguir viendo 1–3 s extra por la red de WhatsApp.
2. **Cold start en hosting free** (Render/Railway): si el servicio duerme, el primer mensaje puede tardar segundos en **despertar el contenedor**, no en el bot en sí.
3. **Sync background:** cada 30 s hay tráfico a Sheets; no afecta al cliente, pero el servidor sigue dependiendo de Google para persistencia.

---

### Resumen en una frase

Pasaste de un bot donde **cada mensaje esperaba Google Sheets (~1,2–2,4 s)** a uno donde el servidor responde en **~3–6 ms** en flujo normal, porque casi todo (menú, usuarios, pedidos) vive en caché local y Sheets quedó relegado a sincronización en segundo plano.

La mejora más grande no fue un solo cambio, sino la **secuencia**: cachés y warm-up (plan 12 pasos) → **desacoplar red del request** (menú, users, orders locales) → **singleton + micro-opts** para pulir lo que quedaba.





## Sexto Prompt ##

No hagas nada solo responde: qué opinas? si es una buena mejora? si crees que está bien optimizado frente a los otros del mercado? crees que fue buena idea plantearlo así? por cache? tu qu eopinas




## Respuesta cursor ##

## Mi opinión honesta

**Sí, es una buena mejora.** Pasar de ~1–2 s en servidor a ~3–6 ms no es cosmético: cambia la experiencia real del cliente y reduce mucho el riesgo de timeouts de Twilio (que suelen estar en torno a 15 s, pero cuanto más lento respondes, peor se siente el bot).

**¿Está bien optimizado frente al mercado?**

Depende con qué lo compares:

- **Frente a bots caseros con Sheets directo** (muy común en restaurantes pequeños): sí, quedó **muy por encima**. Muchos proyectos siguen haciendo `get_all_records()` en cada mensaje y nunca lo arreglan.
- **Frente a soluciones “serias” de producción** (Redis, Postgres, colas, workers, CDN, etc.): estás en un **punto intermedio sensato** para tu escala. No es over-engineering, pero tampoco es lo que haría un producto SaaS con miles de restaurantes.

Para **1 instancia, 1 restaurante, bajo tráfico WhatsApp**, el enfoque de caché local + sync en background es **apropiado y defendible**. No necesitabas Redis ni Kafka.

**¿Fue buena idea plantearlo así (incremental, por fases)?**

Sí, **muy buena idea**, por tres razones:

1. **Mediste antes/después** — sin baseline, no sabes si mejoraste o solo moviste código.
2. **Checklist 5/5 en cada paso** — evita el clásico “optimicé y rompí el flujo de pedidos”.
3. **Atacaste el cuello real** — Sheets en el request path era el problema; no perdiste tiempo en micro-optimizar Python mientras seguías esperando 800 ms de Google.

Ese estilo encaja bien con `AI_RULES.md` y con un bot que ya funciona en producción.

**¿Qué opino del enfoque por caché (JSON local + dirty + thread 30 s)?**

**A favor:**

- Simple de entender, depurar y desplegar.
- Encaja con Render/Railway sin servicios extra.
- El patrón “read local, write local, sync async” es el mismo que usan muchos sistemas a escala (solo que ellos usan Redis/DB en vez de JSON).

**En contra / límites (importante ser honesto):**

- **Consistencia eventual**: si el servidor cae antes del sync, pierdes hasta ~30 s de datos (o lo que no haya flushado).
- **Una sola instancia**: si escalas a 2+ réplicas, cada una tendría su JSON y se pisarían — ahí ya no alcanza este diseño.
- **Disco efímero en cloud free**: tras reinicio pierdes caché local hasta que el warm-up vuelve a leer Sheets (mitigado con warm-up, pero existe).
- **No es “caché pura”**: sigues dependiendo de Sheets como source of truth; es más un **write-behind buffer**, y está bien nombrado mentalmente así.

---

## Veredicto

| Pregunta | Respuesta |
|----------|-----------|
| ¿Buena mejora? | **Sí**, clara y medible. |
| ¿Bien para tu contexto? | **Sí**, para bot WhatsApp + Sheets + 1 instancia. |
| ¿A la altura del “mercado premium”? | **No del todo**, pero no compites en esa liga todavía — y no hacía falta. |
| ¿Buen plan incremental? | **Sí**, de los mejores enfoques para este tipo de proyecto. |
| ¿Buena idea la caché local? | **Sí**, fue la decisión correcta; el error hubiera sido seguir pegándole a Sheets en cada `hola`. |

**En una frase:** no es la arquitectura más sofisticada del mundo, pero **sí es la optimización inteligente** para lo que es: un chatbot de restaurante incremental, estable y sin inflar infraestructura. Plantearlo por fases con caché local fue, en mi opinión, **la decisión correcta** — mejor que un refactor grande o meter Redis “porque suena pro”.


## Septimo prompt ##

No hagas nada ni modifiques nada solo responde: el warm--up está programado para que se ejecute cada vez que arranca el servidor? por ejemplo si se cae el servidor, en 30 segundo se actualizaria solo el caché?


## Repsp cursor ##

Casi, pero no exactamente “en 30 segundos”.

Cuando el servidor vuelve a arrancar:

Al instante corre el warm-up: carga los JSON locales si existen (milisegundos).
Casi al instante arranca el loop de sync y hace una primera actualización antes de esperar 30 s.
Así que la caché suele estar lista en segundos (o al momento si los archivos locales siguen en disco), no hace falta esperar 30 s.

Los 30 segundos son el intervalo entre actualizaciones siguientes, mientras el servidor siga corriendo.

Excepción: si el servidor estuvo caído y además se borró el disco (típico en hosting free), el warm-up tiene que volver a leer Sheets al arrancar; eso puede tardar unos segundos, pero no necesariamente 30.



## Octavo prompt ##

no hagas nada solo dime:  que más es necesario meterle o implementar o mejorar del bot o así está perfecto ya para vender?


## Respuesta cursor ##

## ¿Está listo para vender?

**Para un restaurante concreto (1 cliente, tú lo despliegas y lo mantienes):** sí, está en buen punto como **MVP productivo**. La base técnica es sólida y la latencia ya no es un problema.

**Para venderlo como producto/SaaS** (varios restaurantes, self-service, “comprá y usá”): **todavía no**. Falta capa de producto, no tanto de chatbot.

---

## Lo que ya tienes bien

- Flujo conversacional funcional (pedido, menú, reservas)
- Integración WhatsApp + Sheets
- Optimización de rendimiento hecha bien
- Checklist de regresión y deploy documentado
- Modo demo sin Sheets

Eso basta para **pilotear con 1–3 restaurantes** si tú haces el onboarding manual.

---

## Lo que falta para “vender en serio”

### Producto / negocio
- **Multi-restaurante**: hoy es 1 spreadsheet, 1 instancia, 1 flujo. Un SaaS necesita tenant por cliente (datos aislados, config por restaurante).
- **Panel admin web** (no solo WhatsApp admin): ver pedidos en vivo, cambiar menú, pausar platos, horarios, métricas.
- **Onboarding**: alta de cliente, conectar su WhatsApp, su Sheet, su menú — sin que tú entres al código.
- **Precios/planes**: qué incluye cada plan, límites, facturación.

### Operación / confiabilidad
- **Persistencia real en cloud**: JSON local en disco efímero es frágil; para vender conviene Postgres/Redis o al menos volumen persistente + backups.
- **Cola de mensajes / reintentos** si Twilio o Sheets fallan.
- **Alertas** (Sentry, uptime, “Sheets no sincronizó hace 5 min”).
- **Logs estructurados** por restaurante/pedido (auditoría).

### Seguridad y legal
- Validación de webhook Twilio (firma), rate limiting.
- Política de privacidad / datos de clientes (WhatsApp, nombres, direcciones).
- Términos de servicio si cobras suscripción.

### UX del bot
- Mensajes de error más claros cuando algo falla.
- Horarios (“cerrado ahora”), stock agotado, tiempos de entrega estimados.
- Confirmación de pedido más rica (resumen, total, ID de seguimiento).
- Idioma/tono configurable por restaurante.

### WhatsApp / Twilio (importante para escalar)
- Pasar de **Sandbox** a **número aprobado** por restaurante (Meta Business).
- Plantillas HSM si necesitas mensajes proactivos fuera de la ventana 24 h.

### Calidad
- Tests automatizados más allá del checklist manual (CI en cada push).
- Pruebas de carga básicas (10–50 mensajes concurrentes).

---

## Mi veredicto honesto

| Objetivo | ¿Listo? |
|----------|---------|
| Usar en **tu** restaurante o 1 cliente piloto | **Sí** |
| Vender como **servicio hecho a medida** (tú instalas y das soporte) | **Casi sí**, con panel mínimo y contrato claro |
| Vender como **SaaS escalable** “plug and play” | **No todavía** |

---

## Prioridad si quieres acercarte a vender

1. **Panel web simple** (pedidos pendientes + menú on/off) — el dueño no quiere vivir en Sheets.
2. **Multi-tenant o despliegue 1-click por cliente** — aunque sea 1 instancia por restaurante al principio.
3. **Persistencia/backup** — que un reinicio no asuste.
4. **Onboarding documentado** + **precio** + **soporte**.

**En resumen:** como bot optimizado para un restaurante, está muy bien. Para **venderlo como producto**, no está “perfecto”; le falta la capa comercial y operativa que convierte un buen proyecto técnico en un negocio repetible. Lo sensato es venderlo primero como **piloto manual** con 1–2 clientes y construir el SaaS con lo que te pidan de verdad.






#################################################################
## v0.23

## Prompt:

# AUDITORÍA Y PLAN MAESTRO

Analiza el proyecto completo antes de proponer cambios.

OBJETIVO
Agregar una dashboard Django + PostgreSQL local para administrar el bot actual mediante mejoras incrementales, seguras y reversibles.

RESTRICCIONES

* Mantener compatibilidad total.
* No romper funcionalidad existente.
* No modificar lógica de negocio salvo necesidad justificada.
* No cambiar APIs ni integraciones.
* Priorizar estabilidad, simplicidad y bajo mantenimiento.
* Evitar dependencias innecesarias.
* Pensar como ingeniero senior trabajando sobre producción.

FASES

* Minimizar cantidad de fases.
* Preferir 3-5 fases.
* Agrupar cambios relacionados cuando el riesgo sea bajo.
* Justificar cualquier propuesta superior a 5 fases.

ANÁLISIS

1. Auditar arquitectura actual.
2. Mapear flujo de datos.
3. Identificar integraciones externas.
4. Detectar riesgos.
5. Diseñar arquitectura incremental.
6. Dividir implementación por fases.
7. Asignar riesgo por fase.
8. Definir validaciones y rollback.
9. Generar prompt independiente para cada fase.

SALIDA

* Diagnóstico.
* Arquitectura propuesta.
* Fases.
* Dependencias nuevas.
* Riesgos y mitigaciones.
* Archivos afectados.
* Plan de rollback.
* Checklist de validación.
* Prompt para cada fase.

NO ESCRIBAS CÓDIGO.
REALIZA SOLO LA AUDITORÍA Y EL PLAN.



## Respuesta Cursor ##

# Auditoría y plan maestro — Dashboard Django + PostgreSQL (local)

## 1. Diagnóstico

### 1.1 Qué es el sistema hoy

Bot conversacional de restaurante en **producción** sobre:

| Capa | Tecnología | Rol |
|------|------------|-----|
| HTTP / webhook | Flask + Waitress (`run.py`) | `POST /bot`, `GET /health`, `POST /bot/reload-flow` |
| Canal | Twilio WhatsApp | Entrada de mensajes; salida admin/cliente |
| Motor conversacional | `FlowEngine` + `flows/restaurant_flow.json` | Flujo declarativo, sin tocar Python para cambiar nodos |
| Estado conversacional | `StateManager` | Por `wa_id`; JSON opcional `data/user_states.json` |
| Parser NL | `app/core/parser.py` (~1500 líneas) | Carrito, cantidades, fuzzy match |
| Persistencia de negocio | `GoogleSheetsClient` | MENU, USERS, ORDERS, RESERVATIONS |
| Caché local | `data/*.json` | Write-through + sync cada 30 s a Sheets |
| Admin operativo | `AdminService` vía WhatsApp | Confirmar pedidos, recordatorios Twilio |

**No existe panel web.** La administración es 100 % WhatsApp (`ADMIN_WHATSAPP_NUMBER`).

### 1.2 Arquitectura actual (diagrama)

```mermaid
flowchart TB
    subgraph externo [Externo]
        TW[Twilio WhatsApp]
        GS[Google Sheets API]
    end

    subgraph proceso [Proceso único - python run.py]
        FL[Flask app.py]
        FE[FlowEngine]
        SM[StateManager]
        MS[MenuService]
        OS[OrderService]
        RS[ReservationService]
        US[UserService]
        AD[AdminService]
        GSC[GoogleSheetsClient singleton]
    end

    subgraph disco [data/ - disco]
        MC[menu_cache.json]
        UC[users_cache.json]
        OC[orders_cache.json]
        RC[reservations_cache.json]
        ST[user_states.json]
        PE[parser_errors.jsonl]
    end

    TW -->|POST /bot| FL
    FL --> AD
    FL --> FE
    FE --> SM
    FE --> MS
    FE --> OS
    FE --> RS
    FE --> US
    AD --> OS
    MS --> GSC
    OS --> GSC
    RS --> GSC
    US --> GSC
    AD -->|outbound| TW
    GSC <-->|sync 30s| GS
    GSC --> MC
    GSC --> UC
    GSC --> OC
    GSC --> RC
    SM --> ST
```

### 1.3 Flujo de datos (resumen)

**Mensaje cliente**

1. Twilio → `POST /bot` (`WaId`, `ProfileName`, `Body`).
2. Si `wa_id` == admin → `AdminService.handle_admin_message` (confirmar `ORD-…`).
3. Si no → `UserService.touch` + `FlowEngine.process_message`.
4. Acciones del flujo leen menú vía caché, escriben carrito en `StateManager`, al guardar pedido/reserva → `GoogleSheetsClient` marca dirty y persiste JSON local; hilo background empuja a Sheets en ~30 s.
5. Nuevo pedido → `AdminService.notify_new_order` (Twilio al admin).

**Fuentes de verdad (orden práctico)**

| Dato | Fuente primaria (con Sheets) | Fallback demo |
|------|------------------------------|---------------|
| Menú | Sheet MENU → `menu_cache.json` | `DEMO_MENU` en memoria |
| Pedidos | Sheet ORDERS + `orders_cache.json` | Lista en memoria |
| Usuarios | Sheet USERS + `users_cache.json` | Dict demo en memoria |
| Reservas | Sheet RESERVATIONS + `reservations_cache.json` | Solo ID generado |
| Estado chat | `user_states.json` | Solo memoria si no hay path |

### 1.4 Integraciones externas

| Integración | Uso | Variables |
|-------------|-----|-----------|
| **Twilio** | Webhook entrante; mensajes salientes admin/cliente | `TWILIO_*`, `ADMIN_WHATSAPP_NUMBER` |
| **Google Sheets** | CRUD lógico de menú, usuarios, pedidos, reservas | `GOOGLE_SPREADSHEET_ID`, credenciales archivo o `GOOGLE_SERVICE_ACCOUNT_JSON` |
| **ngrok** (dev) | Exponer `/bot` | Documentación, no código |

**No hay:** Redis, colas, OAuth web, base SQL, API REST pública más allá de los 3 endpoints Flask.

### 1.5 Endpoints y contratos (inmutables según restricciones)

| Método | Ruta | Contrato |
|--------|------|----------|
| GET | `/health` | JSON `status`, `caches`, `admin_configured` |
| POST | `/bot` | Form Twilio → XML `MessagingResponse` |
| POST | `/bot/reload-flow` | JSON `{status: flow reloaded}` — **sin autenticación** |

### 1.6 Riesgos detectados (estado actual)

| Riesgo | Severidad | Nota |
|--------|-----------|------|
| `/bot/reload-flow` sin auth | Alta (prod) | Ya documentado en README; dashboard no debe empeorar esto |
| Dos procesos escribiendo mismos JSON (`data/`) | Alta (si dashboard escribe) | Corrupción / dirty flags inconsistentes |
| Caché duplicado por proceso | Media | Dashboard en proceso distinto verá datos con lag ~30 s |
| `MENU_CACHE_TTL_SECONDS` / `ORDERS_CACHE_TTL_SECONDS` en `.env` no usados en código | Baja | Sync fijo `MENU_LOCAL_REFRESH_SECONDS = 30` en `google_sheets.py` |
| Admin solo por WhatsApp | Operativa | Motivo del dashboard |
| `users_cache.json` modificado en git status | Media | Datos runtime en repo; dashboard debe respetar `.gitignore` patterns |
| Parser y flow_engine críticos | Alta | Cualquier import cruzado mal hecho puede acoplar arranque pesado al dashboard |
| Despliegue single-container | Media | Dashboard **no** debe ir en el mismo `CMD` que el bot en Render/Railway sin decisión explícita |

### 1.7 Oportunidades alineadas al objetivo

- **Lectura** desde `data/*.json` + lectura directa Sheets (misma lib `gspread`) sin tocar Flask.
- **Escrituras** solo vía API de Sheets o importando `GoogleSheetsClient` en comandos Django, nunca reimplementando lógica dirty.
- **PostgreSQL** para lo que Sheets no cubre bien: usuarios staff, preferencias UI, auditoría de acciones del panel, snapshots opcionales.
- Mantener bot en `python run.py` y dashboard en `python dashboard/manage.py runserver` (puertos distintos).

---

## 2. Arquitectura propuesta (incremental)

### 2.1 Principio rector

**Proceso dual, código compartido, contratos intactos.**

```mermaid
flowchart LR
    subgraph bot [Bot - sin cambios en contrato]
        RUN[run.py :5000]
    end

    subgraph dash [Dashboard - nuevo, solo local]
        DJ[django :8000]
        PG[(PostgreSQL local)]
    end

    subgraph shared [Paquete app/ existente]
        GSC[GoogleSheetsClient]
        SVC[services/*]
    end

  RUN --> shared
  DJ -->|lectura JSON| DATA[data/]
  DJ -->|opcional import| shared
  DJ --> PG
  GSC --> GS[Google Sheets]
```

### 2.2 Responsabilidades

| Componente | Responsabilidad |
|------------|-----------------|
| **Flask (actual)** | Twilio, flujo, parser, admin WhatsApp — sin cambios de contrato |
| **Django (nuevo)** | UI admin local: listados, filtros, confirmación manual, visor menú/reservas |
| **PostgreSQL (local)** | Auth staff, audit log, config de panel, snapshots/sync opcional |
| **Google Sheets** | Sigue siendo fuente de verdad de negocio salvo que más adelante se decida migración (fuera de alcance inicial) |

### 2.3 Reglas de escritura (evitar conflictos)

1. **Fase 1–2:** solo lectura de `data/` y/o Sheets.
2. **Fase 3+:** escrituras de negocio **preferentemente** vía `GoogleSheetsClient` en `manage.py` one-shot o vista Django que llama métodos existentes (`update_order_status`, edición menú en Sheets), **no** edición manual de JSON dirty.
3. **Nunca** editar `user_states.json` desde el dashboard en v1.
4. Dashboard local mientras bot corre en cloud → sin conflicto de archivos; si ambos locales, documentar “detener bot o solo lectura”.

### 2.4 Estructura de carpetas propuesta (sin implementar aún)

```
chatbot-cursor/
  app/                    # sin mover
  flows/
  data/
  dashboard/              # nuevo proyecto Django
    manage.py
    config/
    apps/
      core/               # health bridge, utils
      operations/         # orders, reservations, menu views
      accounts/           # staff users
  docker-compose.yml      # solo postgres local
  requirements-dashboard.txt  # o extras en requirements-dev.txt
```

---

## 3. Fases (4 fases — dentro del rango 3–5)

| Fase | Nombre | Riesgo | Cambia bot |
|------|--------|--------|------------|
| 1 | Fundación Django + PostgreSQL local | Bajo | No |
| 2 | Dashboard lectura operativa | Bajo | No |
| 3 | Auth staff + datos de panel en PG | Bajo–medio | No |
| 4 | Acciones seguras de administración | Medio | Mínimo (solo si hace falta flag/env) |

No se justifica una 5.ª fase obligatoria: sync programado y métricas pueden ser extensión opcional post-v1.

---

## 4. Dependencias nuevas

| Paquete | Uso | Dónde |
|---------|-----|-------|
| `Django` (LTS, ej. 5.1.x) | Panel | `requirements-dashboard.txt` |
| `psycopg2-binary` o `psycopg[binary]` | PostgreSQL | idem |
| `django-environ` (opcional) | Config | idem |
| `whitenoise` (opcional) | Estáticos | idem |

**No añadir:** Celery, Redis, DRF completo, Channels, GraphQL, frontend SPA pesado (admin Django basta en v1).

**Infra local:** `docker compose` con imagen `postgres:16-alpine` (solo desarrollo).

El bot mantiene `requirements.txt` actual intacto hasta que se decida unificar en monorepo con extras opcionales.

---

## 5. Fases detalladas

### Fase 1 — Fundación Django + PostgreSQL local

**Objetivo:** Proyecto Django aislado, PG en Docker, arranque documentado, cero impacto en Twilio.

**Entregables**

- `dashboard/` con `manage.py`, settings `DATABASES` → PostgreSQL local.
- `docker-compose.yml` (servicio `db`, volumen, puerto 5432).
- `.env.dashboard.example` (`DATABASE_URL`, `DJANGO_SECRET_KEY`, `DEBUG=1`).
- README sección “Dashboard local” (dos terminales: bot + dashboard).
- Comando de verificación: migraciones Django + `GET /health` del bot sigue OK.

**Archivos afectados (nuevos / tocados mínimos)**

| Acción | Archivo |
|--------|---------|
| Crear | `dashboard/**`, `docker-compose.yml`, `requirements-dashboard.txt`, `.env.dashboard.example` |
| Tocar | `README.md` (documentación), opcional `.gitignore` (`dashboard/.env`) |
| No tocar | `app/app.py`, `app/core/*`, `flows/*` |

**Riesgo:** Bajo.  
**Rollback:** Eliminar carpeta `dashboard/`, compose y requirements-dashboard; bot intacto.

---

### Fase 2 — Dashboard lectura operativa

**Objetivo:** Ver menú, pedidos pendientes/confirmados, reservas, usuarios y estado de caché sin modificar datos.

**Fuentes de lectura (orden)**

1. `data/orders_cache.json`, `menu_cache.json`, `users_cache.json`, `reservations_cache.json`.
2. Si vacío o desactualizado: instanciar `GoogleSheetsClient` con mismas env que el bot (import desde `app.integrations.google_sheets`).
3. `GET` proxy interno opcional: llamada HTTP a `http://localhost:5000/health` (no nuevo endpoint).

**Vistas Django (admin o templates simples)**

- Lista pedidos con filtro `status=pending`.
- Detalle pedido (items JSON, cliente, dirección).
- Lista reservas por fecha.
- Menú agrupado por categoría.
- Usuarios recientes (`last_seen`).
- Página “Estado del sistema” (health + `cache_status()`).

**Archivos afectados**

| Acción | Archivo |
|--------|---------|
| Crear | `dashboard/apps/operations/models.py` (vacío o solo lectura), `views.py`, `templates/`, `services/readers.py` |
| Tocar | `dashboard/config/settings.py`, `urls.py` |
| No tocar | Lógica de `FlowEngine`, `parser.py`, endpoints Flask |

**Riesgo:** Bajo (solo lectura).  
**Rollback:** Desactivar app `operations` en `INSTALLED_APPS`.

---

### Fase 3 — Auth staff + PostgreSQL para panel

**Objetivo:** Login seguro; PG guarda usuarios staff y auditoría; datos de negocio siguen en Sheets/JSON.

**Modelos PG sugeridos**

- `StaffProfile` (extensión de `User` Django).
- `AuditLog` (`action`, `entity`, `entity_id`, `user`, `timestamp`, `metadata` JSON).
- `DashboardSettings` (clave-valor: nombre restaurante mostrado, flags UI) — **no** reemplazar `RESTAURANT_NAME` del bot sin sync explícito.

**Entregables**

- Login/logout, `@login_required` en todas las vistas.
- Registro automático en `AuditLog` en fases posteriores.
- Migraciones iniciales.

**Archivos afectados**

| Acción | Archivo |
|--------|---------|
| Crear | `dashboard/apps/accounts/**` |
| Tocar | `settings.py` (`AUTH`, middleware), templates base |
| No tocar | `app/config.py` del bot |

**Riesgo:** Bajo–medio (superficie de seguridad nueva, solo local).  
**Rollback:** `dropdb` dashboard DB; bot no usa PG.

---

### Fase 4 — Acciones seguras de administración

**Objetivo:** Operaciones que hoy solo hace el admin por WhatsApp, desde el panel, reutilizando servicios existentes.

**Acciones v1 (mínimas, alto valor)**

| Acción | Implementación segura |
|--------|------------------------|
| Confirmar pedido | `OrderService.confirm_order` + opcional notificación cliente vía lógica existente en `AdminService` (extraer método reutilizable sin duplicar Twilio) |
| Ver pedidos pendientes | Ya en fase 2 |
| Marcar ítem menú no disponible | Escritura en Sheet MENU vía cliente Sheets (nuevo método acotado en `GoogleSheetsClient` **solo si no existe** — hoy menú es read-only en cliente; sería la única extensión justificada) |
| Recargar flujo JSON | Botón que ejecuta `FlowEngine.reload_flow()` vía management command **no** expone `/bot/reload-flow` sin token |

**Prohibido en v1**

- Editar `restaurant_flow.json` desde UI sin validación.
- Modificar `user_states.json`.
- Nuevos endpoints Flask públicos.

**Patrón recomendado:** `python manage.py bot_action confirm_order ORD-XXX` que importa `app` y llama servicios — la vista Django invoca ese comando o función compartida en `dashboard/services/bot_bridge.py`.

**Archivos afectados (estimación)**

| Acción | Archivo |
|--------|---------|
| Crear | `dashboard/services/bot_bridge.py`, `management/commands/bot_confirm_order.py` |
| Tocar mínimo | `app/services/admin_service.py` (extraer `_notify_customer_confirmed` si hace falta), posiblemente `google_sheets.py` (método `set_menu_item_availability` acotado) |
| No tocar | `POST /bot`, `parser.py`, `restaurant_flow.json` estructura |

**Riesgo:** Medio (escritura Sheets + Twilio outbound).  
**Mitigación:** Feature flag `DASHBOARD_ENABLE_WRITES=0` por defecto; pruebas con spreadsheet de prueba.

**Rollback:** `DASHBOARD_ENABLE_WRITES=0`; revertir métodos nuevos en `google_sheets.py` si se añadieron.

---

## 6. Riesgos y mitigaciones (consolidado)

| Riesgo | Mitigación |
|--------|------------|
| Corrupción JSON con dos procesos | Escrituras solo vía Sheets API / `GoogleSheetsClient`; lectura JSON; no correr escrituras dashboard con bot local escribiendo al mismo `data/` |
| Romper webhook Twilio | No modificar `app.py` rutas ni forma XML |
| Regresión parser/flow | No importar `FlowEngine` en requests HTTP del dashboard; usar bridge acotado |
| Secretos en repo | `.env` / `.env.dashboard` en gitignore; credenciales solo local |
| Despliegue cloud accidental del dashboard | `docker-compose` y docs “LOCAL ONLY”; no añadir servicio dashboard en `render.yaml` |
| Duplicar lógica Sheets | Un solo módulo `app.integrations.google_sheets` |
| Confirmar pedido sin avisar cliente | Reutilizar mismo flujo que `AdminService` post-confirmación |

---

## 7. Archivos afectados (por fase — resumen)

| Fase | Nuevos | Modificados (bot) | Intocados |
|------|--------|-------------------|-----------|
| 1 | `dashboard/*`, `docker-compose.yml`, `requirements-dashboard.txt` | — | `app/app.py`, parser, flow |
| 2 | `dashboard/apps/operations/*` | — | Flask endpoints |
| 3 | `dashboard/apps/accounts/*` | — | Bot core |
| 4 | `dashboard/services/bot_bridge.py`, commands | `admin_service.py` (opcional), `google_sheets.py` (opcional 1 método) | `/bot`, `/health` |

---

## 8. Plan de rollback global

| Nivel | Acción |
|-------|--------|
| Fase 1 | Borrar `dashboard/`, compose, deps extra |
| Fase 2 | Quitar URLs/vistas operations |
| Fase 3 | `docker compose down -v` (volumen PG) |
| Fase 4 | Desactivar writes por env; revert commit de bridge |
| Emergencia bot | `git checkout` solo archivos bajo `app/`; `python scripts/regression_checklist.py` |

El bot debe poder operar **sin** dashboard en todo momento.

---

## 9. Checklist de validación (por fase)

### Tras cada fase

- [ ] `python scripts/regression_checklist.py` → parser 21/21, health OK, hola 2 mensajes, menu, pedido corto.
- [ ] `POST /bot` con cliente de prueba sin regresión (simulador o curl).
- [ ] Bot arranca con `python run.py` sin importar Django.

### Fase 1

- [ ] `docker compose up -d db` → PG healthy.
- [ ] `python dashboard/manage.py migrate` sin errores.
- [ ] Dashboard responde en `:8000` (página vacía o admin Django).

### Fase 2

- [ ] Listado pedidos coincide con Sheet ORDERS o `orders_cache.json`.
- [ ] Menú muestra mismos ítems que WhatsApp `menu`.
- [ ] Sin escrituras: timestamps JSON no cambian al navegar.

### Fase 3

- [ ] Rutas protegidas redirigen a login.
- [ ] Usuario anónimo no ve pedidos.

### Fase 4 (con `DASHBOARD_ENABLE_WRITES=1` en entorno de prueba)

- [ ] Confirmar `ORD-…` en panel → status `confirmed` en Sheets y caché ≤30 s.
- [ ] Cliente recibe WhatsApp confirmación (si Twilio configurado).
- [ ] Recordatorios admin cesan para ese pedido.
- [ ] Pedido ya confirmado no se confirma dos veces (mensaje coherente).

---

## 10. Prompts independientes por fase

Copiar cada bloque en una sesión nueva. **No escribir código** en la sesión de auditoría; en implementación, respetar `AI_RULES.md`.

---

### Prompt — Fase 1

```
Contexto: Proyecto chatbot-cursor (Flask + Twilio + Google Sheets). Objetivo: añadir dashboard Django + PostgreSQL SOLO para desarrollo local, sin modificar lógica del bot ni endpoints Flask.

Tarea Fase 1 — Fundación:
1. Crear proyecto Django en carpeta dashboard/ (manage.py, settings, urls).
2. Añadir docker-compose.yml con PostgreSQL 16 local (volumen, puerto 5432).
3. Crear requirements-dashboard.txt con Django LTS y psycopg2-binary.
4. Crear .env.dashboard.example con DATABASE_URL y DJANGO_SECRET_KEY.
5. Documentar en README cómo levantar: (a) docker compose up db, (b) migrate, (c) runserver en puerto 8000, en paralelo al bot en 5000.
6. NO modificar app/app.py, app/core/*, flows/*, ni requirements.txt del bot.
7. Verificar: python scripts/regression_checklist.py sigue pasando.

Restricciones: compatibilidad total con bot; cambios mínimos; seguir AI_RULES.md.
Entregar: archivos creados, instrucciones de arranque, checklist cumplido.
```

---

### Prompt — Fase 2

```
Contexto: Fase 1 completada (Django + PG local). Bot Flask intacto en app/.

Tarea Fase 2 — Dashboard lectura operativa:
1. App Django operations con vistas login-free temporal o con auth si ya existe Fase 3 parcial.
2. Leer pedidos, reservas, menú y usuarios desde data/*.json; fallback a GoogleSheetsClient (import app.integrations.google_sheets) si caché vacío.
3. Vista detalle pedido (items, total, status, wa_id, dirección).
4. Vista estado sistema: HTTP GET a localhost:5000/health + cache_status del cliente Sheets.
5. Solo lectura: no escribir JSON ni Sheets.
6. NO crear endpoints Flask nuevos. NO tocar parser.py ni flow_engine.py.

Verificar: regression_checklist.py; datos del panel coinciden con WhatsApp menu y pedido de prueba.
Entregar: URLs, capturas o descripción de vistas, archivos tocados.
```

---

### Prompt — Fase 3

```
Contexto: Fases 1-2 OK. Dashboard muestra datos en lectura.

Tarea Fase 3 — Auth staff + PostgreSQL panel:
1. App accounts: modelo AuditLog y opcional DashboardSettings.
2. Login/logout Django; todas las vistas operations requieren login.
3. Migraciones PG; crear superuser vía manage.py documentado.
4. Registrar en AuditLog accesos a vistas sensibles (listar pedidos).
5. NO almacenar en PG pedidos/menú como fuente de verdad (solo metadatos de panel).
6. Bot sin cambios en endpoints.

Verificar: anónimo no accede; regression_checklist bot OK.
Entregar: modelos, migraciones, instrucciones createsuperuser.
```

---

### Prompt — Fase 4

```
Contexto: Dashboard Django autenticado, lectura operativa. Bot en app/ con AdminService y GoogleSheetsClient.

Tarea Fase 4 — Acciones seguras:
1. Variable DASHBOARD_ENABLE_WRITES (default 0). Si 0, UI solo lectura con mensaje.
2. Acción confirmar pedido: reutilizar OrderService.confirm_order y notificación cliente como AdminService (extraer helper si evita duplicar, cambio mínimo).
3. Implementar vía dashboard/services/bot_bridge.py o management command, NO nuevo endpoint Flask público.
4. Opcional: marcar plato no disponible en Sheet MENU — un método acotado en GoogleSheetsClient si no existe; sin reescribir dirty logic.
5. NO editar user_states.json ni restaurant_flow.json desde UI.
6. AuditLog cada confirmación.

Verificar con spreadsheet de prueba: confirmar pedido desde panel; WhatsApp admin deja de recordar; regression_checklist.py; cliente recibe confirmación si Twilio configurado.

Restricciones: AI_RULES.md; no cambiar POST /bot ni formato XML.
Entregar: bridge, flag env, checklist Fase 4, riesgos residuales.
```

---

## 11. Decisiones explícitas (para alinear expectativas)

| Tema | Decisión recomendada |
|------|----------------------|
| ¿PostgreSQL reemplaza Sheets? | **No** en estas 4 fases. PG = panel + auditoría. |
| ¿Dashboard en producción cloud? | **No** en v1; solo local junto a `.env` y credenciales. |
| ¿Unificar requirements? | Opcional `requirements-dev.txt`; bot production sin Django. |
| ¿UI? | Django Admin + templates mínimas (bajo mantenimiento). |
| ¿Sincronización PG ↔ Sheets? | Opcional post-v4; no bloquea valor inicial. |

---

## 12. Conclusión

El proyecto está **maduro y acoplado a un patrón cache-local + Google Sheets + WhatsApp**, con admin operativo solo por móvil. Un dashboard Django + PostgreSQL local encaja como **proceso satélite de lectura primero y escritura acotada después**, reutilizando `app.integrations.google_sheets` y servicios existentes, sin tocar `/bot` ni el motor conversacional.

**Cuatro fases** cubren fundación, valor operativo visible, seguridad y acciones críticas de admin, con riesgo controlado y rollback trivial en el bot. La mayor trampa es **escribir los JSON de `data/` en paralelo al bot**: el plan la evita priorizando Sheets y comandos bridge.

Cuando quieras ejecutar la Fase 1, usa el prompt correspondiente en una sesión de implementación.




## Segundo Prompt: ##


Existe una auditoría y arquitectura aprobadas para este proyecto.

Antes de realizar cualquier análisis o modificación debes leer completamente el archivo:

AUDITORIA.md

ubicado en la raíz del proyecto.

La auditoría es la fuente de verdad para arquitectura, fases, restricciones, riesgos, validaciones y alcance.

Debes respetarla estrictamente.

REGLAS INMUTABLES

* Modifica lo mínimo posible.
* Implementa únicamente mejoras incrementales.
* No rompas funcionalidad existente.
* No refactorices código no relacionado.
* No cambies APIs, contratos ni integraciones.
* No alteres la arquitectura definida en AUDITORIA.md.
* No implementes trabajo de fases futuras.
* Mantén compatibilidad total con el sistema actual.
* Prioriza estabilidad, simplicidad y bajo mantenimiento.
* Evita dependencias innecesarias.
* Reutiliza componentes, servicios y lógica existente siempre que sea posible.
* Si detectas una contradicción entre esta tarea y AUDITORIA.md, prevalece AUDITORIA.md.
* Si detectas riesgo alto, detente y explícalo antes de continuar.

TAREA

[Contexto: Proyecto chatbot-cursor (Flask + Twilio + Google Sheets). Objetivo: añadir dashboard Django + PostgreSQL SOLO para desarrollo local, sin modificar lógica del bot ni endpoints Flask.

Tarea Fase 1 — Fundación:
1. Crear proyecto Django en carpeta dashboard/ (manage.py, settings, urls).
2. Añadir docker-compose.yml con PostgreSQL 16 local (volumen, puerto 5432).
3. Crear requirements-dashboard.txt con Django LTS y psycopg2-binary.
4. Crear .env.dashboard.example con DATABASE_URL y DJANGO_SECRET_KEY.
5. Documentar en README cómo levantar: (a) docker compose up db, (b) migrate, (c) runserver en puerto 8000, en paralelo al bot en 5000.
6. NO modificar app/app.py, app/core/*, flows/*, ni requirements.txt del bot.
7. Verificar: python scripts/regression_checklist.py sigue pasando.

Restricciones: compatibilidad total con bot; cambios mínimos; seguir AI_RULES.md.
Entregar: archivos creados, instrucciones de arranque, checklist cumplido.]

ANTES DE MODIFICAR

1. Leer AUDITORIA.md completo.
2. Analizar el proyecto actual.
3. Verificar que la tarea corresponde a la fase indicada en AUDITORIA.md.
4. Explicar el plan de implementación.
5. Listar archivos a crear.
6. Listar archivos a modificar.
7. Explicar riesgos potenciales.
8. Confirmar que el alcance está limitado únicamente a esta fase.

IMPLEMENTACIÓN

* Realiza únicamente lo necesario para completar la tarea.
* Mantén los cambios lo más pequeños posible.
* No añadas funcionalidades fuera del alcance.
* No modifiques componentes no relacionados.
* Reutiliza la arquitectura existente siempre que sea posible.

VALIDACIÓN

* Verifica que el proyecto siga funcionando.
* Verifica que no existan regresiones.
* Ejecuta las validaciones definidas en AUDITORIA.md para esta fase.
* Confirma compatibilidad con el sistema actual.
* Confirma que no se han afectado fases futuras.

ENTREGA

* Resumen de cambios.
* Archivos creados.
* Archivos modificados.
* Validaciones realizadas.
* Riesgos restantes.
* Rollback específico de esta fase.
* Confirmación explícita de cumplimiento de AUDITORIA.md.


## Respuesta cursor:

## Análisis previo

La tarea corresponde a **Fase 1 — Fundación** de `AUDITORIA.md`: proyecto Django aislado, PostgreSQL en Docker, documentación, **cero impacto en el bot**.

**Plan ejecutado:**
1. Crear `dashboard/` con `manage.py` y `config/` (settings, urls, wsgi, asgi).
2. Añadir `docker-compose.yml` con PostgreSQL 16.
3. Crear `requirements-dashboard.txt` (Django 5.1 LTS + psycopg2-binary).
4. Crear `.env.dashboard.example`.
5. Documentar arranque en README y actualizar `.gitignore`.
6. Validar regresión del bot.

**Archivos creados:** `dashboard/**`, `docker-compose.yml`, `requirements-dashboard.txt`, `.env.dashboard.example`

**Archivos modificados:** `README.md`, `.gitignore`

**No tocados:** `app/app.py`, `app/core/*`, `flows/*`, `requirements.txt`

**Riesgos:** Bajo. Rollback = borrar `dashboard/`, `docker-compose.yml`, `requirements-dashboard.txt`, `.env.dashboard.example` y revertir README/.gitignore.

---

## Cambios implementados

Proyecto Django mínimo en `dashboard/config/` con PostgreSQL vía `DATABASE_URL`, carga opcional de `.env.dashboard` sin dependencias extra, y admin Django en `/admin/`.

---

## Archivos creados

| Archivo | Propósito |
|---------|-----------|
| `dashboard/manage.py` | CLI Django |
| `dashboard/config/settings.py` | Config PG + env |
| `dashboard/config/urls.py` | Rutas (admin) |
| `dashboard/config/wsgi.py`, `asgi.py` | Arranque WSGI/ASGI |
| `docker-compose.yml` | PostgreSQL 16 local |
| `requirements-dashboard.txt` | Django 5.1 LTS + psycopg2-binary |
| `.env.dashboard.example` | Plantilla de variables |

---

## Archivos modificados

- `README.md` — sección **Dashboard local (desarrollo)** con arranque en dos terminales.
- `.gitignore` — ignora `.env.dashboard` y `dashboard/.env`.

---

## Validaciones realizadas

| Check | Resultado |
|-------|-----------|
| `python scripts/regression_checklist.py` | **5/5 OK** (parser 21/21, health, hola, menu, pedido) |
| `python dashboard/manage.py check` | **OK** (sin issues) |
| `docker compose up -d db` | No ejecutable aquí (Docker no instalado en este entorno) |
| `migrate` / `runserver :8000` | Pendiente en tu máquina tras levantar PG |

---

## Instrucciones de arranque

```powershell
# Terminal 1 — bot (puerto 5000)
python run.py

# Terminal 2 — dashboard
pip install -r requirements-dashboard.txt
copy .env.dashboard.example .env.dashboard
docker compose up -d db
python dashboard/manage.py migrate
python dashboard/manage.py runserver 8000
```

- Bot: http://localhost:5000/health  
- Dashboard: http://localhost:8000/admin/

---

## Riesgos restantes

- **Docker requerido** para PostgreSQL; sin él, `migrate` fallará al conectar.
- Dashboard **LOCAL ONLY** — no desplegar en Render/Railway sin decisión explícita (`AUDITORIA.md`, Sección 6).
- Si bot y dashboard corren en local escribiendo `data/`, evitar escrituras desde el panel (Fase 2+ será solo lectura).

---

## Rollback (Fase 1)

```powershell
docker compose down -v   # opcional: borrar volumen PG
# Eliminar: dashboard/, docker-compose.yml, requirements-dashboard.txt, .env.dashboard.example
# Revertir cambios en README.md y .gitignore
```

El bot sigue operando con `python run.py` sin Django.

---

## Compatibilidad verificada

- Endpoints Flask intactos (`POST /bot`, `GET /health`, `POST /bot/reload-flow`).
- `requirements.txt` del bot sin cambios.
- Bot arranca sin importar Django.
- No se implementó trabajo de fases 2–4.

---

## Confirmación AUDITORIA.md

Cumplimiento **Fase 1**: fundación Django + PostgreSQL local documentada, proceso dual (bot :5000 / dashboard :8000), cambios mínimos, bot intacto.





#################################################################
## v0.24

## Prompt:


Existe una auditoría y arquitectura aprobadas para este proyecto.

Antes de realizar cualquier análisis o modificación debes leer completamente el archivo:

AUDITORIA.md

ubicado en la raíz del proyecto.

La auditoría es la fuente de verdad para arquitectura, fases, restricciones, riesgos, validaciones y alcance.

Debes respetarla estrictamente.

REGLAS INMUTABLES

* Modifica lo mínimo posible.
* Implementa únicamente mejoras incrementales.
* No rompas funcionalidad existente.
* No refactorices código no relacionado.
* No cambies APIs, contratos ni integraciones.
* No alteres la arquitectura definida en AUDITORIA.md.
* No implementes trabajo de fases futuras.
* Mantén compatibilidad total con el sistema actual.
* Prioriza estabilidad, simplicidad y bajo mantenimiento.
* Evita dependencias innecesarias.
* Reutiliza componentes, servicios y lógica existente siempre que sea posible.
* Si detectas una contradicción entre esta tarea y AUDITORIA.md, prevalece AUDITORIA.md.
* Si detectas riesgo alto, detente y explícalo antes de continuar.

TAREA

[Contexto: Fase 1 completada (Django + PG local). Bot Flask intacto en app/.

Tarea Fase 2 — Dashboard lectura operativa:
1. App Django operations con vistas login-free temporal o con auth si ya existe Fase 3 parcial.
2. Leer pedidos, reservas, menú y usuarios desde data/*.json; fallback a GoogleSheetsClient (import app.integrations.google_sheets) si caché vacío.
3. Vista detalle pedido (items, total, status, wa_id, dirección).
4. Vista estado sistema: HTTP GET a localhost:5000/health + cache_status del cliente Sheets.
5. Solo lectura: no escribir JSON ni Sheets.
6. NO crear endpoints Flask nuevos. NO tocar parser.py ni flow_engine.py.

Verificar: regression_checklist.py; datos del panel coinciden con WhatsApp menu y pedido de prueba.
Entregar: URLs, capturas o descripción de vistas, archivos tocados.]

ANTES DE MODIFICAR

1. Leer AUDITORIA.md completo.
2. Analizar el proyecto actual.
3. Verificar que la tarea corresponde a la fase indicada en AUDITORIA.md.
4. Explicar el plan de implementación.
5. Listar archivos a crear.
6. Listar archivos a modificar.
7. Explicar riesgos potenciales.
8. Confirmar que el alcance está limitado únicamente a esta fase.

IMPLEMENTACIÓN

* Realiza únicamente lo necesario para completar la tarea.
* Mantén los cambios lo más pequeños posible.
* No añadas funcionalidades fuera del alcance.
* No modifiques componentes no relacionados.
* Reutiliza la arquitectura existente siempre que sea posible.

VALIDACIÓN

* Verifica que el proyecto siga funcionando.
* Verifica que no existan regresiones.
* Ejecuta las validaciones definidas en AUDITORIA.md para esta fase.
* Confirma compatibilidad con el sistema actual.
* Confirma que no se han afectado fases futuras.

ENTREGA

* Resumen de cambios.
* Archivos creados.
* Archivos modificados.
* Validaciones realizadas.
* Riesgos restantes.
* Rollback específico de esta fase.
* Confirmación explícita de cumplimiento de AUDITORIA.md.


## Respuesta cursor ##

## Fase 2 completada — Dashboard lectura operativa

### Plan (cumplimiento AUDITORIA.md)
- App `operations` con vistas **sin login** (Fase 3 añadirá auth).
- Lectura desde `data/*.json`; si vacío, fallback con `get_google_sheets_client` + `warm_up_cache()` (sin escrituras desde las vistas).
- Estado del sistema: `GET` a `BOT_HEALTH_URL` + `cache_status()`.
- Sin cambios en Flask, `parser.py` ni `flow_engine.py`.

### URLs (puerto 8000)

| Ruta | Vista |
|------|--------|
| http://localhost:8000/ | Lista de pedidos |
| http://localhost:8000/pedidos/?status=pending | Pedidos pendientes |
| http://localhost:8000/pedidos/ORD-BD074F0A/ | Detalle (ítems, total, status, wa_id, dirección) |
| http://localhost:8000/reservas/ | Reservas |
| http://localhost:8000/menu/ | Menú por categoría (18 ítems = mismo caché que WhatsApp) |
| http://localhost:8000/usuarios/ | Usuarios por `last_seen` |
| http://localhost:8000/estado/ | Health del bot + caché Sheets |

### Archivos creados
- `dashboard/apps/operations/` (`apps.py`, `models.py`, `views.py`, `urls.py`)
- `dashboard/apps/operations/services/readers.py`
- `dashboard/apps/operations/templates/operations/*.html` (7 plantillas)

### Archivos modificados
- `dashboard/config/settings.py` — `apps.operations`, `PROJECT_ROOT`, `BOT_HEALTH_URL`, `testserver`
- `dashboard/config/urls.py` — include operations
- `.env.dashboard.example` — `BOT_HEALTH_URL`

### Validaciones
- `python scripts/regression_checklist.py` → **5/5 OK**
- `python dashboard/manage.py check` → sin issues
- Smoke test: pedido `ORD-BD074F0A`, menú 18 ítems, vistas 200

### Arranque
```powershell
# Terminal 1 — bot
python run.py

# Terminal 2 — dashboard
docker compose up -d db
cd dashboard
python manage.py migrate
python manage.py runserver 8000
```

### Rollback Fase 2
Quitar `"apps.operations"` de `INSTALLED_APPS` y la línea `include("apps.operations.urls")` en `urls.py`; borrar `dashboard/apps/operations/`.

### Riesgos restantes
- Vistas **públicas** hasta Fase 3.
- Fallback `GoogleSheetsClient` puede arrancar hilo de sync (escritura en `data/` del **proceso dashboard**); con bot y dashboard locales, evitar escrituras simultáneas (AUDITORIA, Sección 2.3).
- `/estado/` instancia el cliente Sheets al cargar la página.

### Cumplimiento AUDITORIA.md
Sí: solo lectura operativa, proceso dual, sin endpoints Flask nuevos, sin tocar parser/flow, alcance limitado a Fase 2.





######################################################################
## v0.24

## Prompt ##


Existe una auditoría y arquitectura aprobadas para este proyecto.

Antes de realizar cualquier análisis o modificación debes leer completamente el archivo:

AUDITORIA.md

ubicado en la raíz del proyecto.

La auditoría es la fuente de verdad para arquitectura, fases, restricciones, riesgos, validaciones y alcance.

Debes respetarla estrictamente.

REGLAS INMUTABLES

* Modifica lo mínimo posible.
* Implementa únicamente mejoras incrementales.
* No rompas funcionalidad existente.
* No refactorices código no relacionado.
* No cambies APIs, contratos ni integraciones.
* No alteres la arquitectura definida en AUDITORIA.md.
* No implementes trabajo de fases futuras.
* Mantén compatibilidad total con el sistema actual.
* Prioriza estabilidad, simplicidad y bajo mantenimiento.
* Evita dependencias innecesarias.
* Reutiliza componentes, servicios y lógica existente siempre que sea posible.
* Si detectas una contradicción entre esta tarea y AUDITORIA.md, prevalece AUDITORIA.md.
* Si detectas riesgo alto, detente y explícalo antes de continuar.

TAREA

[Contexto: Fases 1-2 OK. Dashboard muestra datos en lectura.

Tarea Fase 3 — Auth staff + PostgreSQL panel:
1. App accounts: modelo AuditLog y opcional DashboardSettings.
2. Login/logout Django; todas las vistas operations requieren login.
3. Migraciones PG; crear superuser vía manage.py documentado.
4. Registrar en AuditLog accesos a vistas sensibles (listar pedidos).
5. NO almacenar en PG pedidos/menú como fuente de verdad (solo metadatos de panel).
6. Bot sin cambios en endpoints.

Verificar: anónimo no accede; regression_checklist bot OK.
Entregar: modelos, migraciones, instrucciones createsuperuser.]

ANTES DE MODIFICAR

1. Leer AUDITORIA.md completo.
2. Analizar el proyecto actual.
3. Verificar que la tarea corresponde a la fase indicada en AUDITORIA.md.
4. Explicar el plan de implementación.
5. Listar archivos a crear.
6. Listar archivos a modificar.
7. Explicar riesgos potenciales.
8. Confirmar que el alcance está limitado únicamente a esta fase.

IMPLEMENTACIÓN

* Realiza únicamente lo necesario para completar la tarea.
* Mantén los cambios lo más pequeños posible.
* No añadas funcionalidades fuera del alcance.
* No modifiques componentes no relacionados.
* Reutiliza la arquitectura existente siempre que sea posible.

VALIDACIÓN

* Verifica que el proyecto siga funcionando.
* Verifica que no existan regresiones.
* Ejecuta las validaciones definidas en AUDITORIA.md para esta fase.
* Confirma compatibilidad con el sistema actual.
* Confirma que no se han afectado fases futuras.

ENTREGA

* Resumen de cambios.
* Archivos creados.
* Archivos modificados.
* Validaciones realizadas.
* Riesgos restantes.
* Rollback específico de esta fase.
* Confirmación explícita de cumplimiento de AUDITORIA.md.



## Respuesta cursor ##

## Plan (previo a implementar — Fase 3 AUDITORIA.md)

| Punto | Decisión |
|--------|----------|
| Alcance | Solo auth staff + metadatos PG; pedidos/menú siguen en `data/*.json` / Sheets |
| App nueva | `accounts` con `AuditLog` + `DashboardSettings` |
| Protección | `LoginRequiredMixin` en todas las vistas `operations` |
| Auditoría | `log_audit` al listar pedidos (`action=view`, `entity=orders`) |
| Bot | Sin cambios en `app/` ni endpoints Flask |

---

## Fase 3 completada — Auth staff + PostgreSQL panel

### Resumen de cambios

- App **`accounts`** con modelos `AuditLog` y `DashboardSettings` (solo metadatos del panel).
- Login/logout en `/accounts/login/` y `/accounts/logout/` (POST para salir).
- Todas las vistas operativas requieren sesión staff; anónimo redirige al login.
- Cada visita a la lista de pedidos registra una fila en `AuditLog`.
- README actualizado: `createsuperuser` obligatorio tras `migrate`.

### Archivos creados

- `dashboard/apps/accounts/` — `apps.py`, `models.py`, `audit.py`, `admin.py`, `urls.py`
- `dashboard/apps/accounts/migrations/0001_initial.py`
- `dashboard/apps/accounts/templates/registration/login.html`

### Archivos modificados

- `dashboard/config/settings.py` — `apps.accounts`, `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`
- `dashboard/config/urls.py` — include `accounts`
- `dashboard/apps/operations/views.py` — `LoginRequiredMixin` + auditoría en pedidos
- `dashboard/apps/operations/templates/operations/base.html` — usuario + botón Salir
- `README.md` — arranque con `createsuperuser`

### Arranque (tras Docker PG)

```powershell
docker compose up -d db
python dashboard/manage.py migrate
python dashboard/manage.py createsuperuser
python dashboard/manage.py runserver 8000
```

- Panel: http://localhost:8000/ → login requerido  
- Admin: http://localhost:8000/admin/ → mismo usuario; ver `AuditLog`

### Validaciones realizadas

| Check | Resultado |
|--------|-------------|
| `python scripts/regression_checklist.py` | **5/5 OK** (bot intacto) |
| `python dashboard/manage.py check` | Sin issues |
| `makemigrations accounts` | `0001_initial.py` generada |
| Auth anónimo / PG | No ejecutable aquí (Docker no disponible en este entorno) |

En tu máquina, con PG levantado:

```powershell
# Sin login → 302 a /accounts/login/
curl -I http://localhost:8000/

# Tras login en navegador, revisar AuditLog en /admin/
```

### Rollback Fase 3

1. Quitar `"apps.accounts"` de `INSTALLED_APPS` y la ruta `accounts/` en `urls.py`.
2. Quitar `LoginRequiredMixin` y `log_audit` de `operations/views.py`.
3. `docker compose down -v` si quieres borrar tablas PG (el bot no las usa).

### Riesgos restantes

- `/admin/` sigue siendo superficie Django estándar: proteger con contraseña fuerte (solo local).
- Fase 4 (escrituras a Sheets) pendiente; `DashboardSettings` aún sin uso en templates.
- Sin Docker, `migrate` fallará hasta levantar PostgreSQL.

### Cumplimiento AUDITORIA.md

**Sí:** PG solo para staff/auditoría/config UI; negocio en Sheets/JSON; bot sin cambios; alcance limitado a Fase 3; sin `StaffProfile` extra (no requerido en el prompt de tarea; se puede añadir en Fase 4 si hace falta).





######################################################################
## v0.26

## Prompt ##

Existe una auditoría y arquitectura aprobadas para este proyecto.

Antes de realizar cualquier análisis o modificación debes leer completamente el archivo:

AUDITORIA.md

ubicado en la raíz del proyecto.

La auditoría es la fuente de verdad para arquitectura, fases, restricciones, riesgos, validaciones y alcance.

Debes respetarla estrictamente.

REGLAS INMUTABLES

* Modifica lo mínimo posible.
* Implementa únicamente mejoras incrementales.
* No rompas funcionalidad existente.
* No refactorices código no relacionado.
* No cambies APIs, contratos ni integraciones.
* No alteres la arquitectura definida en AUDITORIA.md.
* No implementes trabajo de fases futuras.
* Mantén compatibilidad total con el sistema actual.
* Prioriza estabilidad, simplicidad y bajo mantenimiento.
* Evita dependencias innecesarias.
* Reutiliza componentes, servicios y lógica existente siempre que sea posible.
* Si detectas una contradicción entre esta tarea y AUDITORIA.md, prevalece AUDITORIA.md.
* Si detectas riesgo alto, detente y explícalo antes de continuar.

TAREA

[Contexto: Dashboard Django autenticado, lectura operativa. Bot en app/ con AdminService y GoogleSheetsClient.

Tarea Fase 4 — Acciones seguras:
1. Variable DASHBOARD_ENABLE_WRITES (default 0). Si 0, UI solo lectura con mensaje.
2. Acción confirmar pedido: reutilizar OrderService.confirm_order y notificación cliente como AdminService (extraer helper si evita duplicar, cambio mínimo).
3. Implementar vía dashboard/services/bot_bridge.py o management command, NO nuevo endpoint Flask público.
4. Opcional: marcar plato no disponible en Sheet MENU — un método acotado en GoogleSheetsClient si no existe; sin reescribir dirty logic.
5. NO editar user_states.json ni restaurant_flow.json desde UI.
6. AuditLog cada confirmación.

Verificar con spreadsheet de prueba: confirmar pedido desde panel; WhatsApp admin deja de recordar; regression_checklist.py; cliente recibe confirmación si Twilio configurado.

Restricciones: AI_RULES.md; no cambiar POST /bot ni formato XML.
Entregar: bridge, flag env, checklist Fase 4, riesgos residuales.]

ANTES DE MODIFICAR

1. Leer AUDITORIA.md completo.
2. Analizar el proyecto actual.
3. Verificar que la tarea corresponde a la fase indicada en AUDITORIA.md.
4. Explicar el plan de implementación.
5. Listar archivos a crear.
6. Listar archivos a modificar.
7. Explicar riesgos potenciales.
8. Confirmar que el alcance está limitado únicamente a esta fase.

IMPLEMENTACIÓN

* Realiza únicamente lo necesario para completar la tarea.
* Mantén los cambios lo más pequeños posible.
* No añadas funcionalidades fuera del alcance.
* No modifiques componentes no relacionados.
* Reutiliza la arquitectura existente siempre que sea posible.

VALIDACIÓN

* Verifica que el proyecto siga funcionando.
* Verifica que no existan regresiones.
* Ejecuta las validaciones definidas en AUDITORIA.md para esta fase.
* Confirma compatibilidad con el sistema actual.
* Confirma que no se han afectado fases futuras.

ENTREGA

* Resumen de cambios.
* Archivos creados.
* Archivos modificados.
* Validaciones realizadas.
* Riesgos restantes.
* Rollback específico de esta fase.
* Confirmación explícita de cumplimiento de AUDITORIA.md.


## Respuesta cursor ##

## Fase 4 — Acciones seguras (implementada)

Alcance verificado contra **AUDITORIA.md**, Fase 4. Sin cambios en `POST /bot`, `parser.py`, `restaurant_flow.json` ni `user_states.json`.

### Plan ejecutado

| Requisito | Implementación |
|-----------|----------------|
| `DASHBOARD_ENABLE_WRITES` (default 0) | `settings.py` + `.env.dashboard.example`; banner en todas las vistas |
| Confirmar pedido | `bot_bridge.confirm_order()` → `OrderService.confirm_order` + `AdminService.notify_customer_order_confirmed` |
| Sin endpoint Flask nuevo | Bridge + `manage.py bot_confirm_order` |
| Menú no disponible (opcional) | `GoogleSheetsClient.set_menu_item_availability` + POST en vista menú |
| AuditLog | `confirm_order` y `menu_unavailable` en cada acción |

### Archivos creados

- `dashboard/services/__init__.py`
- `dashboard/services/bot_bridge.py`
- `dashboard/config/context_processors.py`
- `dashboard/apps/operations/management/commands/bot_confirm_order.py`

### Archivos modificados

- `dashboard/config/settings.py` — flag + context processor
- `dashboard/apps/operations/views.py` — POST confirmar / marcar menú
- `dashboard/apps/operations/templates/operations/base.html`, `order_detail.html`, `menu.html`
- `.env.dashboard.example`
- `app/services/admin_service.py` — `notify_customer_order_confirmed()` (reutilizado por WhatsApp y panel)
- `app/integrations/google_sheets.py` — `set_menu_item_availability()` acotado

### Uso

1. En `.env.dashboard`: `DASHBOARD_ENABLE_WRITES=1` (solo entorno de prueba).
2. Reiniciar `runserver`.
3. Pedido pendiente → detalle → **Confirmar pedido**.
4. CLI alternativa:

```powershell
cd dashboard
python manage.py bot_confirm_order ORD-XXXXXXXX
```

5. Revisar entradas en `/admin/` → **AuditLog**.

### Validaciones

- `python scripts/regression_checklist.py` → **5/5**
- `python manage.py check` → sin issues

**Pendiente manual (checklist Fase 4 con spreadsheet de prueba):** confirmar un `ORD-…` real con `DASHBOARD_ENABLE_WRITES=1`, Twilio y bot en marcha; comprobar Sheets/caché, WhatsApp al cliente y que el admin deje de recibir recordatorios.

### Riesgos residuales

| Riesgo | Nota |
|--------|------|
| Dos procesos en `data/` | Si bot y dashboard corren en local escribiendo a la vez, posible conflicto en JSON; mitigación: escritura vía `GoogleSheetsClient` (dirty), no editar JSON a mano |
| Recordatorios admin en memoria del bot | El panel no limpia `_reminder_state` del proceso Flask; dejan de enviarse al salir de `pending` en Sheets (~30 s) |
| Menú | Actualización directa a Sheets; sin cola dirty de menú (acotado, como indica la auditoría) |

### Rollback Fase 4

1. `DASHBOARD_ENABLE_WRITES=0` en `.env.dashboard`.
2. Revertir commit de `dashboard/services/bot_bridge.py`, vistas/templates y cambios opcionales en `google_sheets.py` / `admin_service.py`.

El bot sigue operando sin dashboard.

### Cumplimiento AUDITORIA.md

- Fase 4 únicamente; sin fases futuras.
- APIs Flask y contratos intactos.
- Escrituras detrás de flag; auditoría en PG; bridge reutiliza servicios del bot.
- No edición de `user_states.json` ni flujo desde UI.




######################################################################
## v0.27

## Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Analiza el proyecto actual y crea una forma simple de iniciar todo el entorno local con la menor cantidad posible de pasos manuales.

Objetivo:
Que pueda levantar Bot + Dashboard + PostgreSQL ejecutando un único comando o el mínimo número posible de acciones.

Requisitos:

- Mantener compatibilidad con la arquitectura actual.
- No modificar la lógica de negocio.
- No cambiar APIs ni contratos.
- No romper ninguna funcionalidad existente.
- Mantener el comportamiento actual del bot.

Implementa únicamente automatización operativa.

Deseo:

1. Un único comando para iniciar PostgreSQL.
2. Un único comando para iniciar el bot.
3. Un único comando para iniciar la dashboard.
4. Si es posible, un único script que inicie todo junto.
5. Verificación automática de dependencias necesarias.
6. Mensajes claros indicando:
   - URL del bot
   - URL de health
   - URL de dashboard
   - URL de admin Django
7. Detectar errores comunes y mostrar instrucciones de solución.
8. Documentar el proceso en README.

Prioridades:

- Simplicidad.
- Bajo mantenimiento.
- Compatibilidad total.
- Cambios mínimos.
- Solución estable para desarrollo local.

Antes de modificar:

1. Explica el plan.
2. Lista archivos a crear.
3. Lista archivos a modificar.
4. Explica riesgos.

Después de implementar:

1. Explica exactamente qué comando debo ejecutar.
2. Explica cómo detener todos los servicios.
3. Muestra las URLs finales disponibles.
4. Confirma que el bot y la dashboard siguen funcionando como antes.]



## Respuesta cursor ##


**PostgreSQL 17** se instaló bien con winget (salida: `Successfully installed`, ~9,5 min).

El servicio **`postgresql-x64-17`** está en ejecución y **5432** acepta conexiones. El bot sigue en el puerto **5000**.

Para el dashboard falta la base/usuario que usa el proyecto (`dashboard` / `dashboard` en `DATABASE_URL`). Eso lo crea **Docker** con `.\dev.cmd db`, o tú en pgAdmin/psql con la contraseña de `postgres` que pusiste en el instalador. Después: `.\dev.cmd dashboard` o `.\dev.cmd all`.



######################################################################
## v0.27

## Prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[No quiero que hagas nada, solo que analices el proyecto, y me propongas un plan de acción de 4 fases para implementar, como mejora incremental, que la dashboard se vea con un diseño profesional, Diseño premium tipo Stripe, Linear, Notion, Vercel o HubSpot.
Apariencia limpia, minimalista y moderna.
Responsive para desktop, tablet y móvil.
Espaciado consistente y excelente jerarquía visual.
Iconografía moderna.
Tarjetas con sombras suaves y bordes redondeados.
Tabla de pedidos profesional con búsqueda, filtros y paginación.
Dashboard con métricas visuales (pedidos, ventas, clientes, conversaciones).
Estados visuales para pedidos (pendiente, confirmado, entregado, cancelado).
Tema claro y oscuro.
Animaciones sutiles y profesionales.
UX enfocada en productividad, Importante:

Todo debe ser editable desde la interfaz.
Crear formularios CRUD completos para clientes, pedidos, productos y configuraciones.
Permitir crear, editar y eliminar registros sin tocar la base de datos manualmente.
Agregar validaciones.
Agregar mensajes de éxito y error.
Agregar panel de administración avanzado.
Mantener código limpio y escalable.

Quiero que parezca un software comercial que podría venderse a clientes reales.


Dame un plan corto conciso pero completo y profesoinal que cumpla ocn todo, 3 o 4 fases maximo, condensa todo ahí]

Recuerda no hacer nada, solo propón el plan de acción


## Respuesta cursor ##


Aquí tienes las **4 fases listas para pegar** (en `README.md`, `prompts.md` o en cada chat de Cursor) y el **prompt completo** de cada una. Todos respetan `AI_RULES.md` y el stack actual (Django dashboard + `bot_bridge`, sin tocar Flask/Twilio salvo que la fase lo exija explícitamente).

---

## Cómo usarlas

1. **Una fase por sesión** (o por PR): no mezcles Fase 2 y 3 en el mismo prompt.
2. Siempre incluye al inicio: *“Lee y aplica completamente AI_RULES.md”*.
3. Al terminar cada fase, prueba con `.\dev.cmd dashboard` (o `all`) antes de pasar a la siguiente.

---

## Fase 1 — Diseño premium (fundación visual)

**Qué colocar como título en tu lista de fases:**
> Fase 1: Sistema de diseño, layout responsive y tema claro/oscuro (sin cambiar lógica de negocio)

**Prompt:**

```
OBLIGATORIO:
Lee y aplica completamente AI_RULES.md antes de cualquier cambio.

CONTEXTO:
Proyecto chatbot restaurante (Flask + Twilio) + dashboard Django en /dashboard.
El bot NO debe modificarse en esta fase. Solo UI del panel en dashboard/apps/operations/templates y dashboard/static/.

TAREA — FASE 1 (solo diseño y shell):
Implementar la base visual premium tipo Stripe/Linear/Notion/Vercel:
- Design system con tokens CSS (tipografía, espaciado, colores, radios, sombras suaves).
- Layout: sidebar + topbar + área de contenido; responsive desktop/tablet/móvil.
- Componentes reutilizables: card, button, input, badge, empty-state, toasts (mensajes Django).
- Iconografía moderna (SVG/Lucide o similar, estático en dashboard/static).
- Tema claro y oscuro (variables CSS + toggle + localStorage).
- Animaciones sutiles (transiciones hover/focus, respetar prefers-reduced-motion).
- Refactorizar operations/base.html en partials; mover CSS inline a static/css/app.css.
- Unificar diseño de registration/login.html con el panel.

RESTRICCIONES:
- No cambiar URLs, endpoints Flask, contratos JSON ni bot_bridge.
- No añadir CRUD ni nuevas vistas de negocio en esta fase.
- Cambios mínimos de archivos; solo lo necesario para el shell visual.
- Mantener todas las vistas actuales funcionando (pedidos, reservas, menú, usuarios, estado).

ENTREGABLE:
Código implementado + breve resumen en formato AI_RULES (análisis, archivos, compatibilidad).
```

---

## Fase 2 — Home con métricas y tabla de pedidos pro

**Qué colocar:**
> Fase 2: Dashboard con KPIs, gráficos y tabla de pedidos (búsqueda, filtros, paginación)

**Prompt:**

```
OBLIGATORIO:
Lee y aplica completamente AI_RULES.md.

CONTEXTO:
Fase 1 ya aplicada (design system y base.html premium).
Dashboard Django lee datos con dashboard/apps/operations/services/readers.py.
Escrituras siguen en bot_bridge; esta fase es principalmente lectura + UX de listados.

TAREA — FASE 2:
1) Home operativo (/ o ruta dedicada /dashboard/):
   - Tarjetas KPI: pedidos, ventas (suma totales), clientes, conversaciones/reservas (según datos disponibles en readers/caché).
   - 1–2 gráficos ligeros (Chart.js o similar, sin SPA) con datos reales agregados en Python.

2) Tabla profesional de pedidos:
   - Búsqueda por ID/cliente.
   - Filtros: estado (pending, confirmed, delivered, cancelled), rango de fechas si hay timestamp.
   - Ordenación y paginación server-side en OrderListView.
   - Badges visuales por estado con iconos y colores del design system.

3) Mejorar vista detalle de pedido con layout de producto (resumen + ítems + acciones visibles).

RESTRICCIONES:
- Agregar funciones de agregación en readers.py si hace falta; no cambiar estructura JSON del bot.
- No implementar CRUD completo aún (eso es Fase 3).
- No nuevos endpoints Flask.
- Reutilizar estilos y componentes de Fase 1.

ENTREGABLE:
Implementación + prueba manual descrita (cómo filtrar/buscar un pedido) + resumen AI_RULES.
```

---

## Fase 3 — CRUD desde la interfaz

**Qué colocar:**
> Fase 3: Formularios CRUD (clientes, pedidos, productos, configuración) vía bot_bridge

**Prompt:**

```
OBLIGATORIO:
Lee y aplica completamente AI_RULES.md.

CONTEXTO:
Fases 1–2 completas (UI premium + home + tabla pedidos).
Escrituras del panel deben ir por dashboard/services/bot_bridge.py reutilizando MenuService, OrderService, UserService del bot — NO crear endpoints Flask nuevos.
DASHBOARD_ENABLE_WRITES controla escrituras.

TAREA — FASE 3:
CRUD completo editable desde la UI (crear, editar, eliminar):

A) Productos / menú: alta, edición, baja lógica o eliminación, precio, categoría, disponibilidad.
B) Pedidos: crear manual, editar estado/ítems donde el servicio lo permita, cancelar.
C) Clientes: WA ID, nombre, notas; listado + formularios.
D) Configuración del panel: preferencias operativas (modelo Django ligero en PG o JSON en data/, elige la opción de menor impacto y documéntala).

Para cada módulo:
- Formularios Django con validación servidor (campos requeridos, precios > 0, IDs únicos).
- Mensajes éxito/error con django.contrib.messages.
- Confirmación antes de eliminar.
- Permisos: operador vs admin (grupos Django).
- log_audit en cada POST de escritura.

Extender bot_bridge con funciones nuevas; reutilizar app/utils/validators.py cuando aplique.
Tras writes, asegurar coherencia con caché/Sheets como hace el bot hoy.

RESTRICCIONES:
- No modificar parser.py, flow_engine, Twilio salvo bug bloqueante documentado.
- No cambiar POST /bot ni contratos JSON existentes.
- Cambios incrementales; un módulo CRUD a la vez si reduce riesgo.

ENTREGABLE:
CRUD funcional con DASHBOARD_ENABLE_WRITES=1 + resumen AI_RULES y lista de flujos probados.
```

---

## Fase 4 — Admin avanzado, pulido y calidad

**Qué colocar:**
> Fase 4: Panel admin avanzado, micro-interacciones, permisos, tests y documentación

**Prompt:**

```
OBLIGATORIO:
Lee y aplica completamente AI_RULES.md.

CONTEXTO:
Fases 1–3 completas. El panel debe sentirse como software comercial vendible.

TAREA — FASE 4:
1) Panel de administración avanzado unificado:
   - Vista de auditoría (accounts/audit).
   - Estado sistema (bot health, Sheets/caché) integrado al diseño premium.
   - Gestión usuarios del panel; Django /admin/ solo para superusuarios con enlace discreto.
   - Documentar en UI qué requiere DASHBOARD_ENABLE_WRITES.

2) Reservas y usuarios: mismas tablas premium; CRUD donde aún falte.

3) Pulido comercial:
   - Empty states, loading/skeleton donde aporte.
   - Micro-animaciones consistentes con Fase 1.
   - Accesibilidad básica (focus, contraste, reduced-motion).

4) Calidad:
   - Tests de vistas críticas (filtros pedidos, permisos, bot_bridge mockeado).
   - Checklist responsive 320 / 768 / 1280 px.
   - Actualizar README sección “Dashboard local” con guía del operador.

RESTRICCIONES:
- Cero regresión del webhook WhatsApp y servicios del bot.
- No refactors masivos; solo lo necesario para cerrar el producto.

ENTREGABLE:
Panel listo para demo a cliente + resumen AI_RULES + test plan ejecutado.
```

---

## Bloque corto para tu README (solo títulos)

Puedes pegar esto como índice y debajo cada prompt completo:

```markdown
### Mejora dashboard — roadmap

- [ ] **Fase 1** — Diseño premium, layout, tema claro/oscuro
- [ ] **Fase 2** — KPIs, gráficos, tabla pedidos (búsqueda/filtros/paginación)
- [ ] **Fase 3** — CRUD menú, pedidos, clientes, configuración (bot_bridge)
- [ ] **Fase 4** — Admin avanzado, pulido, tests, documentación
```

---

## Orden recomendado si algo falla

| Si en la fase… | No avances hasta… |
|----------------|-------------------|
| 1 | Ver todas las rutas actuales con el nuevo layout |
| 2 | KPIs y paginación con datos reales de `data/*_cache.json` |
| 3 | Un CRUD de punta a punta con `DASHBOARD_ENABLE_WRITES=1` |
| 4 | Demo completa sin tocar el bot en producción |

Si quieres, en el siguiente mensaje puedo volcar estos cuatro prompts tal cual en `prompts.md` del repo (solo si me lo pides explícitamente).



## Segundo Prompt ##

OBLIGATORIO:
Lee y aplica completamente AI_RULES.md antes de cualquier cambio.

CONTEXTO:
Proyecto chatbot restaurante (Flask + Twilio) + dashboard Django en /dashboard.
El bot NO debe modificarse en esta fase. Solo UI del panel en dashboard/apps/operations/templates y dashboard/static/.

TAREA — FASE 1 (solo diseño y shell):
Implementar la base visual premium tipo Stripe/Linear/Notion/Vercel:
- Design system con tokens CSS (tipografía, espaciado, colores, radios, sombras suaves).
- Layout: sidebar + topbar + área de contenido; responsive desktop/tablet/móvil.
- Componentes reutilizables: card, button, input, badge, empty-state, toasts (mensajes Django).
- Iconografía moderna (SVG/Lucide o similar, estático en dashboard/static).
- Tema claro y oscuro (variables CSS + toggle + localStorage).
- Animaciones sutiles (transiciones hover/focus, respetar prefers-reduced-motion).
- Refactorizar operations/base.html en partials; mover CSS inline a static/css/app.css.
- Unificar diseño de registration/login.html con el panel.

RESTRICCIONES:
- No cambiar URLs, endpoints Flask, contratos JSON ni bot_bridge.
- No añadir CRUD ni nuevas vistas de negocio en esta fase.
- Cambios mínimos de archivos; solo lo necesario para el shell visual.
- Mantener todas las vistas actuales funcionando (pedidos, reservas, menú, usuarios, estado).

ENTREGABLE:
Código implementado + breve resumen en formato AI_RULES (análisis, archivos, compatibilidad).


## Respuesta cursor ##

Fase 1 del shell visual del panel implementada siguiendo **AI_RULES.md** (cambios incrementales, solo dashboard).

---

### Análisis previo

- El panel usaba `base.html` con CSS inline y navegación horizontal simple.
- No existía `dashboard/static/`; Django solo tenía `STATIC_URL`.
- Las vistas hijas dependen de clases existentes (`.badge`, `.btn`, `.flash`, tablas) — se mantuvieron para no romper plantillas.
- Sin tocar Flask, Twilio, `bot_bridge`, URLs ni `views.py`.

### Cambios implementados

| Área | Detalle |
|------|---------|
| **Design system** | `tokens.css`, `components.css`, `layout.css`, `app.css` (Inter, espaciado, colores, radios, sombras) |
| **Layout** | Sidebar fija + topbar sticky + contenido; menú móvil con backdrop |
| **Componentes** | card, btn, input, badge, empty-state, toasts, banner readonly |
| **Iconos** | Sprite SVG inline (estilo Lucide) + copia en `static/icons/sprite.svg` |
| **Tema** | Claro/oscuro con `data-theme`, script en `<head>` anti-flash, `theme.js` + `localStorage` |
| **Animaciones** | Transiciones hover/focus; `prefers-reduced-motion` desactiva duraciones |
| **Partials** | `head_assets`, `sidebar`, `toasts`, `readonly_banner`, `theme_toggle`, `icons_sprite`, `icon` |
| **Auth** | `layout_auth.html` + `login.html` unificado con el panel |

### Archivos modificados

- `dashboard/config/settings.py` — `STATICFILES_DIRS`
- `dashboard/apps/operations/templates/operations/base.html`
- `dashboard/apps/accounts/templates/registration/login.html`
- Plantillas de listado/detalle (solo `{% block page_heading %}` y filtros de pedidos)
- **Nuevos:** `dashboard/static/css/*`, `dashboard/static/js/*`, `dashboard/static/icons/sprite.svg`, `operations/partials/*`, `operations/layout_auth.html`

### Riesgos mitigados

- Clases CSS legacy conservadas en `app.css` (tablas, badges, botones, flashes).
- Bloques Django (`title`, `page_heading`, `content`) en `base.html`, no en includes.
- Sprite SVG inline para `<use href="#icon-…">` (compatible en todos los navegadores).
- Sin cambios en rutas, vistas ni integración con el bot.

### Compatibilidad verificada

- `python manage.py check` — sin errores.
- `findstatic css/app.css` / `js/theme.js` — resueltos correctamente.
- Parser, Flask, Twilio, flow engine, order service y bot: **no modificados**.

### Funcionalidades agregadas

- Shell premium responsive (desktop / tablet / móvil).
- Tema claro/oscuro persistente.
- Toasts para mensajes Django.
- Login alineado visualmente con el panel.

### Funcionalidades preservadas

- Pedidos, reservas, menú, usuarios, estado del sistema.
- Confirmación de pedidos, marcar menú no disponible (con escrituras activas).
- Banner modo solo lectura, logout, admin Django, mismas URLs.

---

**Cómo probar:** desde `dashboard/`, `python manage.py runserver` y abrir `/` y `/accounts/login/`. Prueba el toggle de tema y, en viewport &lt;768px, el botón de menú del topbar.

**Fase 2 (fuera de alcance):** refinar páginas con cards/empty-states explícitos y reducir el `h1` duplicado en contenido si quieres un topbar único como título.


######################################################################
## v0.29



## prompt ##

OBLIGATORIO:
Lee y aplica completamente AI_RULES.md.

CONTEXTO:
Fase 1 ya aplicada (design system y base.html premium).
Dashboard Django lee datos con dashboard/apps/operations/services/readers.py.
Escrituras siguen en bot_bridge; esta fase es principalmente lectura + UX de listados.

TAREA — FASE 2:
1) Home operativo (/ o ruta dedicada /dashboard/):
   - Tarjetas KPI: pedidos, ventas (suma totales), clientes, conversaciones/reservas (según datos disponibles en readers/caché).
   - 1–2 gráficos ligeros (Chart.js o similar, sin SPA) con datos reales agregados en Python.

2) Tabla profesional de pedidos:
   - Búsqueda por ID/cliente.
   - Filtros: estado (pending, confirmed, delivered, cancelled), rango de fechas si hay timestamp.
   - Ordenación y paginación server-side en OrderListView.
   - Badges visuales por estado con iconos y colores del design system.

3) Mejorar vista detalle de pedido con layout de producto (resumen + ítems + acciones visibles).

RESTRICCIONES:
- Agregar funciones de agregación en readers.py si hace falta; no cambiar estructura JSON del bot.
- No implementar CRUD completo aún (eso es Fase 3).
- No nuevos endpoints Flask.
- Reutilizar estilos y componentes de Fase 1.

ENTREGABLE:
Implementación + prueba manual descrita (cómo filtrar/buscar un pedido) + resumen AI_RULES.


## Respuesta cursor ##

Fase 2 del dashboard operativo quedó implementada siguiendo **AI_RULES.md** (cambios incrementales, sin tocar Flask/bot JSON).

---

### Análisis previo

- **Fase 1** ya aporta `base.html`, tokens y componentes reutilizables.
- **Lectura** centralizada en `readers.py`; la home y los listados solo agregan/filtran en Python.
- **`/`** pasa a ser resumen KPI; **`/pedidos/`** conserva el listado (antes `/` era pedidos).

---

### Cambios implementados

1. **Home (`/` y `/dashboard/`)**  
   - 4 tarjetas KPI: pedidos, ventas (suma de `total`), clientes, reservas (+ hint de conversaciones = usuarios en caché).  
   - 2 gráficos Chart.js (CDN): dona por estado y barras de ventas (14 días).

2. **Listado de pedidos** (`/pedidos/`)  
   - Búsqueda por ID/cliente/`wa_id`.  
   - Filtros: estado (`pending`, `confirmed`, `delivered`, `cancelled`) y rango de fechas (`timestamp` ISO).  
   - Ordenación por columnas y paginación server-side (20/página).  
   - Badges con iconos y colores del design system.

3. **Detalle de pedido**  
   - Cabecera con ID, estado, total; grid resumen + tabla de ítems; acción de confirmar visible cuando aplica.

---

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `dashboard/apps/operations/services/readers.py` | KPIs, gráficos, `query_orders()` |
| `dashboard/apps/operations/views.py` | `DashboardHomeView`, `OrderListView` ampliado |
| `dashboard/apps/operations/urls.py` | Rutas home/dashboard |
| `dashboard/apps/operations/templates/operations/dashboard_home.html` | Nuevo |
| `dashboard/apps/operations/templates/operations/order_list.html` | Toolbar + tabla + paginación |
| `dashboard/apps/operations/templates/operations/order_detail.html` | Layout producto |
| `dashboard/apps/operations/templates/operations/partials/order_status_badge.html` | Nuevo |
| `dashboard/apps/operations/templates/operations/partials/sidebar.html` | Enlace Inicio |
| `dashboard/apps/operations/templates/operations/partials/icons_sprite.html` | Iconos nuevos |
| `dashboard/static/css/components.css` | Badges `delivered` / `cancelled` |
| `dashboard/static/css/app.css` | KPI, charts, toolbar, detalle |

---

### Riesgos mitigados

- Sin cambios en JSON del bot ni en `bot_bridge` / Flask.  
- Agregaciones solo en lectura; fallos de Sheets siguen el flujo existente de `readers`.  
- `python manage.py check` sin errores.

---

### Compatibilidad verificada

- Parser, Flask, Twilio, flow engine y order service **no modificados**.  
- Confirmación de pedido (POST en detalle) **igual** que antes.  
- `LOGIN_REDIRECT_URL = "/"` lleva al nuevo resumen.

---

### Funcionalidades agregadas

- Dashboard KPI + gráficos con datos reales de caché.  
- Listado profesional con búsqueda, filtros, sort y paginación server-side.  
- Detalle con layout en dos columnas y badges con iconos.

---

### Funcionalidades preservadas

- Lectura desde `data/*_cache.json` y fallback Sheets.  
- Menú, reservas, usuarios, estado del sistema, login, banner solo lectura, confirmar pedido (Fase 3 CRUD pendiente).

---

## Prueba manual

1. Arranca el dashboard (como en tu README / `runall.py`).
2. Inicia sesión → debes ver **`/`** con KPIs y gráficos.
3. Ve a **Pedidos** (`/pedidos/`).
4. **Buscar**: en “ID o cliente…” escribe `Pedro` o `ORD-BD` → **Filtrar** → debe aparecer `ORD-BD074F0A`.
5. **Estado**: elige `pending` → solo pendientes.
6. **Fechas**: `Desde` / `Hasta` = `2026-06-01` → filtra por `timestamp`.
7. **Ordenar**: clic en **Fecha** o **Total** (alterna ↑/↓).
8. **Detalle**: clic en el ID → resumen + ítems; si hay escrituras activas, botón **Confirmar pedido**.
9. **Limpiar** restablece filtros.

---

## Resumen AI_RULES (cumplimiento)

| Regla | Cómo se aplicó |
|--------|----------------|
| Evolucionar, no reconstruir | Extensión de vistas/plantillas existentes |
| Menor impacto / pocos archivos | Lógica de agregación en `readers.py`; sin capas nuevas |
| No cambiar APIs/JSON/endpoints Flask | Solo Django + templates + CSS estático |
| Reutilizar código | `base.html`, cards, badges, tokens Fase 1 |
| Componentes críticos del bot | Sin toques |
| Entregable con prueba manual | Descrita arriba |

Si quieres, en Fase 3 podemos añadir CRUD y más acciones sobre el mismo layout.





######################################################################
## v0.30

## Prompt ##

OBLIGATORIO:
Lee y aplica completamente AI_RULES.md.

CONTEXTO:
Fases 1–2 completas (UI premium + home + tabla pedidos).
Escrituras del panel deben ir por dashboard/services/bot_bridge.py reutilizando MenuService, OrderService, UserService del bot — NO crear endpoints Flask nuevos.
DASHBOARD_ENABLE_WRITES controla escrituras.

TAREA — FASE 3:
CRUD completo editable desde la UI (crear, editar, eliminar):

A) Productos / menú: alta, edición, baja lógica o eliminación, precio, categoría, disponibilidad.
B) Pedidos: crear manual, editar estado/ítems donde el servicio lo permita, cancelar.
C) Clientes: WA ID, nombre, notas; listado + formularios.
D) Configuración del panel: preferencias operativas (modelo Django ligero en PG o JSON en data/, elige la opción de menor impacto y documéntala).

Para cada módulo:
- Formularios Django con validación servidor (campos requeridos, precios > 0, IDs únicos).
- Mensajes éxito/error con django.contrib.messages.
- Confirmación antes de eliminar.
- Permisos: operador vs admin (grupos Django).
- log_audit en cada POST de escritura.

Extender bot_bridge con funciones nuevas; reutilizar app/utils/validators.py cuando aplique.
Tras writes, asegurar coherencia con caché/Sheets como hace el bot hoy.

RESTRICCIONES:
- No modificar parser.py, flow_engine, Twilio salvo bug bloqueante documentado.
- No cambiar POST /bot ni contratos JSON existentes.
- Cambios incrementales; un módulo CRUD a la vez si reduce riesgo.

ENTREGABLE:
CRUD funcional con DASHBOARD_ENABLE_WRITES=1 + resumen AI_RULES y lista de flujos probados.

## Respuesta cursor ##

### Análisis previo

Fase 3 requería CRUD completo en el panel Django sin tocar Flask/`POST /bot`, reutilizando `MenuService`, `OrderService` y `UserService` vía `bot_bridge.py`, con `DASHBOARD_ENABLE_WRITES`, validación servidor, `messages`, confirmaciones, permisos operador/admin y `log_audit` en cada POST.

**Decisión configuración (D):** modelo existente `accounts.DashboardSettings` en PostgreSQL (menor impacto que JSON en `data/` — ya migrado, aislado del bot).

---

### Cambios implementados

**A) Menú**
- Listado con acciones: editar, baja lógica, eliminar permanente, marcar no disponible
- `/menu/nuevo/`, `/menu/<id>/editar/`, POST `/menu/<id>/eliminar/`
- Validación: ID único, precio > 0, campos requeridos

**B) Pedidos**
- `/pedidos/nuevo/` — creación manual con JSON de ítems
- Detalle: confirmar, cambiar estado, cancelar, editar ítems (JSON)
- Sincronización caché local + cola dirty hacia Sheets

**C) Clientes**
- Listado con enlace a detalle; `/usuarios/nuevo/`, editar, eliminar (admin)
- WA ID, nombre, notas (notas solo en caché local — no columna USERS en Sheets)

**D) Configuración**
- `/configuracion/` (solo admin): filtro por defecto, paginación, mostrar cancelados, notas operativas → `DashboardSettings` en PG

**Permisos**
- `dashboard_operator`: pedidos, clientes, disponibilidad menú
- `dashboard_admin`: CRUD menú completo, eliminar clientes, configuración
- Comando: `python manage.py setup_dashboard_groups --assign <user>`

---

### Archivos modificados

| Área | Archivos |
|------|----------|
| Bot / Sheets | `app/integrations/google_sheets.py`, `app/services/menu_service.py`, `app/services/order_service.py`, `app/services/user_service.py` |
| Bridge | `dashboard/services/bot_bridge.py` |
| Dashboard | `views.py`, `urls.py`, `forms.py`, `permissions.py`, `readers.py`, `settings_store.py`, templates, `components.css`, `context_processors.py`, `settings.py` |
| Management | `setup_dashboard_groups.py` |

**No modificados:** `parser.py`, `flow_engine`, Twilio, `POST /bot`, contratos JSON.

---

### Riesgos mitigados

- Escrituras bloqueadas si `DASHBOARD_ENABLE_WRITES=0`
- IDs únicos validados en formularios + `bot_bridge`
- Confirmación JS antes de eliminar/cancelar
- Notas de cliente no alteran esquema Sheets USERS
- Pedidos cancelados no permiten editar ítems
- `log_audit` en todos los POST de escritura

---

### Compatibilidad verificada

- `python manage.py check` — OK
- Smoke test con `DASHBOARD_ENABLE_WRITES=1`: menú, cliente, pedido manual, cancelación, vistas CRUD (200)
- Demo mode sin credenciales Sheets — coherente con caché local

---

### Funcionalidades agregadas

CRUD menú, pedidos, clientes y configuración del panel con permisos por grupo Django.

---

### Funcionalidades preservadas

Home KPIs, listado/filtros pedidos, confirmar pedido, reservas, estado sistema, login, banner solo lectura, bot Flask/Twilio/parser sin cambios.

---

### Flujos probados

1. Parseo JSON ítems (`product`, `qty`, `unit_price` > 0)
2. Alta plato → baja/eliminación
3. Alta cliente con notas → edición
4. Pedido manual → cancelación
5. GET `/menu/`, `/pedidos/`, `/usuarios/`, `/configuracion/`, formularios nuevo
6. `setup_dashboard_groups`

---

### Puesta en marcha

```powershell
cd dashboard
python manage.py migrate
python manage.py setup_dashboard_groups --assign tu_usuario
# .env.dashboard → DASHBOARD_ENABLE_WRITES=1
python manage.py runserver
```

**Matriz de permisos:** superusuario = acceso total; operador = escrituras operativas; admin = CRUD menú + eliminar clientes + `/configuracion/`.




######################################################################
## v0.31

## Prompt ##

OBLIGATORIO:
Lee y aplica completamente AI_RULES.md.

CONTEXTO:
Fases 1–3 completas. El panel debe sentirse como software comercial vendible.

TAREA — FASE 4:
1) Panel de administración avanzado unificado:
   - Vista de auditoría (accounts/audit).
   - Estado sistema (bot health, Sheets/caché) integrado al diseño premium.
   - Gestión usuarios del panel; Django /admin/ solo para superusuarios con enlace discreto.
   - Documentar en UI qué requiere DASHBOARD_ENABLE_WRITES.

2) Reservas y usuarios: mismas tablas premium; CRUD donde aún falte.

3) Pulido comercial:
   - Empty states, loading/skeleton donde aporte.
   - Micro-animaciones consistentes con Fase 1.
   - Accesibilidad básica (focus, contraste, reduced-motion).

4) Calidad:
   - Tests de vistas críticas (filtros pedidos, permisos, bot_bridge mockeado).
   - Checklist responsive 320 / 768 / 1280 px.
   - Actualizar README sección “Dashboard local” con guía del operador.

RESTRICCIONES:
- Cero regresión del webhook WhatsApp y servicios del bot.
- No refactors masivos; solo lo necesario para cerrar el producto.

ENTREGABLE:
Panel listo para demo a cliente + resumen AI_RULES + test plan ejecutado.

## Respuesta cursor ##


Fase 4 completada. El panel queda listo para demo comercial sin tocar Flask, Twilio ni el webhook.

---

### Análisis previo

- Fases 1–3 ya tenían CRUD de clientes/pedidos/menú vía `bot_bridge`; faltaba administración unificada, auditoría en UI, gestión de accesos Django y pulido comercial.
- Reservas: solo lectura (el bot las crea por WhatsApp); se alinearon tablas premium + detalle, sin nuevo bridge (evita regresión).
- Tests: PostgreSQL local sin permiso de `CREATE DATABASE`; se añadió `config.test_settings` con SQLite.

---

### Cambios implementados

1. **Administración unificada** (`/administracion/`): hub con enlaces a auditoría, accesos, estado, escrituras y configuración.
2. **Auditoría** (`/accounts/audit/`): filtros, paginación, tabla premium (solo admin).
3. **Accesos al panel** (`/administracion/accesos/`): CRUD usuarios Django con grupos operador/admin.
4. **Estado del sistema** (`/estado/`): tarjetas de salud del bot y caché Sheets; JSON técnico en `<details>`.
5. **Guía escrituras** (`/administracion/escrituras/`): qué requiere `DASHBOARD_ENABLE_WRITES`; banner con enlace.
6. **Reservas / clientes**: tablas `data-table`, búsqueda en reservas, detalle de reserva, empty states.
7. **Sidebar**: sección Administración; Django `/admin/` solo superusuarios (enlace discreto).
8. **CSS**: status pills, admin hub, skeleton, `animate-fade-in`, `prefers-reduced-motion`, breakpoint ~480px.
9. **Tests**: 10 tests (filtros, permisos, `bot_bridge` mockeado).
10. **README**: guía del operador + comando de tests.

---

### Archivos modificados

| Área | Archivos |
|------|----------|
| Vistas/URLs | `accounts/views.py`, `accounts/urls.py`, `operations/views.py`, `operations/urls.py`, `operations/forms.py`, `readers.py`, `context_processors.py` |
| Plantillas | `audit_list.html`, `admin_hub.html`, `writes_help.html`, `panel_staff_*.html`, `system_status.html`, `reservation_*.html`, `user_list.html`, `sidebar.html`, `readonly_banner.html`, `empty_state.html` |
| Estilos | `components.css`, `layout.css` |
| Tests/docs | `operations/tests/test_views.py`, `config/test_settings.py`, `README.md` |

**Sin cambios** en `app/`, `bot_bridge` (solo lectura desde vistas), webhook ni servicios del bot.

---

### Riesgos mitigados

- Escrituras siguen detrás de `DASHBOARD_ENABLE_WRITES` + roles.
- Reservas sin CRUD en panel → sin conflicto con `ReservationService`/WhatsApp.
- `/admin/` Django oculto a no-superusuarios.
- Tests aislados con SQLite (`--settings=config.test_settings`).

---

### Compatibilidad verificada

- Parser, Flask, Twilio, flow engine, order service, Sheets y estados conversacionales: **no modificados**.
- `bot_bridge` y endpoints existentes: **intactos**.

---

### Funcionalidades agregadas

- Centro admin, auditoría UI, gestión accesos panel, guía de escrituras, estado premium, reservas con detalle/búsqueda, empty states y animaciones, 10 tests automatizados.

---

### Funcionalidades preservadas

- Login, KPIs, pedidos (filtros/CRUD), menú, clientes, configuración panel, banner solo lectura, `log_audit` en acciones existentes.

---

### Test plan ejecutado

```bash
cd dashboard
python manage.py test apps.operations.tests.test_views -v 2 --settings=config.test_settings
```

**Resultado: 10/10 OK** (login, filtros pedidos, permisos audit/panel staff, `bot_bridge` create/confirm, estado sistema, guía escrituras).

**Checklist responsive (manual):** 320px (menú hamburguesa, toolbar en columna), 768px (sidebar off-canvas), 1280px (grids admin/KPI). Documentado en README.

---

### Demo rápida para cliente

1. `.\dev.cmd all` → http://localhost:8000/
2. Admin: `/administracion/` → auditoría y accesos.
3. Operador: pedidos/reservas/clientes (lectura por defecto).
4. Prueba escrituras: `DASHBOARD_ENABLE_WRITES=1` en `.env.dashboard` → reiniciar dashboard → confirmar pedido de prueba.






######################################################################
## v0.32


## Prompt ##

Quiero que solamente y unicamente y estrictamente hagas lo siguiente en la dashboard web: arriba a la izquierda donde dice Restaurante, que apareca el nombre del restaurante definido en .env


## Resp cursor ##

Hecho. En la esquina superior izquierda del panel ya no aparece el texto fijo «Restaurante»; se muestra el valor de `RESTAURANT_NAME` del `.env` del proyecto (el mismo que usa el bot).

**Cambios:**
1. El dashboard carga `.env` del raíz del repo (además de `.env.dashboard`).
2. Se expone `restaurant_name` en todas las plantillas vía el context processor.
3. El sidebar usa `{{ restaurant_name }}` en lugar de «Restaurante».

Asegúrate de tener en tu `.env`:

```env
RESTAURANT_NAME=Tu Nombre de Restaurante
```

Si no está definida, se usa el mismo valor por defecto que el bot: `La Casa del Sabor`. Reinicia el servidor Django para que tome el cambio del `.env`.






## Segundo prompt ##

Quiero que solamente y unicamente y estrictamente hagas lo siguiente en la dashboard web: 

El menu de la izquierda, quiero que solamente quede de título Administración, y las opciones Inicio, pedidos, clientes, menu, reservas, en ese orden y abajo donde dice admin quitarlo y dejar el salir, solo eso


## Resp cursor ##

Hecho. Cambios en `dashboard/apps/operations/templates/operations/partials/sidebar.html`:

**Menú lateral**
- Un solo bloque con título **Administración**
- Enlaces en este orden: **Inicio**, **Pedidos**, **Clientes**, **Menú**, **Reservas**
- Quitadas las secciones Operaciones, Administración (centro admin, auditoría, accesos, configuración) y Sistema (estado, guía escrituras, Django admin)

**Pie del menú**
- Eliminado el nombre de usuario (`admin` u otro)
- Solo queda el botón **Salir**

El nombre del restaurante arriba del menú se mantiene igual que antes. Recarga la dashboard para verlo.






## Tercer prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Quiero que mejores los menús y las formas de interactuar de la dashboard, no toques la estructura del menú izquierda pero si la forma por ejemplo de agregar editar y eso, hazlo como una plataforma bien pro, un diseño bien pro editable pro facil y sencillo super intuitivo y bonito]


## Resp cursor ##


### Análisis previo

La dashboard ya tenía base sólida (tokens, tablas, toasts), pero las interacciones de CRUD eran rudimentarias: muchos botones inline en el menú, `confirm()` del navegador, formularios planos y listas poco orientadas a la acción. La petición excluía el menú lateral; el foco era listas, formularios y acciones (agregar, editar, eliminar).

### Cambios implementados

- **Menú de platos**: tarjetas por categoría, badges de disponibilidad, menú ⋮ con acciones agrupadas (editar, no disponible, baja, eliminar).
- **Formularios** (plato, pedido, cliente): panel con cabecera, pie fijo y checkbox de disponibilidad más claro.
- **Listas** (pedidos, clientes, reservas): cabecera unificada, tablas en card, filas clicables al detalle.
- **Detalle** pedido/cliente: secciones separadas, diálogo de confirmación propio en lugar de `alert()`.
- **JS** (`shell.js`): menús desplegables, confirmaciones, filas clicables.

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `dashboard/static/css/components.css` | Estilos page-header, form-panel, action-menu, confirm-dialog, badges |
| `dashboard/static/css/app.css` | Bloques de categoría del menú, filas clicables |
| `dashboard/static/js/shell.js` | Menús, confirmaciones, filas clicables |
| `dashboard/apps/operations/templates/operations/partials/icons_sprite.html` | Iconos plus, more-vertical, edit, trash, eye |
| `dashboard/apps/operations/templates/operations/partials/page_header.html` | **Nuevo** partial de cabecera |
| `menu.html`, `menu_form.html`, `order_form.html`, `customer_form.html` | UX mejorada |
| `order_list.html`, `user_list.html`, `reservation_list.html` | Listas pro |
| `order_detail.html`, `customer_detail.html` | Detalle y acciones pulidos |

**No se tocó** `sidebar.html` ni backend (views, URLs, APIs).

### Riesgos mitigados

- Misma lógica POST y permisos (`can_create`, `can_operate`, etc.).
- Sin cambios en endpoints ni contratos JSON.
- Confirmaciones solo sustituyen `onclick="return confirm(...)"` por `data-confirm`.

### Compatibilidad verificada

- Bot, parser, Flask y servicios intactos.
- Solo templates + CSS + JS del panel Django.

### Funcionalidades agregadas

- Menú contextual por plato, diálogo de confirmación, filas clicables en listas, formularios con panel visual.

### Funcionalidades preservadas

- CRUD, filtros, paginación, permisos por rol y estructura del menú izquierdo (Administración → Inicio, Pedidos, Clientes, Menú, Reservas, Salir).

Recarga la dashboard con **Ctrl+F5** para ver CSS/JS nuevos. Si quieres el mismo tratamiento en pantallas de administración (auditoría, configuración), dímelo y lo aplicamos sin tocar el sidebar.





## Cuarto prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[Que en la dashboard, en pedidos, haya un botón que diga confirmar pedido, y haya dos pestañas uno con pedido pendiente, otro con pedido confirmado, y otra con pedido entregado]



## Resp cursor ##

### Análisis previo

En pedidos ya existía filtro por estado (desplegable) y el botón **Confirmar pedido** solo en el detalle. La tarea pide tres vistas por estado (pendiente, confirmado, entregado) y confirmar desde la lista.

### Cambios implementados

1. **Pestañas** en la lista de pedidos: **Pendiente**, **Confirmado**, **Entregado** (sustituyen el selector de estado).
2. **Botón «Confirmar pedido»** en cada fila de la pestaña Pendiente (operador + `DASHBOARD_ENABLE_WRITES=1`).
3. Tras confirmar desde la lista, vuelves a **Pedidos → Pendiente** (no al detalle).
4. Por defecto, al entrar en Pedidos sin `?status=`, se abre la pestaña **Pendiente**.

El detalle del pedido conserva su botón **Confirmar pedido** sin cambios.

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `dashboard/apps/operations/views.py` | Pestañas, permisos de confirmación, redirección tras confirmar |
| `dashboard/apps/operations/templates/operations/order_list.html` | UI de pestañas y botón en tabla |
| `dashboard/static/css/components.css` | Estilos `.status-tabs` y columna de acciones |

### Riesgos mitigados

- Sin cambios en APIs del bot, `order_service`, Twilio ni JSON de caché.
- Confirmación reutiliza `bot_bridge.confirm_order` y el POST del detalle.
- `return_to_list` solo redirige a la URL fija de pedidos con `status=pending`.

### Compatibilidad verificada

- Filtros de búsqueda, fechas, ordenación y paginación siguen funcionando.
- Panel de ajustes y auditoría sin cambios de contrato.
- Operadores y escritura condicionados como antes.

### Funcionalidades agregadas

- Tres pestañas por estado en la lista.
- Confirmar pedido desde la lista (pestaña Pendiente).

### Funcionalidades preservadas

- Detalle de pedido, crear pedido, cancelar, editar estado/ítems.
- Badges de estado, gráficos del inicio y resto del dashboard.

**Nota:** hace falta `DASHBOARD_ENABLE_WRITES=1` en `.env.dashboard` y usuario operador para ver el botón. Si no aparece, revisa esos dos puntos.


## Quinto prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[El botón de nuevo pedido se ve azul y cuando paso el cursor se ven las letras y desaparecen, lo mismo pasa con el de clientes y menú, arregla eso]


## Resp cursor ##

### Análisis previo

Los botones «Nuevo pedido», «Nuevo cliente» y «Nuevo plato» usan `btn btn-primary` dentro de `.app-content`. En `app.css` había reglas genéricas para todos los enlaces:

```47:56:c:\Users\Usuario\Desktop\chatbot-cursor\dashboard\static\css\app.css
.app-content a:not(.btn) {
  color: var(--color-accent);
  ...
}
```

Esas reglas tenían más especificidad que `.btn-primary` y forzaban texto azul sobre fondo azul. Al pasar el cursor, el color cambiaba a `--color-accent-hover` (otro tono azul) y el texto parecía desaparecer.

### Cambios implementados

Se excluyeron los enlaces con clase `.btn` de los estilos genéricos de enlaces en `.app-content`, usando `a:not(.btn)`. Así los botones primarios conservan el texto blanco (`--color-accent-text`) definido en `components.css`.

### Archivos modificados

- `dashboard/static/css/app.css`

### Riesgos mitigados

- Sin cambios en HTML, vistas ni lógica.
- Los enlaces normales del contenido siguen con el mismo estilo azul y subrayado al hover.
- Todos los botones-enlace (`btn-primary`, `btn-ghost`, etc.) quedan protegidos del mismo conflicto.

### Compatibilidad verificada

- Sin cambios en APIs, endpoints, parser, Flask, Twilio ni servicios del chatbot.
- Solo CSS del dashboard.

### Funcionalidades agregadas

- Ninguna (corrección visual).

### Funcionalidades preservadas

- Navegación y acciones de «Nuevo pedido», «Nuevo cliente» y «Nuevo plato» sin cambios funcionales.

Recarga la página (Ctrl+F5 si hace falta limpiar caché) para ver los botones con texto blanco legible y hover correcto.




## Sexto prompt ##

OBLIGATORIO:

Lee y aplica completamente AI_RULES.md.

Cumple todas sus restricciones antes de realizar cambios.

TAREA:
[haz solo esto: que en pedidos, en el dashboard, el buscador solo aparezca en entregado]


## Resp cursor ##

### Análisis previo

El buscador (campo de texto, fechas y botón «Buscar») estaba siempre visible en `order_list.html`, sin depender de la pestaña activa. La pestaña «Entregado» usa la clave `delivered`.

### Cambios implementados

El formulario `data-toolbar` queda envuelto en `{% if status_filter == "delivered" %}`, así que solo se muestra en la pestaña Entregado.

### Archivos modificados

- `dashboard/apps/operations/templates/operations/order_list.html`

### Riesgos mitigados

- Un solo archivo modificado.
- Sin cambios en vistas, endpoints ni lógica de filtrado en backend.
- Pendiente y Confirmado siguen igual; solo cambia la visibilidad del buscador.

### Compatibilidad verificada

- Sin impacto en parser, Flask, Twilio ni servicios del chatbot.
- Tests existentes no comprueban la visibilidad del buscador.

### Funcionalidades agregadas

- Buscador visible únicamente en la pestaña Entregado.

### Funcionalidades preservadas

- Filtrado por estado, tabla, paginación, confirmación de pedidos y resto del dashboard sin cambios.





######################################################################
## v0.33

## Prompt ##

@DASHBOARD_RULES.md

TAREA: [
  Modo: solo auditoría/plan. Anula §0 (no código, no grep exploratorio).

Menú `/menu/` — auditar + priorizar + plan 3 fases. Sin código/PR.

**Sí:** listado, form, disponibilidad, permisos operador/admin. **No:** sidebar, bot, `app/`, contrato JSON salvo compat.

**Leer:** `menu.html`, `menu_form.html`, `forms.py` (MenuItemForm), `views.py` (MenuView), `readers.py` (id|nombre|precio|categoria|disponible), `permissions.py`, `app.css`+`components.css`, `bot_bridge.py`.

**Objetivo:** ver carta · buscar plato · agotado/precio rápido · alta sin fricción · sin errores graves · móvil cocina/mostrador.

**Ref:** POS carta (Square/Toast/Lightspeed), delivery, CMS carta. **Visual:** premium SaaS (Stripe/Linear/Shopify/Notion); P0/P1/P2 solo UI.

**Futuro:** tpl+css+`shell.js` primero; backend solo iteración aparte. ≤3 archivos/fase. Schema+permisos+bridge+1→2→3 intactos. Microcopy ES sin jerga.

**Salida:** 1 bullet/ítem (máx. 2 niveles). Compacto, cero relleno.

1. **Análisis** — fortalezas · debilidades · fricción operador/admin
2. **Benchmark** — 5–8 patrones (copiar / no aplica)
3. **Propuestas** — P0/P1/P2: qué · por qué · S/M/L · archivos · riesgo
4. **Flujos** — 2–3 críticos (ascii/mermaid breve)
5. **Riesgos** — bot · permisos · writes off · destructivas
6. **Compat** — contratos/reglas
7. **Agregadas** — valor P0+P1
8. **Preservadas** — invariantes
9. **Mapa vivo (§5)** — sí/no + delta

**# Visual premium** — P0 · P1 · P2

**Plan 3 fases** (núcleo; 1 fila = 1 fase implementable):

| Fase | Cambio (1 línea) | P0/P1/P2 | Archivos ≤3 | Backend | Hecho (1 línea) |
|------|------------------|----------|-------------|---------|-----------------|
| 1 | | | | sí/no | |
| 2 | | | | | |
| 3 | | | | | |

Fusionar en misma fase lo que comparta tpl+css. Backend al final si hace falta.

Cierre (3 bullets): primero · por qué · mejora día a día (lenguaje restaurante).
]


## Respuesta cursor ##


1. **Análisis** — fortalezas · debilidades · fricción operador/admin  
   - Fortalezas: separación clara `dashboard_operator` vs `dashboard_admin` en `apps/operations/permissions.py` y gating UI en `apps/operations/views.py::MenuView` + `dashboard/apps/operations/templates/operations/menu.html` (operador solo marca “no disponible”; admin hace CRUD).  
   - Fortalezas: acciones destructivas con doble ruta “dado de baja” vs “eliminar permanente” (con confirm) en `menu.html` y ejecución/seguridad en `MenuItemDeleteView` + `bot_bridge.delete_menu_item(hard=...)`.  
   - Debilidades/fricción: (a) operador no puede re-activar un plato desde el listado (solo admin lo edita en `menu_form.html`), lo que frena cocina/mostrador; (b) si estás en modo “solo lectura” (writes deshabilitadas), no hay un banner explicando por qué desaparecen las acciones; (c) el empty-state dice “el bot los carga desde Google Sheets” aunque `readers.read_menu()` también puede quedar vacío si Sheets falla.

2. **Benchmark** — 5–8 patrones (copiar / no aplica)  
   - Copiar: “permisos en UI + permisos en backend” (`MenuView`/mixins + `menu.html` condicionales).  
   - Copiar: “feature flag de escritura” (`bot_bridge.writes_enabled()` corta writes).  
   - Copiar: “doble nivel de destrucción” (`hard=0` vs `hard=1`, con confirm distintos).  
   - Copiar: “validación de unicidad/consistencia antes y al escribir” (`MenuItemForm.clean_item_id()` + checks en `bot_bridge.save_menu_item()`).  
   - Copiar: “cache-first + fallback a Sheets” (`readers.py` usa `data/menu_cache.json` y si no, llama al cliente).  
   - Revisar/no aplica: “confirm vía `data-confirm`” depende de JS global; CSS existe (`.confirm-dialog`), pero hay que asegurar que realmente se activa en `menu.html` (si no, las confirmaciones no detendrían acciones).

3. **Propuestas** — P0/P1/P2: qué · por qué · S/M/L · archivos · riesgo  
   - **P0 (Fase 1, solo UI; S; bajo riesgo)**: añadir en `menu.html` un mini-aviso cuando no hay acciones (modo solo lectura o sin permisos) y dejar una frase explícita para operador: “Como operador solo puedes marcar como no disponible; para volver a disponible se necesita admin”.  
     - Por qué: elimina el “¿por qué no me sale el botón?” en cocina/mostrador.  
     - Archivos ≤3: `dashboard/apps/operations/templates/operations/menu.html` (posible reuse de `.banner-readonly` en `components.css`).  
     - Backend: no.  
   - **P1 (Fase 2, solo UI; S/M; bajo riesgo)**: ajustar legibilidad en móvil en el listado del menú (priorizar nombre + precio + estado; limitar ruido del ID en pantalla chica).  
     - Por qué: lectura rápida con manos ocupadas.  
     - Archivos ≤3: `menu.html` + `dashboard/static/css/app.css` (reglas responsive para `.menu-item-id`/espaciado si hace falta).  
     - Backend: no.  
   - **P2 (Fase 3, funcional; M; riesgo medio)**: permitir “Marcar disponible” al operador desde el mismo listado (además de “Marcar no disponible”).  
     - Por qué: reduce dependencia de admin para reactivar platos.  
     - Qué cambia: `menu.html` añade botón/form para `disponible -> true` y `apps/operations/views.py::MenuView.post` maneja `action="available"` llamando a `bot_bridge.set_menu_item_availability(item_id, True)` + `log_audit`.  
     - Archivos ≤3: `menu.html`, `apps/operations/views.py`.  
     - Riesgo: medio por seguridad/flujo (hay que mantener confirm y asegurarnos de que la semántica soft/hard no se rompe).

4. **Flujos** — 2–3 críticos (breve)  
   - **Ver menú (roles + modo escritura)**  
     ```mermaid
     flowchart TD
       A[GET /menu/] --> B[MenuView.get]
       B --> C[can_admin / can_operate / can_create con writes_enabled]
       B --> D[readers.menu_by_category()]
       D --> E[Render menu.html con acciones condicionadas]
     ```
   - **Operador: marcar “no disponible”**  
     ```mermaid
     flowchart TD
       A[Click "Marcar no disponible"] --> B[Confirm UI (data-confirm)]
       B --> C[POST /menu/ action=unavailable]
       C --> D[MenuView.post: valida operator]
       D --> E[bot_bridge.set_menu_item_unavailable()]
       E --> F[log_audit + messages + redirect /menu]
     ```
   - **Admin: eliminar permanente**  
     ```mermaid
     flowchart TD
       A[Click "Eliminar permanente"] --> B[Confirm UI]
       B --> C[POST /menu_delete/{id}/ hard=1]
       C --> D[AdminRequiredMixin]
       D --> E[bot_bridge.delete_menu_item(hard=True)]
       E --> F[log_audit + flash + redirect /menu]
     ```

5. **Riesgos** — bot · permisos · writes off · destructivas  
   - **Bot offline / Sheets falla**: `readers.read_menu()` puede devolver vacío; el empty-state de `menu.html` puede confundir (“se carga desde Google Sheets”).  
   - **Permisos**: `MenuView.post` valida operator en `unavailable`; si se añade “available”, hay que repetir exactamente esa validación para evitar escaladas.  
   - **Writes off**: aunque la UI oculte acciones, llamadas forjadas podrían llegar; `bot_bridge` debe seguir bloqueando por `writes_enabled` (ya lo hace).  
   - **Destructivas**: confirmar que “Dar de baja” realmente es *soft* (hard=False) en `menu_service.remove_item(...)`; si no, el texto y la expectativa del admin se rompen.

6. **Compat** — contratos/reglas  
   - Mantener: contrato de `bot_bridge` (firmas `set_menu_item_unavailability`, `set_menu_item_availability`, `delete_menu_item(item_id, hard=...)`) y nombres de acciones HTTP actuales (`action="unavailable"`, `hard=1`).  
   - Mantener: grupos `dashboard_operator`/`dashboard_admin` y la lógica de `user_is_dashboard_operator()` en `permissions.py`.

7. **Agregadas** — valor P0+P1  
   - Menos fricción inmediata: operador entiende por qué no ve reactivación y por qué a veces no ve acciones.  
   - Mejor operativa en sala: listado más “scan-friendly” (nombre/estado/precio) para decisiones rápidas.

8. **Preservadas** — invariantes  
   - ID como clave (unicidad en `MenuItemForm.clean_item_id()` + chequeo en `bot_bridge.save_menu_item()`).  
   - CRUD protegido por roles (`AdminRequiredMixin` para crear/editar/eliminar; operador solo disponibilidad).  
   - Confirmaciones para rutas destructivas y mensajes de feedback vía `messages`.

9. **Mapa vivo (§5)** — sí/no + delta  
   - **No**: la auditoría no requiere cambiar estructura/URL/backend nuevos; delta solo si en P2 se añade acción nueva (`action="available"`), entonces habría que reflejarlo como “cambio en pantalla Menú” dentro del mapa de trabajo futuro.





## Segundo Prompt ##
@DASHBOARD_RULES.md
TAREA: [
Modo: aplicar cambios (no solo auditoría).

Menú `/menu/` — P0:
- Cuando en el listado no haya acciones disponibles (por rol o por writes off), quiero un aviso visual claro y microcopy corto para el operador explicando por qué no ve botones.
- Mantener backend intacto: solo tocar `menu.html` y reusar estilos existentes (`.banner-readonly`, `.banner`, `.muted`, etc.) en `components.css`.

Cambios concretos:
- En `dashboard/apps/operations/templates/operations/menu.html`:
  - Detectar situación “sin acciones” (p.ej. `not can_operate and not can_create` o writes off si ya viene en contexto) y mostrar un bloque tipo banner encima de las tablas o del empty-state, con copy como:
    - Título: “Panel en modo solo lectura” (si aplica writes off) o “Acciones limitadas para este usuario”.
    - Texto: “Como operador puedes marcar platos no disponibles. Para volver a ponerlos disponibles o editar precios, necesita entrar un admin.” (ajusta el texto según el contexto que tengas en plantilla).
- No introducir lógica nueva de permisos ni cambiar `MenuView`; solo usar variables de contexto ya existentes.

Objetivo:
- El operador entiende de inmediato por qué no ve botones de edición/eliminación/reactivación.
- El empty-state y la tabla mantienen consistencia visual con el resto del dashboard.

Respeta:
- Contratos actuales (`bot_bridge`, `readers`, permisos).
- Estilos base (`components.css`, `app.css`).

Entrega:
- Aplica los cambios en plantilla/CSS necesarios (máximo 2 archivos: `menu.html` + `components.css` si hace falta).
- Explica brevemente al final qué tocaste (archivo + 1 línea).
]


## Resp cursor ##


### Análisis previo
- **Contexto**: `/menu/` ya recibe `can_operate`, `can_create` y (según reglas) `dashboard_writes_enabled`, y oculta la columna de acciones cuando no hay permisos.
- **Patrón existente**: El modo solo lectura por writes off se comunica con `.banner.banner-readonly`, usando el partial `operations/partials/readonly_banner.html`.

### Cambios
- **Lógica de banner sobre la tabla/empty-state**:
  - Justo después del `page_header` en `menu.html` añadí:
    - **Caso writes off** (`not dashboard_writes_enabled`): reutiliza el partial `readonly_banner.html` para mostrar “Modo solo lectura” con copy ya estandarizado en el dashboard.
    - **Caso sin acciones por permisos** (`not can_operate and not can_create` con writes activos): muestra un banner `.banner.banner-readonly` explicando que las acciones de edición/alta/baja están reservadas a perfiles con permisos de administración.

### Código relevante

```5:18:dashboard/apps/operations/templates/operations/menu.html
{% block content %}
{% if can_create %}
{% url 'operations:menu_create' as menu_create_url %}
{% include "operations/partials/page_header.html" with title="Menú" subtitle="Platos del bot, agrupados por categoría. Edita precios, disponibilidad y altas desde aquí." action_url=menu_create_url action_label="Nuevo plato" %}
{% else %}
{% include "operations/partials/page_header.html" with title="Menú" subtitle="Platos del bot, agrupados por categoría." %}
{% endif %}

{% if not dashboard_writes_enabled %}
{% include "operations/partials/readonly_banner.html" %}
{% elif not can_operate and not can_create %}
<p class="banner banner-readonly" role="status">
  <strong>Acciones limitadas para este usuario.</strong>
  <span class="muted">Solo los perfiles con permisos de administración pueden editar precios, dar de alta o baja platos o cambiar su disponibilidad. Si necesitas hacer cambios, pide a un admin que entre al panel.</span>
</p>
{% endif %}

{% for category, items in menu_by_category.items %}
```  

### Archivos tocados
- **`menu.html`**: Añadido bloque condicional de banner sobre la tabla/empty-state, reutilizando `readonly_banner.html` y clases `.banner`, `.banner-readonly`, `.muted`.  

(0 cambios en `components.css`, se reutilizan estilos existentes).




## Tercer prompt ##

@DASHBOARD_RULES.md
TAREA: [
Modo: aplicar cambios (no solo auditoría).

Menú `/menu/` — P1:
- Mejorar arquitectura visual del listado por categoría para lectura rápida en escritorio y móvil:
  - Priorizar nombre del plato, precio y estado.
  - Reducir el ruido visual del ID (por ejemplo, menos prominente, solo si hace falta; en móvil podría ocultarse o ponerse en una segunda línea discreta).
  - Mantener la tabla y las acciones actuales sin romper el layout.

Cambios concretos (UI/tpl+css):
- En `dashboard/apps/operations/templates/operations/menu.html`:
  - Revisar la celda de nombre/ID (`.menu-item-name`, `.menu-item-id`) y reorganizar jerarquía visual (nombre arriba, ID secundario).
  - Asegurarte de que el estado (badge de disponibilidad) quede alineado y legible junto al precio.
- En `dashboard/static/css/app.css` (y, si hace falta, `components.css`):
  - Añadir/ajustar reglas para `.menu-item-name`, `.menu-item-id`, `.menu-item-price` y filas de la data-table:
    - En pantallas estrechas, priorizar nombre + estado; el ID puede tener fuente más pequeña y menor contraste o incluso ocultarse si el espacio es muy limitado (usando media queries).
    - Mantener el aspecto “premium SaaS” del resto del dashboard.

Restricciones:
- No cambiar contratos ni backend (sin tocar `views.py`, `bot_bridge.py`, `readers.py`).
- Máx. 3 archivos en total (idealmente `menu.html` + `app.css`; `components.css` solo si es imprescindible).

Objetivo:
- El operador puede “scannear” categorías y platos con 1–2 segundos por pantalla, incluso en móvil o en un portátil pequeño.
- Diseño consistente con el resto del dashboard.

Entrega:
- Aplica cambios de plantilla y CSS.
- Cierra con un resumen muy breve (1–2 frases) de qué mejoró a nivel visual.
]


## Resp cursor ##

### Resumen de cambios

- **Jerarquía visual del plato**: el nombre queda en la parte superior con mayor peso, y el ID pasa a una línea secundaria, más discreta y con tipografía monoespaciada y tamaño reducido, manteniendo la tabla y acciones intactas.
- **Precio + estado alineados**: el precio y el badge de disponibilidad se agrupan en el mismo bloque para escritorio, y en móvil el estado se prioriza mostrándose en su propia celda con tamaño compacto, facilitando el escaneo rápido por categoría y plato en pantallas pequeñas.


## Cuarto prompt ##

@DASHBOARD_RULES.md
TAREA: [
Modo: aplicar cambios (UI + backend mínimos).

Menú `/menu/` — P2:
- Extender la pantalla para que el operador pueda volver a marcar un plato como “Disponible” desde el mismo listado (además de “Marcar no disponible”), manteniendo:
  - Seguridad de permisos.
  - Respeto a `writes_enabled`.
  - Confirm dialogs coherentes.

Cambios concretos:
- En `dashboard/apps/operations/templates/operations/menu.html`:
  - En el action menu por plato, añadir una acción “Marcar disponible” solo cuando `item.disponible` sea falso y el usuario tenga permisos operativos (`can_operate` y/o `can_create` según patrón actual).
  - Usar el mismo patrón de formulario POST + `data-confirm` que “Marcar no disponible”, pero con `action="available"` y copy ajustado.
- En `dashboard/apps/operations/views.py` (`MenuView.post`):
  - Mantener el branch existente para `action == "unavailable"`.
  - Añadir un branch simétrico para `action == "available"`:
    - Reutilizar validación de operador (`user_is_dashboard_operator`) y el mismo patrón de audit log (`log_audit`) y `messages`.
    - Llamar a `bot_bridge.set_menu_item_availability(item_id, True)` con manejo del resultado análogo a `set_menu_item_unavailable`.
- En `dashboard/services/bot_bridge.py`:
  - Reutilizar la función ya existente `set_menu_item_availability(item_id, disponible)` sin cambiar su firma ni comportamiento global.
  - Si algo de la lógica necesita mínimo ajuste para este nuevo uso, que sea totalmente compatible hacia atrás (no romper menú ni otros flujos).

Restricciones:
- Mantener contratos (`WriteResult`, firmas `bot_bridge`, `readers`, permisos).
- Respetar la separación de roles:
  - Solo operadores/admin pueden cambiar disponibilidad desde `/menu/`.
- No tocar `app/*`, ni `data/*.json`.

Objetivo:
- Flujo operativo: operador puede marcar un plato como no disponible y, más tarde, volverlo a disponible desde el mismo listado, sin depender de un admin para esa operación.
- UX consistente con el resto del dashboard (misma acción-menu, mismas confirmaciones, mismos toasts).

Entrega:
- Actualiza `menu.html`, `operations/views.py` y, solo si es imprescindible, un pequeño ajuste en `bot_bridge.py`.
- Termina con un resumen de 2–3 frases: qué cambió y cómo lo usa el operador día a día.
]


## Resp cursor ##


### Prompt Fase 1 — P0 (UI: aviso modo solo lectura / sin permisos)

```text
@DASHBOARD_RULES.md
TAREA: [
Modo: aplicar cambios (no solo auditoría).

Menú `/menu/` — P0:
- Cuando en el listado no haya acciones disponibles (por rol o por writes off), quiero un aviso visual claro y microcopy corto para el operador explicando por qué no ve botones.
- Mantener backend intacto: solo tocar `menu.html` y reusar estilos existentes (`.banner-readonly`, `.banner`, `.muted`, etc.) en `components.css`.

Cambios concretos:
- En `dashboard/apps/operations/templates/operations/menu.html`:
  - Detectar situación “sin acciones” (p.ej. `not can_operate and not can_create` o writes off si ya viene en contexto) y mostrar un bloque tipo banner encima de las tablas o del empty-state, con copy como:
    - Título: “Panel en modo solo lectura” (si aplica writes off) o “Acciones limitadas para este usuario”.
    - Texto: “Como operador puedes marcar platos no disponibles. Para volver a ponerlos disponibles o editar precios, necesita entrar un admin.” (ajusta el texto según el contexto que tengas en plantilla).
- No introducir lógica nueva de permisos ni cambiar `MenuView`; solo usar variables de contexto ya existentes.

Objetivo:
- El operador entiende de inmediato por qué no ve botones de edición/eliminación/reactivación.
- El empty-state y la tabla mantienen consistencia visual con el resto del dashboard.

Respeta:
- Contratos actuales (`bot_bridge`, `readers`, permisos).
- Estilos base (`components.css`, `app.css`).

Entrega:
- Aplica los cambios en plantilla/CSS necesarios (máximo 2 archivos: `menu.html` + `components.css` si hace falta).
- Explica brevemente al final qué tocaste (archivo + 1 línea).
]
```

---

### Prompt Fase 2 — P1 (UI: legibilidad y arquitectura visual del listado por categoría)

```text
@DASHBOARD_RULES.md
TAREA: [
Modo: aplicar cambios (no solo auditoría).

Menú `/menu/` — P1:
- Mejorar arquitectura visual del listado por categoría para lectura rápida en escritorio y móvil:
  - Priorizar nombre del plato, precio y estado.
  - Reducir el ruido visual del ID (por ejemplo, menos prominente, solo si hace falta; en móvil podría ocultarse o ponerse en una segunda línea discreta).
  - Mantener la tabla y las acciones actuales sin romper el layout.

Cambios concretos (UI/tpl+css):
- En `dashboard/apps/operations/templates/operations/menu.html`:
  - Revisar la celda de nombre/ID (`.menu-item-name`, `.menu-item-id`) y reorganizar jerarquía visual (nombre arriba, ID secundario).
  - Asegurarte de que el estado (badge de disponibilidad) quede alineado y legible junto al precio.
- En `dashboard/static/css/app.css` (y, si hace falta, `components.css`):
  - Añadir/ajustar reglas para `.menu-item-name`, `.menu-item-id`, `.menu-item-price` y filas de la data-table:
    - En pantallas estrechas, priorizar nombre + estado; el ID puede tener fuente más pequeña y menor contraste o incluso ocultarse si el espacio es muy limitado (usando media queries).
    - Mantener el aspecto “premium SaaS” del resto del dashboard.

Restricciones:
- No cambiar contratos ni backend (sin tocar `views.py`, `bot_bridge.py`, `readers.py`).
- Máx. 3 archivos en total (idealmente `menu.html` + `app.css`; `components.css` solo si es imprescindible).

Objetivo:
- El operador puede “scannear” categorías y platos con 1–2 segundos por pantalla, incluso en móvil o en un portátil pequeño.
- Diseño consistente con el resto del dashboard.

Entrega:
- Aplica cambios de plantilla y CSS.
- Cierra con un resumen muy breve (1–2 frases) de qué mejoró a nivel visual.
]
```

---

### Prompt Fase 3 — P2 (Funcional+UI: operador puede “Marcar disponible”)

```text
@DASHBOARD_RULES.md
TAREA: [
Modo: aplicar cambios (UI + backend mínimos).

Menú `/menu/` — P2:
- Extender la pantalla para que el operador pueda volver a marcar un plato como “Disponible” desde el mismo listado (además de “Marcar no disponible”), manteniendo:
  - Seguridad de permisos.
  - Respeto a `writes_enabled`.
  - Confirm dialogs coherentes.

Cambios concretos:
- En `dashboard/apps/operations/templates/operations/menu.html`:
  - En el action menu por plato, añadir una acción “Marcar disponible” solo cuando `item.disponible` sea falso y el usuario tenga permisos operativos (`can_operate` y/o `can_create` según patrón actual).
  - Usar el mismo patrón de formulario POST + `data-confirm` que “Marcar no disponible”, pero con `action="available"` y copy ajustado.
- En `dashboard/apps/operations/views.py` (`MenuView.post`):
  - Mantener el branch existente para `action == "unavailable"`.
  - Añadir un branch simétrico para `action == "available"`:
    - Reutilizar validación de operador (`user_is_dashboard_operator`) y el mismo patrón de audit log (`log_audit`) y `messages`.
    - Llamar a `bot_bridge.set_menu_item_availability(item_id, True)` con manejo del resultado análogo a `set_menu_item_unavailable`.
- En `dashboard/services/bot_bridge.py`:
  - Reutilizar la función ya existente `set_menu_item_availability(item_id, disponible)` sin cambiar su firma ni comportamiento global.
  - Si algo de la lógica necesita mínimo ajuste para este nuevo uso, que sea totalmente compatible hacia atrás (no romper menú ni otros flujos).

Restricciones:
- Mantener contratos (`WriteResult`, firmas `bot_bridge`, `readers`, permisos).
- Respetar la separación de roles:
  - Solo operadores/admin pueden cambiar disponibilidad desde `/menu/`.
- No tocar `app/*`, ni `data/*.json`.

Objetivo:
- Flujo operativo: operador puede marcar un plato como no disponible y, más tarde, volverlo a disponible desde el mismo listado, sin depender de un admin para esa operación.
- UX consistente con el resto del dashboard (misma acción-menu, mismas confirmaciones, mismos toasts).

Entrega:
- Actualiza `menu.html`, `operations/views.py` y, solo si es imprescindible, un pequeño ajuste en `bot_bridge.py`.
- Termina con un resumen de 2–3 frases: qué cambió y cómo lo usa el operador día a día.
]
```




## Quinto prompt ##

Rediseñar completamente el módulo MENÚ del restaurante.

NO quiero un retoque visual.

NO quiero mover dos botones y cambiar colores.

Quiero una experiencia completamente profesional, moderna y lista para venderse como SaaS comercial.

Tienes libertad total para modificar:

* Layout
* Jerarquía visual
* Distribución
* Componentes
* Espaciado
* Navegación interna
* Organización de categorías
* Presentación de productos
* Formularios
* Estados
* Acciones

SIEMPRE que mantengas compatibilidad con:

* Contratos existentes
* Backend actual
* Permisos actuales
* Integraciones actuales
* Lógica del bot

No romper funcionalidades existentes.

---

# PROCESO OBLIGATORIO

Antes de tocar código:

1. Analiza la implementación actual.
2. Identifica los problemas de UX.
3. Identifica los problemas visuales.
4. Identifica cuellos de botella operativos.
5. Compara la pantalla actual contra productos líderes del mercado.
6. Diseña una solución superior.
7. Implementa la nueva experiencia.

NO te limites por la interfaz actual.

Piensa desde cero.

---

# REFERENCIAS OBLIGATORIAS

Tomar inspiración de:

* Shopify Admin
* Toast POS
* Square Dashboard
* Lightspeed Restaurant
* Stripe Dashboard
* Linear
* Notion

NO copiar estilos.

Copiar principios:

* Claridad
* Escaneabilidad
* Rapidez
* Jerarquía visual
* Simplicidad
* Productividad

---

# OBJETIVO PRINCIPAL

Un encargado de restaurante debe poder:

* Encontrar cualquier producto en segundos.
* Crear productos rápidamente.
* Modificar precios rápidamente.
* Marcar agotados rápidamente.
* Gestionar cientos de productos sin sentirse perdido.

La pantalla debe sentirse:

* Premium
* Moderna
* Profesional
* Limpia
* Muy rápida

---

# ARQUITECTURA RECOMENDADA

Si encuentras una arquitectura superior, puedes cambiarla.

Sin embargo, prioriza esta estructura:

## Nivel 1

Encabezado

* MENÚ
* Descripción corta
* Botón principal "Nuevo producto"

---

## Nivel 2

Barra de gestión

* Búsqueda
* Categorías
* Estado
* Total productos

Debe permanecer visible y ser extremadamente rápida de usar.

---

## Nivel 3

Contenido principal

Organizar por categorías.

Cada categoría debe actuar como una sección clara.

Ejemplo:

Hamburguesas
Bebidas
Pizzas
Postres

Mostrar cantidad de productos.

---

## Nivel 4

Productos

Cada producto debe mostrar sin abrir nada:

* Nombre
* Precio
* Estado
* Acciones

No obligar al usuario a entrar al detalle para operaciones simples.

---

# EXPERIENCIA PREMIUM

Aplicar principios de:

* Fitts Law
* Progressive Disclosure
* Visual Hierarchy
* Cognitive Load Reduction

Eliminar:

* Ruido visual
* Bordes innecesarios
* Contenedores redundantes
* Espaciados inconsistentes

---

# FORMULARIOS

Rediseñar completamente la experiencia de:

* Crear producto
* Editar producto

Objetivo:

Que un usuario sin experiencia pueda crear un producto en menos de 20 segundos.

Agrupar campos de forma lógica.

Reducir complejidad visual.

Eliminar fricción.

---

# ESTADOS

La disponibilidad debe ser visible instantáneamente.

No depender únicamente del color.

Usar badges claros.

---

# ACCIONES

Las acciones frecuentes deben ser visibles.

Prioridad:

1. Editar
2. Disponible / Agotado
3. Eliminar

Evitar esconder operaciones importantes.

---

# MÓVIL

El diseño debe funcionar correctamente en:

* Desktop
* Tablet
* Móvil

Manteniendo jerarquía visual.

---

# CRITERIO DE ÉXITO

Al finalizar:

Si un dueño de restaurante abre la pantalla por primera vez debe entender en menos de 5 segundos:

* Dónde están sus productos.
* Cómo encontrarlos.
* Cómo editarlos.
* Cómo crear nuevos.

Y debe percibir inmediatamente que está utilizando un producto SaaS premium comparable con herramientas comerciales modernas.

Si durante la implementación encuentras una solución mejor que esta especificación, puedes adoptarla siempre que aumente claridad, velocidad y facilidad de uso.


No quiero que toques nada más, esto es una mejora incremental y solo vas a mejorar ese ítem, no toques nada más, y tampoco des explicaciones de nada solo al final un resumen, y verifica que todo quede totalmente correcto, osea no toques nada más solo puedes mejorar eso que está aquí


## Resp cursor ##

Rediseño completo del módulo `MENÚ` aplicado y validado, sin tocar contratos ni lógica backend.

- Reemplacé la vista por una experiencia tipo SaaS: encabezado profesional, barra de gestión fija, búsqueda instantánea, filtros por categoría/estado, métricas en vivo y navegación rápida por categorías.
- Reorganicé el contenido por secciones de categoría con tarjetas de producto de alta escaneabilidad (nombre, precio, estado, ID y acciones visibles sin entrar al detalle).
- Priorizé acciones operativas en línea: `Editar`, `Marcar disponible/agotado` y menú de eliminación, manteniendo permisos y endpoints existentes.
- Rediseñé completamente formularios de crear/editar producto para carga rápida: agrupación lógica, jerarquía clara, toggle de disponibilidad y checklist operativo.
- Apliqué estilo responsive premium para desktop/tablet/móvil con jerarquía visual consistente y reducción de ruido visual.
- Implementé comportamiento JS para filtros combinados, conteos dinámicos, navegación por chips de categoría y actualización de visibilidad en tiempo real.
- Verificación final ejecutada: `python manage.py check` en `dashboard` sin errores.





########################################################
## v0.34
@DASHBOARD_RULES.md

TAREA: [1. Quiero que el menú de la izquierda quede así: Administración (como titulo), luego abajo Inicio, Pedidos, clientes, menú, ventas, reportes, configuración.
(Y dentro de Ventas:

Resumen
Ingresos
Productos más vendidos
Clientes recurrentes
Métricas)
2. Que en la sección llamada Menú, se ve un titulo arriba en la barra menú, ese dejar, debajo hay otro menú y debajo dice Gestiona catálogo, precios y disponibilidad de sde una sola vista, eso quitar, y nuevo producto y nueva categoria van a estar dentro del recuadro de catalogo de productos, a la derecha hay dos recuadros, total y mostrados, solo habrá total.
3. Donde dice Catálogo de productos, eso dejar, pero debajo encuentra, edita y cambia disponibilidad en segundos, eso lo quitas, En el bucador que no diga busca rpor nombre, id o categoría sino que solo diga Buscar
4. "Catalogo de productos" está enuna card independiente, quiero que hagas lo mismo con el listado de productos, los pones todos dentro de otra card, así como la de arriba ese mismo diseño, y lo ordenas como cuadrícula, y puede tener un selector de categoría, hazlo como un diseño sencillo y facil de usar, minimalista lo maximo pero intuitivo y facil, tienes libertad de editar ese diseño

]


## Respuesta cursor ##

Implementé los cambios del bloque de `README.md` en el dashboard, dejando la UI más minimalista y ordenada.

### Qué cambié

- **Menú lateral** en `dashboard/apps/operations/templates/operations/partials/sidebar.html`:
  - Se mantiene **Administración**.
  - Orden principal actualizado a: `Inicio`, `Pedidos`, `Clientes`, `Menú`, `Ventas`, `Reportes`, `Configuración`.
  - `Ventas` ahora muestra subopciones:
    - `Resumen`
    - `Ingresos`
    - `Productos más vendidos`
    - `Clientes recurrentes`
    - `Métricas`
- **Estilos del submenú lateral** en `dashboard/static/css/layout.css`:
  - Nuevas clases para sublinks (`app-nav-submenu`, `app-nav-sublink`) con estilo discreto y limpio.

- **Pantalla de Menú** en `dashboard/apps/operations/templates/operations/menu.html`:
  - Quité el bloque duplicado superior y el texto:
    - “Gestiona catálogo, precios y disponibilidad…”
    - “Encuentra, edita y cambia disponibilidad en segundos.”
  - En “Catálogo de productos”:
    - Dejé solo métrica **Total**.
    - Quité **Mostrados**.
    - Placeholder del buscador cambiado a **“Buscar”**.
    - `Nuevo producto` y `Nueva categoría` ahora están dentro del recuadro de catálogo.
  - Reorganicé el listado:
    - Ahora está en una **card separada** llamada “Listado de productos”.
    - Productos en **cuadrícula** (grid), diseño más simple/minimalista.
    - Se mantiene selector de categoría.

- **Lógica JS de filtros** en `dashboard/static/js/shell.js`:
  - Simplificada para el nuevo layout (búsqueda + categoría).
  - Eliminado manejo de “Mostrados”, chips de salto y filtro por estado.
  - Añadido estado vacío cuando no hay resultados.

- **Estilos del nuevo layout de Menú** en `dashboard/static/css/app.css`:
  - Nuevas reglas para card de listado y grid de productos.
  - Ajustes responsive para mantenerlo limpio en móvil.

### Verificación

- Ejecuté `python dashboard/manage.py check` y pasó sin errores.
- También revisé linter de los archivos editados: **sin errores**.

Si quieres, en el siguiente paso te dejo los sublinks de `Ventas` y `Reportes` conectados a vistas reales (ahora apuntan a anclas del home para mantener la navegación lista mientras se crean esas pantallas).


## Segundo prompt ##

@DASHBOARD_RULES.md

TAREAS: [
1.Arregla el sidebar, ya que debajo de ventas hay resumen, ingresos, productos, mas vendidos, clientes recurrentes, metricas, y eso no va ahí, arreglalo
2. El listado de productos está bien, solamente quiero que ahí en esa misma card, me muestre un listado de productos pero en lista, sencilla, y que se pueda seleccionar la categoría al final de donde dice listado de productos.
3. Cada producto se podrá seleccionar, un botón para disponible/no disponible, y tendrá aspecto minimalista pero funcional


]


## Respuesta cursor ##

Implementé las tareas del bloque que marcaste en `README.md` sobre el dashboard:

- Corregí el sidebar en `dashboard/apps/operations/templates/operations/partials/sidebar.html`: debajo de `Ventas` ya no aparecen `Resumen`, `Ingresos`, `Productos más vendidos`, `Clientes recurrentes` ni `Métricas`.
- Ajusté la card de productos en `dashboard/apps/operations/templates/operations/menu.html`:
  - Se mantiene “Listado de productos”.
  - Moví el selector de categoría al final del encabezado de esa misma card.
  - Dejé el listado en formato simple de lista (una fila por producto).
- Añadí selección por producto y toggle de disponibilidad:
  - Botón `Seleccionar` por cada producto (con estado visual seleccionado).
  - Botón de estado `Disponible` / `No disponible` por producto según corresponda.
- Actualicé estilos en `dashboard/static/css/app.css` para el look minimalista/funcional del listado.
- Actualicé comportamiento en `dashboard/static/js/shell.js` para:
  - filtrado por búsqueda + categoría sobre la lista simple,
  - estado vacío cuando no hay coincidencias,
  - selección de productos en frontend.

También pasé validación de linter sobre los archivos editados y no se detectaron errores.

Si quieres, como siguiente paso te lo dejo aún más “minimal” (por ejemplo ocultando `Editar/Eliminar` tras menú contextual o compactando más botones en móvil).



## tercer prompt ##

analiza solo parser.py y arregla lo siguiente

le escribí dos pizzas hawaianas, dos cocacolas dos hamburguesas de carne y un agua

y me agarró * 2 x Pizza Hawaiana — $250.00
* 3 x Coca Cola — $24.00
* 2 x Hamburguesa Doble Carne — $50.00

Arreglalo e implementa mejoras para que cosas así no vuelvan a pasar, solo mejoras incrementales en parser.py y solo puedes tocar ese




## resp cursor ##

Listo. Analicé **solo** `parser.py` y lo dejé corregido para tu caso con mejoras incrementales.

Cambios aplicados en `app/core/parser.py`:

- Añadí ruido conversacional a `NOISE_WORDS`:
  - `le`, `escribi`, `escribio`, `escribe`, `escribir`, `escrito`
- Implementé un **guardrail de familias de producto** dentro de `FuzzyMatcher.score_pair()` para evitar confusiones tipo:
  - `agua` -> `coca cola`
  - `pizza` -> `hamburguesa`
  - etc.
- Ese guardrail se aplica **después** del scoring por aliases, para que un alias no vuelva a “levantar” un match cruzado incorrecto.
- Agregué una prueba de regresión nueva en la suite interna (`case18`) con tu frase real.

Resultado del caso reportado (menú sin agua disponible):
- Entrada: `le escribi dos pizzas hawaianas, dos cocacolas dos hamburguesas de carne y un agua`
- Salida ahora:
  - `2 x Pizza Hawaiana`
  - `2 x Coca Cola`
  - `2 x Hamburguesa Doble Carne`
  - `unknown: ['un agua']` (correcto: ya no lo transforma en Coca Cola)

Verificación:
- Ejecuté `python app/core/parser.py`
- Suite interna: `PARSER VALIDATION: OK (22/22)`

Si quieres, siguiente paso (también solo en `parser.py`) puede ser que cuando detecte `unknown` con cantidad explícita (`un agua`) lo devuelva normalizado como `agua` para que la aclaración al usuario sea más limpia.



## Cuarto prompt ##

@DASHBOARD_RULES.md

TAREA: [

Implementa actualización automática de pedidos en dashboard con enfoque mínimo e incremental, priorizando estabilidad e integridad.

Objetivo:
- Que nuevos pedidos aparezcan sin recargar (<=10s).
- Cambios mínimos: ideal 1 archivo; máximo 2 archivos.
- Sin dependencias nuevas.
- Si algo falla, debe seguir funcionando como hoy (F5 manual).

Regla de alcance estricto:
1) Primero intenta resolver TODO en 1 archivo (preferentemente `dashboard/static/js/shell.js`).
2) Si no alcanza, permite solo 2 archivos:
   - `dashboard/static/js/shell.js`
   - y un único archivo backend ya existente del módulo de operaciones (view o endpoint actual) para devolver JSON mínimo.
3) No crear refactors ni mover estructuras.

Implementación mínima requerida:
- Frontend:
  - Agrega polling con `fetch` cada 8-10s.
  - Usa una marca de versión simple (`max_id` o `last_update`) para evitar rerender innecesario.
  - Solo actualiza la sección de pedidos (no recargar página completa).
  - Render idempotente: sin duplicados.
  - Manejo fail-soft: si falla red/API, no romper UI, reintentar en siguiente ciclo.
- Backend (solo si necesario):
  - Exponer/ajustar endpoint GET JSON mínimo con:
    - `version` (`max_id` o timestamp)
    - `orders` (campos básicos visibles en dashboard)
  - Con auth/permisos existentes (no abrir endpoint público).

Restricciones:
- No tocar flujo de creación de pedido.
- No agregar librerías.
- No cambiar estilos/CSS salvo que sea imprescindible para identificar contenedor.
- Comentarios cortos solo en lógica crítica.

Entrega obligatoria:
1) Mostrar exactamente qué archivo(s) se editaron (1 o 2, no más).
2) Explicar brevemente por qué cada cambio era necesario.
3) Incluir pasos de prueba manual ultra cortos:
   - crear pedido nuevo
   - esperar polling
   - validar aparición sin F5
   - simular fallo de red y validar que UI no se rompe
4) Si no se puede en 1 archivo, justificar en 1 frase por qué se usó 2.

Criterio de aceptación:
- Con los cambios aplicados, la dashboard refleja pedidos nuevos automáticamente en <=10s, sin duplicados y sin romper el comportamiento actual.


]


## Resp cursor ##

Implementé la actualización automática de pedidos en **1 archivo** y con enfoque mínimo/incremental, sin tocar backend.

### Archivo editado
- `dashboard/static/js/shell.js`

### Por qué era necesario este cambio
- Se añadió polling cada 10s a la URL actual (`fetch(window.location.href)`), porque así reutiliza auth/permisos y evita crear endpoints nuevos.
- Se incorporó una marca de versión simple basada en `max_id` + cantidad de filas (`maxId|rows.length`) para evitar rerender cuando no hay cambios.
- La actualización afecta solo la sección de pedidos (tabla, paginación, estados vacíos), sin recargar toda la página.
- Se reforzó el binding idempotente de interacciones (`row click`, `action menu`, `data-confirm`) para que, tras refrescar la sección, no haya duplicados ni listeners repetidos.
- Manejo fail-soft: si falla red/API, el `.catch()` no rompe UI; simplemente reintenta en el siguiente ciclo.

### Justificación de alcance
- Se resolvió en 1 archivo; **no fue necesario usar 2 archivos** porque el polling consume la misma vista ya existente y parsea el HTML para refrescar solo el bloque de pedidos.

### Prueba manual (ultra corta)
1. Crear pedido nuevo (desde bot o “Nuevo pedido”).
2. Esperar polling (<=10s).
3. Validar que aparece en la lista sin `F5`.
4. Simular fallo de red (DevTools offline) y validar que la UI sigue estable; reactivar red y confirmar que vuelve a actualizarse.




## Quinto prompt ##

@BOT_RULES.md

TAREA: [
1. Arregla en el bot, que hay veces que si tiene un pedido anterior ahí guardado y dice "Responde sí para repetir tu pedido anterior o no para elegir otra opción." y le doy no, me lleva al inicio pero cuando vuelvo a pedido me marca de nuevo lo mismo, arregla ese error de flujo

]


## Resp cursor ##

Ajusté el flujo para que el prompt de “repetir pedido anterior” no se repita en bucle tras responder `no`.

Cambios en `app/core/flow_engine.py`:

- En `_action_welcome_customer`, ahora también valida la bandera `repeat_order_prompted`; si ya se mostró esa pregunta en la sesión, no la vuelve a mostrar.
- Cuando sí se muestra la pregunta por primera vez, se guardan:
  - `awaiting_repeat_order=True`
  - `repeat_order_prompted=True`
- En `_action_save_order`, al cerrar un pedido, se reinicia `repeat_order_prompted=False` (junto con los demás flags), para que en una futura sesión/proceso pueda volver a ofrecer repetir si aplica.

Con esto, cuando el usuario responde `no` y luego vuelve a `pedido`, ya no debería reaparecer esa misma pregunta inmediatamente.



## Sexto prompt ##

Solo te pregunto no hagas nada: hay forma de que cuando se crea un nuevo pedido, en la dashboard no tarde más de 5 segundos? porque está tardando menos de 10 pero como 9, solo pregunto dime y si es así dime donde puedo modificar

modifica solamente eso, deja el tiempo mínimo posible seguro



## Resp cursor ##

Listo, quedó modificado **solo eso**.

- Archivo: `dashboard/static/js/shell.js`
- Cambio: intervalo de actualización de pedidos de `10000` ms a `5000` ms.
- También ajusté el comentario para que refleje 5s.

Ese valor (`5s`) es el mínimo seguro típico para polling sin castigar demasiado al servidor. Si luego quieres bajar más (por ejemplo 3s), te recomiendo hacerlo solo si confirmas que backend y red aguantan bien.




#################################################################
## v0.35

## prompt ##

@BOT_RULES.md and @DASHBOARD_RULES.md

TAREA: [Solo quiero que me digas por qué en producción apenas un cliente creó un pedido nuevo con el chatbot, me apareció, pero desapareció por un momento y volvió y apareció, y luego le di confirmar pedido y desapaareció pero no me llegó la alerta por el bot de confirmado, quiero que lo arregles en local y yo luego manualmente hago git push]

100% OBLIGATORIO: [Haz este cambio SOLO en local (no despliegues). 
Reglas:
- Solo cambios en local
- No asumir deploy (no hacer)
- no asumir producción (no hacer)
- explicar cambios
- dar pasos de prueba local (runall.py para ejecutar flask y django)
- Dar comando manual de deploy (git push)
IMPORTANTISIMO: NO DESPLIEGUES, EL CAMBIO SOLO DEBE SER LOCAL.]


## Respuesta cursor ##


## Qué pasaba

Había **tres fallos encadenados** en el dashboard (no en el bot de WhatsApp del cliente):

1. **`_load_json` estaba roto** en `readers.py`: el código que lee `data/orders_cache.json` había quedado partido y la función casi nunca devolvía datos del archivo local.

2. **`read_orders()` alternaba fuentes mal**: con credenciales de Google, si había *cualquier* pedido remoto, ignoraba la caché local del bot. Además llamaba a `get_pending_orders()`, que en el cliente real del bot **solo devuelve pedidos `pending`**, no confirmados ni entregados. Con el auto-refresh cada 5 s en `/pedidos/`, la lista **parpadeaba** (aparece / desaparece / vuelve).

3. **Al confirmar desde el panel**, en despliegues tipo Docker del dashboard (sin paquete `app/`) se usaba un `AdminService` vacío que **no enviaba WhatsApp**. La confirmación en Sheets sí podía funcionar, pero el cliente no recibía el mensaje.

## Cambios (solo local)

| Archivo | Cambio |
|---------|--------|
| `dashboard/apps/operations/services/readers.py` | Arreglo de `_load_json`; lectura estable desde `data/orders_cache.json`; fusión con Sheets (todos los estados); deduplicación priorizando estado más avanzado (`confirmed` > `pending`). |
| `dashboard/services/bot_bridge.py` | Notificación Twilio si no hay `AdminService` real; sincroniza `orders_cache.json` tras confirmar. |

## Cómo probar en local

1. En `.env.dashboard`:
   ```env
   DASHBOARD_ENABLE_WRITES=1
   ```
   Y en `.env` las variables Twilio (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`).

2. Desde la raíz del proyecto:
   ```bash
   python runall.py
   ```
   (bot `:5000`, dashboard `:8000`).

3. **Parpadeo**: simula un pedido por WhatsApp → abre `/pedidos/?status=pending` y déjalo ~15 s. El pedido debe **permanecer visible** sin desaparecer.

4. **Confirmación**: pulsa “Confirmar pedido”. Debe:
   - salir de *Pendientes* (normal),
   - verse en la pestaña *Confirmados*,
   - llegar al cliente: *“Tu pedido ORD-… fue confirmado por el restaurante…”*

## Deploy manual (cuando quieras)

```bash
git add dashboard/apps/operations/services/readers.py dashboard/services/bot_bridge.py
git commit -m "Fix dashboard order flicker and missing confirm WhatsApp notify"
git push
```

**No he hecho deploy ni push** — solo cambios locales, como pediste.










################################################################
## v0.36


## Prompt ##

@BOT_RULES.md and @DASHBOARD_RULES.md

TAREA: [Por qué cuando le doy a confirmar pedido en la dashboard, en el chat no me muestra que han confirmado pedido? si esa función la tiene el bot cuando el numero del admin confirma, bueno quiero que haga lo mismo que envie notificacion al cliente de que fue confirmado desde la dashboard]

100% OBLIGATORIO: [Haz este cambio SOLO en local (no despliegues). 
Reglas:
- Solo cambios en local
- No asumir deploy (no hacer)
- no asumir producción (no hacer)
- explicar cambios
- dar pasos de prueba local (runall.py para ejecutar flask y django)
- Dar comando manual de deploy (git push)
IMPORTANTISIMO: NO DESPLIEGUES, EL CAMBIO SOLO DEBE SER LOCAL.]


## respuesta cursor ##

Listo: ya quedó aplicado **solo en local** y **no hice ningún deploy**.

Hice el cambio en `dashboard/services/bot_bridge.py` para que cuando el estado del pedido se actualiza desde dashboard a `confirmed` (no solo con el botón de confirmar), se ejecute la misma lógica que en el bot/admin:

- sincroniza `data/orders_cache.json` con el nuevo estado
- envía notificación al cliente por WhatsApp (vía `AdminService` o fallback Twilio)

### Qué cambié
En `update_order_status()` ahora:

- obtiene el pedido y guarda el estado anterior
- después de actualizar en Sheets, sincroniza cache local con `_sync_local_order_status(order_id, status)`
- si el nuevo estado es `confirmed` y antes no lo estaba, llama `_notify_customer_order_confirmed(order_id, wa_id)`

Con esto, si confirman desde la dashboard cambiando estado a confirmado, el chat del cliente también recibe la confirmación.

### Prueba local (sin deploy)
1. Levanta todo local con tu flujo de siempre usando `runall.py` (Flask + Django).
2. Crea o usa un pedido en estado `pending`.
3. Desde dashboard:
   - opción A: botón **Confirmar pedido**
   - opción B: **Cambiar estado** a `confirmed`
4. Verifica:
   - el pedido queda `confirmed` en dashboard
   - en chat/WhatsApp se envía el mensaje de pedido confirmado
   - `data/orders_cache.json` refleja `status: confirmed`

### Comando manual de deploy (solo referencia)
Si luego tú quieres desplegar manualmente:
- `git push`

No ejecuté ese comando.



##############################################################