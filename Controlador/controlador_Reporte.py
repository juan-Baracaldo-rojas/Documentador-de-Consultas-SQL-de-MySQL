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

