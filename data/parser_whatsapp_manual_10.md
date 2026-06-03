# Fase 3 — 10 frases para probar manualmente en WhatsApp

Usar el número conectado al bot con menú **Hawaiana** + **cocacola**.  
Anotar si la respuesta coincide con la intención esperada.

| # | Mensaje a enviar | Intención esperada | Qué debería pasar |
|---|------------------|-------------------|-------------------|
| 1 | `hola` | saludo | Bienvenida + menú + opciones pedido/reservar |
| 2 | `dame dos pizzas hawaianas` | pedido | Carrito con 2× Hawaiana |
| 3 | `Quiero comer dos pizzas hawaianas y tomar 2 cocacolas por favor` | pedido | 2 Hawaiana + 2 cocacola (sin tratar "comer"/"tomar" como producto) |
| 4 | `agrega una cocacola` | modificar carrito | Suma 1 cocacola al carrito actual |
| 5 | `sin hawaiana` | modificar carrito | Quita Hawaiana del carrito |
| 6 | `menu principal` | inicio | Reinicia flujo (no solo muestra carta) |
| 7 | `ya no quiero el pedido` | cancelar | Cancela / sale del pedido |
| 8 | `reserva mañana a las 8 pm para 4` | dato_reserva | No debe confundirse con comando `reservar`; captura fecha/hora/personas |
| 9 | `si` (en pantalla de confirmación) | confirmar | Confirma pedido |
| 10 | `inicio` (con pedido en curso) | inicio | Pregunta si abandonar pedido antes de reiniciar |

## Mensajes reales ya vistos en logs (`client_messages_log/`)

- `dame dos pizzas hawaianas` — OK en producción
- `Quiero comer dos pizzas hawaianas y tomar 2 cocacolas por favor` — parsea productos pero aún marca "quiero comer"/"tomar" como unknown (mejora pendiente UX)
- `keke` / `f` — deberían pedir aclaración, no inventar productos
