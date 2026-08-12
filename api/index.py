"""
Entry point para Vercel serverless.
Importa la app Flask desde el directorio raíz.
"""
import sys
import os

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
