from flask import Flask, render_template

# Crear la instancia de la aplicación Flask
app = Flask(__name__, static_folder='static')

# Definir la ruta para la página principal
@app.route('/')
def index():
    return render_template('index.html')

# Definir la ruta para la página "Sobre la IA"
@app.route('/IAgotic')
def sobre_la_ia():
    return render_template('IAgotic.html')

@app.route('/')
def home():
    return render_template('index.html')

# Ejecutar la aplicación si este archivo es el principal
if __name__ == '__main__':
    app.run(debug=True)
