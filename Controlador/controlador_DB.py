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
