# Guion de demo ejecutiva (10 minutos) - Brasaland

Este guion permite mostrar valor de negocio por rol con evidencia funcional en vivo.

## Preparacion (1 minuto)

1. Verificar servicios activos:
- API: http://localhost:8000/health
- Dashboard ejecutivo: http://localhost:4173
- App mobile fidelizacion/pedidos: http://localhost:4174
2. Tener lista una ventana por interfaz:
- Dashboard (operaciones/compras/marketing)
- App mobile cliente

## Agenda de demo

## 1) Felipe Guerrero - Operaciones (3 minutos)

Objetivo: demostrar visibilidad diaria y accion operativa inmediata en 14 locales.

Flujo:
1. Abrir dashboard en http://localhost:4173.
2. Mostrar ventas por local y cambiar filtros de pais/moneda (COP/USD).
3. Entrar a alertas de inactividad en horario de apertura.
4. Ejecutar accion sobre una alerta (ACK y luego RESOLVE).
5. Abrir recomendaciones de pedidos inteligentes (historico + stock).

Mensajes clave:
- La cadena tiene monitoreo continuo por local.
- La operacion puede responder alertas sin salir del panel.
- El pedido sugerido reduce quiebres por inventario insuficiente.

## 2) Lucia Fernandez - Compras y Proveedores (3 minutos)

Objetivo: demostrar control de costos y negociacion centralizada multipais.

Flujo:
1. Ir a seccion Compras y proveedores.
2. Mostrar historial de precios por proveedor/SKU.
3. Mostrar alertas por variacion de precio configurable.
4. Mostrar consolidado de compras de cadena (CO + US).

Mensajes clave:
- Se detectan subidas de precio con umbrales configurables.
- El consolidado habilita volumen para negociar mejores condiciones.
- La vista soporta pais y moneda para decisiones comparables.

## 3) Camila Ospina - Marketing y Experiencia Digital (3 minutos)

Objetivo: demostrar ciclo completo cliente-CRM-personalizacion.

Flujo:
1. En dashboard, abrir panel de Marketing y mostrar CRM overview.
2. Mostrar listado de clientes con historial y comportamiento.
3. Mostrar recomendaciones personalizadas por cliente.
4. Abrir app mobile en http://localhost:4174 y simular pedido.

Mensajes clave:
- Cada pedido digital alimenta puntos de fidelizacion.
- El CRM agrupa historial y preferencias para activar campañas.
- La personalizacion incrementa probabilidad de recompra.

## Cierre ejecutivo (1 minuto)

Resumen de impacto:
1. Operaciones: menos tiempo de reaccion ante inactividad.
2. Compras: mejor posicion negociadora por consolidado de demanda.
3. Marketing: mayor recurrencia por fidelizacion y recomendaciones.

## Plan de contingencia rapido

Si el dashboard no carga datos:
1. Verificar API health en http://localhost:8000/health.
2. Reiniciar API con scripts/restart_api_local.sh.

Si la app mobile no carga:
1. Confirmar puerto 4174 activo.
2. Levantar servidor estatico en uis/marketing-loyalty-app con python3 -m http.server 4174 --bind 0.0.0.0.

Si un endpoint devuelve error:
1. Revisar headers de rol/token.
2. Repetir con ejemplos de services/brasaland-api/README.es.md.
