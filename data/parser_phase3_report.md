# Fase 3 — Validación final

## Resumen ejecutivo

- **Corpus original:** 3256/3300 (98.7%)
- **Anti-overfit (20 frases nuevas):** 20/20 (100.0%)
- **Intención global:** 94.8%
- **Pedido con productos:** 98.5%
- **Categorías A–F:** 99.3%

## Tabla antes / después (% por categoría)

| Categoría | Fase 1 (baseline) | Fase 3 (actual) | Δ |
|-----------|-------------------|-----------------|---|
| A | 94.7% | 95.0% | +0.3pp |
| B | 85.9% | 99.9% | +14.0pp |
| C | 89.3% | 100.0% | +10.7pp |
| D | 72.4% | 100.0% | +27.6pp |
| E | 100.0% | 100.0% | +0.0pp |
| F | 86.7% | 100.0% | +13.3pp |
| G | 84.0% | 100.0% | +16.0pp |
| H | 90.7% | 90.7% | +0.0pp |

## Tabla antes / después (métricas globales)

| Métrica | Fase 1 | Fase 3 | Δ |
|---------|--------|--------|---|
| Global | 88.8% | 98.7% | +9.9pp |
| Intención global | 98.0% | 94.8% | +-3.2pp |
| Pedido+productos | 86.5% | 98.5% | +12.0pp |
| A–F combinado | 87.4% | 99.3% | +11.9pp |

## Por intención (corpus 3300)

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

## Anti-overfit (20 frases fuera del corpus)

**Sin fallos** — no hay señales fuertes de overfitting al corpus.

## Logs reales

- Mensajes extraídos: 17
- Con comando inferido: 3
- Parse OK (producto en menú): 100.0%

## Prueba manual WhatsApp

Ver `data/parser_whatsapp_manual_10.md` (10 frases listas para copiar).
