import sqlite3
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

def crear_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


def inicializar_base_datos():
    conexion = sqlite3.connect('examen_usuarios.db')
    cursor = conexion.cursor()
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    
    cursor.execute('DELETE FROM usuarios')

    
    integrantes = [
        ("Shneider Chery", "cisco123"),
        ("Francisco Gatica", "redes2026"),
        
    ]

    
    for usuario, password in integrantes:
        cursor.execute(
            'INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)',
            (usuario, crear_hash(password))
        )
    
    conexion.commit()
    conexion.close()


@app.route('/validar', methods=['GET'])
def validar_usuario():
    user = request.args.get('usuario')
    pwd = request.args.get('password')

    if not user or not pwd:
        return jsonify({"Error": "Faltan datos de usuario o password"}), 400

    pwd_hash = crear_hash(pwd)

    conexion = sqlite3.connect('examen_usuarios.db')
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE usuario = ? AND password_hash = ?', (user, pwd_hash))
    resultado = cursor.fetchone()
    conexion.close()

    if resultado:
        return jsonify({"Mensaje": f"Validacion Exitosa. Bienvenido {user}."}), 200
    else:
        return jsonify({"Error": "Usuario o contraseña incorrectos."}), 401

if __name__ == '__main__':
    print("Inicializando base de datos...")
    inicializar_base_datos()
    print("Iniciando servidor web...")
    app.run(host='0.0.0.0', port=5800)
