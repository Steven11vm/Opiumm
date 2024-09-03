import openai
import Config

class GeminiPro:
    def __init__(self, name="Opium", version="Pro 1.0"):
        self.name = name
        self.version = version
        openai.api_key = Config.py['OPENAI_API_KEY']  # Usa la clave de API desde la configuración

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
