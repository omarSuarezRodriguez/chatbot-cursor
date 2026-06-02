# DASHBOARD_RULES.md

`@DASHBOARD_RULES.md` + TAREA. Alcance `dashboard/`. **La Sección 1 (AI_RULES) manda.**

## 0 Agente

| ✓ | ✗ |
|---|---|
| Código directo; mapa (Secciones 4 y 5); regla 1→2→3 | Pseudocódigo, planes, explicar antes; grep/glob/búsqueda; explorar `app/` |
| UI → template + `dashboard/static/css/components.css` | `views.py` si solo UI |

Respuesta: **solo Sección 6** (1 bullet/ítem). Riesgo (`app/`, contratos): parar, 1 línea, pedir OK.

## 1 AI_RULES

Incremental, compatible, mínimo impacto, reutilizar. **No:** APIs, endpoints, JSON, estados conversacionales, comportamiento validado; renombrar/mover; refactors no pedidos. **Preservar:** Parser, Flask, Twilio, Flow Engine, Order Service, Persistencia, estados conversacionales. **No tocar bot:** `app/core/parser.py`, `app/services/order_service.py`, `app/core/flow_engine.py`, `flows/restaurant_flow.json`, `app/integrations/google_sheets.py`. **1→2→3** archivos.

## 2 Alcance

**Sí:** `dashboard/apps/operations/`, `accounts/`, `config/`, `services/bot_bridge.py`, `static/` · **No:** `app/*`, editar `data/*.json` · **Flujo:** read `readers.py`→`data/*.json` | write `views`→`bot_bridge`→bot (`DASHBOARD_ENABLE_WRITES=1`) · **Tpl:** `dashboard/apps/operations/templates/operations/` · **Static:** `dashboard/static/`

## 3 Contexto

Caché `data/{menu,orders,users,reservations}_cache.json` · Ctx `dashboard_writes_enabled` `restaurant_name` `is_dashboard_admin` `is_dashboard_operator` · Grupos `dashboard_operator` (operar) / `dashboard_admin` (+CRUD, settings) · Pedidos `pending|confirmed|delivered|cancelled` · Bridge `WriteResult(ok,message,already_confirmed,entity_id)` sin cambiar firmas

## 4 Mapa pantalla

Tpl en Sección 2 salvo login. `components.css`=`dashboard/static/css/components.css`. Solo tpl + includes + fila «leer».

| Pantalla | URL | template | leer |
|----------|-----|----------|------|
| Inicio | `/` | dashboard_home.html | tpl, components.css |
| Pedidos | `/pedidos/` | order_list.html | tpl, components.css |
| Pedido | `/pedidos/<id>/` | order_detail.html | tpl, partials/order_status_badge.html, css |
| Pedido nuevo | `/pedidos/nuevo/` | order_form.html | tpl, operations/forms.py, css |
| Reservas | `/reservas/` | reservation_list.html | tpl, css |
| Menú | `/menu/` | menu.html | tpl, css |
| Clientes | `/usuarios/` | user_list.html | tpl, css |
| Cliente | `/usuarios/<wa_id>/` | customer_detail.html | tpl, css |
| Admin | `/administracion/` | admin_hub.html | tpl, css |
| Accesos | `.../accesos/` | panel_staff_list.html | tpl, css |
| Config | `/configuracion/` | panel_settings.html | tpl, operations/views.py, css |
| Estado | `/estado/` | system_status.html | tpl, operations/views.py, css |
| Login | — | accounts/.../login.html | tpl, layout.css |
| Sidebar | — | partials/sidebar.html | tpl, layout.css |

**Decisión:** UI→tpl+css · ctx→operations/views.py+tpl · write→bot_bridge+view · nav→partials/sidebar.html

**Backend:** operations/{views,urls,forms,permissions}.py · operations/services/readers.py · bot_bridge.py · config/{settings,context_processors}.py · tests/test_views.py

**UI:** partials base, sidebar, page_header, empty_state, order_status_badge, icon, icons_sprite, toasts, readonly_banner · CSS components→layout→app→tokens · JS shell.js theme.js · clases `.card` `.btn` `.btn-primary` `.empty-state` `.data-table` `.status-tabs` `.badge` · `page_header`/`icon` include · `data-confirm` `data-row-href`

**Compat:** readers · permisos · bot_bridge contrato · writes=0 · bot intacto

## 5 Mapa vivo

Si la TAREA modifica estructura, agrega pantalla/URL/backend/partial nueva o deja un dato útil para ahorrar tokens en futuros prompts → actualizar Secciones 3 y 4 de este archivo (solo delta, compacto). Si no aplica, no tocar. En la Sección 6, bullet **Mapa vivo (Sección 5):** sí/no + qué.

## 6 Entrega + prompt

Secciones (1 bullet c/u): Análisis previo · Cambios · Archivos · Riesgos · Compatibilidad · Agregadas · Preservadas · Mapa vivo (Sección 5)

```
@DASHBOARD_RULES.md
TAREA: [pantalla + cambio]
```
Mismo chat: `TAREA 2:` sin re-adjuntar.
