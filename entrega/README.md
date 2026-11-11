# Reporte de Cartera Vencida

## Descripción

Script Python 3 que genera el reporte de cartera vencida a partir de archivos CSV de clientes, facturas y pagos, siguiendo las reglas de negocio definidas en `docs/spec.md`.

## Uso

```bash
# Con fecha de corte por defecto (2026-11-30)
python3 entrega/cartera.py

# Con fecha de corte personalizada
python3 entrega/cartera.py --fecha-corte 2026-10-15
```

## Salida

- **Consola:** Tabla formateada con el reporte completo
- **Archivo CSV:** `entrega/cartera_vencida.csv`

## Columnas del reporte

| Columna | Descripción |
|---------|-------------|
| cliente_id | ID del cliente |
| cliente_nombre | Nombre del cliente |
| cliente_ruc | RUC del cliente |
| saldo_vencido_total | Suma de saldos vencidos del cliente |
| factura_mas_antigua_id | ID de la factura vencida más antigua |
| factura_mas_antigua_fecha | Fecha de vencimiento de esa factura |
| vendedor | Vendedor asignado (actualmente "SIN ASIGNAR") |

## Reglas aplicadas

1. **Facturas vencidas:** `fecha_vencimiento < fecha_corte` (días_vencidos > 0)
2. **Saldo:** `total - suma_pagos` (solo se incluyen saldos > 0)
3. **Estados:** Solo facturas con `estado = 'emitida'` (anuladas se excluyen)
4. **Clientes:** Todos los estados (activos e inactivos)
5. **Fecha nula:** Se asigna +30 días desde emisión (factura 7)
6. **Fechas invertidas:** Se corrige con +30 días desde emisión (factura 15)
7. **Pagos huérfanos:** Se ignoran (pago 10 → factura 99)
8. **Sobrepagos:** No se incluyen en cartera vencida (factura 12)
9. **Vendedor:** "SIN ASIGNAR" (dato no disponible en archivos fuente)

## Resumen de exclusiones

El script imprime un resumen detallado de:
- Facturas anuladas
- Facturas no vencidas
- Facturas con saldo cero (pagadas)
- Facturas con saldo negativo (sobrepagos)
- Pagos huérfanos (sin factura asociada)
- Correcciones aplicadas a fechas

## Orden del reporte

Descendente por `saldo_vencido_total`, con desempate por `cliente_id` ascendente (orden determinista).

## Dependencias

Solo librería estándar de Python 3:
- `csv` - Lectura/escritura de archivos CSV
- `datetime` - Manejo de fechas
- `pathlib` - Rutas de archivos
- `collections` - Estructuras de datos

No requiere instalación de paquetes externos.
