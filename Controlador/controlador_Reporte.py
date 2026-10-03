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

# ESTILOS Y FORMATOS
def formatear_numero(valor):
    if isinstance(valor, float):
        return f"{valor:,.2f}"
    if isinstance(valor, decimal.Decimal):
        return f"{valor:,.2f}"
    if isinstance(valor, int):
        return f"{valor:,}"
    try:
        return f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return str(valor)

def construir_estilos():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Subtitulo",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#1f4e79"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TituloConsulta",
            parent=styles["Heading1"],
            textColor=colors.HexColor("#1f4e79"),
            fontSize=16,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Metrica",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Codigo",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=8,
            textColor=colors.HexColor("#333333"),
            backColor=colors.HexColor("#f2f2f2"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubSubtitulo",
            parent=styles["Heading3"],
            textColor=colors.HexColor("#1f4e79"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Aviso",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            backColor=colors.HexColor("#fdecea"),
            borderColor=colors.HexColor("#c0392b"),
            borderWidth=0.5,
            borderPadding=6,
            textColor=colors.HexColor("#7a2c22"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Error",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            backColor=colors.HexColor("#fdecea"),
            borderColor=colors.HexColor("#c0392b"),
            borderWidth=0.5,
            borderPadding=8,
            textColor=colors.HexColor("#7a2c22"),
        )
    )
    return styles
