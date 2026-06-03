# Fase 1 — Benchmark corpus 95%

- **Líneas evaluadas:** 3300
- **Tiempo:** 9099 ms
- **Acierto global (todas las filas):** 98.7%
- **Intención global (menu/pedido/reservar/inicio/cancelar):** 94.8%
- **Pedido con productos (`pedido_con_productos`):** 98.5%
- **Categorías A–F:** 99.3% (2811/2830)
- **Categorías G–H:** 94.7% (445/470)

## Por categoría
| Cat | OK | Total | % |
|-----|-----|-------|---|
| A | 342 | 360 | 95.0% |
| B | 1279 | 1280 | 99.9% |
| C | 430 | 430 | 100.0% |
| D | 290 | 290 | 100.0% |
| E | 230 | 230 | 100.0% |
| F | 240 | 240 | 100.0% |
| G | 200 | 200 | 100.0% |
| H | 245 | 270 | 90.7% |

## Por intención esperada (peores primero)

- **pedido:** 86.3% (63/73)
- **menu:** 92.2% (95/103)
- **pedido_con_productos:** 98.5% (1677/1702)
- **ruido:** 99.3% (139/140)
- **cancelar:** 100.0% (32/32)
- **reservar:** 100.0% (89/89)
- **saludo:** 100.0% (55/55)
- **inicio:** 100.0% (49/49)
- **rechazar:** 100.0% (3/3)
- **confirmar:** 100.0% (23/23)
- **modificar_carrito:** 100.0% (423/423)
- **dato_reserva:** 100.0% (274/274)
- **datos_entrega:** 100.0% (230/230)
- **ambiguo:** 100.0% (104/104)

## Logs reales (`client_messages_log/`)
- Mensajes cliente extraídos: 17
- Con comando inferido: 3
- Parse OK en mensajes con producto del menú: 100.0%
