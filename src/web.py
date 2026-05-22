import logging
from flask import Flask, render_template, jsonify
import src.db as db

# Configuración del servidor Flask
app = Flask(__name__)

# Configurar logs de Werkzeug/Flask para que no saturen la terminal
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

@app.route('/')
def home():
    """Sirve la interfaz del panel visual (Dashboard)."""
    return render_template("dashboard.html")

@app.route('/api/stats')
def api_stats():
    """Retorna estadísticas generales del sistema, base de datos y memoria."""
    try:
        # Obtener resumen financiero dinámico e histórico
        summary = db.get_financial_summary()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Cantidad de mensajes en la memoria de chat
            cursor.execute("SELECT COUNT(*) FROM chat_memory")
            chat_count = cursor.fetchone()[0]
            
            # Cantidad de gastos
            cursor.execute("SELECT COUNT(*) FROM expenses")
            expenses_count = cursor.fetchone()[0] or 0
            
            # Cantidad de ingresos
            cursor.execute("SELECT COUNT(*) FROM income")
            income_count = cursor.fetchone()[0] or 0
            
            # Cantidad de eventos programados
            cursor.execute("SELECT COUNT(*) FROM calendar")
            calendar_count = cursor.fetchone()[0]
            
        return jsonify({
            "status": "online",
            "db_connected": True,
            "chat_messages_count": chat_count,
            "expenses": {
                "count": expenses_count,
                "total": summary["total_expenses"]
            },
            "income": {
                "count": income_count,
                "total": summary["total_income"]
            },
            "net_balance": summary["net_balance"],
            "financial_summary": summary,
            "calendar": {
                "count": calendar_count
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "db_connected": False,
            "error_message": str(e)
        }), 500

@app.route('/api/expenses')
def api_expenses():
    """Retorna los últimos 50 gastos registrados."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT category, concept, amount, date_added FROM expenses ORDER BY date_added DESC LIMIT 50"
            )
            rows = cursor.fetchall()
            
        expenses_list = [dict(row) for row in rows]
        return jsonify(expenses_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/income')
def api_income():
    """Retorna los últimos 50 ingresos registrados."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT category, concept, amount, date_added FROM income ORDER BY date_added DESC LIMIT 50"
            )
            rows = cursor.fetchall()
            
        income_list = [dict(row) for row in rows]
        return jsonify(income_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/calendar')
def api_calendar():
    """Retorna los eventos de la agenda (ordenados por fecha)."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Seleccionar eventos futuros o todos ordenados por fecha
            cursor.execute(
                "SELECT title, start_time FROM calendar ORDER BY start_time ASC LIMIT 50"
            )
            rows = cursor.fetchall()
            
        events_list = [dict(row) for row in rows]
        return jsonify(events_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """Retorna los últimos 20 registros del historial de chat."""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, timestamp FROM chat_memory ORDER BY id DESC LIMIT 20"
            )
            rows = cursor.fetchall()
            
        chat_logs = [dict(row) for row in rows]
        return jsonify(chat_logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_server(host="0.0.0.0", port=5050):
    """Inicializa la ejecución del servidor web Flask."""
    app.run(host=host, port=port, debug=False, use_reloader=False)
