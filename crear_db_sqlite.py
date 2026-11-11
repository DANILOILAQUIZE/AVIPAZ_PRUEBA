#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear base de datos SQLite desde los CSV.
Para uso con MCP de SQLite.
"""

import csv
import sqlite3
from pathlib import Path


def leer_csv(ruta):
    """Lee CSV con encoding utf-8-sig."""
    with open(ruta, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    base_dir = Path(__file__).parent
    datos_dir = base_dir / 'datos'
    
    # Leer CSV
    print("Leyendo archivos CSV...")
    clientes = leer_csv(datos_dir / 'clientes.csv')
    facturas = leer_csv(datos_dir / 'facturas.csv')
    pagos = leer_csv(datos_dir / 'pagos.csv')
    
    print(f"  {len(clientes)} clientes")
    print(f"  {len(facturas)} facturas")
    print(f"  {len(pagos)} pagos")
    
    # Crear base de datos
    db_path = datos_dir / 'cartera.db'
    if db_path.exists():
        db_path.unlink()
    
    print(f"\nCreando base de datos: {db_path}")
    conn = sqlite3.connect(db_path)
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
            observaciones TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE pagos (
            id TEXT PRIMARY KEY,
            factura_id TEXT,
            fecha TEXT,
            valor REAL,
            FOREIGN KEY (factura_id) REFERENCES facturas(id)
        )
    ''')
    
    # Insertar datos
    print("Insertando clientes...")
    for c in clientes:
        cursor.execute(
            'INSERT INTO clientes VALUES (?, ?, ?, ?, ?)',
            (c['id'], c['nombre'], c['ruc'], c['ciudad'], c['estado'])
        )
    
    print("Insertando facturas...")
    for f in facturas:
        cursor.execute(
            'INSERT INTO facturas VALUES (?, ?, ?, ?, ?, ?, ?)',
            (f['id'], f['cliente_id'], f['fecha_emision'], f['fecha_vencimiento'],
             float(f['total']) if f['total'] else 0, f['estado'], f.get('observaciones', ''))
        )
    
    print("Insertando pagos...")
    for p in pagos:
        cursor.execute(
            'INSERT INTO pagos VALUES (?, ?, ?, ?)',
            (p['id'], p['factura_id'], p['fecha'], float(p['valor']) if p['valor'] else 0)
        )
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Base de datos creada: {db_path}")
    print("\nPuedes consultarla con:")
    print(f"  sqlite3 {db_path}")


if __name__ == '__main__':
    main()
