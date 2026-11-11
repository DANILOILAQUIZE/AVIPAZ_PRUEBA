# Opcional 6: Conexión con MCP

**Objetivo:** Permitir que la IA consulte los datos directamente sin necesidad de copiar/pegar archivos.

---

## Configuración Realizada

### 1. MCP de Sistema de Archivos

**Archivo de configuración:** `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "filesystem-cartera": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/macbook/Documents/PRUEBA_AVIPAZ_DARWIN_ILA/cartera/datos"
      ],
      "disabled": false
    },
    "sqlite-cartera": {
      "command": "uvx",
      "args": [
        "mcp-server-sqlite",
        "--db-path",
        "/Users/macbook/Documents/PRUEBA_AVIPAZ_DARWIN_ILA/cartera/datos/cartera.db"
      ],
      "disabled": false
    }
  }
}
```

**Qué hace:**
- **filesystem-cartera:** Permite leer archivos CSV directamente desde `datos/`
- **sqlite-cartera:** Permite ejecutar consultas SQL sobre la base de datos

---

## Pasos de Implementación

### Paso 1: Crear configuración MCP

1. Creé la carpeta `.kiro/settings/`
2. Creé el archivo `mcp.json` con la configuración de 2 servidores MCP
3. Especifiqué rutas absolutas a la carpeta de datos

### Paso 2: Preparar base de datos SQLite

Para el MCP de SQLite, necesitaba una base de datos:

1. Creé `crear_db_sqlite.py` que:
   - Lee los 3 archivos CSV
   - Crea una base de datos `datos/cartera.db`
   - Define 3 tablas: clientes, facturas, pagos
   - Inserta todos los datos
   - Mantiene las foreign keys

2. Ejecuté el script:
   ```bash
   python3 crear_db_sqlite.py
   ```

**Resultado:** Base de datos con 14 clientes, 21 facturas, 10 pagos

### Paso 3: Reiniciar Kiro

Para que Kiro detecte los nuevos servidores MCP:
- Cerré y reabrí Kiro IDE
- Los servidores MCP se conectan automáticamente al iniciar

---

## Cómo Comprobar que Funciona

### Prueba 1: Consultar archivos directamente

**Prompt de prueba:**
> "Usando el MCP filesystem-cartera, lista los archivos disponibles en la carpeta de datos"

**Respuesta esperada:**
La IA debe usar la herramienta MCP para listar:
- clientes.csv
- facturas.csv
- pagos.csv
- cartera.db

**Evidencia de uso:**
- En el log de herramientas de Kiro aparecerá la llamada al MCP
- La respuesta mostrará los archivos sin que yo los haya pegado

### Prueba 2: Leer contenido de un CSV

**Prompt de prueba:**
> "Lee el archivo clientes.csv usando el MCP y dime cuántos clientes hay"

**Respuesta esperada:**
La IA debe:
1. Usar el MCP filesystem para leer clientes.csv
2. Contar las filas
3. Responder: "14 clientes"

**Evidencia de uso:**
- El log muestra `read_file` del MCP
- La IA no me pidió que le pegara el contenido

### Prueba 3: Consultar la base de datos

**Prompt de prueba:**
> "Usando el MCP sqlite-cartera, ejecuta este query: SELECT COUNT(*) FROM facturas WHERE estado = 'emitida'"

**Respuesta esperada:**
La IA debe:
1. Usar el MCP sqlite para ejecutar la consulta
2. Devolver el resultado: 20 facturas emitidas

**Evidencia de uso:**
- El log muestra `execute_query` del MCP sqlite
- El resultado viene directamente de la base de datos

### Prueba 4: Calcular cartera vencida con SQL

**Prompt de prueba:**
> "Usando el MCP sqlite-cartera, calcula el total de cartera vencida al 30/11/2026 con una consulta SQL"

**Respuesta esperada:**
La IA debe:
1. Escribir un query SQL complejo
2. Ejecutarlo usando el MCP
3. Devolver: $17,900.00

**Evidencia de uso:**
- Query ejecutado directamente en la base de datos
- Resultado sin scripts Python intermedios

---

## Ventajas del MCP en Este Caso

### Sin MCP (método tradicional):
1. ❌ Tengo que copiar/pegar contenido de CSV
2. ❌ La IA no puede explorar los datos libremente
3. ❌ Cada consulta nueva requiere mi intervención
4. ❌ No hay forma de verificar queries SQL directamente

### Con MCP (método implementado):
1. ✅ La IA lee archivos directamente cuando los necesita
2. ✅ Puede explorar y descubrir datos por su cuenta
3. ✅ Ejecuta queries SQL sin intermediarios
4. ✅ Autonomía total para análisis de datos
5. ✅ Verificación instantánea de resultados

---

## Casos de Uso Reales

### Uso 1: Análisis exploratorio
**Prompt:** "Revisa los datos y dime qué problemas encuentras"

**Con MCP:** La IA lee los 3 archivos, detecta problemas, genera reporte
**Sin MCP:** Yo tendría que pegar cada archivo manualmente

### Uso 2: Verificación de resultados
**Prompt:** "Verifica que el total de $17,900 es correcto usando la base de datos"

**Con MCP:** La IA ejecuta SQL directamente y confirma
**Sin MCP:** Tendría que ejecutar el query yo mismo y pasarle el resultado

### Uso 3: Responder preguntas ad-hoc
**Prompt:** "¿Cuántos clientes tienen estado 'inactivo'?"

**Con MCP:** La IA consulta directamente: 1 cliente
**Sin MCP:** Yo busco manualmente o le paso el archivo completo

---

## Limitaciones y Consideraciones

### Limitaciones encontradas:

1. **Rutas absolutas:** El MCP necesita rutas completas, no funciona con relativas
2. **Seguridad:** El MCP filesystem tiene acceso SOLO a la carpeta especificada (datos/)
3. **Dependencias:** Requiere `npx` (Node.js) y `uvx` (uv/Python) instalados

### Alternativas no usadas:

- **MCP de PostgreSQL:** Hubiera requerido instalar PostgreSQL (overkill)
- **MCP de Google Drive:** Los datos no están en la nube
- **MCP de Git:** No era necesario para este caso

---

## Comprobación de que Se Usó Realmente

### Evidencia 1: Logs de Kiro
En el panel de herramientas de Kiro IDE aparecen:
- Llamadas a `filesystem_read_file`
- Llamadas a `sqlite_execute_query`
- Timestamps de cada operación

### Evidencia 2: Sin copiar/pegar
Durante las consultas de prueba:
- NO pegué contenido de CSV en el chat
- NO ejecuté queries SQL manualmente
- La IA respondió con datos precisos

### Evidencia 3: Velocidad de respuesta
Con MCP:
- Respuesta inmediata a preguntas sobre datos
- No hay delay de "espera mientras busco el archivo"

### Evidencia 4: Queries complejos
La IA pudo ejecutar:
```sql
SELECT c.nombre, SUM(f.total - COALESCE(p.valor, 0)) as saldo
FROM clientes c
JOIN facturas f ON c.id = f.cliente_id
LEFT JOIN pagos p ON f.id = p.factura_id
WHERE f.fecha_vencimiento < '2026-11-30'
GROUP BY c.id
```

Sin intermediarios ni scripts.

---

## Archivos Creados para Este Opcional

1. `.kiro/settings/mcp.json` - Configuración de servidores MCP
2. `crear_db_sqlite.py` - Script para generar la base de datos
3. `datos/cartera.db` - Base de datos SQLite (49 KB)
4. `entrega/opcional_mcp.md` - Esta documentación

---

## Conclusión

✅ **MCP configurado y funcionando**

**Beneficios logrados:**
- Autonomía total de la IA para consultar datos
- Verificación instantánea con SQL
- No más copiar/pegar archivos
- Análisis exploratorio sin fricción

**Tiempo de implementación:** ~20 minutos

**Valor agregado:** Alto - especialmente para análisis repetitivos y verificaciones

---

**Nota:** Para usar esto en producción, habría que:
1. Generalizar las rutas (no hardcodear rutas absolutas)
2. Agregar autenticación si los datos son sensibles
3. Considerar un MCP de base de datos real (PostgreSQL) si el volumen crece
