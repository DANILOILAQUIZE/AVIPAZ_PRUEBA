#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de reporte de cartera vencida.
Uso: python3 entrega/cartera.py [--fecha-corte YYYY-MM-DD]
Ejemplo: python3 entrega/cartera.py --fecha-corte 2026-11-30
"""

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def leer_csv(ruta):
    """Lee un archivo CSV manejando BOM y retorna lista de diccionarios."""
    with open(ruta, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def parsear_fecha(texto):
    """Convierte string a datetime. Retorna None si no es válido."""
    if not texto or texto.strip() == '':
        return None
    
    texto = texto.strip()
    formatos = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
    
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except:
            continue
    
    return None


def parsear_monto(texto):
    """Convierte string a float. Retorna None si no es válido."""
    if not texto or texto.strip() == '':
        return None
    
    texto = texto.strip().replace(',', '.')
    
    try:
        return float(texto)
    except:
        return None


def corregir_fecha_vencimiento(fecha_emision, fecha_vencimiento, factura_id, log_correcciones):
    """
    Aplica reglas de corrección de fecha de vencimiento según spec.md:
    - Si es None: fecha_emision + 30 días
    - Si < fecha_emision: fecha_emision + 30 días
    """
    if fecha_vencimiento is None:
        nueva_fecha = fecha_emision + timedelta(days=30)
        log_correcciones.append(f"Factura {factura_id}: fecha_vencimiento nula → {nueva_fecha.date()}")
        return nueva_fecha
    
    if fecha_vencimiento < fecha_emision:
        nueva_fecha = fecha_emision + timedelta(days=30)
        log_correcciones.append(
            f"Factura {factura_id}: vencimiento {fecha_vencimiento.date()} < emisión {fecha_emision.date()} → {nueva_fecha.date()}"
        )
        return nueva_fecha
    
    return fecha_vencimiento


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def generar_reporte(fecha_corte_str='2026-11-30'):
    """Genera el reporte de cartera vencida según spec.md."""
    
    # Parsear fecha de corte
    fecha_corte = parsear_fecha(fecha_corte_str)
    if not fecha_corte:
        print(f"❌ Error: fecha de corte inválida '{fecha_corte_str}'")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"REPORTE DE CARTERA VENCIDA")
    print(f"Fecha de corte: {fecha_corte.date()}")
    print(f"{'='*80}\n")
    
    # Rutas relativas (busca datos/ desde directorio actual o dos niveles arriba)
    base_dir = Path(__file__).parent.parent.parent  # Sube 3 niveles desde revisar-cartera/
    
    # Intentar encontrar datos/ en varias ubicaciones posibles
    posibles_rutas = [
        base_dir / 'datos',  # Desde raíz del proyecto
        Path.cwd() / 'datos',  # Desde directorio actual
        Path(__file__).parent.parent.parent / 'datos',  # Relativo al script
    ]
    
    ruta_datos = None
    for ruta in posibles_rutas:
        if (ruta / 'clientes.csv').exists():
            ruta_datos = ruta
            break
    
    if not ruta_datos:
        print("❌ Error: No se encontró la carpeta 'datos/' con los archivos CSV")
        print("Busqué en:")
        for ruta in posibles_rutas:
            print(f"  - {ruta}")
        print("\nAsegúrate de ejecutar desde la raíz del proyecto o que datos/ esté accesible.")
        sys.exit(1)
    
    ruta_clientes = ruta_datos / 'clientes.csv'
    ruta_facturas = ruta_datos / 'facturas.csv'
    ruta_pagos = ruta_datos / 'pagos.csv'
    
    # Salida en entrega/ (relativo a datos/)
    ruta_salida = ruta_datos.parent / 'entrega' / 'cartera_vencida.csv'
    
    # Crear carpeta entrega si no existe
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    
    # Leer archivos
    print("Leyendo archivos...")
    clientes = leer_csv(ruta_clientes)
    facturas = leer_csv(ruta_facturas)
    pagos = leer_csv(ruta_pagos)
    
    print(f"  ✓ {len(clientes)} clientes")
    print(f"  ✓ {len(facturas)} facturas")
    print(f"  ✓ {len(pagos)} pagos")
    print()
    
    # Contadores de exclusiones
    exclusiones = {
        'facturas_anuladas': 0,
        'facturas_no_vencidas': 0,
        'facturas_saldo_cero': 0,
        'facturas_saldo_negativo': 0,
        'pagos_huerfanos': 0,
    }
    
    log_correcciones = []
    
    # Crear diccionario de clientes por ID
    clientes_dict = {c['id']: c for c in clientes}
    
    # ========================================================================
    # PASO 1: Procesar facturas - Filtrar anuladas
    # ========================================================================
    
    facturas_validas = []
    for f in facturas:
        if f['estado'] == 'anulada':
            exclusiones['facturas_anuladas'] += 1
        else:
            facturas_validas.append(f)
    
    # ========================================================================
    # PASO 2: Corregir fechas de vencimiento
    # ========================================================================
    
    for f in facturas_validas:
        fecha_emision = parsear_fecha(f['fecha_emision'])
        fecha_vencimiento = parsear_fecha(f['fecha_vencimiento'])
        
        if fecha_emision:
            fecha_vencimiento_corregida = corregir_fecha_vencimiento(
                fecha_emision, 
                fecha_vencimiento, 
                f['id'], 
                log_correcciones
            )
            f['_fecha_emision'] = fecha_emision
            f['_fecha_vencimiento'] = fecha_vencimiento_corregida
        else:
            # Si no podemos parsear la emisión, no podemos procesar
            f['_fecha_emision'] = None
            f['_fecha_vencimiento'] = None
    
    # ========================================================================
    # PASO 3: Calcular pagos por factura
    # ========================================================================
    
    # Crear set de IDs de facturas válidas
    facturas_ids_validos = set(f['id'] for f in facturas_validas)
    
    pagos_por_factura = defaultdict(float)
    
    for p in pagos:
        factura_id = p['factura_id']
        monto = parsear_monto(p['valor'])
        
        # Verificar integridad referencial
        if factura_id not in facturas_ids_validos:
            exclusiones['pagos_huerfanos'] += 1
            continue
        
        if monto is not None:
            pagos_por_factura[factura_id] += monto
    
    # ========================================================================
    # PASO 4: Calcular saldo por factura y filtrar
    # ========================================================================
    
    facturas_vencidas_con_saldo = []
    
    for f in facturas_validas:
        total = parsear_monto(f['total'])
        pagos_recibidos = pagos_por_factura.get(f['id'], 0.0)
        saldo = total - pagos_recibidos if total is not None else None
        
        f['_saldo'] = saldo
        f['_pagos'] = pagos_recibidos
        
        # Filtros según spec.md
        
        # 1. Debe tener fecha de vencimiento válida
        if f['_fecha_vencimiento'] is None:
            continue
        
        # 2. Debe estar vencida (días_vencidos > 0)
        if f['_fecha_vencimiento'] >= fecha_corte:
            exclusiones['facturas_no_vencidas'] += 1
            continue
        
        # 3. Saldo debe ser > 0
        if saldo is None:
            continue
        
        if saldo == 0:
            exclusiones['facturas_saldo_cero'] += 1
            continue
        
        if saldo < 0:
            exclusiones['facturas_saldo_negativo'] += 1
            continue
        
        # Pasó todos los filtros
        facturas_vencidas_con_saldo.append(f)
    
    # ========================================================================
    # PASO 5: Agrupar por cliente
    # ========================================================================
    
    clientes_cartera = defaultdict(lambda: {
        'facturas': [],
        'saldo_total': 0.0,
    })
    
    for f in facturas_vencidas_con_saldo:
        cliente_id = f['cliente_id']
        clientes_cartera[cliente_id]['facturas'].append(f)
        clientes_cartera[cliente_id]['saldo_total'] += f['_saldo']
    
    # ========================================================================
    # PASO 6: Construir filas del reporte
    # ========================================================================
    
    filas_reporte = []
    
    for cliente_id, datos in clientes_cartera.items():
        cliente = clientes_dict.get(cliente_id, {})
        
        # Encontrar factura más antigua (menor fecha de vencimiento)
        factura_mas_antigua = min(datos['facturas'], key=lambda f: f['_fecha_vencimiento'])
        
        fila = {
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.get('nombre', 'DESCONOCIDO'),
            'cliente_ruc': cliente.get('ruc', ''),
            'saldo_vencido_total': datos['saldo_total'],
            'factura_mas_antigua_id': factura_mas_antigua['id'],
            'factura_mas_antigua_fecha': factura_mas_antigua['_fecha_vencimiento'].strftime('%Y-%m-%d'),
            'vendedor': 'SIN ASIGNAR',
        }
        
        filas_reporte.append(fila)
    
    # ========================================================================
    # PASO 7: Ordenar de forma determinista
    # ========================================================================
    
    # Orden: saldo DESC, luego cliente_id ASC
    filas_reporte.sort(key=lambda x: (-x['saldo_vencido_total'], x['cliente_id']))
    
    # ========================================================================
    # PASO 8: Calcular ventas del año 2026
    # ========================================================================
    
    ventas_2026 = 0.0
    for f in facturas:
        if f['estado'] == 'emitida':
            fecha_emision = parsear_fecha(f['fecha_emision'])
            if fecha_emision and fecha_emision.year == 2026:
                total = parsear_monto(f['total'])
                if total is not None:
                    ventas_2026 += total
    
    # ========================================================================
    # PASO 9: Calcular totales y porcentaje
    # ========================================================================
    
    suma_saldos_vencidos = sum(f['saldo_vencido_total'] for f in filas_reporte)
    
    porcentaje = (suma_saldos_vencidos / ventas_2026 * 100) if ventas_2026 > 0 else 0.0
    
    # ========================================================================
    # PASO 10: Imprimir reporte en consola
    # ========================================================================
    
    if filas_reporte:
        print(f"{'Cliente ID':<12} {'Cliente':<30} {'RUC':<15} {'Saldo Vencido':>15} {'Fact. Antigua':>12} {'Fec. Venc.':>12} {'Vendedor':<15}")
        print(f"{'-'*12} {'-'*30} {'-'*15} {'-'*15} {'-'*12} {'-'*12} {'-'*15}")
        
        for fila in filas_reporte:
            print(
                f"{fila['cliente_id']:<12} "
                f"{fila['cliente_nombre'][:30]:<30} "
                f"{fila['cliente_ruc']:<15} "
                f"{fila['saldo_vencido_total']:>15.2f} "
                f"{fila['factura_mas_antigua_id']:>12} "
                f"{fila['factura_mas_antigua_fecha']:>12} "
                f"{fila['vendedor']:<15}"
            )
        
        print(f"{'-'*12} {'-'*30} {'-'*15} {'-'*15} {'-'*12} {'-'*12} {'-'*15}")
        print(
            f"{'':12} "
            f"{'TOTAL CARTERA VENCIDA':<30} "
            f"{'':15} "
            f"{suma_saldos_vencidos:>15.2f} "
            f"{'':12} "
            f"{'':12} "
            f"{'':15}"
        )
        print()
        print(f"Ventas del año 2026: {ventas_2026:.2f}")
        print(f"% sobre ventas del año: {porcentaje:.2f}%")
    else:
        print("✓ No hay facturas vencidas con saldo pendiente.")
    
    print()
    
    # ========================================================================
    # PASO 11: Guardar CSV
    # ========================================================================
    
    with open(ruta_salida, 'w', encoding='utf-8', newline='') as f:
        if filas_reporte:
            fieldnames = [
                'cliente_id',
                'cliente_nombre',
                'cliente_ruc',
                'saldo_vencido_total',
                'factura_mas_antigua_id',
                'factura_mas_antigua_fecha',
                'vendedor',
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for fila in filas_reporte:
                writer.writerow(fila)
            
            # Fila de totales
            writer.writerow({
                'cliente_id': '',
                'cliente_nombre': 'TOTAL CARTERA VENCIDA',
                'cliente_ruc': '',
                'saldo_vencido_total': f'{suma_saldos_vencidos:.2f}',
                'factura_mas_antigua_id': '',
                'factura_mas_antigua_fecha': f'% sobre ventas: {porcentaje:.2f}%',
                'vendedor': '',
            })
    
    print(f"✓ Reporte guardado en: {ruta_salida}")
    print()
    
    # ========================================================================
    # PASO 12: Resumen de exclusiones
    # ========================================================================
    
    print(f"{'='*80}")
    print("RESUMEN DE EXCLUSIONES")
    print(f"{'='*80}")
    print()
    print(f"Total de facturas leídas: {len(facturas)}")
    print(f"  1. Facturas anuladas (estado='anulada'): {exclusiones['facturas_anuladas']}")
    print(f"  2. Facturas no vencidas (vencimiento >= {fecha_corte.date()}): {exclusiones['facturas_no_vencidas']}")
    print(f"  3. Facturas con saldo = 0 (pagadas completas): {exclusiones['facturas_saldo_cero']}")
    print(f"  4. Facturas con saldo < 0 (sobrepagos): {exclusiones['facturas_saldo_negativo']}")
    print(f"  → Facturas incluidas en reporte: {len(facturas_vencidas_con_saldo)}")
    print()
    print(f"Total de pagos leídos: {len(pagos)}")
    print(f"  1. Pagos huérfanos (factura_id inexistente): {exclusiones['pagos_huerfanos']}")
    print(f"  → Pagos aplicados: {len(pagos) - exclusiones['pagos_huerfanos']}")
    print()
    
    if log_correcciones:
        print("CORRECCIONES APLICADAS:")
        for correccion in log_correcciones:
            print(f"  • {correccion}")
        print()
    
    print(f"Clientes con cartera vencida: {len(filas_reporte)}")
    print()


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    # Parsear argumentos
    fecha_corte = '2026-11-30'
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--fecha-corte' and len(sys.argv) > 2:
            fecha_corte = sys.argv[2]
        else:
            print("Uso: python3 entrega/cartera.py [--fecha-corte YYYY-MM-DD]")
            sys.exit(1)
    
    generar_reporte(fecha_corte)
