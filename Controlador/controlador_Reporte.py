import argparse
import datetime
import decimal
import os
import sys

from Controlador.Controlador_DB import cargar_consultas_desde_archivo,procesar_consulta
import pymysql
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)
from dotenv import load_dotenv

load_dotenv()

# VARIABLES DE CONFIGURACION Y CONSULTAS
#Listado de consultas SQL
SQL_QUERIES = [
    {
        "nombre": "Ventas recientes",
        "query": """
        SELECT * FROM asistencias;
        """,
    },
    {
        "nombre": "Ventas por categoría Tecnología",
        "query": """
            SELECT * 
            FROM empleados 
            WHERE salario > 10000;
        """,
    },
]

# Título general del reporte
REPORT_TITLE = "Reporte de Métricas - Consultas SQL"

# Archivo de salida
OUTPUT_PDF = os.environ.get("OUTPUT_PDF", "reporte_ventas.pdf")

DB_CONFIG = {
    "host": os.getenv("HOST_MYSQL"), 
    "port": os.getenv("PUERTO_MYSQL"), 
    "user":os.getenv("USUARIO_MYSQL"), 
    "password":os.getenv("PASSWORD_MYSQL"), 
    "database":os.getenv("BASE_DE_DATOS_MYSQL") ,
    "cursorclass": pymysql.cursors.DictCursor,
}

MAX_ROWS_IN_TABLE = 50
