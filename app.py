from flask import Flask, render_template, request, jsonify
from custom_ai import CustomAI  # Importamos CustomAI de nuestro archivo custom_ai.py

app = Flask(__name__, static_folder='static')
ai_assistant = CustomAI()  # Creamos una instancia de CustomAI

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/IAgotic')
def sobre_la_ia():
    greeting = ai_assistant.greet_user()
    return render_template('IAgotic.html', greeting=greeting)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.form.get('user_input')
        
        # Validación de la entrada del usuario
        if not user_input:
            return jsonify({"error": "No se proporcionó ninguna entrada."}), 400
        
        # Obtener la respuesta de la IA
        response = ai_assistant.chat(user_input)
        
        # Verificar si se recibió una respuesta válida
        if not response:
            return jsonify({"error": "No se pudo obtener una respuesta de la IA."}), 500
        
        return jsonify({"response": response})
    
    except Exception as e:
        return jsonify({"error": f"Se produjo un error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
