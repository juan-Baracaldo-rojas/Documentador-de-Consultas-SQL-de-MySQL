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