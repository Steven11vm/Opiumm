import os
import logging
from datetime import datetime
import google.generativeai as genai

logging.basicConfig(level=logging.DEBUG)

# Modelos a probar en orden (algunos pueden no estar en tu región/cuenta)
GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-8b-latest",
    "gemini-1.5-pro-latest",
    "gemini-pro",
]


class CustomAI:
    def __init__(self, name="Opium", version="Pro 1.0"):
        self.name = name
        self.version = version
        self.history = []
        self._model = None
        self._model_index = 0
        self._initialize_client()

    def _get_api_key(self):
        """Lee la clave desde Config o directamente del entorno (importante en Vercel)."""
        from Config import Config
        key = (Config.GEMINI_API_KEY or "").strip()
        if key:
            return key
        return (os.environ.get("GEMINI_API_KEY") or "").strip()

    def _initialize_client(self, api_key=None):
        api_key = api_key or self._get_api_key()
        if not api_key:
            logging.warning("GEMINI_API_KEY no configurada. Usa .env o variables de entorno.")
            return
        if self._model_index >= len(GEMINI_MODELS):
            return
        genai.configure(api_key=api_key)
        model_name = GEMINI_MODELS[self._model_index]
        system_instruction = (
            "Eres Opium, asistente de música en español. Responde siempre en español. "
            "Si piden crear beats o música, indica que usen la Consola DJ en esta web (Avanzado o sección Consola DJ)."
        )
        try:
            try:
                self._model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
            except TypeError:
                self._model = genai.GenerativeModel(model_name)
            logging.info("Gemini API usando modelo: %s", model_name)
        except Exception as e:
            logging.warning("Modelo %s no disponible: %s", model_name, str(e))
            self._model = None

    def ensure_initialized(self):
        """En Vercel las env vars están en runtime: intentar de nuevo si aún no hay modelo."""
        if self._model:
            return
        key = os.environ.get("GEMINI_API_KEY") or self._get_api_key()
        if key:
            self._initialize_client(api_key=key.strip())

    def _try_next_model(self):
        """Cambiar al siguiente modelo de la lista (p. ej. tras un 404)."""
        self._model = None
        self._model_index += 1
        if self._model_index < len(GEMINI_MODELS):
            self._initialize_client()

    def greet_user(self):
        return f"Hola, soy {self.name}, tu asistente de música. Pregúntame lo que quieras."

    def wants_to_generate_music(self, user_input):
        """
        Detecta si el usuario pide crear/generar música o un beat.
        Devuelve None o un dict con style, mood, duration para /generate-beat.
        """
        t = (user_input or "").strip().lower()
        if not t:
            return None
        crear = (
            "crea" in t or "genera" in t or "generame" in t or "genérame" in t or "hazme" in t or "haz" in t
            or "quiero un" in t or "dame" in t or "pon" in t or "haz un" in t or "crealo" in t or "generalo" in t or "hazlo" in t
        )
        musica = (
            "beat" in t or "música" in t or "musica" in t or "canción" in t or "cancion" in t
            or "track" in t or "algo" in t or "ritmo" in t or "uno" in t
            or ("lo" in t and ("crea" in t or "genera" in t or "haz" in t))
        )
        artista = "artista" in t or "estilo" in t or "tipo" in t or "como" in t
        if not (crear and (musica or artista or "algo" in t)):
            return None
        style = "mix"
        if "rage" in t:
            style = "rage"
        elif "trap" in t:
            style = "trap"
        elif "electrónica" in t or "electronica" in t or "electro" in t:
            style = "electronic"
        elif "bleesd" in t:
            style = "bleesd"
        mood = "energetic"
        if "chill" in t or "tranquilo" in t or "relajad" in t:
            mood = "chill"
        elif "oscuro" in t or "dark" in t:
            mood = "dark"
        elif "eufóric" in t or "euphoric" in t:
            mood = "euphoric"
        duration = 60
        if "corto" in t or "poco" in t:
            duration = 30
        elif "largo" in t or "minuto" in t or "cambios" in t or "cambio" in t:
            duration = 90
        return {"style": style, "mood": mood, "duration": min(180, max(15, duration))}

    def _current_date_context_es(self):
        """Fecha y hora actual en español para que la IA no se equivoque al preguntar 'qué día es hoy'."""
        now = datetime.now()
        weekday = now.strftime("%A")  # Monday, Tuesday...
        weekdays_es = {
            "Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles",
            "Thursday": "jueves", "Friday": "viernes", "Saturday": "sábado", "Sunday": "domingo"
        }
        months_es = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
            7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        dia_semana = weekdays_es.get(weekday, weekday)
        mes = months_es.get(now.month, str(now.month))
        return f"{dia_semana.capitalize()}, {now.day} de {mes} de {now.year}"

    def chat(self, user_input):
        self.ensure_initialized()
        if not self._model:
            if os.environ.get("VERCEL") == "1":
                return "No está configurada la API de Gemini. En Vercel: Settings → Environment Variables → añade GEMINI_API_KEY (nombre exacto), guarda y haz Redeploy."
            return "No está configurada la API de Gemini. Añade GEMINI_API_KEY en .env (local) o en Environment Variables (Vercel)."

        try:
            fecha_actual = self._current_date_context_es()
            message_with_context = f"[La fecha actual del sistema es: {fecha_actual}. Usa siempre esta fecha cuando pregunten por el día de hoy.]\n\n{user_input}"
            self.history.append({"role": "user", "parts": [message_with_context]})
            response = self._model.generate_content(self.history)
            text = response.text if response.text else "(Sin respuesta)"
            self.history.append({"role": "model", "parts": [text]})
            logging.info("Gemini respondió correctamente")
            return text
        except Exception as e:
            err_str = str(e).lower()
            if "404" in err_str or "not found" in err_str:
                logging.warning("Modelo no disponible, probando siguiente: %s", e)
                if self.history and self.history[-1].get("role") == "user":
                    self.history.pop()
                self._try_next_model()
                if self._model:
                    return self.chat(user_input)
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                logging.warning("Cuota agotada en modelo %s, probando siguiente: %s", GEMINI_MODELS[max(0, self._model_index)], e)
                if self.history and self.history[-1].get("role") == "user":
                    self.history.pop()
                self._try_next_model()
                if self._model:
                    return self.chat(user_input)
                return (
                    "La cuota gratuita de Gemini AI está agotada por hoy. "
                    "Para seguir usando la IA, activa la facturación en "
                    "https://aistudio.google.com o intenta mañana con la misma clave."
                )
            logging.error(f"Error Gemini: {str(e)}")
            return f"Error al conectar con la IA: {str(e)}"
