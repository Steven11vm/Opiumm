"""
Opium — Aplicación Flask
Backend endurecido: headers de seguridad estrictos, rate-limit, validación,
manejo de errores sin fugas de información y páginas de error personalizadas.
"""
import io
import os
import re
import time
import uuid
import base64
import logging
import secrets
import threading
from pathlib import Path
from collections import deque

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from flask import (
    Flask, render_template, request, jsonify, send_file,
    send_from_directory, Response, abort, g,
)
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from pydub.generators import Sine, Square
from pydub.utils import which

from Config import Config
from custom_ai import CustomAI

# ------------------------------------------------------------------ #
#  Configuración / logging
# ------------------------------------------------------------------ #
IS_VERCEL = os.environ.get("VERCEL") == "1"
IS_DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1" and not IS_VERCEL

logging.basicConfig(
    level=logging.INFO if not IS_DEBUG else logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("opium")

# ------------------------------------------------------------------ #
#  Flask
# ------------------------------------------------------------------ #
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.from_object(Config)
app.config.update(
    MAX_CONTENT_LENGTH=25 * 1024 * 1024,           # 25 MB por request
    SEND_FILE_MAX_AGE_DEFAULT=60 * 60 * 24 * 7,    # 7 días de cache estático
    JSON_SORT_KEYS=False,
    PREFERRED_URL_SCHEME="https",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=not IS_DEBUG,
    SESSION_COOKIE_SAMESITE="Lax",
)

ai_assistant = CustomAI()
if not (Config.GEMINI_API_KEY or "").strip():
    log.warning("GEMINI_API_KEY vacía. Crea .env con GEMINI_API_KEY=tu_clave")
else:
    log.info("GEMINI_API_KEY cargada correctamente")

# ------------------------------------------------------------------ #
#  FFmpeg / ffprobe (pydub)
# ------------------------------------------------------------------ #
_ffmpeg = which("ffmpeg")
try:
    import imageio_ffmpeg
    _ffmpeg = _ffmpeg or imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    pass
if _ffmpeg:
    AudioSegment.converter = _ffmpeg

# ------------------------------------------------------------------ #
#  Constantes de validación
# ------------------------------------------------------------------ #
ALLOWED_STYLES = {"trap", "rage", "bleesd", "mix", "electronic"}
ALLOWED_MOODS = {"energetic", "chill", "dark", "euphoric"}
ALLOWED_AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,120}$")
MAX_CHAT_LEN = 4000
MIN_DURATION, MAX_DURATION = 5, 180

# ------------------------------------------------------------------ #
#  Rate limiting en memoria (por IP + endpoint)
# ------------------------------------------------------------------ #
_rl_lock = threading.Lock()
_rl_bucket: dict = {}

def _client_ip() -> str:
    # Solo confía en la cabecera si estamos detrás de un proxy conocido.
    if IS_VERCEL:
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"

def rate_limit(max_calls: int, window_sec: int):
    """Rate-limit por (IP, endpoint). Ligero, sin dependencias externas."""
    def decorator(fn):
        endpoint = fn.__name__

        def wrapper(*args, **kwargs):
            ip = _client_ip()
            key = f"{ip}:{endpoint}"
            now = time.time()
            with _rl_lock:
                q = _rl_bucket.setdefault(key, deque())
                while q and (now - q[0]) > window_sec:
                    q.popleft()
                if len(q) >= max_calls:
                    retry_after = int(window_sec - (now - q[0])) + 1
                    resp = jsonify({"error": "Demasiadas peticiones. Intenta más tarde."})
                    resp.status_code = 429
                    resp.headers["Retry-After"] = str(retry_after)
                    return resp
                q.append(now)
            return fn(*args, **kwargs)

        wrapper.__name__ = endpoint
        return wrapper
    return decorator

# ------------------------------------------------------------------ #
#  Utilidades de path seguras
# ------------------------------------------------------------------ #
def safe_join(base_dir: Path, filename: str) -> Path:
    """Une un base_dir con un filename garantizando que no se escapa el path."""
    name = secure_filename(filename or "")
    if not name or not SAFE_FILENAME_RE.match(name):
        abort(400, description="Nombre de archivo inválido")
    candidate = (base_dir / name).resolve()
    if base_dir.resolve() not in candidate.parents and candidate.parent != base_dir.resolve():
        abort(403, description="Ruta no permitida")
    return candidate

def _writable_dir(subdir: str) -> Path:
    if IS_VERCEL:
        d = Path("/tmp") / subdir
    else:
        d = BASE_DIR / "static" / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d

# ------------------------------------------------------------------ #
#  Seguridad: nonce por request + cabeceras
# ------------------------------------------------------------------ #
@app.before_request
def _security_context():
    g.csp_nonce = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
    g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
    g.request_start = time.time()

@app.context_processor
def _inject_csp_nonce():
    return {
        "csp_nonce": getattr(g, "csp_nonce", ""),
        "canonical_url": f"{request.headers.get('X-Forwarded-Proto', 'https')}://{request.host}{request.path}",
        "site_url": f"{request.headers.get('X-Forwarded-Proto', 'https')}://{request.host}",
    }

@app.after_request
def _apply_security_headers(resp: Response) -> Response:
    nonce = getattr(g, "csp_nonce", "")

    # CSP endurecida — permite fuentes de Google y estilos inline necesarios.
    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "worker-src 'self' blob:; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "upgrade-insecure-requests"
    )
    resp.headers.setdefault("Content-Security-Policy", csp)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()"
    )
    resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    resp.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    resp.headers.setdefault("X-DNS-Prefetch-Control", "off")
    if not IS_DEBUG:
        resp.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload"
        )
    # No cache de HTML dinámico
    if resp.mimetype == "text/html":
        resp.headers.setdefault("Cache-Control", "no-store")

    # Trazabilidad
    rid = getattr(g, "request_id", "")
    if rid:
        resp.headers["X-Request-Id"] = rid
    started = getattr(g, "request_start", None)
    if started:
        dur_ms = int((time.time() - started) * 1000)
        resp.headers["Server-Timing"] = f"app;dur={dur_ms}"
    return resp

# ------------------------------------------------------------------ #
#  Manejadores de error (páginas y JSON, sin fugas de traceback)
# ------------------------------------------------------------------ #
def _wants_json() -> bool:
    accept = request.accept_mimetypes
    return (
        request.path.startswith("/api/")
        or request.is_json
        or (accept["application/json"] >= accept["text/html"] and accept["application/json"] > 0)
    )

def _render_error(code: int, title: str, message: str):
    if _wants_json():
        resp = jsonify({"error": message, "code": code})
        resp.status_code = code
        return resp
    return render_template("error.html", code=code, title=title, message=message), code

@app.errorhandler(400)
def _e400(e):
    return _render_error(400, "Petición inválida",
                         getattr(e, "description", "La solicitud no es válida."))

@app.errorhandler(403)
def _e403(e):
    return _render_error(403, "Acceso denegado",
                         "No tienes permiso para acceder a este recurso.")

@app.errorhandler(404)
def _e404(e):
    return _render_error(404, "Página no encontrada",
                         "La página que buscas no existe o ha sido movida.")

@app.errorhandler(405)
def _e405(e):
    return _render_error(405, "Método no permitido",
                         "Este método HTTP no está permitido en esta ruta.")

@app.errorhandler(413)
def _e413(e):
    return _render_error(413, "Archivo demasiado grande",
                         "El archivo supera el tamaño máximo permitido (25 MB).")

@app.errorhandler(429)
def _e429(e):
    return _render_error(429, "Demasiadas peticiones",
                         "Has hecho demasiadas peticiones. Espera un momento.")

@app.errorhandler(500)
def _e500(e):
    log.exception("Error interno 500")
    return _render_error(500, "Error interno",
                         "Se produjo un error interno. Nuestro equipo ha sido notificado.")

@app.errorhandler(Exception)
def _handle_any(e):
    if isinstance(e, HTTPException):
        return _render_error(e.code or 500, e.name or "Error",
                             e.description or "Error.")
    log.exception("Excepción no manejada")
    return _render_error(500, "Error interno",
                         "Se produjo un error inesperado.")

# ------------------------------------------------------------------ #
#  Rutas: páginas
# ------------------------------------------------------------------ #
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/IAgotic")
def ia_gotic():
    return render_template("IAgotic.html", greeting=None)

@app.route("/dj-console")
def dj_console():
    return render_template("dj-console.html")

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(BASE_DIR / "static", "favicon.svg",
                               mimetype="image/svg+xml")

@app.route("/apple-touch-icon.png")
@app.route("/apple-touch-icon-precomposed.png")
def apple_touch_icon():
    return send_from_directory(BASE_DIR / "static", "apple-touch-icon.svg",
                               mimetype="image/svg+xml")

@app.route("/manifest.json")
@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(BASE_DIR / "static", "manifest.webmanifest",
                               mimetype="application/manifest+json")

@app.route("/robots.txt")
def robots():
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    host = request.host
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /generate-beat\n"
        "Disallow: /chat\n"
        "Disallow: /extract-instrumental\n"
        "Disallow: /download-beat/\n"
        "Disallow: /list-beats\n"
        "Disallow: /list-music\n"
        f"Sitemap: {scheme}://{host}/sitemap.xml\n"
    )
    resp = Response(body, mimetype="text/plain")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp

@app.route("/sitemap.xml")
def sitemap():
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    host = request.host
    urls = ["/", "/IAgotic", "/dj-console"]
    items = "\n".join(
        f"  <url>\n"
        f"    <loc>{scheme}://{host}{u}</loc>\n"
        f"    <changefreq>weekly</changefreq>\n"
        f"    <priority>{ '1.0' if u == '/' else '0.8' }</priority>\n"
        f"  </url>"
        for u in urls
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{items}\n"
        '</urlset>\n'
    )
    resp = Response(xml, mimetype="application/xml")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp

@app.route("/.well-known/security.txt")
@app.route("/security.txt")
def security_txt():
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    host = request.host
    from datetime import datetime, timezone, timedelta
    expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = (
        f"Contact: mailto:security@{host}\n"
        f"Expires: {expires}\n"
        f"Preferred-Languages: es, en\n"
        f"Canonical: {scheme}://{host}/.well-known/security.txt\n"
    )
    resp = Response(body, mimetype="text/plain")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "opium", "vercel": IS_VERCEL})

# ------------------------------------------------------------------ #
#  API: generación de beats
# ------------------------------------------------------------------ #
@app.route("/generate-beat", methods=["POST"])
@rate_limit(max_calls=10, window_sec=60)
def generate_beat():
    try:
        style = (request.form.get("style") or "").strip().lower()
        duration_raw = (request.form.get("duration") or "").strip()
        mood = (request.form.get("mood") or "").strip().lower()

        if style not in ALLOWED_STYLES:
            return jsonify({"error": "Estilo no válido"}), 400
        if mood not in ALLOWED_MOODS:
            return jsonify({"error": "Mood no válido"}), 400
        try:
            duration = int(duration_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "Duración inválida"}), 400
        duration = max(MIN_DURATION, min(MAX_DURATION, duration))

        file_name = f"{uuid.uuid4().hex}.wav"
        save_dir = _writable_dir("beats") if not IS_VERCEL else Path("/tmp")
        file_path = save_dir / file_name

        tone_freq, kick_duration, snare_duration = 440, 100, 50
        if mood == "energetic":
            tone_freq, kick_duration, snare_duration = 440, 80, 40
        elif mood == "chill":
            tone_freq, kick_duration, snare_duration = 220, 120, 70
        elif mood == "dark":
            tone_freq, kick_duration, snare_duration = 110, 180, 80
        elif mood == "euphoric":
            tone_freq, kick_duration, snare_duration = 880, 60, 50

        length_ms = duration * 1000
        beat = AudioSegment.silent(duration=length_ms)
        tone = Sine(tone_freq).to_audio_segment(duration=length_ms)
        beat = beat.overlay(tone)
        kick = Square(60).to_audio_segment(duration=kick_duration).apply_gain(10)
        snare = Square(30).to_audio_segment(duration=snare_duration).apply_gain(5)
        step = kick_duration + snare_duration
        for i in range(0, length_ms, step):
            beat = beat.overlay(kick, position=i)
            if (i + kick_duration) < length_ms:
                beat = beat.overlay(snare, position=i + kick_duration // 2)

        beat.export(str(file_path), format="wav")

        if IS_VERCEL:
            with open(file_path, "rb") as f:
                data = f.read()
            return Response(
                data, mimetype="audio/wav",
                headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
            )
        return jsonify({"message": "Beat generado con éxito", "filename": file_name})

    except Exception:
        log.exception("Error al generar beat")
        return jsonify({"error": "No se pudo generar el beat"}), 500

# ------------------------------------------------------------------ #
#  API: descargar beat (validación estricta de path)
# ------------------------------------------------------------------ #
@app.route("/download-beat/<path:filename>")
def download_beat(filename):
    beats_dir = BASE_DIR / "static" / "beats"
    file_path = safe_join(beats_dir, filename)
    if not file_path.is_file():
        abort(404)
    return send_file(str(file_path), as_attachment=True,
                     download_name=file_path.name)

# ------------------------------------------------------------------ #
#  API: listar biblioteca
# ------------------------------------------------------------------ #
def _list_audio(dir_name: str, url_prefix: str, kind: str):
    d = BASE_DIR / "static" / dir_name
    if not d.is_dir():
        return []
    items = []
    for entry in d.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in ALLOWED_AUDIO_EXTS:
            continue
        if not SAFE_FILENAME_RE.match(entry.name):
            continue
        items.append({
            "name": entry.name,
            "path": f"{url_prefix}/{entry.name}",
            "type": kind,
        })
    return items

@app.route("/list-beats", methods=["GET"])
def list_beats():
    return jsonify({"beats": [x["name"] for x in _list_audio("beats", "/static/beats", "beat")]})

@app.route("/list-music", methods=["GET"])
def list_music():
    return jsonify({
        "music": _list_audio("Music", "/static/Music", "music"),
        "beats": _list_audio("beats", "/static/beats", "beat"),
    })

# ------------------------------------------------------------------ #
#  API: chat
# ------------------------------------------------------------------ #
@app.route("/chat", methods=["POST"])
@rate_limit(max_calls=30, window_sec=60)
def chat():
    user_input = ""
    if request.is_json:
        try:
            payload = request.get_json(silent=True) or {}
            user_input = (payload.get("user_input") or "").strip()
        except Exception:
            user_input = ""
    if not user_input:
        user_input = (request.form.get("user_input") or "").strip()

    if not user_input:
        return jsonify({"error": "No se proporcionó ninguna entrada."}), 400
    if len(user_input) > MAX_CHAT_LEN:
        return jsonify({"error": f"Mensaje demasiado largo (máx {MAX_CHAT_LEN} caracteres)."}), 400

    try:
        trigger = ai_assistant.wants_to_generate_music(user_input)
        if trigger:
            return jsonify({
                "response": "Voy a crear tu beat ahora mismo. En un momento lo escuchas aquí.",
                "trigger_beat": {
                    "style": trigger["style"],
                    "mood": trigger["mood"],
                    "duration": trigger["duration"],
                },
            })
        response = ai_assistant.chat(user_input)
        if not response:
            return jsonify({"error": "No se pudo obtener una respuesta de la IA."}), 502
        return jsonify({"response": response})
    except Exception:
        log.exception("Error en /chat")
        return jsonify({"error": "Error al procesar tu mensaje."}), 500

# ------------------------------------------------------------------ #
#  API: extraer instrumental
# ------------------------------------------------------------------ #
@app.route("/extract-instrumental", methods=["POST"])
@rate_limit(max_calls=8, window_sec=60)
def extract_instrumental():
    song = request.form.get("song") or request.args.get("song") or ""
    music_dir = BASE_DIR / "static" / "Music"
    file_path = safe_join(music_dir, song)
    if file_path.suffix.lower() not in ALLOWED_AUDIO_EXTS:
        return jsonify({"error": "Formato no soportado"}), 400
    if not file_path.is_file():
        return jsonify({"error": "Canción no encontrada"}), 404

    try:
        audio = AudioSegment.from_file(str(file_path))
        if audio.channels < 2:
            return jsonify({"error": "La canción debe ser estéreo para extraer instrumental"}), 400
        left, right = audio.split_to_mono()
        instrumental = left.overlay(right.invert_phase())
        out_name = f"instrumental_{file_path.stem}.wav"
        if IS_VERCEL:
            buf = io.BytesIO()
            instrumental.export(buf, format="wav")
            buf.seek(0)
            return Response(
                buf.read(), mimetype="audio/wav",
                headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
            )
        save_dir = _writable_dir("beats")
        out_path = save_dir / out_name
        instrumental.export(str(out_path), format="wav")
        return send_file(str(out_path), as_attachment=True, download_name=out_name)
    except (FileNotFoundError, OSError) as e:
        if getattr(e, "errno", None) == 2 or "ffprobe" in str(e).lower() or "ffmpeg" in str(e).lower():
            log.warning("FFmpeg/ffprobe no disponible: %s", e)
            return jsonify({
                "error": "La extracción de vocales no está disponible en este servidor. "
                         "Instala FFmpeg localmente o usa un entorno que lo incluya."
            }), 503
        log.exception("Error al extraer instrumental (IO)")
        return jsonify({"error": "No se pudo procesar el audio"}), 500
    except Exception:
        log.exception("Error al extraer instrumental")
        return jsonify({"error": "No se pudo procesar el audio"}), 500

# ------------------------------------------------------------------ #
#  Ruta de salud simple para diagnósticos
# ------------------------------------------------------------------ #
@app.route("/test", methods=["GET"])
def test():
    return jsonify({"message": "Test OK", "ok": True})

# ------------------------------------------------------------------ #
if __name__ == "__main__":
    app.run(debug=IS_DEBUG, host="127.0.0.1", port=5000)
