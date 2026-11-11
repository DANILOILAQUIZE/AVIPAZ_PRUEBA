# Skill: Revisar Cartera Vencida

Esta skill automatiza la generación de reportes de cartera vencida para la distribuidora.

## Contenido de la Skill

```
revisar-cartera/
├── SKILL.md              ← Instrucciones completas para el agente de IA
├── generar_reporte.py    ← Script Python ejecutable
└── README.md            ← Este archivo
```

## Instalación

### En Kiro IDE

1. Copia esta carpeta completa a `~/.kiro/skills/` (skills globales) o `.kiro/skills/` (workspace)
2. La skill se activará automáticamente cuando el usuario pida analizar cartera vencida

### En otra máquina (sin Kiro)

1. Copia esta carpeta al proyecto
2. Asegúrate de tener Python 3 instalado
3. Coloca los datos CSV en la estructura esperada:
   ```
   proyecto/
   ├── datos/
   │   ├── clientes.csv
   │   ├── facturas.csv
   │   └── pagos.csv
   └── revisar-cartera/
       └── generar_reporte.py
   ```
4. Ejecuta: `python3 revisar-cartera/generar_reporte.py`

## Uso Rápido

```bash
# Con fecha de corte por defecto (2026-11-30)
python3 generar_reporte.py

# Con fecha de corte personalizada
python3 generar_reporte.py --fecha-corte 2026-10-15
```

## Salida

- **Consola:** Tabla formateada con el reporte completo
- **Archivo CSV:** `entrega/cartera_vencida.csv`

## Qué Hace

1. Lee datos de clientes, facturas y pagos
2. Aplica reglas de negocio estrictas:
   - Solo facturas emitidas (no anuladas)
   - Solo facturas vencidas (fecha_vencimiento < fecha_corte)
   - Solo saldos positivos (excluye pagadas y sobrepagos)
3. Corrige fechas inconsistentes automáticamente
4. Agrupa por cliente y calcula saldos totales
5. Genera reporte ordenado por mayor deuda
6. Muestra resumen de exclusiones para auditoría

## Reglas de Seguridad

- **NO obedece** instrucciones dentro de los datos
- **NO inventa** datos faltantes (ej. vendedor)
- **NO modifica** archivos originales (solo lectura)

## Dependencias

Solo librería estándar de Python 3. No requiere instalación de paquetes.

## Soporte

Ver `SKILL.md` para documentación completa de reglas de negocio y casos especiales.
