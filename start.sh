#!/bin/bash
# Script de inicio persistente y auto-actualizable para el Asistente de IA (Linux/Termux)

# Obtener la ruta del directorio del script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================="
echo "🤖 Iniciando Demonio del Asistente de IA..."
echo "=========================================="

while true; do
    echo "------------------------------------------"
    echo "🔄 Comprobando actualizaciones en Git (timeout 5s)..."
    
    # Intentar descargar cabeceras de git de forma segura
    if git fetch --timeout=5 origin >/dev/null 2>&1; then
        LOCAL=$(git rev-parse HEAD)
        REMOTE=$(git rev-parse @{u} 2>/dev/null)
        
        if [ "$LOCAL" != "$REMOTE" ] && [ ! -z "$REMOTE" ]; then
            echo "🆕 ¡Nueva versión detectada en el repositorio remoto!"
            echo "Descargando actualizaciones mediante git pull..."
            if git pull; then
                echo "✅ Código actualizado."
                
                # Activar venv para instalar dependencias actualizadas
                if [ -d "venv" ]; then
                    source venv/bin/activate
                elif [ -d ".venv" ]; then
                    source .venv/bin/activate
                fi
                
                if [ -f "requirements.txt" ]; then
                    echo "📦 Actualizando dependencias desde requirements.txt..."
                    pip install --upgrade -r requirements.txt
                fi
            else
                echo "⚠️ Error al actualizar mediante git pull. Continuando con versión local..."
            fi
        else
            echo "✅ El asistente ya está en la versión más reciente."
        fi
    else
        echo "🌐 No se pudo conectar al repositorio remoto (sin internet o sin upstream). Continuando..."
    fi

    # Buscar y activar el entorno virtual para la ejecución
    if [ -d "venv" ]; then
        echo "Activo entorno virtual 'venv'..."
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        echo "Activo entorno virtual '.venv'..."
        source .venv/bin/activate
    else
        echo "⚠️ Advertencia: No se encontró venv/.venv. Usando Python del sistema."
    fi

    echo "🚀 Arrancando Asistente de IA (main.py)..."
    python main.py
    
    echo "⚠️ El proceso de main.py ha finalizado."
    echo "🔄 Reiniciando en 5 segundos... (Presiona Ctrl+C para cancelar)"
    sleep 5
done
