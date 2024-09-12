import os
import uuid
import logging
import traceback
from flask import Flask, render_template, request, jsonify, send_file
from pydub import AudioSegment
from pydub.generators import Sine, Square
from pydub.utils import which
import librosa
from Config import Config
from custom_ai import CustomAI

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)  # Cambiar a DEBUG para obtener más detalles

# Inicialización de Flask
app = Flask(__name__, static_folder='static')
app.config.from_object(Config)
ai_assistant = CustomAI()

# Asegúrate de que pydub pueda encontrar FFmpeg
AudioSegment.converter = which("ffmpeg")

@app.route('/generate-beat', methods=['POST'])
def generate_beat():
    try:
        # Obtener los datos del formulario
        style = request.form.get('style')
        duration = request.form.get('duration')
        mood = request.form.get('mood')

        # Validar que los campos estén presentes
        if not style or not duration or not mood:
            return jsonify({"error": "Faltan datos en el formulario"}), 400

        # Convertir la duración a entero
        try:
            duration = int(duration)
        except ValueError:
            return jsonify({"error": "Duración inválida"}), 400

        # Generar el nombre y la ruta del archivo
        file_name = f"{uuid.uuid4()}.wav"
        file_path = os.path.join('static', 'beats', file_name)
        logging.debug(f"Ruta del archivo: {file_path}")

        # Crear un beat básico con pydub
        beat = AudioSegment.silent(duration=duration * 1000)  # Duración en milisegundos

        # Ajustar el beat según el estilo
        tone_freq = 440  # Frecuencia por defecto
        kick_duration = 100
        snare_duration = 50

        if style == "energetic":
            tone_freq = 440
            kick_duration = 80
            snare_duration = 40
        elif style == "chill":
            tone_freq = 220
            kick_duration = 120
            snare_duration = 70
        elif style == "dark":
            tone_freq = 110
            kick_duration = 180
            snare_duration = 80
        elif style == "euphoric":
            tone_freq = 880
            kick_duration = 60
            snare_duration = 50

        tone = Sine(tone_freq).to_audio_segment(duration=duration * 1000)
        beat = beat.overlay(tone)

        kick = Square(60).to_audio_segment(duration=kick_duration).apply_gain(10)
        snare = Square(30).to_audio_segment(duration=snare_duration).apply_gain(5)

        # Añadir kick y snare al beat
        for i in range(0, duration * 1000, kick_duration + snare_duration):
            beat = beat.overlay(kick, position=i)
            if (i + kick_duration) < duration * 1000:
                beat = beat.overlay(snare, position=i + int(kick_duration / 2))

        # Guardar el archivo generado
        logging.debug(f"Guardando beat en: {file_path}")
        beat.export(file_path, format="wav")

        # Retornar la respuesta con el nombre del archivo generado
        return jsonify({
            "message": "Beat generado con éxito",
            "filename": file_name
        })

    except ValueError as e:
        logging.error(f"Error de valor: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error de valor: {str(e)}"}), 400
    except EOFError as e:
        logging.error(f"Error EOF: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error EOF: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Error al generar el beat: {str(e)}", exc_info=True)
        return jsonify({
            "error": f"Error al generar el beat: {str(e)}",
            "details": traceback.format_exc()
        }), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/IAgotic')
def sobre_la_ia():
    greeting = ai_assistant.greet_user()
    return render_template('IAgotic.html', greeting=greeting)

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Test OK"})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.form.get('user_input')
        if not user_input:
            return jsonify({"error": "No se proporcionó ninguna entrada."}), 400
        
        response = ai_assistant.chat(user_input)
        if not response:
            return jsonify({"error": "No se pudo obtener una respuesta de la IA."}), 500
        
        return jsonify({"response": response})
    except Exception as e:
        logging.error(f"Error al procesar el chat: {str(e)}", exc_info=True)
        return jsonify({"error": f"Se produjo un error: {str(e)}"}), 500

@app.route('/download-beat/<filename>')
def download_beat(filename):
    try:
        return send_file(os.path.join('static', 'beats', filename), as_attachment=True)
    except Exception as e:
        logging.error(f"Error al descargar el beat: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error al descargar el beat: {str(e)}"}), 500

@app.route('/list-beats', methods=['GET'])
def list_beats():
    try:
        beats_dir = os.path.join('static', 'beats')
        beats = [f for f in os.listdir(beats_dir) if os.path.isfile(os.path.join(beats_dir, f))]
        return jsonify({"beats": beats})
    except Exception as e:
        logging.error(f"Error al listar los beats: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error al listar los beats: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
