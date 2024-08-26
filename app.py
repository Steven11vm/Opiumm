from flask import Flask, render_template

# Crear la instancia de la aplicación Flask
app = Flask(__name__)
app = Flask(__name__, static_folder='static')

# Definir la ruta para la página principal
@app.route('/')
def index():
    return render_template('index.html')

# Ejecutar la aplicación si este archivo es el principal
if __name__ == '__main__':
    app.run(debug=True)
