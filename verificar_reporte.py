#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación independiente del reporte de cartera vencida.
Usa SQLite en memoria con un algoritmo diferente al script principal.
"""

import csv
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def leer_csv_simple(ruta):
    """Lee CSV con encoding utf-8-sig."""
    with open(ruta, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    print("\n" + "="*80)
    print("VERIFICACIÓN INDEPENDIENTE - MÉTODO SQLite")
    print("="*80 + "\n")
    
    # Rutas
    base_dir = Path(__file__).parent
    
    # Leer archivos originales
    clientes = leer_csv_simple(base_dir / 'datos' / 'clientes.csv')
    facturas = leer_csv_simple(base_dir / 'datos' / 'facturas.csv')
    pagos = leer_csv_simple(base_dir / 'datos' / 'pagos.csv')
    
    print(f"Archivos leídos: {len(clientes)} clientes, {len(facturas)} facturas, {len(pagos)} pagos\n")
    
    # Crear BD en memoria
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Crear tablas
    cursor.execute('''
        CREATE TABLE clientes (
            id TEXT PRIMARY KEY,
            nombre TEXT,
            ruc TEXT,
            ciudad TEXT,
            estado TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE facturas (
            id TEXT PRIMARY KEY,
            cliente_id TEXT,
            fecha_emision TEXT,
            fecha_vencimiento TEXT,
            total REAL,
            estado TEXT,
            observaciones TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE pagos (
            id TEXT PRIMARY KEY,
            factura_id TEXT,
            fecha TEXT,
            valor REAL
        )
    ''')
    
    # Insertar datos
    for c in clientes:
        cursor.execute(
            'INSERT INTO clientes VALUES (?, ?, ?, ?, ?)',
            (c['id'], c['nombre'], c['ruc'], c['ciudad'], c['estado'])
        )
    
    for f in facturas:
        cursor.execute(
            'INSERT INTO facturas VALUES (?, ?, ?, ?, ?, ?, ?)',
            (f['id'], f['cliente_id'], f['fecha_emision'], f['fecha_vencimiento'],
             float(f['total']) if f['total'] else 0, f['estado'], f.get('observaciones', ''))
        )
    
    for p in pagos:
        cursor.execute(
            'INSERT INTO pagos VALUES (?, ?, ?, ?)',
            (p['id'], p['factura_id'], p['fecha'], float(p['valor']) if p['valor'] else 0)
        )
    
    conn.commit()
    
    # Fecha de corte
    fecha_corte = datetime(2026, 11, 30)
    fecha_corte_str = fecha_corte.strftime('%Y-%m-%d')
    
    print(f"Fecha de corte: {fecha_corte_str}\n")
    
    # ========================================================================
    # ALGORITMO ALTERNATIVO: SQL con CTEs
    # ========================================================================
    
    query = f'''
    WITH 
    -- Paso 1: Corregir fechas de vencimiento
    facturas_corregidas AS (
        SELECT 
            f.id,
            f.cliente_id,
            f.fecha_emision,
            CASE
                -- Si vencimiento es nulo o vacío: emisión + 30 días
                WHEN f.fecha_vencimiento IS NULL OR f.fecha_vencimiento = '' 
                    THEN date(f.fecha_emision, '+30 days')
                -- Si vencimiento < emisión: emisión + 30 días
                WHEN f.fecha_vencimiento < f.fecha_emision 
                    THEN date(f.fecha_emision, '+30 days')
                ELSE f.fecha_vencimiento
            END as fecha_vencimiento_corregida,
            f.total,
            f.estado
        FROM facturas f
        WHERE f.estado = 'emitida'  -- Solo facturas emitidas
    ),
    
    -- Paso 2: Calcular suma de pagos por factura (solo pagos con factura existente)
    pagos_por_factura AS (
        SELECT 
            p.factura_id,
            SUM(p.valor) as total_pagos
        FROM pagos p
        INNER JOIN facturas f ON p.factura_id = f.id
        GROUP BY p.factura_id
    ),
    
    -- Paso 3: Calcular saldos
    facturas_con_saldo AS (
        SELECT 
            fc.id,
            fc.cliente_id,
            fc.fecha_emision,
            fc.fecha_vencimiento_corregida,
            fc.total,
            COALESCE(ppf.total_pagos, 0) as pagos,
            fc.total - COALESCE(ppf.total_pagos, 0) as saldo
        FROM facturas_corregidas fc
        LEFT JOIN pagos_por_factura ppf ON fc.id = ppf.factura_id
        WHERE 
            fc.fecha_vencimiento_corregida < '{fecha_corte_str}'  -- Vencida
            AND fc.total - COALESCE(ppf.total_pagos, 0) > 0       -- Saldo positivo
    ),
    
    -- Paso 4: Agrupar por cliente
    cartera_por_cliente AS (
        SELECT 
            c.id as cliente_id,
            c.nombre as cliente_nombre,
            c.ruc as cliente_ruc,
            SUM(fcs.saldo) as saldo_vencido_total,
            COUNT(fcs.id) as num_facturas,
            MIN(fcs.fecha_vencimiento_corregida) as fecha_vencimiento_mas_antigua
        FROM clientes c
        INNER JOIN facturas_con_saldo fcs ON c.id = fcs.cliente_id
        GROUP BY c.id, c.nombre, c.ruc
    )
    
    SELECT 
        cpc.cliente_id,
        cpc.cliente_nombre,
        cpc.cliente_ruc,
        cpc.saldo_vencido_total,
        cpc.num_facturas,
        cpc.fecha_vencimiento_mas_antigua
    FROM cartera_por_cliente cpc
    ORDER BY cpc.saldo_vencido_total DESC, cpc.cliente_id ASC
    '''
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    print("RESULTADOS DEL MÉTODO SQL:")
    print(f"{'Cliente ID':<12} {'Cliente':<30} {'Saldo':>12} {'# Facts':>8} {'Fecha más antigua':>18}")
    print("-" * 82)
    
    suma_sql = 0
    for row in resultados:
        cliente_id, nombre, ruc, saldo, num_facts, fecha_antigua = row
        suma_sql += saldo
        print(f"{cliente_id:<12} {nombre[:30]:<30} {saldo:>12.2f} {num_facts:>8} {fecha_antigua:>18}")
    
    print("-" * 82)
    print(f"{'TOTAL':<44} {suma_sql:>12.2f}")
    print()
    
    # ========================================================================
    # Leer salida del script original
    # ========================================================================
    
    ruta_salida = base_dir / 'entrega' / 'cartera_vencida.csv'
    
    if not ruta_salida.exists():
        print("❌ No se encontró entrega/cartera_vencida.csv. Ejecuta primero entrega/cartera.py")
        return
    
    salida_original = leer_csv_simple(ruta_salida)
    
    # Filtrar la fila de totales
    filas_datos = [f for f in salida_original if f['cliente_id']]
    
    print("RESULTADOS DEL SCRIPT ORIGINAL (entrega/cartera_vencida.csv):")
    print(f"{'Cliente ID':<12} {'Cliente':<30} {'Saldo':>12}")
    print("-" * 56)
    
    suma_original = 0
    for fila in filas_datos:
        cliente_id = fila['cliente_id']
        nombre = fila['cliente_nombre']
        saldo = float(fila['saldo_vencido_total'])
        suma_original += saldo
        print(f"{cliente_id:<12} {nombre[:30]:<30} {saldo:>12.2f}")
    
    print("-" * 56)
    print(f"{'TOTAL':<44} {suma_original:>12.2f}")
    print()
    
    # ========================================================================
    # COMPARACIÓN
    # ========================================================================
    
    print("="*80)
    print("COMPARACIÓN DE RESULTADOS")
    print("="*80 + "\n")
    
    print(f"Total método SQL:      {suma_sql:>12.2f}")
    print(f"Total script original: {suma_original:>12.2f}")
    diferencia = abs(suma_sql - suma_original)
    print(f"Diferencia:            {diferencia:>12.2f}")
    
    if diferencia < 0.01:
        print("\n✅ TOTALES COINCIDEN (diferencia < 0.01)\n")
    else:
        print(f"\n❌ DIFERENCIA DETECTADA: {diferencia:.2f}\n")
    
    # Comparar clientes uno por uno
    print("Comparación cliente por cliente:")
    print(f"{'Cliente':<12} {'SQL':>12} {'Original':>12} {'Diferencia':>12}")
    print("-" * 50)
    
    dict_sql = {row[0]: row[3] for row in resultados}
    dict_original = {f['cliente_id']: float(f['saldo_vencido_total']) for f in filas_datos}
    
    todos_clientes = set(dict_sql.keys()) | set(dict_original.keys())
    
    hay_diferencias = False
    for cliente_id in sorted(todos_clientes):
        saldo_sql = dict_sql.get(cliente_id, 0)
        saldo_orig = dict_original.get(cliente_id, 0)
        diff = abs(saldo_sql - saldo_orig)
        
        marca = "❌" if diff >= 0.01 else "✅"
        print(f"{cliente_id:<12} {saldo_sql:>12.2f} {saldo_orig:>12.2f} {diff:>12.2f} {marca}")
        
        if diff >= 0.01:
            hay_diferencias = True
    
    if not hay_diferencias:
        print("\n✅ Todos los clientes coinciden\n")
    else:
        print("\n❌ Hay diferencias por cliente\n")
    
    # ========================================================================
    # (a) VERIFICAR: suma por cliente = suma por factura
    # ========================================================================
    
    print("="*80)
    print("(a) VERIFICACIÓN: SUMA POR CLIENTE = SUMA POR FACTURA")
    print("="*80 + "\n")
    
    # Suma por cliente (ya la tenemos)
    suma_por_cliente = suma_sql
    
    # Suma por factura
    cursor.execute(f'''
        SELECT SUM(saldo) as total
        FROM (
            SELECT 
                fc.id,
                fc.total - COALESCE(ppf.total_pagos, 0) as saldo
            FROM (
                SELECT 
                    f.id,
                    f.cliente_id,
                    f.fecha_emision,
                    CASE
                        WHEN f.fecha_vencimiento IS NULL OR f.fecha_vencimiento = '' 
                            THEN date(f.fecha_emision, '+30 days')
                        WHEN f.fecha_vencimiento < f.fecha_emision 
                            THEN date(f.fecha_emision, '+30 days')
                        ELSE f.fecha_vencimiento
                    END as fecha_vencimiento_corregida,
                    f.total,
                    f.estado
                FROM facturas f
                WHERE f.estado = 'emitida'
            ) fc
            LEFT JOIN (
                SELECT p.factura_id, SUM(p.valor) as total_pagos
                FROM pagos p
                INNER JOIN facturas f ON p.factura_id = f.id
                GROUP BY p.factura_id
            ) ppf ON fc.id = ppf.factura_id
            WHERE 
                fc.fecha_vencimiento_corregida < '{fecha_corte_str}'
                AND fc.total - COALESCE(ppf.total_pagos, 0) > 0
        )
    ''')
    
    suma_por_factura = cursor.fetchone()[0] or 0
    
    print(f"Suma de saldos por cliente:  {suma_por_cliente:>12.2f}")
    print(f"Suma de saldos por factura:  {suma_por_factura:>12.2f}")
    print(f"Diferencia:                  {abs(suma_por_cliente - suma_por_factura):>12.2f}")
    
    if abs(suma_por_cliente - suma_por_factura) < 0.01:
        print("\n✅ VERIFICACIÓN PASADA: Las sumas coinciden\n")
    else:
        print("\n❌ PROBLEMA: Las sumas NO coinciden\n")
    
    # ========================================================================
    # (b) VERIFICAR 3 CLIENTES A MANO (factura por factura)
    # ========================================================================
    
    print("="*80)
    print("(b) VERIFICACIÓN MANUAL: 3 CLIENTES (factura por factura)")
    print("="*80 + "\n")
    
    # Elegir 3 clientes: el de mayor saldo, el de menor saldo, y uno intermedio
    clientes_verificar = [
        resultados[0][0],      # Mayor saldo
        resultados[len(resultados)//2][0] if len(resultados) > 1 else resultados[0][0],  # Medio
        resultados[-1][0],     # Menor saldo
    ]
    
    for cliente_id in clientes_verificar:
        cliente_info = cursor.execute('SELECT nombre, ruc FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
        nombre_cliente = cliente_info[0] if cliente_info else 'DESCONOCIDO'
        
        print(f"Cliente {cliente_id}: {nombre_cliente}")
        print("-" * 80)
        
        # Obtener facturas vencidas del cliente
        cursor.execute(f'''
            SELECT 
                f.id,
                f.fecha_emision,
                CASE
                    WHEN f.fecha_vencimiento IS NULL OR f.fecha_vencimiento = '' 
                        THEN date(f.fecha_emision, '+30 days')
                    WHEN f.fecha_vencimiento < f.fecha_emision 
                        THEN date(f.fecha_emision, '+30 days')
                    ELSE f.fecha_vencimiento
                END as fecha_vencimiento_corregida,
                f.total,
                COALESCE(
                    (SELECT SUM(p.valor) FROM pagos p WHERE p.factura_id = f.id 
                     AND p.factura_id IN (SELECT id FROM facturas)), 
                    0
                ) as pagos,
                f.total - COALESCE(
                    (SELECT SUM(p.valor) FROM pagos p WHERE p.factura_id = f.id
                     AND p.factura_id IN (SELECT id FROM facturas)), 
                    0
                ) as saldo
            FROM facturas f
            WHERE 
                f.cliente_id = ?
                AND f.estado = 'emitida'
            ORDER BY fecha_vencimiento_corregida
        ''', (cliente_id,))
        
        facturas_cliente = cursor.fetchall()
        
        print(f"{'Factura':<10} {'Emisión':<12} {'Vencimiento':<12} {'Total':>10} {'Pagos':>10} {'Saldo':>10} {'Vencida?':<8}")
        
        suma_saldos_cliente = 0
        for f_id, emision, vencimiento, total, pagos, saldo in facturas_cliente:
            vencida = "SÍ" if vencimiento < fecha_corte_str and saldo > 0 else "NO"
            print(f"{f_id:<10} {emision:<12} {vencimiento:<12} {total:>10.2f} {pagos:>10.2f} {saldo:>10.2f} {vencida:<8}")
            
            if vencimiento < fecha_corte_str and saldo > 0:
                suma_saldos_cliente += saldo
        
        print(f"{'':<10} {'':<12} {'':<12} {'':<10} {'':<10} {'-'*10}")
        print(f"{'':<10} {'':<12} {'SALDO VENCIDO →':<12} {'':<10} {'':<10} {suma_saldos_cliente:>10.2f}")
        
        # Comparar con el resultado
        saldo_sql = dict_sql.get(cliente_id, 0)
        print(f"\nVerificación:")
        print(f"  Calculado manual:  {suma_saldos_cliente:.2f}")
        print(f"  Método SQL:        {saldo_sql:.2f}")
        print(f"  Diferencia:        {abs(suma_saldos_cliente - saldo_sql):.2f}")
        
        if abs(suma_saldos_cliente - saldo_sql) < 0.01:
            print("  ✅ COINCIDE\n")
        else:
            print("  ❌ NO COINCIDE\n")
    
    # ========================================================================
    # (c) CASOS LÍMITE
    # ========================================================================
    
    print("="*80)
    print("(c) CASOS LÍMITE")
    print("="*80 + "\n")
    
    print("1. Factura que vence EXACTAMENTE 30 días antes del corte (2026-10-31):")
    cursor.execute('''
        SELECT f.id, f.cliente_id, f.fecha_vencimiento, f.total,
               COALESCE((SELECT SUM(p.valor) FROM pagos p WHERE p.factura_id = f.id), 0) as pagos
        FROM facturas f
        WHERE f.fecha_vencimiento = '2026-10-31' AND f.estado = 'emitida'
    ''')
    
    fac_30d = cursor.fetchall()
    if fac_30d:
        for f_id, cli_id, venc, total, pagos in fac_30d:
            saldo = total - pagos
            dias = (fecha_corte - datetime.strptime(venc, '%Y-%m-%d')).days
            incluida = "SÍ" if saldo > 0 else "NO (saldo <= 0)"
            print(f"   Factura {f_id} (cliente {cli_id}): vence {venc}, {dias} días antes del corte")
            print(f"   Total: {total:.2f}, Pagos: {pagos:.2f}, Saldo: {saldo:.2f}")
            print(f"   ¿Incluida? {incluida}")
    else:
        print("   No hay facturas que venzan exactamente 30 días antes.")
    print()
    
    print("2. Factura con pago PARCIAL:")
    cursor.execute('''
        SELECT f.id, f.cliente_id, f.fecha_vencimiento, f.total, f.estado,
               COALESCE((SELECT SUM(p.valor) FROM pagos p WHERE p.factura_id = f.id), 0) as pagos
        FROM facturas f
        WHERE f.estado = 'emitida'
        ORDER BY f.id
    ''')
    
    found_parcial = False
    for f_id, cli_id, venc, total, estado, pagos in cursor.fetchall():
        saldo = total - pagos
        if 0 < pagos < total:  # Pago parcial
            venc_corr = venc if venc else None
            if venc_corr and venc_corr < fecha_corte_str:
                print(f"   Factura {f_id} (cliente {cli_id}): Total {total:.2f}, Pagos {pagos:.2f}, Saldo {saldo:.2f}")
                print(f"   Vence: {venc_corr}, ¿Incluida? SÍ (vencida con saldo > 0)")
                found_parcial = True
                break
    
    if not found_parcial:
        print("   No hay facturas con pago parcial vencidas.")
    print()
    
    print("3. Factura con pago MAYOR al total (sobrepago):")
    cursor.execute('''
        SELECT f.id, f.cliente_id, f.fecha_vencimiento, f.total,
               COALESCE((SELECT SUM(p.valor) FROM pagos p WHERE p.factura_id = f.id), 0) as pagos
        FROM facturas f
        WHERE f.estado = 'emitida'
    ''')
    
    found_sobrepago = False
    for f_id, cli_id, venc, total, pagos in cursor.fetchall():
        if pagos > total:
            saldo = total - pagos
            print(f"   Factura {f_id} (cliente {cli_id}): Total {total:.2f}, Pagos {pagos:.2f}, Saldo {saldo:.2f}")
            print(f"   ¿Incluida? NO (saldo negativo, sobrepago de {abs(saldo):.2f})")
            found_sobrepago = True
            break
    
    if not found_sobrepago:
        print("   No hay facturas con sobrepago.")
    print()
    
    print("4. Factura SIN pagos:")
    cursor.execute('''
        SELECT f.id, f.cliente_id, f.fecha_vencimiento, f.total, f.estado
        FROM facturas f
        WHERE f.estado = 'emitida'
          AND f.id NOT IN (SELECT DISTINCT factura_id FROM pagos)
        ORDER BY f.id
        LIMIT 1
    ''')
    
    fac_sin_pago = cursor.fetchone()
    if fac_sin_pago:
        f_id, cli_id, venc, total, estado = fac_sin_pago
        venc_corr = venc if venc and venc >= fac_sin_pago[1][:10] else None
        if not venc_corr:
            # Buscar emisión para corregir
            cursor.execute('SELECT fecha_emision FROM facturas WHERE id = ?', (f_id,))
            emision = cursor.fetchone()[0]
            venc_corr = (datetime.strptime(emision, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
        
        incluida = "SÍ" if venc_corr and venc_corr < fecha_corte_str else "NO (no vencida)"
        print(f"   Factura {f_id} (cliente {cli_id}): Total {total:.2f}, Sin pagos, Saldo {total:.2f}")
        print(f"   Vence: {venc_corr}, ¿Incluida? {incluida}")
    else:
        print("   Todas las facturas tienen al menos un pago.")
    print()
    
    conn.close()
    
    print("="*80)
    print("FIN DE LA VERIFICACIÓN")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
