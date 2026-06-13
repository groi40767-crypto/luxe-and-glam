import sqlite3
import urllib.parse
import requests
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = 'luxe_glam_secret_key_exclusivo_2026'

# --- FUNCIÓN CORREGIDA PARA OBTENER LA TASA REAL DE VENEZUELA (BCV) ---
def obtener_tasa_bcb_real():
    try:
        # Usamos un proveedor financiero global con datos en vivo actualizados a 2026
        url = "https://open.er-api.com/v6/latest/USD"
        respuesta = requests.get(url, timeout=5)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            tasa_oficial = float(datos['rates']['VES'])
            return round(tasa_oficial, 2)
    except Exception as e:
        print(f"No se pudo conectar a la API principal, usando respaldo: {e}")
    
    return 590.00  # RESPALDO ACTUALIZADO: Tasa real de emergencia si falla internet

# Inicializamos la tasa con el valor real del mercado actual
TASA_CAMBIO = obtener_tasa_bcb_real()

def conectar_db():
    conn = sqlite3.connect('tienda.db')
    conn.row_factory = sqlite3.Row
    return conn

def verificar_base_datos():
    conn = conectar_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL,
            imagen TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def inicio():
    global TASA_CAMBIO
    TASA_CAMBIO = obtener_tasa_bcb_real()
    
    conn = conectar_db()
    productos_db = conn.execute('SELECT * FROM productos').fetchall()
    conn.close()
    
    productos = []
    for p in productos_db:
        tonos_lista = None
        # Si la categoría contiene comas, significa que el administrador guardó tonos de maquillaje
        if ',' in p['categoria']:
            tonos_lista = p['categoria'].split(',')
            
        productos.append({
            'id': p['id'],
            'nombre': p['nombre'],
            'precio': p['precio'],
            'precio_bs': round(p['precio'] * TASA_CAMBIO, 2),
            'stock': p['stock'],
            'imagen': p['imagen'],
            'tonos': tonos_lista
        })
    
    total_articulos_carrito = sum(item['cantidad'] for item in session.get('carrito', {}).values())
    return render_template('index.html', productos=productos, tasa=TASA_CAMBIO, total_carrito=total_articulos_carrito)

@app.route('/agregar_al_carrito/<int:producto_id>')
def agregar_al_carrito(producto_id):
    if 'carrito' not in session:
        session['carrito'] = {}
        
    carrito = session['carrito']
    id_str = str(producto_id)
    
    conn = conectar_db()
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    conn.close()
    
    if producto:
        if id_str in carrito:
            carrito[id_str]['cantidad'] += 1
        else:
            carrito[id_str] = {
                'nombre': producto['nombre'],
                'precio': producto['precio'],
                'imagen': producto['imagen'],
                'cantidad': 1
            }
        session['carrito'] = carrito
        session.modified = True
        
    return redirect('/')

@app.route('/carrito')
def ver_carrito():
    carrito = session.get('carrito', {})
    total_usd = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    total_bs = total_usd * TASA_CAMBIO
    
    # RECUERDA: Coloca aquí tu número de teléfono real para WhatsApp (ej: 584121234567)
    TELEFONO_COMPRA = "584165665675" 
    
    texto_mensaje = "🛍️ *NUEVO PEDIDO EN LUXE & GLAM*\n\n"
    for item in carrito.values():
        texto_mensaje += f"• {item['nombre']} (Cant: {item['cantidad']}) - ${item['precio'] * item['cantidad']}\n"
    
    texto_mensaje += f"\n💵 *Total en USD:* ${round(total_usd, 2)}"
    texto_mensaje += f"\n🇻🇪 *Total en Bs.:* {round(total_bs, 2)} Bs."
    texto_mensaje += "\n\n¡Hola! Me gustaría coordinar el pago de este pedido. ✨"
    mensaje_codificado = urllib.parse.quote(texto_mensaje)
    link_whatsapp = f"https://wa.me/{TELEFONO_COMPRA}?text={mensaje_codificado}"
    
    return render_template('carrito.html', carrito=carrito, total_usd=total_usd, total_bs=total_bs, tasa=TASA_CAMBIO, link_whatsapp=link_whatsapp)

@app.route('/vaciar_carrito')
def vaciar_carrito():
    session.pop('carrito', None)
    return redirect('/carrito')

@app.route('/admin')
def admin():
    global TASA_CAMBIO
    TASA_CAMBIO = obtener_tasa_bcb_real()
    
    conn = conectar_db()
    productos = conn.execute('SELECT * FROM productos').fetchall()
    conn.close()
    return render_template('admin.html', productos=productos, tasa=TASA_CAMBIO)

@app.route('/admin/tasa', methods=['POST'])
def actualizar_tasa():
    global TASA_CAMBIO
    TASA_CAMBIO = float(request.form['tasa'])
    return redirect('/admin')

@app.route('/admin/agregar', methods=['POST'])
def agregar():
    nombre = request.form['nombre']
    categoria = request.form['categoria']
    
    # Si la categoría es maquillaje y se rellenó el campo de tonos, guardamos la lista de tonos como categoría
    if categoria == 'maquillaje' and request.form.get('tonos'):
        categoria = request.form['tonos']
        
    precio = float(request.form['precio'])
    stock = int(request.form['stock'])
    imagen = request.form['imagen']
    
    conn = conectar_db()
    conn.execute('INSERT INTO productos (nombre, categoria, precio, stock, imagen) VALUES (?, ?, ?, ?, ?)', 
                 (nombre, categoria, precio, stock, imagen))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/eliminar/<int:producto_id>')
def eliminar(producto_id):
    conn = conectar_db()
    conn.execute('DELETE FROM productos WHERE id = ?', (producto_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    verificar_base_datos()
    app.run(debug=True, host='0.0.0.0', port=8000)
