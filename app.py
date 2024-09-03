from flask import Flask, render_template, request
import openai
import Config

app = Flask(__name__, static_folder='static')
app.config.from_object(Config.Config)

class GeminiPro:
    def __init__(self, name="Opium", version="Pro 1.0"):
        self.name = name
        self.version = version
        openai.api_key = app.config['OPENAI_API_KEY']  # Usa la clave de API desde la configuración

    def greet_user(self):
        return f"Hola, soy {self.name}, tu asistente de inteligencia artificial."

    def chat(self, user_input):
        return self.answer_question(user_input)

    def answer_question(self, question):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}],
                max_tokens=100
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            return f"Error al obtener respuesta de OpenAI: {e}"

# Crear una instancia de la IA GeminiPro
gemini = GeminiPro()

# Definir la ruta para la página principal
@app.route('/')
def index():
    return render_template('index.html')

# Definir la ruta para la página "Sobre la IA"
@app.route('/IAgotic')
def sobre_la_ia():
    greeting = gemini.greet_user()
    return render_template('IAgotic.html', greeting=greeting)

# Definir la ruta para interactuar con la IA
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('user_input')
    response = gemini.chat(user_input)
    return render_template('IAgotic.html', response=response)

# Ejecutar la aplicación si este archivo es el principal
if __name__ == '__main__':
    app.run(debug=True)
