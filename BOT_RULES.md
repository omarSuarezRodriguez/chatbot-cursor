# BOT_RULES.md

`@BOT_RULES.md` + TAREA. Alcance `app/`, `flows/`, `data/` vía servicios. **AI_RULES §1 manda.**

## 0 Agente

| ✓ | ✗ |
|---|---|
| Código directo; mapa §4–5; regla 1→2→3 | Pseudocódigo, planes, explicar antes; grep/glob/búsqueda; explorar `dashboard/` |

Respuesta: **solo §6** (1 bullet/ítem). Riesgo (contratos, estados, endpoints): parar, 1 línea, pedir OK.

## 1 AI_RULES

Incremental, compatible, mínimo impacto, reutilizar. **No:** APIs, endpoints, JSON contrato, estados conversacionales, comportamiento validado; renombrar/mover; refactors no pedidos. **Preservar:** Parser, Flask, Twilio, Flow Engine, Order Service, Persistencia, estados conversacionales. **Críticos (solo TAREA explícita):** `app/core/parser.py`, `app/services/order_service.py`, `app/core/flow_engine.py`, `flows/restaurant_flow.json`, `app/integrations/google_sheets.py`. **1→2→3** archivos.

## 2 Alcance

**Sí:** `app/`, `flows/restaurant_flow.json`, `.env` (sin secretos en commits) · **No:** `dashboard/*`, editar `data/*.json` a mano · **Dev:** `runall.py` bot:5000 dash:8000 — no cambiar salvo TAREA

## 3 Stack

`Twilio POST /bot`→`app/app.py`→admin? `admin_service` : `user_service.touch`+`flow_engine.process_message`→`state_manager`+nodos JSON→services→`google_sheets`+`data/*_cache.json`→TwiML 200

| Módulo | Rol |
|--------|-----|
| app/app.py | Flask `/health` `/bot` `/bot/reload-flow` webhook |
| core/flow_engine.py | `process_message`, acciones nodos |
| core/state_manager.py | `{flow,step,data}`→`data/user_states.json` |
| core/parser.py | OrderParser NL→carrito |
| services/order_service.py | parser+pedidos |
| services/{menu,reservation,user,admin}_service.py | dominio |
| integrations/google_sheets.py | Sheets+caché |
| utils/validators.py | fecha/hora/sí-no/delivery |
| config.py | env, FLOWS_PATH, GLOBAL_COMMANDS |

Twilio: webhook `app.py`; envío `admin_service` (`TWILIO_*`). No `app/integrations/twilio/`.

**Endpoints (no cambiar):** GET `/health` · POST `/bot` (`WaId`,`Body`,`ProfileName`) · POST `/bot/reload-flow`

**Estado:** `DEFAULT_STATE`=`{flow:idle,step:start,data:{}}` · flows `idle|order|reservation` · cmds `menu|pedido|reservar|inicio|cancelar` · nodos `start,menu_node,order_*,reservation_*` (JSON `flows/restaurant_flow.json`) · acciones en `flow_engine._actions` · pedido status `pending→confirmed→delivered|cancelled` · cart `{name,qty,price,...}` sin cambiar schema

**Data/env:** states→user_states.json · cache→menu/orders/users/reservations_cache.json · errors→parser_errors.jsonl · env `RESTAURANT_NAME` `GOOGLE_*` `STATE_PERSIST_PATH` `ADMIN_WHATSAPP_NUMBER` `TWILIO_*` `*_CACHE_TTL_SECONDS`

## 4 Mapa área

Solo estos + import directo necesario.

| Área | leer |
|------|------|
| Webhook/wiring | app/app.py |
| Texto/ruta nodo | flows/restaurant_flow.json (+flow_engine si lógica) |
| Conversación/acciones | app/core/flow_engine.py, state_manager.py |
| NL pedidos | app/core/parser.py, services/order_service.py |
| Persist pedidos | order_service.py, integrations/google_sheets.py |
| Menú | services/menu_service.py, google_sheets.py |
| Reservas | services/reservation_service.py, flow_engine.py |
| Usuarios WA | services/user_service.py |
| Admin/reminders | services/admin_service.py, config.py |
| Validación | utils/validators.py |
| Config | config.py |
| Sheets/caché | integrations/google_sheets.py |

**Decisión:** texto→JSON · acción→flow_engine · NL→parser · persist→service+sheets · estado→state_manager · endpoint→app.py

**Compat:** Parser · Flask · Twilio · Flow · Order Service · Persistencia · estados · dashboard intacto

## 5 Mapa vivo

Si la TAREA modifica estructura, agrega módulo/endpoint/nodo/flujo/acción nueva o deja un dato útil para ahorrar tokens en futuros prompts → actualizar §3–4 de este archivo (solo delta, compacto). Si no aplica, no tocar. §6: bullet **Mapa §5:** sí/no + qué.

## 6 Entrega + prompt

Secciones (1 bullet c/u): Análisis previo · Cambios · Archivos · Riesgos · Compatibilidad · Agregadas · Preservadas · Mapa §5

```
@BOT_RULES.md
TAREA: [área + cambio]
```
Mismo chat: `TAREA 2:` sin re-adjuntar.
