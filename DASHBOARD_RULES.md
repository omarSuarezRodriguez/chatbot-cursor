# DASHBOARD_RULES.md

Documento **único** para trabajar en la dashboard Django. Incluye las reglas globales de `AI_RULES.md` (prioridad máxima) + mapa completo de la dashboard.

**Propósito principal:** ahorrar tokens. No explorar el repo: lee este archivo, identifica archivos mínimos, implementa.

**En el chat solo adjunta:** `@DASHBOARD_RULES.md` + la TAREA (prompt al final).

---

## Jerarquía de reglas

1. **Sección «Reglas globales»** (= `AI_RULES.md`) — **manda siempre**. Ante conflicto, gana AI_RULES.
2. **Secciones dashboard** — amplían y concretan para `dashboard/` sin relajar seguridad ni compatibilidad.
3. **La TAREA del prompt** — define el cambio concreto; no autoriza refactors ni alcance extra.

Si una mejora de dashboard implica tocar el bot (`app/`), **detener**, explicar riesgo y pedir confirmación (regla AI_RULES).

---

## Cómo ahorra tokens

| Sin este archivo | Con este archivo |
|------------------|------------------|
| `grep` / `glob` / búsqueda semántica en todo el repo | Mapa fijo abajo → ir directo al archivo |
| Explorar `app/`, Twilio, parser “por si acaso” | Alcance acotado; bot solo vía `bot_bridge.py` si la tarea escribe |
| Abrir `views.py` en cambios solo visuales | Árbol de decisión → template + CSS |
| Adjuntar AI_RULES + mapa + tarea | **Un solo MD** + tarea corta |

---

# Reglas globales (AI_RULES — prioridad máxima)

> Copia fiel de `AI_RULES.md`. Si difiere con otra sección de este documento, **prevalece esto**.

## PRIORIDAD MÁXIMA

Estas reglas tienen prioridad sobre cualquier sugerencia de refactorización, optimización o rediseño arquitectónico.

## Misión

Evolucionar el sistema existente mediante cambios incrementales, seguros y compatibles.

La prioridad es preservar la estabilidad del proyecto.

## Principios

* Evolucionar, no reconstruir.
* Mantener compatibilidad total.
* Preservar funcionalidades existentes.
* Aplicar siempre la solución de menor impacto.
* Reutilizar primero el código existente.
* Mantener la arquitectura actual salvo que la tarea exija lo contrario.

## Restricciones

No:

* Cambiar APIs existentes.
* Cambiar contratos públicos.
* Cambiar endpoints.
* Cambiar estructuras JSON existentes.
* Cambiar estados conversacionales existentes.
* Cambiar comportamiento funcional ya validado.
* Renombrar archivos sin necesidad estricta.
* Renombrar clases sin necesidad estricta.
* Renombrar funciones sin necesidad estricta.
* Mover archivos innecesariamente.
* Crear nuevas capas arquitectónicas para resolver mejoras pequeñas.
* Refactorizar módulos completos para implementar una mejora puntual.

## Estrategia de implementación

Antes de modificar código:

1. Identificar la funcionalidad solicitada.
2. Identificar archivos realmente afectados.
3. Evaluar riesgos de regresión.
4. Seleccionar la solución más simple posible.
5. Modificar únicamente los componentes necesarios.

**Regla:** Si puede hacerse con 1 archivo, no modificar 2. Si puede hacerse con 2, no modificar 3.

## Alcance de los cambios

Modificar la menor cantidad posible de archivos, líneas y funciones.

No tocar archivos no relacionados. No mejoras, optimizaciones ni refactors no solicitados.

## Compatibilidad obligatoria

Toda mejora debe preservar:

* Parser
* Flask
* Twilio
* Flow Engine
* Order Service
* Persistencia
* Estados conversacionales

## Si existe riesgo

Si implica riesgo significativo de romper compatibilidad:

* Detener implementación.
* Explicar el riesgo.
* Proponer alternativa segura.
* Solicitar confirmación antes de continuar.

## Formato de respuesta

Siempre entregar:

### Análisis previo
### Cambios implementados
### Archivos modificados
### Riesgos mitigados
### Compatibilidad verificada
### Funcionalidades agregadas
### Funcionalidades preservadas

## Componentes críticos (no modificar salvo tarea explícita)

- `app/core/parser.py`
- `app/services/order_service.py`
- `app/flow/*`
- `app/integrations/twilio/*`
- `app/integrations/google_sheets/*`

---

# Reglas específicas dashboard

Complementan AI_RULES. **No las anulan.**

## Alcance de archivos

### Sí tocar

```
dashboard/
├── apps/operations/          # vistas, templates, forms, permisos, readers, tests
├── apps/accounts/            # login, audit
├── config/                   # settings, context_processors, urls
├── services/bot_bridge.py    # única vía de escritura al bot desde el panel
└── static/                   # css, js, icons
```

### No tocar (salvo TAREA explícita)

- Todo `app/` excepto lo que `bot_bridge.py` importe internamente (no editar desde dashboard).
- `data/*.json` — los escribe el bot; la dashboard solo **lee** vía `readers.py`.

## Reglas de implementación dashboard

1. **Solo visual** → template (+ `components.css`). No abrir `views.py`.
2. **Nuevo dato en pantalla** → vista concreta en `views.py` + template.
3. **Escritura al bot** (crear pedido, confirmar, menú, cliente) → `bot_bridge.py` + vista/form. Validaciones en bridge, no duplicar lógica del bot.
4. **Máximo 2 archivos** (ideal: template + CSS). Más solo con justificación en análisis previo.
5. Reutilizar partials y clases existentes antes de crear componentes nuevos.
6. Textos UI en **español**.
7. No cambiar URLs (`urls.py`), nombres de vistas, contratos JSON de caché ni permisos sin que la TAREA lo pida.
8. No crear archivos nuevos salvo necesidad clara.
9. **No búsquedas amplias** en el repo: usar mapas de este documento.
10. Antes de editar: **una línea** indicando archivos a tocar y por qué.

---

# Arquitectura dashboard (no explorar)

## Stack

- **Django** panel operativo en `dashboard/`
- **Bot Flask** en `app/` — la dashboard **no** llama endpoints Flask; lectura por JSON en `data/`, escritura por `bot_bridge.py` → servicios del bot
- **Caché JSON** (repo root `data/`):
  - `menu_cache.json`
  - `orders_cache.json`
  - `users_cache.json`
  - `reservations_cache.json`

## Flujo de datos

```
LECTURA:  readers.py  →  data/*.json  (fallback Google Sheets si falta caché)
ESCRITURA: views.py  →  bot_bridge.py  →  app/services/*  (solo si DASHBOARD_ENABLE_WRITES=1)
UI:        views.py (contexto)  →  templates/operations/*.html  →  static/css + js
```

## Settings relevantes (`dashboard/config/settings.py`, `.env.dashboard`)

| Variable | Efecto |
|----------|--------|
| `DASHBOARD_ENABLE_WRITES` | `0` = solo lectura; banner `readonly_banner.html`; forms de escritura deshabilitados |
| `RESTAURANT_NAME` | Nombre en UI vía `dashboard_flags` |

## Contexto global en templates (`context_processors.py`)

| Variable | Uso |
|----------|-----|
| `dashboard_writes_enabled` | Mostrar/ocultar acciones de escritura |
| `restaurant_name` | Marca en UI |
| `is_dashboard_admin` | CRUD completo, settings, accesos |
| `is_dashboard_operator` | Operaciones: pedidos, clientes, menú (disponibilidad) |
| `show_django_admin_link` | Superuser → enlace Django admin |

## Permisos (`permissions.py`)

| Grupo | Mixin | Puede |
|-------|-------|-------|
| `dashboard_operator` | `OperatorRequiredMixin` | Leer + operar pedidos, clientes, menú |
| `dashboard_admin` | `AdminRequiredMixin` | Todo lo anterior + CRUD menú, borrar clientes, settings, accesos panel |

Comando setup grupos: `dashboard/apps/operations/management/commands/setup_dashboard_groups.py`

## Pedidos — dominio UI

Estados: `pending` · `confirmed` · `delivered` · `cancelled`

Pestañas lista (`ORDER_LIST_TAB_STATUSES`): Pendiente · Confirmado · Entregado

Variables de contexto frecuentes en `OrderListView`: `orders`, `status_filter`, `order_status_tabs`, `can_create_order`, `can_confirm_orders`, `q`, `date_from`, `date_to`, `sort`, `direction`, `page_obj`, `base_query`

Badge partial: `partials/order_status_badge.html`

## Escrituras (`bot_bridge.py`)

- `writes_enabled()` — comprueba `DASHBOARD_ENABLE_WRITES`
- `WriteResult(ok, message, already_confirmed, entity_id)`
- Estados pedido válidos: `pending`, `confirmed`, `delivered`, `cancelled`
- **No cambiar** firmas ni contratos de respuesta sin tarea explícita

---

# Mapa URLs → template

Rutas: `dashboard/apps/operations/urls.py`  
Templates base: `dashboard/apps/operations/templates/operations/`

| URL | name | Template |
|-----|------|----------|
| `/` o `/dashboard/` | `operations:home` | `dashboard_home.html` |
| `/pedidos/` | `operations:orders` | `order_list.html` |
| `/pedidos/nuevo/` | `operations:order_create` | `order_form.html` |
| `/pedidos/<id>/` | `operations:order_detail` | `order_detail.html` |
| `/reservas/` | `operations:reservations` | `reservation_list.html` |
| `/reservas/<id>/` | `operations:reservation_detail` | `reservation_detail.html` |
| `/menu/` | `operations:menu` | `menu.html` |
| `/menu/nuevo/` | `operations:menu_create` | `menu_form.html` |
| `/menu/<id>/editar/` | `operations:menu_edit` | `menu_form.html` |
| `/usuarios/` | `operations:users` | `user_list.html` |
| `/usuarios/nuevo/` | `operations:customer_create` | `customer_form.html` |
| `/usuarios/<wa_id>/` | `operations:customer_detail` | `customer_detail.html` |
| `/usuarios/<wa_id>/editar/` | `operations:customer_edit` | `customer_form.html` |
| `/administracion/` | `operations:admin_hub` | `admin_hub.html` |
| `/administracion/accesos/` | `operations:panel_staff_list` | `panel_staff_list.html` |
| `/administracion/accesos/nuevo/` | `operations:panel_staff_create` | `panel_staff_form.html` |
| `/administracion/escrituras/` | `operations:writes_help` | `writes_help.html` |
| `/configuracion/` | `operations:panel_settings` | `panel_settings.html` |
| `/estado/` | `operations:system_status` | `system_status.html` |
| Login | accounts | `dashboard/apps/accounts/templates/registration/login.html` |

---

# Layout y partials

Prefijo: `dashboard/apps/operations/templates/operations/`

| Qué | Archivo |
|-----|---------|
| Shell (sidebar + topbar) | `base.html` |
| Sidebar / nav | `partials/sidebar.html` |
| Título + botón acción | `partials/page_header.html` |
| Estado vacío genérico | `partials/empty_state.html` |
| Badge estado pedido | `partials/order_status_badge.html` |
| Icono SVG | `partials/icon.html` |
| Sprite iconos | `partials/icons_sprite.html` |
| Toasts Django | `partials/toasts.html` |
| Banner solo lectura | `partials/readonly_banner.html` |
| Toggle tema | `partials/theme_toggle.html` |
| CSS/JS en head | `partials/head_assets.html` |

Iconos disponibles en sprite: `orders`, `calendar`, `utensils`, `users`, `activity`, `settings`, `menu`, `sun`, `moon`, `log-out`, `home`, `search`, `euro`, `clock`, `check-circle`, `truck`, `x-circle`, `arrow-left`, `plus`, `more-vertical`, `edit`, `trash`, `eye`

---

# Backend por responsabilidad

| Qué | Archivo |
|-----|---------|
| Vistas + contexto | `dashboard/apps/operations/views.py` |
| URLs | `dashboard/apps/operations/urls.py` |
| Formularios | `dashboard/apps/operations/forms.py` |
| Permisos | `dashboard/apps/operations/permissions.py` |
| Lectura caché | `dashboard/apps/operations/services/readers.py` |
| Escrituras bot | `dashboard/services/bot_bridge.py` |
| Settings panel | `dashboard/services/settings_store.py` |
| Settings Django | `dashboard/config/settings.py` |
| Context processors | `dashboard/config/context_processors.py` |
| Tests vistas | `dashboard/apps/operations/tests/test_views.py` |
| Audit log | `dashboard/apps/accounts/audit.py` |

---

# Estilos y JS

## CSS (orden de prioridad al añadir estilos)

1. `dashboard/static/css/components.css` — botones, cards, tablas, empty-state, badges, toasts
2. `dashboard/static/css/layout.css` — shell, sidebar, topbar, auth
3. `dashboard/static/css/app.css` — estilos de página
4. `dashboard/static/css/tokens.css` — variables (solo si falta un token)

## Clases habituales

`.card` · `.btn` · `.btn-primary` · `.btn-ghost` · `.btn-sm` · `.input` · `.label` · `.badge` · `.empty-state` · `.empty-state__title` · `.empty-state__desc` · `.empty-state--orders-waiting` · `.data-table` · `.status-tabs` · `.pagination` · `.muted` · `.animate-fade-in` · `.data-toolbar` · `.table-wrap`

## JS

| Qué | Archivo |
|-----|---------|
| Sidebar móvil, filas clicables, `data-confirm` | `dashboard/static/js/shell.js` |
| Tema claro/oscuro | `dashboard/static/js/theme.js` |

---

# Árbol de decisión (agente)

```
¿Solo texto/HTML/CSS?
  → template (+ components.css)

¿Variable nueva en template?
  → views.py (vista concreta) + template

¿Filtro, orden, paginación?
  → views.py + template (+ test_views.py si cambia lógica)

¿Acción que persiste en bot/Sheets?
  → bot_bridge.py + views.py (+ forms.py)

¿Item sidebar?
  → partials/sidebar.html

¿Global (banner, toasts, tema)?
  → partial + CSS/JS correspondiente
```

---

# Convenciones UI

- Extender `base.html`; contenido en `{% block content %}`.
- Listados: `{% include "operations/partials/page_header.html" with title="..." subtitle="..." action_url=... action_label="..." %}`.
- Iconos: `{% include "operations/partials/icon.html" with name="search" class="icon--sm" %}`.
- Vacío: `.empty-state.card` o `{% include "operations/partials/empty_state.html" with title="..." description="..." %}`.
- Forms destructivos: `data-confirm="¿...?"` (confirmación en `shell.js`).
- Gradiente marca: `linear-gradient(135deg, var(--color-accent), #7c3aed)`.
- Tablas clicables: `data-row-href` en `<tr>` (`shell.js`).

---

# Referencia por pantalla (archivos mínimos a leer)

No explorar más allá de esta lista + partials que el template incluya con `{% include %}`.

| Pantalla | Archivos |
|----------|----------|
| Pedidos lista | `order_list.html`, `components.css` |
| Pedido detalle | `order_detail.html`, `partials/order_status_badge.html`, `components.css` |
| Pedido crear | `order_form.html`, `forms.py`, `components.css` |
| Reservas lista | `reservation_list.html`, `components.css` |
| Menú | `menu.html`, `components.css` |
| Clientes lista | `user_list.html`, `components.css` |
| Cliente detalle | `customer_detail.html`, `components.css` |
| Inicio | `dashboard_home.html`, `components.css` |
| Sidebar | `partials/sidebar.html`, `layout.css` |
| Configuración | `panel_settings.html`, `views.py`, `settings_store.py`, `components.css` |
| Estado sistema | `system_status.html`, `views.py`, `readers.py` |
| Admin hub | `admin_hub.html`, `components.css` |
| Accesos panel | `panel_staff_list.html`, `panel_staff_form.html`, `permissions.py` |
| Login | `registration/login.html`, `layout.css` |

Rutas completas: prefijo `dashboard/apps/operations/templates/operations/` (salvo login).

---

# Compatibilidad dashboard (checklist entrega)

Además del checklist AI_RULES, verificar:

- Lectura de caché (`readers.py`) intacta
- Permisos operator/admin respetados
- `bot_bridge.py` sin cambios de contrato (si no tocado)
- Modo solo lectura (`DASHBOARD_ENABLE_WRITES=0`) sigue funcionando
- Bot/parser/Twilio/flow **no modificados**

---

# PROMPT PARA USAR CADA VEZ

Adjunta **solo** `@DASHBOARD_RULES.md`. Copia el bloque y rellena la TAREA.

```
OBLIGATORIO:
Lee y aplica completamente DASHBOARD_RULES.md (las reglas globales AI_RULES incluidas tienen prioridad máxima).
Alcance: solo dashboard/. No explorar app/ ni el bot salvo escritura vía bot_bridge.py explícita en la tarea.

Identifica los archivos mínimos con el mapa y árbol de decisión de DASHBOARD_RULES.md.
Lee únicamente esos archivos y partials incluidos. No hagas búsquedas amplias en el repo.
Modifica la menor cantidad posible de archivos y líneas (regla: 1 archivo si basta; si no, 2 como máximo salvo justificación).
Antes de editar, indica en una línea qué archivos tocarás y por qué.
Entrega con el formato de respuesta de AI_RULES.

TAREA:
[Qué pantalla, qué cambiar, cómo debe verse o comportarse]
```

### Ejemplo

```
OBLIGATORIO:
Lee y aplica completamente DASHBOARD_RULES.md.
Alcance: solo dashboard/. No explorar app/ ni el bot.
Identifica archivos mínimos, no busques en el repo, modifica lo mínimo, indica archivos antes de editar.

TAREA:
En Pedidos > pestaña Pendiente, estado vacío con 🤖 "Esperando nuevos pedidos", texto WhatsApp y botón "Nuevo pedido". Diseño coherente con el dashboard.
```
