import matplotlib
matplotlib.use('Agg') # Desactivar backend con interfaz gráfica para ejecución headless
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from datetime import datetime
from pathlib import Path
from src.config import REPORTS_DIR

def generate_agenda_image(events: list, date_str: str) -> str:
    """
    Genera una imagen digital estética con la agenda del día.
    Retorna la ruta del archivo PNG generado.
    """
    fig, ax = plt.subplots(figsize=(7, 9), facecolor='#0b0f19')
    ax.set_facecolor('#0b0f19')
    
    # Ocultar ejes por completo
    ax.axis('off')
    
    # Dibujar borde de tarjeta premium
    rect = patches.FancyBboxPatch(
        (0.02, 0.02), 0.96, 0.96,
        boxstyle="round,pad=0.02",
        edgecolor='#1f2937',
        facecolor='#111827',
        linewidth=2,
        transform=ax.transAxes
    )
    ax.add_patch(rect)
    
    # Cabecera / Títulos
    ax.text(0.5, 0.90, "📅 AGENDA DIARIA", color='#ffffff', fontsize=22, fontweight='bold', ha='center', fontname='sans-serif')
    
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dia_semana = dias[dt.weekday()]
        fecha_larga = f"{dia_semana}, {dt.day} de {meses[dt.month-1]} de {dt.year}"
    except Exception:
        fecha_larga = date_str
        
    ax.text(0.5, 0.83, fecha_larga.upper(), color='#06b6d4', fontsize=12, fontweight='bold', ha='center', fontname='sans-serif')
    
    # Línea divisoria decorativa
    ax.plot([0.15, 0.85], [0.80, 0.80], color='#1f2937', transform=ax.transAxes, linewidth=1.5)
    
    # Listar eventos
    if not events:
        # Estado vacío estilizado
        ax.text(0.5, 0.50, "☕ ¡ESTÁS LIBRE HOY!", color='#10b981', fontsize=16, fontweight='bold', ha='center', fontname='sans-serif')
        ax.text(0.5, 0.44, "No hay compromisos programados en tu agenda.\nDisfruta tu día al máximo.", color='#9ca3af', fontsize=11, ha='center', fontname='sans-serif', style='italic')
    else:
        # Dibujar lista de eventos
        y_pos = 0.72
        max_events = 7
        for idx, event in enumerate(events[:max_events]):
            # Separar hora del título
            time_part = "Todo el día"
            title_part = event.get("title", "Evento sin título")
            
            if " " in event.get("start_time", ""):
                time_part = event["start_time"].split(" ")[1]
            
            # Dibujar contenedor individual de evento
            event_rect = patches.FancyBboxPatch(
                (0.08, y_pos - 0.035), 0.84, 0.07,
                boxstyle="round,pad=0.01",
                edgecolor='#1f2937',
                facecolor='#1f2937',
                alpha=0.4,
                transform=ax.transAxes
            )
            ax.add_patch(event_rect)
            
            # Dibujar un pequeño punto indicador de tiempo
            ax.plot([0.12], [y_pos], marker='o', color='#8b5cf6', markersize=8, transform=ax.transAxes)
            
            # Hora en color Cyan
            ax.text(0.16, y_pos, time_part, color='#06b6d4', fontsize=13, fontweight='bold', va='center', fontname='sans-serif')
            
            # Título del evento
            # Truncar título si es muy largo
            display_title = title_part if len(title_part) <= 30 else title_part[:27] + "..."
            ax.text(0.32, y_pos, display_title, color='#f3f4f6', fontsize=13, fontweight='medium', va='center', fontname='sans-serif')
            
            y_pos -= 0.09
            
        if len(events) > max_events:
            rest = len(events) - max_events
            ax.text(0.5, y_pos + 0.02, f"+ {rest} evento(s) adicional(es) en tu agenda", color='#9ca3af', fontsize=11, ha='center', fontname='sans-serif', style='italic')
            
    # Pie de foto
    ax.text(0.5, 0.06, "Asistente Personal Privado 24/7", color='#6b7280', fontsize=9, ha='center', fontname='sans-serif')
    
    # Guardar archivo
    file_path = REPORTS_DIR / f"agenda_{date_str}.png"
    plt.savefig(file_path, dpi=200, bbox_inches='tight', facecolor='#0b0f19')
    plt.close()
    
    return str(file_path)

def generate_financial_chart_image(expenses: list, total_income: float, total_expenses: float) -> str:
    """
    Genera una imagen digital con un gráfico de dona y resumen financiero.
    Retorna la ruta del archivo PNG generado.
    """
    # Configurar dimensiones (proporción horizontal estilo dashboard)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6.5), facecolor='#0b0f19')
    fig.subplots_adjust(wspace=0.15)
    
    # Fondo del lienzo
    for ax in [ax1, ax2]:
        ax.set_facecolor('#0b0f19')
        ax.axis('off')
        
    # --- DIBUJAR FONDO Y CONTENEDOR EN CADA SUBPLOT ---
    # Subplot 1: Gráfico de dona
    rect1 = patches.FancyBboxPatch(
        (0.02, 0.02), 0.96, 0.96,
        boxstyle="round,pad=0.02",
        edgecolor='#1f2937',
        facecolor='#111827',
        linewidth=1.5,
        transform=ax1.transAxes
    )
    ax1.add_patch(rect1)
    
    # Subplot 2: Resumen numérico
    rect2 = patches.FancyBboxPatch(
        (0.02, 0.02), 0.96, 0.96,
        boxstyle="round,pad=0.02",
        edgecolor='#1f2937',
        facecolor='#111827',
        linewidth=1.5,
        transform=ax2.transAxes
    )
    ax2.add_patch(rect2)
    
    # --- SUBPLOT 1: GRÁFICO DE GASTOS (DONUT CHART) ---
    if not expenses:
        ax1.text(0.5, 0.5, "Sin gastos registrados\npara este reporte.", color='#9ca3af', fontsize=14, ha='center', va='center', style='italic')
    else:
        df = pd.DataFrame(expenses)
        # Agrupar gastos por categoría
        category_sums = df.groupby('category')['amount'].sum().reset_index()
        category_sums = category_sums.sort_values(by='amount', ascending=False)
        
        # Paleta de colores Premium
        colors = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#3b82f6', '#14b8a6', '#ef4444']
        # Ciclar colores si hay más categorías que colores
        slice_colors = colors[:len(category_sums)]
        if len(category_sums) > len(colors):
            slice_colors = colors * (len(category_sums) // len(colors) + 1)
            slice_colors = slice_colors[:len(category_sums)]
            
        # Dibujar gráfico de pastel
        # Crear un eje interno flotante en el Subplot 1
        ax_pie = fig.add_axes([0.12, 0.12, 0.28, 0.65])
        ax_pie.axis('off')
        
        wedges, texts, autotexts = ax_pie.pie(
            category_sums['amount'],
            labels=category_sums['category'].str.capitalize(),
            autopct='%1.0f%%',
            startangle=90,
            colors=slice_colors,
            wedgeprops=dict(width=0.4, edgecolor='#111827', linewidth=2), # width=0.4 hace que sea Dona
            textprops=dict(color='#9ca3af', fontsize=9, fontweight='medium')
        )
        
        # Estilizar textos del porcentaje (autotexts)
        for autotext in autotexts:
            autotext.set_color('#ffffff')
            autotext.set_fontsize(9)
            autotext.set_weight('bold')
            
    ax1.text(0.5, 0.88, "📊 DISTRIBUCIÓN DE GASTOS", color='#ffffff', fontsize=15, fontweight='bold', ha='center', transform=ax1.transAxes)
    
    # --- SUBPLOT 2: TARJETA DE RESUMEN FINANCIERO ---
    ax2.text(0.5, 0.88, "💵 RESUMEN FINANCIERO", color='#ffffff', fontsize=15, fontweight='bold', ha='center', transform=ax2.transAxes)
    
    # Calcular Balance y datos adicionales
    balance = total_income - total_expenses
    balance_color = '#10b981' if balance >= 0 else '#ef4444'
    balance_sign = '+' if balance >= 0 else ''
    
    # Buscar categoría con mayor gasto
    top_category_text = "N/A"
    if expenses:
        df_exp = pd.DataFrame(expenses)
        top_cat = df_exp.groupby('category')['amount'].sum().idxmax()
        top_cat_amount = df_exp.groupby('category')['amount'].sum().max()
        top_category_text = f"{top_cat.capitalize()} (${top_cat_amount:.2f})"
        
    # Dibujar filas de información financiera
    y_start = 0.72
    y_gap = 0.13
    
    # Fila 1: Ingresos
    ax2.text(0.10, y_start, "Ingresos Totales:", color='#9ca3af', fontsize=12, transform=ax2.transAxes)
    ax2.text(0.90, y_start, f"+ ${total_income:,.2f}", color='#10b981', fontsize=14, fontweight='bold', ha='right', transform=ax2.transAxes)
    
    # Fila 2: Gastos
    ax2.text(0.10, y_start - y_gap, "Gastos Totales:", color='#9ca3af', fontsize=12, transform=ax2.transAxes)
    ax2.text(0.90, y_start - y_gap, f"- ${total_expenses:,.2f}", color='#ef4444', fontsize=14, fontweight='bold', ha='right', transform=ax2.transAxes)
    
    # Línea divisoria en el resumen
    ax2.plot([0.10, 0.90], [y_start - y_gap - 0.05, y_start - y_gap - 0.05], color='#1f2937', linewidth=1, transform=ax2.transAxes)
    
    # Fila 3: Balance Neto
    ax2.text(0.10, y_start - 2*y_gap - 0.04, "Balance General:", color='#ffffff', fontsize=13, fontweight='bold', transform=ax2.transAxes)
    ax2.text(0.90, y_start - 2*y_gap - 0.04, f"{balance_sign}${balance:,.2f}", color=balance_color, fontsize=15, fontweight='bold', ha='right', transform=ax2.transAxes)
    
    # Contenedor especial para la categoría top
    top_rect = patches.FancyBboxPatch(
        (0.08, 0.14), 0.84, 0.12,
        boxstyle="round,pad=0.01",
        edgecolor='#1f2937',
        facecolor='#1f2937',
        alpha=0.6,
        transform=ax2.transAxes
    )
    ax2.add_patch(top_rect)
    
    # Contenido de categoría top
    ax2.text(0.12, 0.21, "Categoría de Mayor Gasto:", color='#9ca3af', fontsize=10, transform=ax2.transAxes)
    ax2.text(0.12, 0.16, top_category_text, color='#8b5cf6', fontsize=11, fontweight='bold', transform=ax2.transAxes)
    
    # Pie de foto global
    fig.text(0.5, 0.04, "Reporte Financiero Generado Localmente", color='#6b7280', fontsize=10, ha='center')
    
    # Guardar archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = REPORTS_DIR / f"reporte_financiero_{timestamp}.png"
    plt.savefig(file_path, dpi=200, bbox_inches='tight', facecolor='#0b0f19')
    plt.close()
    
    return str(file_path)
