import json
from datetime import datetime
from openai import OpenAI
import src.db as db
import src.reports as reports
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
            "description": "Registra un nuevo gasto financiero en la base de datos local.",
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
            "name": "search_expenses",
            "description": "Busca transacciones y gastos históricos utilizando una palabra clave que coincida con el concepto o la categoría.",
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
            "name": "generate_expense_report",
            "description": "Compila y genera un reporte en formato Excel estructurado por categorías de todos los gastos y lo prepara para ser enviado al usuario.",
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
            "description": "Consulta el calendario de la agenda para una fecha específica (YYYY-MM-DD) para verificar si hay eventos programados.",
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

def execute_tool(name: str, arguments: dict) -> tuple[str, dict | None]:
    """
    Ejecuta localmente la función indicada y retorna el resultado de texto 
    junto con cualquier efecto secundario (como una ruta de archivo generada).
    """
    side_effect = None
    try:
        if name == "add_expense":
            result = db.add_expense(
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
        elif name == "generate_expense_report":
            report_result = reports.generate_expense_excel()
            if report_result["status"] == "success":
                side_effect = {"action": "send_document", "file_path": report_result["file_path"]}
                result = f"Reporte Excel generado con éxito y guardado en {report_result['file_path']}. El sistema procederá a enviártelo de inmediato."
            else:
                result = report_result["message"]
        elif name == "add_calendar_event":
            result = db.add_calendar_event(
                title=arguments.get("title"),
                start_time=arguments.get("start_time")
            )
        elif name == "check_availability":
            rows = db.check_availability(date_str=arguments.get("date_str"))
            if rows:
                result = f"Agenda para el {arguments.get('date_str')}:\n"
                for r in rows:
                    result += f"- {r['start_time'].split(' ')[1]}: {r['title']}\n"
            else:
                result = f"No hay eventos programados para el {arguments.get('date_str')}. Estás completamente libre."
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
        
    return result, side_effect

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
        "1. Módulo Financiero: Permite registrar gastos, buscar transacciones pasadas y generar reportes en Excel.\n"
        "2. Agenda y Calendario: Permite agendar eventos bloqueantes y verificar disponibilidad para fechas específicas.\n"
        "3. Búsqueda Web: Permite consultar información en tiempo real o hechos de actualidad en internet cuando sea necesario.\n\n"
        "REGLAS IMPORTANTES:\n"
        "- Toda la persistencia de datos ocurre en una base de datos local SQLite y los archivos Excel se compilan localmente.\n"
        f"- La fecha y hora actual en el servidor es: {current_time_str}.\n"
        "- Cuando el usuario haga referencias temporales relativas (como 'hoy', 'mañana', 'el lunes', 'ayer'), debes calcular la fecha exacta en base a la hora actual indicada arriba antes de llamar a las herramientas.\n"
        "- Para agendar eventos, es OBLIGATORIO que uses el formato de fecha y hora 'YYYY-MM-DD HH:MM'. Si el usuario no te da la hora, asume una hora prudente o pregúntale, pero nunca envíes un formato inválido a la herramienta.\n"
        "- Si el usuario te pide un reporte de gastos, debes invocar la herramienta 'generate_expense_report'. El bot interceptará la llamada y le enviará el archivo. Confírmale que lo estás enviando.\n"
        "- Si el usuario hace preguntas sobre hechos de actualidad, noticias recientes o cosas que requieran internet, invoca 'web_search'.\n"
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
        # Añadir la respuesta intermedia al historial de la API
        messages.append(response_message)
        
        # Procesar cada llamada a herramienta secuencialmente
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Ejecutar la herramienta local
            tool_output, side_effect = execute_tool(function_name, function_args)
            if side_effect:
                pending_side_effects.append(side_effect)
                
            # Añadir el resultado de la herramienta al flujo de mensajes de la API
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_output
            })
            
        # Llamar de nuevo a la API para enviar los resultados de las herramientas
        # y verificar si requiere más llamadas o da la respuesta final
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages,
            tools=TOOLS
        )
        response_message = response.choices[0].message

    # Garantizar que final_text no sea None
    final_text = response_message.content or "Procesamiento completado con éxito."

    return final_text, pending_side_effects
