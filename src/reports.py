import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from src.config import REPORTS_DIR
from src.db import get_all_expenses

def generate_expense_excel() -> dict:
    """
    Genera un archivo Excel estructurado y estilizado a partir de los gastos registrados en SQLite.
    
    Retorna un diccionario con el estado, la ruta del archivo generado y un mensaje explicativo.
    """
    expenses = get_all_expenses()
    if not expenses:
        return {
            "status": "empty",
            "file_path": None,
            "message": "No hay gastos registrados en la base de datos para generar un reporte."
        }
        
    # Crear un DataFrame
    df = pd.DataFrame(expenses)
    
    # Renombrar columnas para el reporte
    df = df.rename(columns={
        "date_added": "Fecha de Registro",
        "category": "Categoría",
        "concept": "Concepto",
        "amount": "Monto"
    })
    
    # Formatear la fecha
    df["Fecha de Registro"] = pd.to_datetime(df["Fecha de Registro"]).dt.strftime("%Y-%m-%d %H:%M")
    # Poner la categoría en mayúsculas para presentación visual
    df["Categoría"] = df["Categoría"].str.capitalize()
    
    # Crear archivo Excel en la ruta configurada
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"reporte_gastos_{timestamp}.xlsx"
    file_path = REPORTS_DIR / file_name
    
    # Iniciar ExcelWriter con openpyxl
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        # 1. Crear Hoja 1: Transacciones Detalladas
        df.to_excel(writer, sheet_name="Detalle de Gastos", index=False)
        
        # 2. Crear Hoja 2: Resumen por Categoría
        summary_df = df.groupby("Categoría").agg(
            Total_Gastado=("Monto", "sum"),
            Promedio_Transaccion=("Monto", "mean"),
            Cantidad_Transacciones=("Monto", "count")
        ).reset_index()
        
        summary_df = summary_df.rename(columns={
            "Total_Gastado": "Total Gastado",
            "Promedio_Transaccion": "Promedio por Gasto",
            "Cantidad_Transacciones": "Número de Transacciones"
        })
        
        summary_df.to_excel(writer, sheet_name="Resumen por Categoría", index=False)
        
        # Obtener libro de openpyxl para estilizar
        workbook = writer.book
        
        # Estilos premium
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid") # Azul oscuro elegante
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        regular_font = Font(name="Segoe UI", size=10)
        bold_font = Font(name="Segoe UI", size=10, bold=True)
        accent_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid") # Gris suave
        
        border_thin = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )
        border_total = Border(
            top=Side(style='thin', color='000000'),
            bottom=Side(style='double', color='000000') # Doble línea al final
        )
        
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")
        align_center = Alignment(horizontal="center", vertical="center")
        
        # --- ESTILIZAR HOJA: Detalle de Gastos ---
        ws_detail = workbook["Detalle de Gastos"]
        ws_detail.views.sheetView[0].showGridLines = True
        
        # Encabezados
        for col_idx in range(1, 5):
            cell = ws_detail.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center
            cell.border = border_thin
            
        # Filas de datos
        max_row = ws_detail.max_row
        for row_idx in range(2, max_row + 1):
            # Celdas básicas
            ws_detail.cell(row=row_idx, column=1).alignment = align_center # Fecha
            ws_detail.cell(row=row_idx, column=2).alignment = align_left   # Categoría
            ws_detail.cell(row=row_idx, column=3).alignment = align_left   # Concepto
            
            # Monto
            monto_cell = ws_detail.cell(row=row_idx, column=4)
            monto_cell.alignment = align_right
            monto_cell.number_format = '$#,##0.00'
            
            # Aplicar fuentes y bordes
            for col_idx in range(1, 5):
                c = ws_detail.cell(row=row_idx, column=col_idx)
                c.font = regular_font
                c.border = border_thin
                
        # Fila de Total General al final
        total_row_idx = max_row + 1
        ws_detail.cell(row=total_row_idx, column=3, value="Total General").font = bold_font
        ws_detail.cell(row=total_row_idx, column=3).alignment = align_right
        
        total_cell = ws_detail.cell(row=total_row_idx, column=4, value=f"=SUM(D2:D{max_row})")
        total_cell.font = bold_font
        total_cell.alignment = align_right
        total_cell.number_format = '$#,##0.00'
        total_cell.border = border_total
        ws_detail.cell(row=total_row_idx, column=3).border = Border(top=Side(style='thin', color='000000'))
        
        # Ajustar ancho de columnas automáticamente
        for col in ws_detail.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                # Evitar contar la fórmula de SUM
                if cell.value and not str(cell.value).startswith("="):
                    max_len = max(max_len, len(str(cell.value)))
            ws_detail.column_dimensions[col_letter].width = max(max_len + 4, 15)
            
        # --- ESTILIZAR HOJA: Resumen por Categoría ---
        ws_summary = workbook["Resumen por Categoría"]
        ws_summary.views.sheetView[0].showGridLines = True
        
        # Encabezados
        for col_idx in range(1, 5):
            cell = ws_summary.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center
            cell.border = border_thin
            
        # Filas de datos
        max_row_sum = ws_summary.max_row
        for row_idx in range(2, max_row_sum + 1):
            ws_summary.cell(row=row_idx, column=1).alignment = align_left   # Categoría
            
            # Total gastado
            tot_cell = ws_summary.cell(row=row_idx, column=2)
            tot_cell.alignment = align_right
            tot_cell.number_format = '$#,##0.00'
            
            # Promedio por gasto
            avg_cell = ws_summary.cell(row=row_idx, column=3)
            avg_cell.alignment = align_right
            avg_cell.number_format = '$#,##0.00'
            
            # Cantidad
            cnt_cell = ws_summary.cell(row=row_idx, column=4)
            cnt_cell.alignment = align_center
            
            # Aplicar fuentes y bordes
            for col_idx in range(1, 5):
                c = ws_summary.cell(row=row_idx, column=col_idx)
                c.font = regular_font
                c.border = border_thin
                
        # Fila de Total de Totales
        total_row_sum_idx = max_row_sum + 1
        ws_summary.cell(row=total_row_sum_idx, column=1, value="Total General").font = bold_font
        ws_summary.cell(row=total_row_sum_idx, column=1).alignment = align_left
        ws_summary.cell(row=total_row_sum_idx, column=1).border = Border(top=Side(style='thin', color='000000'))
        
        # Total gastado acumulado
        tot_sum_cell = ws_summary.cell(row=total_row_sum_idx, column=2, value=f"=SUM(B2:B{max_row_sum})")
        tot_sum_cell.font = bold_font
        tot_sum_cell.alignment = align_right
        tot_sum_cell.number_format = '$#,##0.00'
        tot_sum_cell.border = border_total
        
        # Promedio general ponderado
        avg_sum_cell = ws_summary.cell(row=total_row_sum_idx, column=3, value=f"=AVERAGE(C2:C{max_row_sum})")
        avg_sum_cell.font = bold_font
        avg_sum_cell.alignment = align_right
        avg_sum_cell.number_format = '$#,##0.00'
        avg_sum_cell.border = border_total
        
        # Cantidad total
        cnt_sum_cell = ws_summary.cell(row=total_row_sum_idx, column=4, value=f"=SUM(D2:D{max_row_sum})")
        cnt_sum_cell.font = bold_font
        cnt_sum_cell.alignment = align_center
        cnt_sum_cell.border = border_total
        
        # Ajustar ancho de columnas automáticamente
        for col in ws_summary.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value and not str(cell.value).startswith("="):
                    max_len = max(max_len, len(str(cell.value)))
            ws_summary.column_dimensions[col_letter].width = max(max_len + 4, 18)
            
    return {
        "status": "success",
        "file_path": str(file_path),
        "message": f"Reporte de gastos generado exitosamente: {file_name}"
    }
