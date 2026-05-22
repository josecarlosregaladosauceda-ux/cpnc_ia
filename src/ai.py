import json
from datetime import datetime
from openai import OpenAI
import src.db as db
import src.reports as reports
import src.visuals as visuals
from src.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

# Inicializar cliente de OpenAI configurado para OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com/google/antigravity",
        "X-Title": "Asistente Personal Privado 24/7 MVP"
    }
)

# Definición de herramientas para Function Calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Registra un nuevo gasto financiero (salida de dinero) en la base de datos local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Categoría homogénea del gasto en minúsculas (ej: comida, transporte, servicios, salud, ocio, educación)."
                    },
                    "concept": {
                        "type": "string",
                        "description": "Concepto descriptivo detallado del gasto (ej: Almuerzo con cliente, Gasolina, Pago de luz)."
                    },
                    "amount": {
                        "type": "number",
                        "description": "El monto del gasto como número decimal (ej: 150.50)."
                    }
                },
                "required": ["category", "concept", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_income",
            "description": "Registra un nuevo ingreso financiero (entrada de dinero) en la base de datos local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Categoría homogénea del ingreso en minúsculas (ej: trabajo, ventas, inversiones, regalos, otros)."
                    },
                    "concept": {
                        "type": "string",
                        "description": "Concepto descriptivo detallado del ingreso (ej: Pago de nómina, Venta de teléfono, Intereses bancarios)."
                    },
                    "amount": {
                        "type": "number",
                        "description": "El monto del ingreso como número decimal (ej: 1500.00)."
                    }
                },
                "required": ["category", "concept", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_expenses",
            "description": "Busca gastos históricos utilizando una palabra clave que coincida con el concepto o la categoría.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Palabra clave para realizar la búsqueda mediante similitud (LIKE) en la base de datos."
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_income",
            "description": "Busca ingresos históricos utilizando una palabra clave que coincida con el concepto o la categoría.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Palabra clave para realizar la búsqueda mediante similitud (LIKE) en la base de datos."
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_financial_report",
            "description": "Compila y genera un reporte unificado de finanzas (gastos e ingresos) en Excel y crea un gráfico de distribución y balance financiero visual.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_calendar_event",
            "description": "Agenda un nuevo evento bloqueante en el calendario para una fecha y hora específicas. Formato de start_time obligatorio: YYYY-MM-DD HH:MM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Título o descripción del evento (ej: Reunión de proyecto, Cita con el dentista)."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Fecha y hora de inicio en formato estricto YYYY-MM-DD HH:MM (ej: 2026-05-22 15:30)."
                    }
                },
                "required": ["title", "start_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Consulta el calendario de la agenda para una fecha específica (YYYY-MM-DD) para verificar eventos programados y generar un resumen visual de la agenda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {
                        "type": "string",
                        "description": "Fecha a consultar en formato YYYY-MM-DD (ej: 2026-05-22)."
                    }
                },
                "required": ["date_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Realiza una consulta de búsqueda en internet para obtener datos, noticias, o información actualizada de la actualidad.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta de búsqueda a realizar (ej: quién ganó el partido de ayer, clima en Monterrey hoy)."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def execute_tool(name: str, arguments: dict) -> tuple[str, list[dict]]:
    """
    Ejecuta localmente la función indicada y retorna el resultado de texto 
    junto con cualquier efecto secundario (como una ruta de archivo generada).
    """
    side_effects = []
    try:
        if name == "add_expense":
            result = db.add_expense(
                category=arguments.get("category"),
                concept=arguments.get("concept"),
                amount=arguments.get("amount")
            )
            
            try:
                summary = db.get_financial_summary()
                p_inc = summary["period_income"]
                p_exp = summary["period_expenses"]
                p_bal = summary["period_balance"]
                net_bal = summary["net_balance"]
                start_date_str = summary["start_date"]
                
                # Formatear la fecha de inicio en español de manera amigable
                try:
                    dt_start = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                    months_es = [
                        "enero", "febrero", "marzo", "abril", "mayo", "junio",
                        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
                    ]
                    start_formatted = f"{dt_start.day} de {months_es[dt_start.month - 1]}"
                except Exception:
                    start_formatted = start_date_str.split(" ")[0]
                
                # Semáforo de color
                color = "🟢"
                if p_inc > 0:
                    pct = (p_exp / p_inc) * 100
                    if 50 < pct <= 85:
                        color = "🟡"
                    elif pct > 85:
                        color = "🔴"
                    
                    filled = min(10, int(pct / 10))
                    empty = 10 - filled
                    bar = "█" * filled + "░" * empty
                    bar_str = f"`[{bar}] {pct:.1f}%`"
                    pct_desc = f"Has consumido el {pct:.1f}% de tu depósito de este período."
                else:
                    color = "🔴"
                    bar_str = "`[░░░░░░░░░░] (Sin ingresos en el período)`"
                    pct_desc = "⚠️ No has registrado ingresos recientes. Se está tomando la ventana de los últimos 7 días."
                
                status_desc = "dentro del presupuesto" if color == "🟢" else ("cerca del límite" if color == "🟡" else "presupuesto excedido o sin fondos")
                
                result += (
                    f"\n\n📊 **Estado del Período Financiero** (desde el {start_formatted}):\n"
                    f"- 📥 **Depósitos recibidos:** ${p_inc:.2f}\n"
                    f"- 📤 **Gastos acumulados:** ${p_exp:.2f}\n"
                    f"- 💰 **Saldo disponible:** {color} `${p_bal:.2f}` ({status_desc})\n"
                    f"- 📉 **Consumo de presupuesto:**\n"
                    f"  {bar_str}\n"
                    f"  _{pct_desc}_\n\n"
                    f"💼 **Balance Neto General** (ahorro acumulado):\n"
                    f"- {'🟢' if net_bal >= 0 else '🔴'} `${net_bal:.2f}`"
                )
            except Exception as ex:
                result += f"\n\n(No se pudo calcular el balance actual: {str(ex)})"
        elif name == "add_income":
            result = db.add_income(
                category=arguments.get("category"),
                concept=arguments.get("concept"),
                amount=arguments.get("amount")
            )
        elif name == "search_expenses":
            rows = db.search_expenses(keyword=arguments.get("keyword"))
            if rows:
                result = "Se encontraron los siguientes gastos:\n"
                for r in rows:
                    result += f"- [{r['date_added']}] {r['category'].capitalize()}: {r['concept']} - ${r['amount']:.2f}\n"
            else:
                result = f"No se encontraron gastos con el término '{arguments.get('keyword')}'."
        elif name == "search_income":
            rows = db.search_income(keyword=arguments.get("keyword"))
            if rows:
                result = "Se encontraron los siguientes ingresos:\n"
                for r in rows:
                    result += f"- [{r['date_added']}] {r['category'].capitalize()}: {r['concept']} - ${r['amount']:.2f}\n"
            else:
                result = f"No se encontraron ingresos con el término '{arguments.get('keyword')}'."
        elif name == "generate_financial_report":
            report_result = reports.generate_financial_excel()
            if report_result["status"] == "success":
                excel_path = report_result["file_path"]
                side_effects.append({"action": "send_document", "file_path": excel_path})
                
                # Generar imagen de gráfico
                try:
                    all_exp = db.get_all_expenses()
                    all_inc = db.get_all_income()
                    total_inc = sum(i['amount'] for i in all_inc)
                    total_exp = sum(e['amount'] for e in all_exp)
                    
                    chart_path = visuals.generate_financial_chart_image(all_exp, total_inc, total_exp)
                    side_effects.append({
                        "action": "send_photo", 
                        "file_path": chart_path, 
                        "caption": "📊 *Reporte Financiero Visual*\nAquí tienes la distribución de tus gastos y tu balance neto actual."
                    })
                    result = "Reporte financiero generado con éxito. Se han enviado el archivo Excel detallado y el resumen en imagen."
                except Exception as ex_img:
                    result = f"Reporte Excel generado con éxito en {excel_path}, pero falló la generación de la imagen: {str(ex_img)}."
            else:
                result = report_result["message"]
        elif name == "add_calendar_event":
            result = db.add_calendar_event(
                title=arguments.get("title"),
                start_time=arguments.get("start_time")
            )
        elif name == "check_availability":
            date_str = arguments.get("date_str")
            rows = db.check_availability(date_str=date_str)
            
            # Generar la imagen de agenda diaria
            try:
                img_path = visuals.generate_agenda_image(rows, date_str)
                side_effects.append({
                    "action": "send_photo",
                    "file_path": img_path,
                    "caption": f"📅 *Tu Agenda para el {date_str}*"
                })
            except Exception as ex_img:
                # No bloquear si la generación de la imagen falla
                pass
                
            if rows:
                result = f"Agenda para el {date_str}:\n"
                for r in rows:
                    result += f"- {r['start_time'].split(' ')[1]}: {r['title']}\n"
            else:
                result = f"No hay eventos programados para el {date_str}. Estás completamente libre."
        elif name == "web_search":
            from duckduckgo_search import DDGS
            query = arguments.get("query")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            if results:
                result = f"Resultados de búsqueda en la web para '{query}':\n"
                for r in results:
                    result += f"- {r['title']}: {r['body']} (Fuente: {r['href']})\n"
            else:
                result = f"No se encontraron resultados para la búsqueda '{query}'."
        else:
            result = f"Error: Herramienta '{name}' no reconocida."
    except Exception as e:
        result = f"Error al ejecutar la herramienta '{name}': {str(e)}"
        
    return result, side_effects

def process_message_with_ai(user_id: int, user_message: str) -> tuple[str, list[dict]]:
    """
    Orquesta el envío de mensajes a OpenRouter. Resuelve el Function Calling,
    ejecuta las herramientas correspondientes de forma local y devuelve la
    respuesta final textual y una lista de efectos secundarios (como enviar archivos).
    """
    # Obtener fecha y hora actuales en español para inyectar en el system prompt
    now = datetime.now()
    dias_semana = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    dia_es = dias_semana.get(now.strftime("%A"), now.strftime("%A"))
    current_time_str = now.strftime(f"%Y-%m-%d %H:%M (Día: {dia_es})")

    # Inyección de instrucciones del sistema
    system_prompt = (
        "Eres un Asistente Personal de IA Privado y Local, diseñado para ejecutarse 24/7 en un servidor perimetral local.\n"
        "Tus tres funciones principales son:\n"
        "1. Módulo Financiero: Registra gastos e ingresos en tu base de datos local y genera reportes combinados (Excel e imágenes de resúmenes).\n"
        "2. Agenda y Calendario: Permite agendar eventos bloqueantes con alertas automáticas y revisar tu disponibilidad diaria de forma visual.\n"
        "3. Búsqueda Web: Consulta información en tiempo real en internet de forma transparente cuando sea necesario.\n\n"
        "REGLAS IMPORTANTES:\n"
        "- Toda la persistencia ocurre localmente en SQLite.\n"
        f"- La fecha y hora actual en el servidor es: {current_time_str}.\n"
        "- Cuando el usuario haga referencias temporales relativas (como 'hoy', 'mañana', 'el lunes', 'ayer'), debes calcular la fecha exacta en base a la hora actual indicada arriba antes de llamar a las herramientas.\n"
        "- Para agendar eventos, es OBLIGATORIO usar el formato 'YYYY-MM-DD HH:MM'. Si no especifican la hora, asume una o consulta, pero nunca dejes un formato inválido.\n"
        "- Cuando el usuario diga expresiones como 'me pagaron', 'recibí', 'ingreso de', etc., debes invocar 'add_income'.\n"
        "- Si el usuario te pide un reporte financiero o de gastos/ingresos, debes invocar la herramienta 'generate_financial_report'. Ésta generará tanto el Excel con el detalle como una imagen del gráfico de pastel/dona como resumen. Confírmale que estás enviando ambos archivos.\n"
        "- Si el usuario consulta su agenda o disponibilidad diaria ('¿qué tengo hoy?', 'agenda para mañana'), debes invocar la herramienta 'check_availability', la cual además del texto generará una imagen estilizada de su agenda de forma automática.\n"
        "- Responde siempre en español de manera formal, clara y concisa. Utiliza formato Markdown en tus respuestas escritas."
    )

    # 1. Recuperar el contexto de los últimos 15 mensajes del chat
    history = db.get_chat_history(user_id=user_id, limit=15)
    
    # Construir lista de mensajes para el modelo
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Agregar el nuevo mensaje del usuario
    messages.append({"role": "user", "content": user_message})

    # Llamada inicial a OpenRouter
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    pending_side_effects = []
    
    # Ciclo para resolver llamadas a herramientas de forma recursiva
    while response_message.tool_calls:
        messages.append(response_message)
        
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            tool_output, side_effects = execute_tool(function_name, function_args)
            if side_effects:
                pending_side_effects.extend(side_effects)
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_output
            })
            
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            tools=TOOLS
        )
        response_message = response.choices[0].message

    final_text = response_message.content or "Procesamiento completado con éxito."

    return final_text, pending_side_effects
