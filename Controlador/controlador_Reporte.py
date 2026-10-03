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

# CONTENIDO INFORME PDF
def _tabla_resumen_indices(resultado):
    info_tablas = resultado["info_tablas"]
    nombres_tablas = [t["tabla"] for t in info_tablas]
    tablas_texto = ", ".join(dict.fromkeys(nombres_tablas)) if nombres_tablas else "No determinado"

    if info_tablas:
        usa_algun_indice = any(t["usa_indice"] for t in info_tablas)
        todas_usan_indice = all(t["usa_indice"] for t in info_tablas)
        if todas_usan_indice:
            indice_texto = "Sí, en todas las tablas"
        elif usa_algun_indice:
            indice_texto = "Parcial (algunas tablas sin índice)"
        else:
            indice_texto = "No (full table scan)"
    else:
        indice_texto = "No determinado"

    return tablas_texto, indice_texto

def agregar_portada_comparativa(story, styles, titulo_general, resultados):
    story.append(Paragraph(titulo_general, styles["Title"]))
    fecha_generacion = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Generado el {fecha_generacion}", styles["Normal"]))
    story.append(
        Paragraph(f"Consultas incluidas en este reporte: {len(resultados)}", styles["Normal"])
    )
    story.append(Spacer(1, 16))

    if len(resultados) > 1:
        story.append(Paragraph("Resumen comparativo", styles["Subtitulo"]))

        encabezado = ["#", "Consulta", "Filas", "Tiempo", "Tablas", "¿Usa índice?"]
        filas_tabla = [encabezado]
        for i, r in enumerate(resultados, start=1):
            if r["error"]:
                filas_tabla.append([str(i), r["nombre"], "-", "-", "-", "Error"])
                continue
            tablas_texto, indice_texto = _tabla_resumen_indices(r)
            tiempo_texto = (
                f"{r['tiempo_ejecucion'] * 1000:,.2f} ms" if r["tiempo_ejecucion"] is not None else "N/D"
            )
            filas_tabla.append(
                [
                    str(i),
                    r["nombre"],
                    formatear_numero(len(r["filas"])),
                    tiempo_texto,
                    tablas_texto,
                    indice_texto,
                ]
            )

        tabla_comparativa = Table(
            filas_tabla, repeatRows=1, colWidths=[1 * cm, 5.8 * cm, 1.8 * cm, 2.3 * cm, 3.2 * cm, 3.4 * cm]
        )
        estilo_comp = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fb")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]
        # Resaltar en rojo las consultas con error o sin uso de índice
        for i, r in enumerate(resultados, start=1):
            if r["error"]:
                estilo_comp.append(("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#c0392b")))
            elif r["info_tablas"] and not any(t["usa_indice"] for t in r["info_tablas"]):
                estilo_comp.append(("TEXTCOLOR", (5, i), (5, i), colors.HexColor("#c0392b")))
                estilo_comp.append(("FONTNAME", (5, i), (5, i), "Helvetica-Bold"))

        tabla_comparativa.setStyle(TableStyle(estilo_comp))
        story.append(tabla_comparativa)

    story.append(PageBreak())

def agregar_seccion_consulta(story, styles, indice, resultado):
    nombre = resultado["nombre"]
    query = resultado["query"]

    story.append(Paragraph(f"Consulta {indice}: {nombre}", styles["TituloConsulta"]))
    story.append(Paragraph("Consulta ejecutada", styles["Subtitulo"]))
    story.append(Paragraph(query.strip().replace("\n", "<br/>"), styles["Codigo"]))
    story.append(Spacer(1, 18))

    if resultado["error"]:
        story.append(
            Paragraph(f"<b>Error al ejecutar esta consulta:</b> {resultado['error']}", styles["Error"])
        )
        return

    columnas = resultado["columnas"]
    filas = resultado["filas"]
    metricas = resultado["metricas"]
    metricas_texto = resultado["metricas_texto"]
    tiempo_ejecucion = resultado["tiempo_ejecucion"]
    info_tablas = resultado["info_tablas"]

    # --- Resumen general ---
    story.append(Paragraph("Resumen general", styles["Subtitulo"]))
    tablas_texto, indice_texto = _tabla_resumen_indices(resultado)
    tiempo_texto = f"{tiempo_ejecucion * 1000:,.2f} ms" if tiempo_ejecucion is not None else "No medido"

    resumen_data = [
        ["Total de filas", formatear_numero(metricas["total_filas"])],
        ["Total de columnas", formatear_numero(metricas["total_columnas"])],
        ["Columnas numéricas con métricas", formatear_numero(len(metricas["por_columna"]))],
        ["Tiempo de ejecución", tiempo_texto],
        ["Tablas afectadas", tablas_texto],
        ["¿Usa índice?", indice_texto],
    ]
    tabla_resumen = Table(resumen_data, colWidths=[9 * cm, 6 * cm])
    tabla_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1f4e79")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#eaf1f8")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1f4e79")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
            ]
        )
    )
    story.append(tabla_resumen)
    story.append(Spacer(1, 20))

    # --- Análisis de tablas afectadas y uso de índices ---
    if info_tablas:
        story.append(Paragraph("Tablas afectadas y uso de índices", styles["Subtitulo"]))

        encabezado_idx = ["Tabla", "Tipo de acceso", "Índice usado", "Índices posibles", "Filas est.", "Detalle"]
        filas_idx = [encabezado_idx]
        filas_sin_indice = []

        for i, t in enumerate(info_tablas, start=1):
            filas_idx.append(
                [
                    t["tabla"],
                    t["tipo_acceso"],
                    t["indice"] if t["usa_indice"] else "Sin índice (full scan)",
                    t["indices_posibles"],
                    formatear_numero(t["filas_estimadas"]) if t["filas_estimadas"] is not None else "N/D",
                    t["extra"],
                ]
            )
            if not t["usa_indice"]:
                filas_sin_indice.append(i)

        tabla_idx = Table(filas_idx, repeatRows=1)
        estilo_idx = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fb")]),
        ]
        for fila_idx_num in filas_sin_indice:
            estilo_idx.append(("BACKGROUND", (0, fila_idx_num), (-1, fila_idx_num), colors.HexColor("#fdecea")))
            estilo_idx.append(("TEXTCOLOR", (2, fila_idx_num), (2, fila_idx_num), colors.HexColor("#c0392b")))
            estilo_idx.append(("FONTNAME", (2, fila_idx_num), (2, fila_idx_num), "Helvetica-Bold"))

        tabla_idx.setStyle(TableStyle(estilo_idx))
        story.append(tabla_idx)

        if filas_sin_indice:
            story.append(Spacer(1, 8))
            story.append(
                Paragraph(
                    "<b>Aviso:</b> se detectaron tablas sin uso de índice (full table scan), lo que "
                    "puede afectar el rendimiento en tablas grandes. Considera agregar un índice "
                    "sobre las columnas usadas en las cláusulas WHERE, JOIN u ORDER BY.",
                    styles["Aviso"],
                )
            )
        story.append(Spacer(1, 20))

    # --- Métricas por columna numérica ---
    if metricas["por_columna"]:
        story.append(Paragraph("Métricas destacadas por columna", styles["Subtitulo"]))

        encabezado = ["Columna", "Tipo", "Suma", "Promedio", "Mínimo", "Máximo", "N° valores"]
        filas_metricas = [encabezado]
        for col, m in metricas["por_columna"].items():
            filas_metricas.append(
                [
                    col,
                    m["tipo"],
                    formatear_numero(m["suma"]),
                    formatear_numero(m["promedio"]),
                    formatear_numero(m["minimo"]),
                    formatear_numero(m["maximo"]),
                    formatear_numero(m["conteo"]),
                ]
            )

        tabla_metricas = Table(filas_metricas, repeatRows=1)
        tabla_metricas.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fb")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(tabla_metricas)
    else:
        story.append(
            Paragraph("No se encontraron columnas numéricas para calcular métricas.", styles["Normal"])
        )

    story.append(Spacer(1, 20))

    # --- Métricas de columnas de texto (VARCHAR/CHAR/TEXT) ---
    if metricas_texto:
        story.append(Paragraph("Métricas de columnas de texto (VARCHAR)", styles["Subtitulo"]))

        encabezado_txt = [
            "Columna", "Valores", "Distintos", "Más frecuente",
            "Frecuencia", "Long. mín", "Long. máx", "Long. prom",
        ]
        filas_txt = [encabezado_txt]
        for col, m in metricas_texto.items():
            valor_frecuente_mostrado = m["valor_mas_frecuente"]
            if len(valor_frecuente_mostrado) > 20:
                valor_frecuente_mostrado = valor_frecuente_mostrado[:17] + "..."
            filas_txt.append(
                [
                    col,
                    formatear_numero(m["total_valores"]),
                    formatear_numero(m["valores_distintos"]),
                    valor_frecuente_mostrado,
                    f"{formatear_numero(m['frecuencia_mas_frecuente'])} ({m['porcentaje_mas_frecuente']:.1f}%)",
                    formatear_numero(m["longitud_minima"]),
                    formatear_numero(m["longitud_maxima"]),
                    f"{m['longitud_promedio']:.1f}",
                ]
            )

        tabla_txt = Table(filas_txt, repeatRows=1)
        tabla_txt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fb")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(tabla_txt)
        story.append(Spacer(1, 14))

        columnas_con_top = {col: m for col, m in metricas_texto.items() if m["top_valores"]}
        if columnas_con_top:
            story.append(Paragraph("Valores más frecuentes en columnas categóricas", styles["SubSubtitulo"]))
            for col, m in columnas_con_top.items():
                story.append(Paragraph(f"<b>{col}</b>", styles["Metrica"]))
                encabezado_top = ["Valor", "Frecuencia", "% del total"]
                filas_top = [encabezado_top]
                for item in m["top_valores"]:
                    filas_top.append(
                        [item["valor"], formatear_numero(item["frecuencia"]), f"{item['porcentaje']:.1f}%"]
                    )
                tabla_top = Table(filas_top, colWidths=[8 * cm, 3.5 * cm, 3.5 * cm])
                tabla_top.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e75b6")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4fa")]),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(tabla_top)
                story.append(Spacer(1, 10))

    story.append(PageBreak())

    # --- Detalle de resultados ---
    story.append(Paragraph("Detalle de resultados", styles["Subtitulo"]))

    filas_mostradas = filas
    if MAX_ROWS_IN_TABLE is not None and len(filas) > MAX_ROWS_IN_TABLE:
        filas_mostradas = filas[:MAX_ROWS_IN_TABLE]
        story.append(
            Paragraph(f"Mostrando las primeras {MAX_ROWS_IN_TABLE} de {len(filas)} filas.", styles["Normal"])
        )
        story.append(Spacer(1, 8))

    if filas_mostradas:
        tabla_detalle_data = [columnas]
        for fila in filas_mostradas:
            tabla_detalle_data.append([str(fila.get(col, "")) for col in columnas])

        tabla_detalle = Table(tabla_detalle_data, repeatRows=1)
        tabla_detalle.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fb")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(tabla_detalle)
    else:
        story.append(Paragraph("La consulta no devolvió resultados.", styles["Normal"]))

def construir_pdf_multiple(resultados, ruta_salida, titulo_general):
    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )
    styles = construir_estilos()
    story = []

    agregar_portada_comparativa(story, styles, titulo_general, resultados)

    for i, resultado in enumerate(resultados, start=1):
        agregar_seccion_consulta(story, styles, i, resultado)
        if i < len(resultados):
            story.append(PageBreak())

    doc.build(story)

# ENCRIPTACION 
def proteger_pdf_con_pypdf(ruta_pdf: str, password: str | None = None):
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(ruta_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    if password:
        writer.encrypt(password)

    with open(ruta_pdf, "wb") as f:
        writer.write(f)

