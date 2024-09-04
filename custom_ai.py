import google.generativeai as genai
from config import Config

class CustomAI:
    def __init__(self, name="Opium", version="Pro 1.0"):
        self.name = name
        self.version = version
        self._initialize_client()

    def _initialize_client(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)

    def greet_user(self):
        return f"Hola, soy {self.name}, tu asistente de inteligencia artificial gótica."

    def chat(self, user_input):
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(user_input)
            return response.text
        except Exception as e:
            return f"Error al obtener respuesta de Gemini: {str(e)}"