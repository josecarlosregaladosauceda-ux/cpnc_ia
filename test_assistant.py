import sys
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Añadir la raíz al path para poder importar src
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.config import DB_PATH, REPORTS_DIR
import src.db as db
import src.reports as reports
import src.visuals as visuals
from main import check_pending_events_in_db, mark_event_as_notified

def setup_test_db():
    """Limpia la base de datos de pruebas si existe y la inicializa."""
    # Eliminar archivo DB existente para empezar limpios
    if DB_PATH.exists():
        try:
            os.remove(DB_PATH)
            print("Base de datos anterior eliminada.")
        except PermissionError:
            print("No se pudo eliminar la BD anterior, probablemente está bloqueada por otro proceso.")
        
    db.init_db()
    print("Base de datos inicializada.")

def run_tests():
    print("=== INICIANDO PRUEBAS DE INTEGRACIÓN LOCALES V3 ===")
    
    try:
        # Configurar ambiente limpio
        setup_test_db()
        
        # --- PRUEBA 1: Memoria de Chat ---
        print("\n[Prueba 1] Verificando Memoria de Chat...")
        user_id = 999999
        
        # Insertar 20 mensajes (más del límite de 15)
        for i in range(1, 21):
            role = "user" if i % 2 != 0 else "assistant"
            db.add_chat_message(user_id=user_id, role=role, content=f"Mensaje de prueba número {i}")
            
        history = db.get_chat_history(user_id=user_id, limit=15)
        
        # Validaciones de memoria
        assert len(history) == 15, f"ERROR: Debería retornar solo 15 mensajes, retornó {len(history)}."
        assert history[0]["content"] == "Mensaje de prueba número 6", f"ERROR: El primer mensaje del historial debería ser el #6, es: {history[0]['content']}"
        assert history[-1]["content"] == "Mensaje de prueba número 20", f"ERROR: El último mensaje debería ser el #20, es: {history[-1]['content']}"
        print("OK: Memoria de chat funcionando correctamente.")
        
        # --- PRUEBA 2: Módulo Financiero (Gastos e Ingresos) ---
        print("\n[Prueba 2] Verificando Módulo Financiero...")
        
        # Registrar gastos
        db.add_expense(category="  ComiDa   ", concept="Almuerzo de trabajo", amount=150.75)
        db.add_expense(category="transporte", concept="Gasolina camioneta", amount=500.00)
        
        # Registrar ingresos
        db.add_income(category="   Trabajo  ", concept="Pago quincena", amount=2500.00)
        db.add_income(category="ventas", concept="Venta de audífonos", amount=350.00)
        
        # Escalonar las fechas de las transacciones para simular tiempo de producción
        # (necesario porque SQLite CURRENT_TIMESTAMP usa precisión por segundos)
        conn = db.get_connection()
        cursor = conn.cursor()
        now_utc = datetime.utcnow()
        cursor.execute(
            "UPDATE expenses SET date_added = ? WHERE concept = 'Almuerzo de trabajo'",
            ((now_utc - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),)
        )
        cursor.execute(
            "UPDATE expenses SET date_added = ? WHERE concept = 'Gasolina camioneta'",
            ((now_utc - timedelta(minutes=8)).strftime("%Y-%m-%d %H:%M:%S"),)
        )
        cursor.execute(
            "UPDATE income SET date_added = ? WHERE concept = 'Pago quincena'",
            ((now_utc - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),)
        )
        cursor.execute(
            "UPDATE income SET date_added = ? WHERE concept = 'Venta de audífonos'",
            ((now_utc - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S"),)
        )
        conn.commit()
        conn.close()
        
        # Validar gastos
        all_expenses = db.get_all_expenses()
        assert len(all_expenses) == 2, f"ERROR: Esperados 2 gastos, obtenidos {len(all_expenses)}."
        assert all_expenses[0]["category"] == "comida", "ERROR: La categoría del gasto no se normalizó."
        assert all_expenses[0]["amount"] == 150.75
        
        # Validar ingresos
        all_income = db.get_all_income()
        assert len(all_income) == 2, f"ERROR: Esperados 2 ingresos, obtenidos {len(all_income)}."
        assert all_income[0]["category"] == "trabajo", "ERROR: La categoría del ingreso no se normalizó."
        assert all_income[0]["amount"] == 2500.00
        
        # Validar búsquedas con LIKE para ingresos y gastos
        res_busqueda_exp = db.search_expenses(keyword="camioneta")
        assert len(res_busqueda_exp) == 1, "ERROR: Búsqueda de gastos falló."
        
        res_busqueda_inc = db.search_income(keyword="audífonos")
        assert len(res_busqueda_inc) == 1, "ERROR: Búsqueda de ingresos falló."
        
        # Validar cálculo de balance dinámico basado en último depósito (get_financial_summary)
        summary = db.get_financial_summary()
        assert summary["last_deposit_amount"] == 350.00, f"ERROR: Esperado 350.00, obtenido {summary['last_deposit_amount']}"
        assert summary["period_income"] == 350.00, f"ERROR: Esperado ingresos de período 350.00, obtenido {summary['period_income']}"
        # Los gastos se registraron antes de la fecha del último ingreso, por lo que los gastos del período deben ser 0.0
        assert summary["period_expenses"] == 0.0, f"ERROR: Esperados gastos de período 0.0, obtenidos {summary['period_expenses']}"
        
        # Agregar gasto temporal en el período actual
        db.add_expense(category="comida", concept="Gasto temporal de prueba", amount=50.00)
        summary2 = db.get_financial_summary()
        assert summary2["period_expenses"] == 50.00, f"ERROR: Esperado gastos del período 50.00, obtenido {summary2['period_expenses']}"
        assert summary2["period_balance"] == 300.00
        
        # Eliminar el gasto temporal para no alterar las pruebas posteriores
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE concept = 'Gasto temporal de prueba'")
        conn.commit()
        conn.close()
        
        print("OK: Módulo financiero y cálculos del período dinámico funcionan correctamente en BD.")
        
        # --- PRUEBA 3: Reportes de Excel y Visuales ---
        print("\n[Prueba 3] Verificando Reportes en Excel e Imágenes...")
        
        # Generación de Excel unificado
        report_res = reports.generate_financial_excel()
        assert report_res["status"] == "success", f"ERROR: {report_res['message']}"
        excel_path = Path(report_res["file_path"])
        assert excel_path.exists(), "ERROR: El archivo de Excel no fue creado."
        print(f"   Log: Excel creado en: {excel_path}")
        
        # Generación de imagen de gráfico financiero
        img_chart_path = Path(visuals.generate_financial_chart_image(all_expenses, 2850.00, 650.75))
        assert img_chart_path.exists(), "ERROR: La imagen del gráfico financiero no fue creada."
        print(f"   Log: Gráfico financiero en: {img_chart_path}")
        
        print("OK: Generación de Excel unificado y gráfico financiero en imagen correctos.")
        
        # --- PRUEBA 4: Agenda, Calendario y Notificaciones ---
        print("\n[Prueba 4] Verificando Agenda, Calendario y Notificaciones...")
        
        # Registrar evento para hoy
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        db.add_calendar_event(title="Reunión diaria V3", start_time=f"{tomorrow_str} 09:30")
        
        # Comprobar disponibilidad
        agenda = db.check_availability(date_str=tomorrow_str)
        assert len(agenda) == 1, "ERROR: No se encontró el evento agendado."
        
        # Generar imagen de agenda diaria
        img_agenda_path = Path(visuals.generate_agenda_image(agenda, tomorrow_str))
        assert img_agenda_path.exists(), "ERROR: La imagen de la agenda no fue creada."
        print(f"   Log: Agenda visual en: {img_agenda_path}")
        
        # Probar lógica de recordatorios (Programar evento en 10 minutos en el futuro)
        reminder_time = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
        db.add_calendar_event(title="Recordatorio agua", start_time=reminder_time)
        
        # Verificar que el recordatorio está pendiente y es detectado
        pending_events = check_pending_events_in_db()
        # Debe haber al menos el evento de "Recordatorio agua"
        water_reminders = [e for e in pending_events if e["title"] == "Recordatorio agua"]
        assert len(water_reminders) == 1, "ERROR: El recordatorio programado a 10 minutos no fue detectado."
        
        # Marcar como notificado
        event_id = water_reminders[0]["id"]
        mark_event_as_notified(event_id)
        
        # Volver a verificar (ya no debe ser detectado porque notified = 1)
        pending_after = check_pending_events_in_db()
        water_reminders_after = [e for e in pending_after if e["title"] == "Recordatorio agua"]
        assert len(water_reminders_after) == 0, "ERROR: El recordatorio sigue detectándose tras ser notificado."
        
        print("OK: Módulo de agenda, imagen visual y recordatorios proactivos funcionando correctamente.")
        
        # --- PRUEBA 5: Búsqueda Web ---
        print("\n[Prueba 5] Verificando Búsqueda Web (DuckDuckGo)...")
        from duckduckgo_search import DDGS
        results = []
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text("python programming", max_results=2))
                if results:
                    break
            except Exception as search_err:
                print(f"   Aviso: Intento {attempt + 1} fallido ({search_err}). Reintentando...")
        assert len(results) > 0, "ERROR: La búsqueda en la web no retornó resultados."
        print(f"   Log: Primer título de búsqueda: {results[0]['title']}")
        print("OK: Búsqueda en DuckDuckGo funcionando correctamente.")
        
        # --- PRUEBA 6: Servidor Web Flask ---
        print("\n[Prueba 6] Verificando Endpoints de Flask Actualizados...")
        from src.web import app
        flask_test_client = app.test_client()
        
        # Probar GET /api/stats
        res_stats = flask_test_client.get('/api/stats')
        assert res_stats.status_code == 200, f"ERROR: /api/stats retorno código {res_stats.status_code}"
        stats_json = res_stats.get_json()
        assert stats_json["db_connected"] is True
        assert stats_json["expenses"]["count"] == 2
        assert stats_json["income"]["count"] == 2
        # Balance = Ingresos (2850.0) - Gastos (650.75) = 2199.25
        assert stats_json["net_balance"] == 2199.25, f"ERROR: Balance neto esperado 2199.25, obtenido {stats_json['net_balance']}"
        
        # Probar GET /api/income
        res_inc = flask_test_client.get('/api/income')
        assert res_inc.status_code == 200
        assert len(res_inc.get_json()) == 2
        
        # Probar GET /api/expenses
        res_exp = flask_test_client.get('/api/expenses')
        assert res_exp.status_code == 200
        assert len(res_exp.get_json()) == 2
        
        print("OK: Endpoints de API Flask (ingresos/gastos/balance/stats) correctos.")
        
        print("\n=== TODAS LAS PRUEBAS DE LA V3 PASARON CON ÉXITO ===")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO EN LAS PRUEBAS: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
