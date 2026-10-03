import time
import decimal
import pymysql

# CLASIFICACION DE TIPO DE COLUMNA
def es_numerico(valor) -> bool:
    if isinstance(valor, bool):
        return False
    return isinstance(valor, (int, float, decimal.Decimal))

def es_texto(valor) -> bool:
    return isinstance(valor, str)

def tipo_amigable(valor):
    if isinstance(valor, bool):
        return "Booleano"
    if isinstance(valor, int):
        return "Entero"
    if isinstance(valor, decimal.Decimal):
        return "Decimal"
    if isinstance(valor, float):
        return "Double/Float"
    return type(valor).__name__

# CONSULTAS
def ejecutar_consulta(config: dict, query: str):
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cursor:
            inicio = time.perf_counter()
            cursor.execute(query)
            filas = cursor.fetchall()
            tiempo_ejecucion = time.perf_counter() - inicio
            columnas = [desc[0] for desc in cursor.description] if cursor.description else []
        return columnas, filas, tiempo_ejecucion
    finally:
        conn.close()

def cargar_consultas_desde_archivo(ruta: str):
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    bloques = contenido.split(";")
    consultas = []
    contador = 1
    for bloque in bloques:
        bloque = bloque.strip()
        if not bloque:
            continue

        nombre = f"Consulta {contador}"
        lineas = bloque.splitlines()
        if lineas and lineas[0].strip().lower().startswith("-- nombre:"):
            nombre = lineas[0].split(":", 1)[1].strip() or nombre
            bloque = "\n".join(lineas[1:]).strip()

        if not bloque:
            continue

        consultas.append({"nombre": nombre, "query": bloque})
        contador += 1

    return consultas

# ANALISIS DE CONSULTAS
def analizar_plan_consulta(config: dict, query: str):
    query_limpia = query.strip().rstrip(";")
    if not query_limpia.lower().startswith(("select", "with")):
        # EXPLAIN aplica principalmente a SELECT (y CTEs con WITH)
        return []

    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"EXPLAIN {query_limpia}")
            plan = cursor.fetchall()
        return plan
    except pymysql.MySQLError:
        # Si el motor no puede explicar la consulta, no se detiene el reporte
        return []
    finally:
        conn.close()

def resumir_uso_indices(plan):
    tablas = []
    for paso in plan:
        tabla = paso.get("table")
        if not tabla:
            continue
        key_usada = paso.get("key")
        posibles_keys = paso.get("possible_keys")
        tipo_acceso = paso.get("type")
        filas_estimadas = paso.get("rows")
        try:
            filas_estimadas = int(filas_estimadas) if filas_estimadas is not None else None
        except (ValueError, TypeError):
            pass  # se deja tal cual si no es convertible
        tablas.append(
            {
                "tabla": tabla,
                "usa_indice": bool(key_usada),
                "indice": key_usada or "Ninguno",
                "indices_posibles": posibles_keys or "Ninguno",
                "tipo_acceso": tipo_acceso or "N/D",
                "filas_estimadas": filas_estimadas,
                "extra": paso.get("Extra") or "",
            }
        )
    return tablas

def calcular_metricas(columnas, filas):
    metricas = {}
    total_filas = len(filas)

    for col in columnas:
        valores = [fila[col] for fila in filas if es_numerico(fila.get(col))]
        if valores:
            metricas[col] = {
                "suma": sum(valores),
                "promedio": sum(valores) / len(valores),
                "minimo": min(valores),
                "maximo": max(valores),
                "conteo": len(valores),
                "tipo": tipo_amigable(valores[0]),
            }

    return {
        "total_filas": total_filas,
        "total_columnas": len(columnas),
        "por_columna": metricas,
    }

def calcular_metricas_texto(columnas, filas, max_top_valores=5, umbral_categorico=0.9):
    metricas = {}

    for col in columnas:
        valores = [fila[col] for fila in filas if es_texto(fila.get(col)) and fila.get(col) != ""]
        if not valores:
            continue

        total_valores = len(valores)
        conteo = {}
        longitudes = []
        for v in valores:
            conteo[v] = conteo.get(v, 0) + 1
            longitudes.append(len(v))

        valores_distintos = len(conteo)
        valor_top, frecuencia_top = max(conteo.items(), key=lambda item: item[1])

        top_valores = None
        if total_valores > 0 and (valores_distintos / total_valores) <= umbral_categorico:
            ranking = sorted(conteo.items(), key=lambda item: item[1], reverse=True)
            top_valores = [
                {"valor": v, "frecuencia": f, "porcentaje": (f / total_valores) * 100}
                for v, f in ranking[:max_top_valores]
            ]

        metricas[col] = {
            "total_valores": total_valores,
            "valores_distintos": valores_distintos,
            "valor_mas_frecuente": valor_top,
            "frecuencia_mas_frecuente": frecuencia_top,
            "porcentaje_mas_frecuente": (frecuencia_top / total_valores) * 100,
            "longitud_minima": min(longitudes),
            "longitud_maxima": max(longitudes),
            "longitud_promedio": sum(longitudes) / len(longitudes),
            "top_valores": top_valores,
        }

    return metricas
