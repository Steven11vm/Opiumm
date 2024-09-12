import os
import uuid
import logging
from flask import Flask, render_template, request, jsonify, send_file
from pydub import AudioSegment
from pydub.generators import Sine, Square
from pydub.utils import which
from Config import Config
from custom_ai import CustomAI

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='static')
ai_assistant = CustomAI()

# Asegurarse de que pydub pueda encontrar FFmpeg
AudioSegment.converter = which("ffmpeg")


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
@app.route('/generate-beat', methods=['POST'])
def generate_beat():
    try:
        # Obtener los datos del formulario
        style = request.form.get('style')
        duration = request.form.get('duration')
        bpm = request.form.get('bpm')
        mood = request.form.get('mood')

        # Validar que los campos estén presentes
        if not style or not duration or not bpm:
            return jsonify({"error": "Faltan datos en el formulario"}), 400

        # Convertir los valores a enteros
        duration = int(duration)
        bpm = int(bpm)

        # Generar el nombre y la ruta del archivo
        file_name = f"{uuid.uuid4()}.wav"  # Cambiar extensión a .wav
        file_path = os.path.join('static', 'beats', file_name)
        print(f"Ruta del archivo: {file_path}")  # Depuración

        # Asegúrate de que el directorio donde se guardará el archivo existe
        directory = os.path.dirname(file_path)
        print(f"Directorio de destino: {directory}")  # Depuración
        os.makedirs(directory, exist_ok=True)

        # Crear un beat básico con pydub
        beat = AudioSegment.silent(duration=duration * 1000)  # Duración en milisegundos
        tone = Sine(440)  # Frecuencia de ejemplo (tono A4)
        beat = beat.overlay(tone.to_audio_segment(duration=duration * 1000))

        # Añadir un ritmo simple basado en el BPM
        kick = Square(60).to_audio_segment(duration=100).apply_gain(10)
        for i in range(0, duration * 1000, int(60000 / bpm)):  # Ajustar según el BPM
            beat = beat.overlay(kick, position=i)

        # Guardar el archivo generado como WAV
        print(f"Guardando beat en: {file_path}")  # Depuración
        beat.export(file_path, format="wav")

        # Verificar si el archivo WAV está vacío
        if os.path.getsize(file_path) == 0:
            raise ValueError("El archivo WAV generado está vacío.")

        # Retornar la respuesta con el nombre del archivo generado
        return jsonify({
            "message": "Beat generado con éxito",
            "filename": file_name
        })

    except Exception as e:
        logging.error(f"Error al generar el beat: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error al generar el beat: {str(e)}"}), 500


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
