#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis exhaustivo de datos de cartera sin modificar los originales.
Genera reporte completo en docs/hallazgos.md
"""

import csv
import re
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path


def leer_csv(ruta):
    """Lee CSV intentando varios encodings y delimitadores."""
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    delimitadores = [',', ';', '\t']
    
    for enc in encodings:
        for delim in delimitadores:
            try:
                with open(ruta, 'r', encoding=enc, newline='') as f:
                    reader = csv.DictReader(f, delimiter=delim)
                    datos = list(reader)
                    if datos and len(datos[0]) > 1:  # Más de una columna
                        return datos, reader.fieldnames, enc, delim
            except:
                continue
    
    raise Exception(f"No se pudo leer {ruta} con ningún encoding/delimitador")


def distancia_levenshtein(s1, s2):
    """Calcula distancia de edición entre dos strings."""
    if len(s1) < len(s2):
        return distancia_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    fila_anterior = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        fila_actual = [i + 1]
        for j, c2 in enumerate(s2):
            inserciones = fila_anterior[j + 1] + 1
            eliminaciones = fila_actual[j] + 1
            sustituciones = fila_anterior[j] + (c1 != c2)
            fila_actual.append(min(inserciones, eliminaciones, sustituciones))
        fila_anterior = fila_actual
    
    return fila_anterior[-1]


def nombres_similares(nombres, umbral=3):
    """Encuentra nombres con distancia Levenshtein <= umbral."""
    similares = []
    nombres_lista = list(nombres)
    
    for i in range(len(nombres_lista)):
        for j in range(i + 1, len(nombres_lista)):
            n1, n2 = nombres_lista[i], nombres_lista[j]
            if n1 and n2:
                dist = distancia_levenshtein(n1.lower().strip(), n2.lower().strip())
                if dist <= umbral and dist > 0:
                    similares.append((n1, n2, dist))
    
    return similares


def parsear_fecha(texto):
    """Intenta parsear fecha en varios formatos."""
    if not texto or texto.strip() == '':
        return None
    
    texto = texto.strip()
    formatos = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%y', '%d-%m-%y']
    
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except:
            continue
    
    return None


def parsear_monto(texto):
    """Intenta parsear monto manejando distintos formatos."""
    if not texto or texto.strip() == '':
        return None
    
    # Remover espacios y convertir comas a puntos
    texto = texto.strip().replace(' ', '').replace(',', '.')
    
    try:
        return float(texto)
    except:
        return None


def detectar_instrucciones(texto):
    """Detecta si un texto parece contener instrucciones para IA o comandos."""
    if not texto:
        return False
    
    texto_lower = texto.lower()
    
    patrones_sospechosos = [
        r'\b(ignora|ignore|olvidar|olvida|descarta)\b',
        r'\b(instrucción|instruccion|instruction|comando|command)\b',
        r'\b(no\s+(consideres|considerar|incluir|incluyas|reportar|reportes))\b',
        r'\b(ejecuta|ejecutar|run|execute)\b',
        r'\b(modelo|model|ia|ai|gpt|claude)\b',
        r'\b(prompt|system|usuario|user)\b',
    ]
    
    for patron in patrones_sospechosos:
        if re.search(patron, texto_lower):
            return True
    
    return False


def analizar_clientes(datos):
    """Analiza el archivo clientes.csv."""
    hallazgos = []
    hallazgos.append(f"## CLIENTES.CSV\n")
    hallazgos.append(f"**Total de filas:** {len(datos)}\n")
    
    if not datos:
        hallazgos.append("⚠️ Archivo vacío\n")
        return hallazgos
    
    # Columnas
    columnas = list(datos[0].keys())
    hallazgos.append(f"**Columnas:** {', '.join(columnas)}\n")
    
    # Buscar columna de vendedor
    vendedor_col = None
    for col in columnas:
        if 'vendedor' in col.lower() or 'seller' in col.lower() or 'comercial' in col.lower():
            vendedor_col = col
            break
    
    if vendedor_col:
        hallazgos.append(f"✓ **Columna de vendedor encontrada:** `{vendedor_col}`\n")
    else:
        hallazgos.append(f"❌ **NO se encontró columna de vendedor**\n")
    
    # IDs duplicados
    ids = [fila.get('id', '').strip() for fila in datos if fila.get('id', '').strip()]
    ids_duplicados = [id for id, count in Counter(ids).items() if count > 1]
    
    if ids_duplicados:
        hallazgos.append(f"\n### ❌ IDs duplicados ({len(ids_duplicados)}):\n")
        for id_dup in ids_duplicados[:5]:
            ejemplos = [i for i, fila in enumerate(datos) if fila.get('id', '').strip() == id_dup]
            hallazgos.append(f"- ID `{id_dup}`: aparece {Counter(ids)[id_dup]} veces (filas {ejemplos})\n")
    else:
        hallazgos.append(f"\n✓ No hay IDs duplicados\n")
    
    # RUCs duplicados
    rucs = [fila.get('ruc', '').strip() for fila in datos if fila.get('ruc', '').strip()]
    rucs_duplicados = [ruc for ruc, count in Counter(rucs).items() if count > 1]
    
    if rucs_duplicados:
        hallazgos.append(f"\n### ❌ RUCs duplicados ({len(rucs_duplicados)}):\n")
        for ruc_dup in rucs_duplicados[:5]:
            ejemplos = [i for i, fila in enumerate(datos) if fila.get('ruc', '').strip() == ruc_dup]
            hallazgos.append(f"- RUC `{ruc_dup}`: aparece {Counter(rucs)[ruc_dup]} veces (filas {ejemplos})\n")
    else:
        hallazgos.append(f"\n✓ No hay RUCs duplicados\n")
    
    # Nombres similares
    nombres = [fila.get('nombre', '').strip() for fila in datos if fila.get('nombre', '').strip()]
    similares = nombres_similares(nombres, umbral=3)
    
    if similares:
        hallazgos.append(f"\n### ⚠️ Nombres similares (distancia Levenshtein ≤ 3): {len(similares)}\n")
        for n1, n2, dist in similares[:10]:
            hallazgos.append(f"- `{n1}` ↔ `{n2}` (distancia: {dist})\n")
    else:
        hallazgos.append(f"\n✓ No hay nombres sospechosamente similares\n")
    
    # Valores nulos por columna
    hallazgos.append(f"\n### Valores nulos/vacíos por columna:\n")
    for col in columnas:
        nulos = sum(1 for fila in datos if not fila.get(col, '').strip())
        if nulos > 0:
            hallazgos.append(f"- `{col}`: {nulos} nulos ({nulos*100/len(datos):.1f}%)\n")
    
    # Estados
    estados = [fila.get('estado', '').strip() for fila in datos]
    estados_unicos = Counter(estados)
    hallazgos.append(f"\n### Estados encontrados:\n")
    for estado, count in estados_unicos.most_common():
        hallazgos.append(f"- `{estado}`: {count} ({count*100/len(datos):.1f}%)\n")
    
    # Formatos mezclados
    hallazgos.append(f"\n### Formatos detectados:\n")
    
    # Mayúsculas en nombres
    nombres_mayus = sum(1 for n in nombres if n and n.isupper())
    nombres_minus = sum(1 for n in nombres if n and n.islower())
    nombres_mixto = len(nombres) - nombres_mayus - nombres_minus
    
    if nombres_mayus > 0 and (nombres_minus > 0 or nombres_mixto > 0):
        hallazgos.append(f"⚠️ Nombres con mayúsculas mezcladas: {nombres_mayus} TODO_MAYUS, {nombres_minus} todo_minus, {nombres_mixto} Mixto\n")
    
    # Observaciones
    if 'observaciones' in columnas:
        obs_llenas = [fila.get('observaciones', '').strip() for fila in datos if fila.get('observaciones', '').strip()]
        hallazgos.append(f"\n### 📝 Observaciones ({len(obs_llenas)} no vacías de {len(datos)}):\n")
        
        for i, fila in enumerate(datos):
            obs = fila.get('observaciones', '').strip()
            if obs:
                es_sospechosa = detectar_instrucciones(obs)
                marca = "🚨 **POSIBLE INSTRUCCIÓN/COMANDO**" if es_sospechosa else ""
                hallazgos.append(f"- Fila {i} (ID: {fila.get('id', 'N/A')}): `{obs}` {marca}\n")
    
    # Datos de vendedor si existe la columna
    if vendedor_col:
        vendedores = [fila.get(vendedor_col, '').strip() for fila in datos]
        vendedores_unicos = Counter([v for v in vendedores if v])
        hallazgos.append(f"\n### 👤 Datos de vendedor:\n")
        hallazgos.append(f"**Total con vendedor asignado:** {sum(1 for v in vendedores if v)} de {len(datos)}\n")
        hallazgos.append(f"**Vendedores únicos:** {len(vendedores_unicos)}\n")
        for vendedor, count in vendedores_unicos.most_common():
            hallazgos.append(f"- `{vendedor}`: {count} clientes\n")
    
    return hallazgos


def analizar_facturas(datos, clientes_datos):
    """Analiza el archivo facturas.csv."""
    hallazgos = []
    hallazgos.append(f"\n\n## FACTURAS.CSV\n")
    hallazgos.append(f"**Total de filas:** {len(datos)}\n")
    
    if not datos:
        hallazgos.append("⚠️ Archivo vacío\n")
        return hallazgos
    
    # Columnas
    columnas = list(datos[0].keys())
    hallazgos.append(f"**Columnas:** {', '.join(columnas)}\n")
    
    # Buscar columna de vendedor
    vendedor_col = None
    for col in columnas:
        if 'vendedor' in col.lower() or 'seller' in col.lower() or 'comercial' in col.lower():
            vendedor_col = col
            break
    
    if vendedor_col:
        hallazgos.append(f"✓ **Columna de vendedor encontrada:** `{vendedor_col}`\n")
    else:
        hallazgos.append(f"❌ **NO se encontró columna de vendedor**\n")
    
    # IDs duplicados
    ids = [fila.get('id', '').strip() for fila in datos if fila.get('id', '').strip()]
    ids_duplicados = [id for id, count in Counter(ids).items() if count > 1]
    
    if ids_duplicados:
        hallazgos.append(f"\n### ❌ IDs de factura duplicados ({len(ids_duplicados)}):\n")
        for id_dup in ids_duplicados[:5]:
            ejemplos = [i for i, fila in enumerate(datos) if fila.get('id', '').strip() == id_dup]
            hallazgos.append(f"- ID `{id_dup}`: aparece {Counter(ids)[id_dup]} veces (filas {ejemplos})\n")
    else:
        hallazgos.append(f"\n✓ No hay IDs de factura duplicados\n")
    
    # Valores nulos
    hallazgos.append(f"\n### Valores nulos/vacíos por columna:\n")
    for col in columnas:
        nulos = sum(1 for fila in datos if not fila.get(col, '').strip())
        if nulos > 0:
            hallazgos.append(f"- `{col}`: {nulos} nulos ({nulos*100/len(datos):.1f}%)\n")
    
    # Estados
    estados = [fila.get('estado', '').strip() for fila in datos]
    estados_unicos = Counter(estados)
    hallazgos.append(f"\n### Estados encontrados:\n")
    for estado, count in estados_unicos.most_common():
        hallazgos.append(f"- `{estado}`: {count} ({count*100/len(datos):.1f}%)\n")
    
    # Validar fechas
    hallazgos.append(f"\n### 📅 Validación de fechas:\n")
    fechas_invalidas = []
    fechas_imposibles = []
    
    for i, fila in enumerate(datos):
        fecha_emision = parsear_fecha(fila.get('fecha_emision', ''))
        fecha_vencimiento = parsear_fecha(fila.get('fecha_vencimiento', ''))
        
        if not fecha_emision:
            fechas_invalidas.append((i, fila.get('id', 'N/A'), 'fecha_emision', fila.get('fecha_emision', '')))
        
        if not fecha_vencimiento:
            fechas_invalidas.append((i, fila.get('id', 'N/A'), 'fecha_vencimiento', fila.get('fecha_vencimiento', '')))
        
        if fecha_emision and fecha_vencimiento:
            if fecha_vencimiento < fecha_emision:
                fechas_imposibles.append((i, fila.get('id', 'N/A'), fecha_emision, fecha_vencimiento))
    
    if fechas_invalidas:
        hallazgos.append(f"❌ **Fechas inválidas/no parseables:** {len(fechas_invalidas)}\n")
        for fila_idx, fac_id, campo, valor in fechas_invalidas[:10]:
            hallazgos.append(f"- Fila {fila_idx} (Factura {fac_id}), campo `{campo}`: `{valor}`\n")
    
    if fechas_imposibles:
        hallazgos.append(f"\n❌ **Fechas imposibles (vencimiento < emisión):** {len(fechas_imposibles)}\n")
        for fila_idx, fac_id, emision, venc in fechas_imposibles[:10]:
            hallazgos.append(f"- Fila {fila_idx} (Factura {fac_id}): emisión {emision.date()} → vencimiento {venc.date()}\n")
    
    if not fechas_invalidas and not fechas_imposibles:
        hallazgos.append(f"✓ Todas las fechas son válidas y cronológicamente correctas\n")
    
    # Validar montos
    hallazgos.append(f"\n### 💰 Validación de montos (total):\n")
    montos_invalidos = []
    montos_cero = []
    montos_negativos = []
    montos_atipicos = []
    
    montos_validos = []
    
    for i, fila in enumerate(datos):
        total = parsear_monto(fila.get('total', ''))
        
        if total is None:
            montos_invalidos.append((i, fila.get('id', 'N/A'), fila.get('total', '')))
        elif total == 0:
            montos_cero.append((i, fila.get('id', 'N/A')))
        elif total < 0:
            montos_negativos.append((i, fila.get('id', 'N/A'), total))
        else:
            montos_validos.append(total)
    
    if montos_invalidos:
        hallazgos.append(f"❌ **Montos no parseables:** {len(montos_invalidos)}\n")
        for fila_idx, fac_id, valor in montos_invalidos[:5]:
            hallazgos.append(f"- Fila {fila_idx} (Factura {fac_id}): `{valor}`\n")
    
    if montos_cero:
        hallazgos.append(f"\n⚠️ **Facturas con total = 0:** {len(montos_cero)}\n")
        for fila_idx, fac_id in montos_cero[:5]:
            hallazgos.append(f"- Fila {fila_idx} (Factura {fac_id})\n")
    
    if montos_negativos:
        hallazgos.append(f"\n❌ **Facturas con total negativo:** {len(montos_negativos)}\n")
        for fila_idx, fac_id, total in montos_negativos:
            hallazgos.append(f"- Fila {fila_idx} (Factura {fac_id}): {total}\n")
    
    # Detectar atípicos (fuera de 3 desviaciones estándar)
    if montos_validos and len(montos_validos) > 2:
        media = sum(montos_validos) / len(montos_validos)
        varianza = sum((x - media) ** 2 for x in montos_validos) / len(montos_validos)
        desv_std = varianza ** 0.5
        
        for i, fila in enumerate(datos):
            total = parsear_monto(fila.get('total', ''))
            if total and total > 0:
                if abs(total - media) > 3 * desv_std:
                    montos_atipicos.append((i, fila.get('id', 'N/A'), total))
        
        if montos_atipicos:
            hallazgos.append(f"\n⚠️ **Montos atípicos (>3σ):** {len(montos_atipicos)} (media: {media:.2f}, σ: {desv_std:.2f})\n")
            for fila_idx, fac_id, total in montos_atipicos[:5]:
                hallazgos.append(f"- Fila {fila_idx} (Factura {fac_id}): {total:.2f}\n")
    
    # Integridad referencial: cliente_id existe en clientes
    hallazgos.append(f"\n### 🔗 Integridad referencial (cliente_id):\n")
    clientes_ids = set(c.get('id', '').strip() for c in clientes_datos if c.get('id', '').strip())
    
    clientes_inexistentes = []
    for i, fila in enumerate(datos):
        cliente_id = fila.get('cliente_id', '').strip()
        if cliente_id and cliente_id not in clientes_ids:
            clientes_inexistentes.append((i, fila.get('id', 'N/A'), cliente_id))
    
    if clientes_inexistentes:
        hallazgos.append(f"❌ **Facturas con cliente_id inexistente:** {len(clientes_inexistentes)}\n")
        for fila_idx, fac_id, cli_id in clientes_inexistentes[:10]:
            hallazgos.append(f"- Fila {fila_idx} (Factura {fac_id}): cliente_id `{cli_id}` no existe\n")
    else:
        hallazgos.append(f"✓ Todos los cliente_id existen en clientes.csv\n")
    
    # Formatos mezclados en montos
    hallazgos.append(f"\n### Formatos de montos detectados:\n")
    totales_raw = [fila.get('total', '').strip() for fila in datos if fila.get('total', '').strip()]
    con_coma = sum(1 for t in totales_raw if ',' in t)
    con_espacio = sum(1 for t in totales_raw if ' ' in t)
    
    if con_coma > 0:
        hallazgos.append(f"⚠️ Montos con coma decimal: {con_coma}\n")
        ejemplos_coma = [t for t in totales_raw if ',' in t][:3]
        hallazgos.append(f"  Ejemplos: {ejemplos_coma}\n")
    
    if con_espacio > 0:
        hallazgos.append(f"⚠️ Montos con espacios: {con_espacio}\n")
        ejemplos_espacio = [t for t in totales_raw if ' ' in t][:3]
        hallazgos.append(f"  Ejemplos: {ejemplos_espacio}\n")
    
    # Observaciones
    if 'observaciones' in columnas:
        obs_llenas = [fila.get('observaciones', '').strip() for fila in datos if fila.get('observaciones', '').strip()]
        hallazgos.append(f"\n### 📝 Observaciones ({len(obs_llenas)} no vacías de {len(datos)}):\n")
        
        for i, fila in enumerate(datos):
            obs = fila.get('observaciones', '').strip()
            if obs:
                es_sospechosa = detectar_instrucciones(obs)
                
                # Detectar patrones específicos
                es_anulacion = 'anula' in obs.lower() or 'cancelad' in obs.lower() or 'invalid' in obs.lower()
                es_nota_credito = 'nota' in obs.lower() and 'crédit' in obs.lower() or 'nota' in obs.lower() and 'credit' in obs.lower()
                es_acuerdo = 'acuerdo' in obs.lower() or 'convenio' in obs.lower() or 'negociac' in obs.lower()
                
                marcas = []
                if es_sospechosa:
                    marcas.append("🚨 **POSIBLE INSTRUCCIÓN/COMANDO**")
                if es_anulacion:
                    marcas.append("🔴 ANULACIÓN")
                if es_nota_credito:
                    marcas.append("🟡 NOTA DE CRÉDITO")
                if es_acuerdo:
                    marcas.append("🟢 ACUERDO DE PAGO")
                
                marca_str = " | ".join(marcas) if marcas else ""
                hallazgos.append(f"- Fila {i} (Factura {fila.get('id', 'N/A')}): `{obs}` {marca_str}\n")
    
    # Datos de vendedor si existe la columna
    if vendedor_col:
        vendedores = [fila.get(vendedor_col, '').strip() for fila in datos]
        vendedores_unicos = Counter([v for v in vendedores if v])
        hallazgos.append(f"\n### 👤 Datos de vendedor:\n")
        hallazgos.append(f"**Total con vendedor asignado:** {sum(1 for v in vendedores if v)} de {len(datos)}\n")
        hallazgos.append(f"**Vendedores únicos:** {len(vendedores_unicos)}\n")
        for vendedor, count in vendedores_unicos.most_common():
            hallazgos.append(f"- `{vendedor}`: {count} facturas\n")
    
    return hallazgos


def analizar_pagos(datos, facturas_datos):
    """Analiza el archivo pagos.csv."""
    hallazgos = []
    hallazgos.append(f"\n\n## PAGOS.CSV\n")
    hallazgos.append(f"**Total de filas:** {len(datos)}\n")
    
    if not datos:
        hallazgos.append("⚠️ Archivo vacío\n")
        return hallazgos
    
    # Columnas
    columnas = list(datos[0].keys())
    hallazgos.append(f"**Columnas:** {', '.join(columnas)}\n")
    
    # Buscar columna de vendedor
    vendedor_col = None
    for col in columnas:
        if 'vendedor' in col.lower() or 'seller' in col.lower() or 'comercial' in col.lower():
            vendedor_col = col
            break
    
    if vendedor_col:
        hallazgos.append(f"✓ **Columna de vendedor encontrada:** `{vendedor_col}`\n")
    else:
        hallazgos.append(f"❌ **NO se encontró columna de vendedor**\n")
    
    # IDs duplicados
    ids = [fila.get('id', '').strip() for fila in datos if fila.get('id', '').strip()]
    ids_duplicados = [id for id, count in Counter(ids).items() if count > 1]
    
    if ids_duplicados:
        hallazgos.append(f"\n### ❌ IDs de pago duplicados ({len(ids_duplicados)}):\n")
        for id_dup in ids_duplicados[:5]:
            ejemplos = [i for i, fila in enumerate(datos) if fila.get('id', '').strip() == id_dup]
            hallazgos.append(f"- ID `{id_dup}`: aparece {Counter(ids)[id_dup]} veces (filas {ejemplos})\n")
    else:
        hallazgos.append(f"\n✓ No hay IDs de pago duplicados\n")
    
    # Valores nulos
    hallazgos.append(f"\n### Valores nulos/vacíos por columna:\n")
    for col in columnas:
        nulos = sum(1 for fila in datos if not fila.get(col, '').strip())
        if nulos > 0:
            hallazgos.append(f"- `{col}`: {nulos} nulos ({nulos*100/len(datos):.1f}%)\n")
    
    # Validar fechas
    hallazgos.append(f"\n### 📅 Validación de fechas de pago:\n")
    fechas_invalidas = []
    
    for i, fila in enumerate(datos):
        fecha_pago = parsear_fecha(fila.get('fecha_pago', ''))
        
        if not fecha_pago:
            fechas_invalidas.append((i, fila.get('id', 'N/A'), fila.get('fecha_pago', '')))
    
    if fechas_invalidas:
        hallazgos.append(f"❌ **Fechas de pago inválidas:** {len(fechas_invalidas)}\n")
        for fila_idx, pago_id, valor in fechas_invalidas[:10]:
            hallazgos.append(f"- Fila {fila_idx} (Pago {pago_id}): `{valor}`\n")
    else:
        hallazgos.append(f"✓ Todas las fechas de pago son válidas\n")
    
    # Validar pagos antes de emisión de factura
    hallazgos.append(f"\n### 📅 Pagos antes de emisión de factura:\n")
    facturas_dict = {f.get('id', '').strip(): f for f in facturas_datos if f.get('id', '').strip()}
    
    pagos_imposibles = []
    for i, fila in enumerate(datos):
        fecha_pago = parsear_fecha(fila.get('fecha_pago', ''))
        factura_id = fila.get('factura_id', '').strip()
        
        if fecha_pago and factura_id in facturas_dict:
            fecha_emision = parsear_fecha(facturas_dict[factura_id].get('fecha_emision', ''))
            if fecha_emision and fecha_pago < fecha_emision:
                pagos_imposibles.append((i, fila.get('id', 'N/A'), factura_id, fecha_pago, fecha_emision))
    
    if pagos_imposibles:
        hallazgos.append(f"❌ **Pagos antes de emisión:** {len(pagos_imposibles)}\n")
        for fila_idx, pago_id, fac_id, f_pago, f_emision in pagos_imposibles[:10]:
            hallazgos.append(f"- Fila {fila_idx} (Pago {pago_id} → Factura {fac_id}): pago {f_pago.date()} < emisión {f_emision.date()}\n")
    else:
        hallazgos.append(f"✓ Todos los pagos son posteriores a la emisión de su factura\n")
    
    # Validar montos
    hallazgos.append(f"\n### 💰 Validación de montos de pago:\n")
    montos_invalidos = []
    montos_cero = []
    montos_negativos = []
    
    for i, fila in enumerate(datos):
        monto = parsear_monto(fila.get('monto', ''))
        
        if monto is None:
            montos_invalidos.append((i, fila.get('id', 'N/A'), fila.get('monto', '')))
        elif monto == 0:
            montos_cero.append((i, fila.get('id', 'N/A')))
        elif monto < 0:
            montos_negativos.append((i, fila.get('id', 'N/A'), monto))
    
    if montos_invalidos:
        hallazgos.append(f"❌ **Montos no parseables:** {len(montos_invalidos)}\n")
        for fila_idx, pago_id, valor in montos_invalidos[:5]:
            hallazgos.append(f"- Fila {fila_idx} (Pago {pago_id}): `{valor}`\n")
    
    if montos_cero:
        hallazgos.append(f"\n⚠️ **Pagos con monto = 0:** {len(montos_cero)}\n")
        for fila_idx, pago_id in montos_cero[:5]:
            hallazgos.append(f"- Fila {fila_idx} (Pago {pago_id})\n")
    
    if montos_negativos:
        hallazgos.append(f"\n❌ **Pagos con monto negativo:** {len(montos_negativos)}\n")
        for fila_idx, pago_id, monto in montos_negativos:
            hallazgos.append(f"- Fila {fila_idx} (Pago {pago_id}): {monto}\n")
    
    # Integridad referencial: factura_id existe
    hallazgos.append(f"\n### 🔗 Integridad referencial (factura_id):\n")
    facturas_ids = set(f.get('id', '').strip() for f in facturas_datos if f.get('id', '').strip())
    
    facturas_inexistentes = []
    for i, fila in enumerate(datos):
        factura_id = fila.get('factura_id', '').strip()
        if factura_id and factura_id not in facturas_ids:
            facturas_inexistentes.append((i, fila.get('id', 'N/A'), factura_id))
    
    if facturas_inexistentes:
        hallazgos.append(f"❌ **Pagos con factura_id inexistente:** {len(facturas_inexistentes)}\n")
        for fila_idx, pago_id, fac_id in facturas_inexistentes[:10]:
            hallazgos.append(f"- Fila {fila_idx} (Pago {pago_id}): factura_id `{fac_id}` no existe\n")
    else:
        hallazgos.append(f"✓ Todos los factura_id existen en facturas.csv\n")
    
    # Suma de pagos vs total de factura
    hallazgos.append(f"\n### 💰 Pagos que exceden el total de la factura:\n")
    
    pagos_por_factura = defaultdict(list)
    for fila in datos:
        factura_id = fila.get('factura_id', '').strip()
        monto = parsear_monto(fila.get('monto', ''))
        if factura_id and monto is not None:
            pagos_por_factura[factura_id].append(monto)
    
    facturas_excedidas = []
    for factura_id, montos in pagos_por_factura.items():
        suma_pagos = sum(montos)
        if factura_id in facturas_dict:
            total_factura = parsear_monto(facturas_dict[factura_id].get('total', ''))
            if total_factura is not None and suma_pagos > total_factura:
                facturas_excedidas.append((factura_id, total_factura, suma_pagos, suma_pagos - total_factura))
    
    if facturas_excedidas:
        hallazgos.append(f"❌ **Facturas con pagos > total:** {len(facturas_excedidas)}\n")
        for fac_id, total, suma, exceso in facturas_excedidas[:10]:
            hallazgos.append(f"- Factura `{fac_id}`: total {total:.2f}, pagos {suma:.2f}, exceso {exceso:.2f}\n")
    else:
        hallazgos.append(f"✓ Ninguna factura tiene pagos que excedan su total\n")
    
    # Observaciones
    if 'observaciones' in columnas:
        obs_llenas = [fila.get('observaciones', '').strip() for fila in datos if fila.get('observaciones', '').strip()]
        hallazgos.append(f"\n### 📝 Observaciones ({len(obs_llenas)} no vacías de {len(datos)}):\n")
        
        for i, fila in enumerate(datos):
            obs = fila.get('observaciones', '').strip()
            if obs:
                es_sospechosa = detectar_instrucciones(obs)
                marca = "🚨 **POSIBLE INSTRUCCIÓN/COMANDO**" if es_sospechosa else ""
                hallazgos.append(f"- Fila {i} (Pago {fila.get('id', 'N/A')}): `{obs}` {marca}\n")
    
    # Datos de vendedor si existe la columna
    if vendedor_col:
        vendedores = [fila.get(vendedor_col, '').strip() for fila in datos]
        vendedores_unicos = Counter([v for v in vendedores if v])
        hallazgos.append(f"\n### 👤 Datos de vendedor:\n")
        hallazgos.append(f"**Total con vendedor asignado:** {sum(1 for v in vendedores if v)} de {len(datos)}\n")
        hallazgos.append(f"**Vendedores únicos:** {len(vendedores_unicos)}\n")
        for vendedor, count in vendedores_unicos.most_common():
            hallazgos.append(f"- `{vendedor}`: {count} pagos\n")
    
    return hallazgos


def main():
    """Función principal."""
    base_dir = Path(__file__).parent
    datos_dir = base_dir / 'datos'
    docs_dir = base_dir / 'docs'
    
    # Crear carpeta docs si no existe
    docs_dir.mkdir(exist_ok=True)
    
    print("Leyendo archivos CSV...")
    
    # Leer archivos
    clientes, cols_cli, enc_cli, delim_cli = leer_csv(datos_dir / 'clientes.csv')
    facturas, cols_fac, enc_fac, delim_fac = leer_csv(datos_dir / 'facturas.csv')
    pagos, cols_pag, enc_pag, delim_pag = leer_csv(datos_dir / 'pagos.csv')
    
    print(f"✓ clientes.csv: {len(clientes)} filas (encoding: {enc_cli}, delim: '{delim_cli}')")
    print(f"✓ facturas.csv: {len(facturas)} filas (encoding: {enc_fac}, delim: '{delim_fac}')")
    print(f"✓ pagos.csv: {len(pagos)} filas (encoding: {enc_pag}, delim: '{delim_pag}')")
    
    print("\nAnalizando datos...")
    
    # Análisis
    reporte = []
    reporte.append("# HALLAZGOS DEL ANÁLISIS DE DATOS\n\n")
    reporte.append(f"**Fecha de análisis:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    reporte.append("---\n\n")
    
    reporte.extend(analizar_clientes(clientes))
    reporte.extend(analizar_facturas(facturas, clientes))
    reporte.extend(analizar_pagos(pagos, facturas))
    
    # Resumen final
    reporte.append("\n\n---\n\n")
    reporte.append("## 🎯 RESUMEN EJECUTIVO\n\n")
    reporte.append("### Datos de vendedor\n")
    
    tiene_vendedor_cli = any('vendedor' in col.lower() for col in clientes[0].keys()) if clientes else False
    tiene_vendedor_fac = any('vendedor' in col.lower() for col in facturas[0].keys()) if facturas else False
    tiene_vendedor_pag = any('vendedor' in col.lower() for col in pagos[0].keys()) if pagos else False
    
    if not (tiene_vendedor_cli or tiene_vendedor_fac or tiene_vendedor_pag):
        reporte.append("❌ **NO SE ENCONTRÓ NINGUNA COLUMNA DE VENDEDOR** en ninguno de los 3 archivos.\n\n")
        reporte.append("**Implicación:** No es posible asignar vendedor a las facturas vencidas sin inventar datos.\n\n")
    else:
        if tiene_vendedor_cli:
            reporte.append("✓ Vendedor encontrado en: clientes.csv\n")
        if tiene_vendedor_fac:
            reporte.append("✓ Vendedor encontrado en: facturas.csv\n")
        if tiene_vendedor_pag:
            reporte.append("✓ Vendedor encontrado en: pagos.csv\n")
    
    reporte.append("\n### Problemas críticos detectados\n")
    reporte.append("Revisar las secciones marcadas con ❌ y 🚨 arriba.\n")
    
    # Guardar reporte
    archivo_salida = docs_dir / 'hallazgos.md'
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write(''.join(reporte))
    
    print(f"\n✅ Reporte guardado en: {archivo_salida}")


if __name__ == '__main__':
    main()
