# VERIFICACIÓN INDEPENDIENTE DEL REPORTE DE CARTERA VENCIDA

**Fecha:** 2026-11-10
**Método alternativo:** SQLite en memoria con CTEs (Common Table Expressions)

---

## METODOLOGÍA

Para validar el reporte generado por `entrega/cartera.py`, se implementó un **script de verificación independiente** (`verificar_reporte.py`) que:

1. **Usa una base de datos SQLite en memoria** (algoritmo diferente al script principal)
2. **Aplica las mismas reglas de negocio** mediante SQL con CTEs
3. **Compara resultados** a nivel de totales y por cliente individual
4. **Verifica 3 clientes manualmente** factura por factura
5. **Prueba casos límite** específicos

---

## RESULTADOS DE LA COMPARACIÓN

### ✅ TOTALES COINCIDEN

| Método | Total Cartera Vencida |
|--------|----------------------:|
| Script original (`entrega/cartera.py`) | **$17,900.00** |
| Método SQL alternativo (SQLite) | **$17,900.00** |
| **Diferencia** | **$0.00** |

### ✅ COMPARACIÓN POR CLIENTE (12 clientes)

Todos los clientes coinciden exactamente:

| Cliente ID | Nombre | Saldo (Original) | Saldo (SQL) | Diferencia |
|------------|--------|----------------:|------------:|------------|
| 4 | Pollos del Valle | $3,100.00 | $3,100.00 | ✅ $0.00 |
| 11 | Avícola Pichincha Sur | $2,700.00 | $2,700.00 | ✅ $0.00 |
| 7 | Agropecuaria Santa Rosa | $2,200.00 | $2,200.00 | ✅ $0.00 |
| 1 | Granja Los Pinos | $2,000.00 | $2,000.00 | ✅ $0.00 |
| 2 | Avícola El Sol | $1,500.00 | $1,500.00 | ✅ $0.00 |
| 6 | Porcícola Los Andes | $1,480.00 | $1,480.00 | ✅ $0.00 |
| 9 | Distribuidora Cevallos | $1,350.00 | $1,350.00 | ✅ $0.00 |
| 5 | Hacienda La Esperanza | $980.00 | $980.00 | ✅ $0.00 |
| 8 | Granja Avícola El Sol S.A. | $900.00 | $900.00 | ✅ $0.00 |
| 10 | Granja Doña Mercedes | $700.00 | $700.00 | ✅ $0.00 |
| 13 | Granja Tres Hermanos | $610.00 | $610.00 | ✅ $0.00 |
| 14 | Pollera Don Aurelio | $380.00 | $380.00 | ✅ $0.00 |

**Conclusión:** ✅ **Todos los clientes coinciden al 100%**

---

## (a) VERIFICACIÓN: SUMA POR CLIENTE = SUMA POR FACTURA

Se verificó que la agregación por cliente es correcta:

```
Suma de saldos agrupados por cliente:  $17,900.00
Suma de saldos individuales por factura: $17,900.00
Diferencia:                              $0.00
```

**Conclusión:** ✅ **La agregación es consistente. No hay pérdida ni duplicación de datos.**

---

## (b) VERIFICACIÓN MANUAL: 3 CLIENTES (factura por factura)

### Cliente 4: Pollos del Valle

| Factura | Emisión | Vencimiento | Total | Pagos | Saldo | ¿Vencida? |
|---------|---------|-------------|------:|------:|------:|-----------|
| 7 | 2026-09-01 | 2026-10-01 | $3,100.00 | $0.00 | $3,100.00 | SÍ |
| **TOTAL** | | | | | **$3,100.00** | |

- Calculado manual: $3,100.00
- Método SQL: $3,100.00
- ✅ **COINCIDE**

**Notas:**
- Factura 7 originalmente tenía fecha_vencimiento **nula**
- Se aplicó corrección: emisión + 30 días = 2026-10-01
- Vence 60 días antes del corte (30/11) → **SÍ está vencida**

---

### Cliente 9: Distribuidora Cevallos (INACTIVO)

| Factura | Emisión | Vencimiento | Total | Pagos | Saldo | ¿Vencida? |
|---------|---------|-------------|------:|------:|------:|-----------|
| 14 | 2026-07-10 | 2026-08-09 | $1,350.00 | $0.00 | $1,350.00 | SÍ |
| **TOTAL** | | | | | **$1,350.00** | |

- Calculado manual: $1,350.00
- Método SQL: $1,350.00
- ✅ **COINCIDE**

**Notas:**
- Este cliente tiene estado = **"inactivo"**
- Según spec.md, clientes inactivos **SÍ se incluyen** si tienen cartera vencida
- Confirmado: la regla se aplicó correctamente

---

### Cliente 14: Pollera Don Aurelio

| Factura | Emisión | Vencimiento | Total | Pagos | Saldo | ¿Vencida? |
|---------|---------|-------------|------:|------:|------:|-----------|
| 20 | 2026-10-28 | 2026-11-27 | $380.00 | $0.00 | $380.00 | SÍ |
| **TOTAL** | | | | | **$380.00** | |

- Calculado manual: $380.00
- Método SQL: $380.00
- ✅ **COINCIDE**

**Notas:**
- Vence el 27/11, fecha de corte 30/11
- Días vencidos = 3 días
- 3 > 0 → **SÍ está vencida** (regla: días_vencidos > 0)

---

## (c) CASOS LÍMITE PROBADOS

### 1. Factura que vence EXACTAMENTE 30 días antes del corte

**Factura 8** (cliente 5 - Hacienda La Esperanza):
- Fecha vencimiento: **2026-10-31**
- Fecha corte: **2026-11-30**
- Días vencidos: **30 días exactos**
- Total: $560.00, Pagos: $0.00, Saldo: $560.00
- **¿Incluida?** ✅ **SÍ**

**Confirmación de regla:** La regla es `días_vencidos > 0`, por lo que 30 días de atraso cuenta como vencida.

---

### 2. Factura con pago PARCIAL

**Factura 10** (cliente 6 - Porcícola Los Andes):
- Total: $1,980.00
- Pagos: $500.00 (pago parcial)
- **Saldo: $1,480.00**
- Vencimiento: 2026-10-10
- **¿Incluida?** ✅ **SÍ** (vencida con saldo > 0)

**Confirmación de regla:** Los pagos parciales se restan correctamente del total, y el saldo pendiente se reporta.

---

### 3. Factura con pago MAYOR al total (sobrepago)

**Factura 12** (cliente 7 - Agropecuaria Santa Rosa):
- Total: $1,000.00
- Pagos: $1,100.00
- **Saldo: -$100.00** (sobrepago)
- **¿Incluida?** ❌ **NO**

**Confirmación de regla:** Según spec.md, saldos negativos (sobrepagos) **NO se incluyen** en el reporte de cartera vencida. Esto es correcto porque un sobrepago no es una deuda.

**Nota:** El cliente 7 aparece en el reporte con $2,200.00 porque tiene otra factura vencida (factura 13) con saldo positivo.

---

### 4. Factura SIN pagos

**Factura 1** (cliente 1 - Granja Los Pinos):
- Total: $1,200.00
- Pagos: $0.00
- **Saldo: $1,200.00** (100% del total)
- Vencimiento: 2026-09-04
- **¿Incluida?** ✅ **SÍ**

**Confirmación de regla:** Las facturas sin pagos se incluyen correctamente con su saldo = total.

**Nota:** El cliente 1 tiene 2 facturas:
- Factura 1: $1,200.00 (sin pagos)
- Factura 2: $800.00 (sin pagos)
- **Total cliente 1: $2,000.00** ✅ Correcto

---

## RESUMEN DE DATOS PROCESADOS

### Facturas procesadas (21 total):

| Regla | Cantidad | Detalle |
|-------|----------|---------|
| Total facturas leídas | 21 | |
| - Anuladas (excluidas) | 1 | Factura 5 |
| - No vencidas (excluidas) | 1 | Vencimiento >= 2026-11-30 |
| - Saldo cero (excluidas) | 3 | Facturas pagadas completas |
| - Saldo negativo (excluidas) | 1 | Factura 12 (sobrepago) |
| **= Incluidas en reporte** | **15** | **Con saldo > 0 y vencidas** |

### Pagos procesados (10 total):

| Regla | Cantidad | Detalle |
|-------|----------|---------|
| Total pagos leídos | 10 | |
| - Pagos huérfanos (excluidos) | 1 | Pago 10 → Factura 99 (no existe) |
| **= Pagos aplicados** | **9** | |

### Correcciones aplicadas:

1. **Factura 7:** fecha_vencimiento **nula** → 2026-10-01 (emisión + 30 días)
2. **Factura 15:** vencimiento **antes de emisión** → 2026-11-14 (emisión + 30 días)

---

## DIFERENCIAS ENCONTRADAS

### ❌ NINGUNA

No se encontraron diferencias entre el método original y el método de verificación SQL.

**Todos los valores coinciden exactamente:**
- ✅ Total general
- ✅ Totales por cliente (12 clientes)
- ✅ Consistencia suma por cliente vs suma por factura
- ✅ Verificación manual de 3 clientes
- ✅ Casos límite procesados correctamente

---

## CONCLUSIONES

1. **El reporte `entrega/cartera_vencida.csv` es CORRECTO**
   - Los cálculos son exactos
   - Las reglas de negocio de `docs/spec.md` se aplicaron fielmente
   - No hay errores de agregación ni pérdida de datos

2. **Las reglas de negocio funcionan como se especificó:**
   - ✅ Solo facturas emitidas (anuladas excluidas)
   - ✅ Solo facturas vencidas (fecha_vencimiento < fecha_corte)
   - ✅ Solo saldos positivos (cero y negativos excluidos)
   - ✅ Corrección de fechas nulas e invertidas (+30 días)
   - ✅ Exclusión de pagos huérfanos
   - ✅ Clientes inactivos incluidos

3. **Los casos límite se manejan correctamente:**
   - ✅ Factura vencida hace exactamente 30 días: incluida
   - ✅ Pago parcial: saldo calculado correctamente
   - ✅ Sobrepago: excluido (no es deuda)
   - ✅ Sin pagos: incluida con saldo = total

4. **Orden determinista verificado:**
   - Los clientes están ordenados por saldo DESC
   - Desempate por cliente_id ASC
   - Mismo orden en ambos métodos

---

## RECOMENDACIÓN FINAL

✅ **El reporte está LISTO para entrega.**

No se requieren correcciones. El script `entrega/cartera.py` produce resultados precisos y consistentes que cumplen al 100% con las especificaciones definidas en `docs/spec.md`.
