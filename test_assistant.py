import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

# Añadir la raíz al path para poder importar src
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.config import DB_PATH, REPORTS_DIR
import src.db as db
import src.reports as reports

def setup_test_db():
    """Limpia la base de datos de pruebas si existe y la inicializa."""
    # Eliminar archivo DB existente para empezar limpios
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print("Base de datos anterior eliminada.")
        
    db.init_db()
    print("Base de datos inicializada.")

def run_tests():
    print("=== INICIANDO PRUEBAS DE INTEGRACIÓN LOCALES ===")
    
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
        assert history[0]["content"] == "Mensaje de prueba número 6", f"ERROR: El primer mensaje del historial debería ser el #6 (cronológico), es: {history[0]['content']}"
        assert history[-1]["content"] == "Mensaje de prueba número 20", f"ERROR: El último mensaje del historial debería ser el #20 (cronológico), es: {history[-1]['content']}"
        print("OK: Memoria de chat: Limites e historico cronologico correctos.")
        
        # --- PRUEBA 2: Modulo Financiero ---
        print("\n[Prueba 2] Verificando Modulo Financiero...")
        
        # Registrar gastos
        msg1 = db.add_expense(category="  ComiDa   ", concept="Almuerzo de trabajo", amount=150.75)
        msg2 = db.add_expense(category="transporte", concept="Gasolina camioneta", amount=500.00)
        msg3 = db.add_expense(category="comida", concept="Cena ligera", amount=85.50)
        
        print(f"   Log: {msg1}")
        print(f"   Log: {msg2}")
        print(f"   Log: {msg3}")
        
        # Validar categorías guardadas (deben estar homogeneizadas en minúsculas)
        all_expenses = db.get_all_expenses()
        assert len(all_expenses) == 3, f"ERROR: Deberían haber 3 gastos registrados, hay {len(all_expenses)}."
        assert all_expenses[0]["category"] == "comida", f"ERROR: La categoría debería estar en minúsculas 'comida', es: '{all_expenses[0]['category']}'"
        assert all_expenses[0]["amount"] == 150.75, f"ERROR: El monto debe ser flotante 150.75, es: {all_expenses[0]['amount']}"
        
        # Validar búsqueda con LIKE
        res_busqueda = db.search_expenses(keyword="camioneta")
        assert len(res_busqueda) == 1, f"ERROR: Debería encontrar 1 gasto para 'camioneta', encontró {len(res_busqueda)}."
        assert res_busqueda[0]["concept"] == "Gasolina camioneta", f"ERROR: Concepto no coincide."
        
        res_busqueda_cat = db.search_expenses(keyword="comida")
        assert len(res_busqueda_cat) == 2, f"ERROR: Debería encontrar 2 gastos bajo la categoría 'comida', encontró {len(res_busqueda_cat)}."
        
        print("OK: Registro de gastos: Normalizacion, tipado y consultas LIKE correctas.")
        
        # --- PRUEBA 3: Reportes de Excel ---
        print("\n[Prueba 3] Verificando Generacion de Reportes Excel...")
        report_res = reports.generate_expense_excel()
        
        assert report_res["status"] == "success", f"ERROR: La generación falló con mensaje: {report_res['message']}"
        file_path = Path(report_res["file_path"])
        assert file_path.exists(), f"ERROR: El archivo de Excel no se creó en la ruta {file_path}"
        assert file_path.suffix == ".xlsx", f"ERROR: El archivo no tiene extensión .xlsx: {file_path.suffix}"
        
        print(f"   Log: Archivo de Excel generado correctamente en: {file_path}")
        print("OK: Generador de reportes: Archivo Excel compilado con exito.")
        
        # --- PRUEBA 4: Agenda y Calendario ---
        print("\n[Prueba 4] Verificando Agenda y Calendario...")
        
        # Registrar eventos válidos
        msg_ev1 = db.add_calendar_event(title="Reunión de alineación de MVP", start_time="2026-05-22 10:00")
        msg_ev2 = db.add_calendar_event(title="Cena con inversionistas", start_time="2026-05-22 20:30")
        print(f"   Log: {msg_ev1}")
        print(f"   Log: {msg_ev2}")
        
        # Validar inserción incorrecta (debe fallar la validación de formato YYYY-MM-DD HH:MM)
        formato_invalido_exito = False
        try:
            db.add_calendar_event(title="Evento fallido", start_time="22-05-2026 10:00")
        except ValueError as e:
            formato_invalido_exito = True
            print(f"   Validación exitosa (capturada excepción esperada): {str(e)}")
            
        assert formato_invalido_exito, "ERROR: El sistema debió rechazar la fecha en formato '22-05-2026 10:00'."
        
        # Validar consulta de disponibilidad
        agenda_hoy = db.check_availability(date_str="2026-05-22")
        assert len(agenda_hoy) == 2, f"ERROR: Deberían retornar 2 eventos para el 2026-05-22, retornó {len(agenda_hoy)}."
        assert agenda_hoy[0]["title"] == "Reunión de alineación de MVP", f"ERROR: El primer evento no coincide."
        
        agenda_libre = db.check_availability(date_str="2026-05-23")
        assert len(agenda_libre) == 0, f"ERROR: No debería haber eventos para el 2026-05-23, se encontraron {len(agenda_libre)}."
        
        # Validar formato de fecha incorrecto al consultar disponibilidad
        consulta_invalida_exito = False
        try:
            db.check_availability(date_str="22/05/2026")
        except ValueError as e:
            consulta_invalida_exito = True
            print(f"   Validación exitosa (capturada excepción esperada): {str(e)}")
            
        assert consulta_invalida_exito, "ERROR: El sistema debió rechazar la fecha '22/05/2026' en la consulta."
        
        print("OK: Agenda y calendario: Inserciones, validaciones de formato y consultas correctas.")
        
        # --- PRUEBA 5: Búsqueda Web ---
        print("\n[Prueba 5] Verificando Busqueda Web (DuckDuckGo)...")
        from duckduckgo_search import DDGS
        results = []
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text("python", max_results=2))
                if results:
                    break
            except Exception as search_err:
                print(f"   Aviso: Intento {attempt + 1} de busqueda fallido ({search_err}). Reintentando...")
        assert len(results) > 0, "ERROR: La busqueda web no retorno ningun resultado despues de 3 intentos."
        print(f"   Log: Primer resultado: {results[0]['title']}")
        print("OK: Busqueda web: DuckDuckGo funcionando correctamente.")
        
        # --- PRUEBA 6: Servidor Web Flask ---
        print("\n[Prueba 6] Verificando Endpoints del Servidor Flask...")
        from src.web import app
        flask_test_client = app.test_client()
        
        # Probar GET /api/stats
        res_stats = flask_test_client.get('/api/stats')
        assert res_stats.status_code == 200, f"ERROR: /api/stats retorno codigo {res_stats.status_code}"
        stats_json = res_stats.get_json()
        assert stats_json["db_connected"] is True, "ERROR: La API no detecta conexion a base de datos."
        assert stats_json["expenses"]["count"] == 3, f"ERROR: Cantidad de gastos incorrecta, esperados 3, obtenidos {stats_json['expenses']['count']}"
        
        # Probar GET /api/expenses
        res_exp = flask_test_client.get('/api/expenses')
        assert res_exp.status_code == 200, f"ERROR: /api/expenses retorno codigo {res_exp.status_code}"
        assert len(res_exp.get_json()) == 3, "ERROR: Deberian haber 3 gastos en la lista JSON."
        
        # Probar GET / (Dashboard UI)
        res_home = flask_test_client.get('/')
        assert res_home.status_code == 200, f"ERROR: / (home) retorno codigo {res_home.status_code}"
        
        print("OK: Servidor Flask: Endpoints de API y plantilla HTML funcionando.")
        
        print("\n=== TODAS LAS PRUEBAS SE COMPLETARON CON EXITO ===")
        
    except Exception as e:
        print(f"\nERROR CRITICO EN PRUEBAS: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
