# Resumen cobertura corpus (~95% tráfico esperado)
Total líneas: 2898

## Por categoría
| Categoría | Líneas | % | Rol en cobertura |
|-----------|--------|---|------------------|
| A_onboarding | 360 | 12.4% | Navegación / comandos / saludos |
| B_pedido_nl | 1280 | 44.2% | Pedidos lenguaje natural |
| C_carrito | 430 | 14.8% | Carrito y confirmación |
| D_reserva | 290 | 10.0% | Reserva de mesa |
| E_entrega | 21 | 0.7% | Domicilio / dirección / nombre |
| F_mezclas | 240 | 8.3% | Mensajes mixtos críticos |
| G_ruido | 200 | 6.9% | Ruido y fuera de alcance |
| H_adversarial | 77 | 2.7% | Adversarial / no menú |

## Por intención esperada (top)

- pedido_con_productos: 1584 (54.7%)
- modificar_carrito: 423 (14.6%)
- dato_reserva: 274 (9.5%)
- ruido: 134 (4.6%)
- menu: 104 (3.6%)
- reservar: 89 (3.1%)
- pedido: 73 (2.5%)
- saludo: 56 (1.9%)
- inicio: 49 (1.7%)
- ambiguo: 34 (1.2%)
- cancelar: 32 (1.1%)
- confirmar: 22 (0.8%)
- datos_entrega: 21 (0.7%)
- rechazar: 3 (0.1%)

# Top 30 huecos (~5% no cubierto)

1. Audio de voz mal transcrito con palabras inventadas
2. Imagen/foto del menú sin texto
3. Pedidos en idioma indígena o portugués mezclado
4. Referencias a promos del mes no configuradas en flujo
5. Pedido para fecha futura específica (navidad, cumple)
6. Split bill / pagar separado entre personas
7. Alergias y restricciones médicas largas
8. Quejas formales / pedir gerente
9. Propinas en el mensaje de pedido
10. Cupones y códigos de descuento
11. Pedido B2B (oficina, 50 personas)
12. Coordenadas GPS en lugar de dirección
13. Ubicación compartida de WhatsApp (lat/long)
14. Reenvío de mensaje de otro contacto
15. Catálogo PDF adjunto referenciado
16. Menú de competencia mencionado
17. Pedidos de desayuno si el local no abre
18. Solicitud de factura CFDI con RFC
19. Cambio de método de pago mid-flujo
20. Multi-sucursal ("sucursal norte")
21. Pedido programado exacto al minuto
22. Modificar pedido ya entregado
23. Estado de pedido en ruta (tracking)
24. Chat interno entre empleados por error
25. Stickers animados sin texto util
26. Plantillas WhatsApp Business del cliente
27. Mensajes de bot de otro negocio copiados
28. Unicode raro / caracteres RTL
29. Pedido en dialecto muy local no listado
30. Conversación multi-turno referenciando "lo de arriba"

**Detección en logs:** buscar en `client_messages_log` respuestas fallback repetidas,
`Aún no tengo productos`, `No logré entender`, o mismos `wa_id` con 3+ reformulaciones seguidas.


# 15 cambios sugeridos (parser.py / GLOBAL_COMMAND_INTENTS)

1. Filtrar segmentos `unknown` que son solo frases de intención ("quiero comer", "tomar") — no tratarlos como producto.
2. Expandir `ORDER_INTENT_NON_PRODUCT` en señal de cantidad para "tomar", "comer", "ordenar".
3. Sinónimo `tomar` → bebida solo si hay ítem bebida en menú y contexto de cantidad.
4. Boost fuzzy `hawaina` / `hawaiiana` → Hawaiana (ya parcial; reforzar en typos).
5. `refresco` / `soda` → cocacola cuando una sola bebida en menú.
6. Frase compuesta "quiero comer algo" → intención pedido sin productos.
7. "menu" dentro de pedido largo → no cortar flujo si `has_products`.
8. Reserva: reconocer "para el 15" sin mes sin perder como fecha.
9. Confirmación: mapear "esta bien", "ok gracias", "va" → confirmar.
10. Carrito: "sin cebolla" como nota, no producto (notas en parser).
11. Cantidad "docena" solo con productos contables del menú.
12. Ignorar segmentos de 1 palabra en NOISE_WORDS al armar unknown.
13. Prefijo "pedido:" como etiqueta admin de pedido (ya existe; documentar).
14. Categoría "pizza" → default Hawaiana si es única pizza disponible.
15. Log interno opcional `intent` en parser audit sin mostrar al usuario.
