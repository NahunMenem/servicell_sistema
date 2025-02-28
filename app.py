from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Necesario para usar sesiones

# Función para conectar a la base de datos
def get_db_connection():
    conn = sqlite3.connect('negocio.db')
    conn.row_factory = sqlite3.Row
    return conn

# Ruta principal--------------------------------------
@app.route('/')
def index():
    return render_template('index.html')



# Ruta para registrar ventas---------------------------------------------
@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Inicializar el carrito en la sesión si no existe
    if 'carrito' not in session:
        session['carrito'] = []

    if request.method == 'POST':
        # Buscar producto por código de barras o nombre
        if 'buscar' in request.form:
            busqueda = request.form['busqueda']
            cursor.execute('''
            SELECT id, nombre, codigo_barras, stock, precio FROM productos
            WHERE codigo_barras = ? OR nombre LIKE ?
            ''', (busqueda, f'%{busqueda}%'))
            productos = cursor.fetchall()
            conn.close()
            return render_template('registrar_venta.html', productos=productos, carrito=session['carrito'])

        # Agregar producto al carrito (venta normal)
        elif 'agregar' in request.form:
            producto_id = request.form['producto_id']
            cantidad = int(request.form['cantidad'])

            # Obtener detalles del producto
            cursor.execute('SELECT id, nombre, precio FROM productos WHERE id = ?', (producto_id,))
            producto = cursor.fetchone()

            if producto:
                # Verificar que el precio no sea None
                if producto['precio'] is not None:
                    # Agregar producto al carrito
                    item = {
                        'id': producto['id'],
                        'nombre': producto['nombre'],
                        'precio': producto['precio'],
                        'cantidad': cantidad
                    }
                    session['carrito'].append(item)
                    session.modified = True  # Marcar la sesión como modificada
                else:
                    conn.close()
                    return f"Error: El producto '{producto['nombre']}' no tiene un precio definido."
            else:
                conn.close()
                return "Error: Producto no encontrado."

        # Agregar venta manual al carrito
        elif 'agregar_manual' in request.form:
            nombre = request.form['nombre_manual']
            precio = float(request.form['precio_manual'])
            cantidad = int(request.form['cantidad_manual'])

            # Agregar venta manual al carrito
            item = {
                'id': None,  # No tiene ID porque no está en el stock
                'nombre': nombre,
                'precio': precio,
                'cantidad': cantidad
            }
            session['carrito'].append(item)
            session.modified = True  # Marcar la sesión como modificada

        # Registrar la venta (tanto normal como manual)
        elif 'registrar' in request.form:
            if not session['carrito']:
                conn.close()
                return "El carrito está vacío. Agrega productos antes de registrar la venta."

            # Obtener el tipo de pago y el DNI del cliente
            tipo_pago = request.form['tipo_pago']
            dni_cliente = request.form['dni_cliente']
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Registrar cada producto del carrito
            for item in session['carrito']:
                producto_id = item['id']
                nombre = item['nombre']
                precio = item['precio']
                cantidad = item['cantidad']

                if producto_id is not None:
                    # Verificar si hay suficiente stock (solo para productos en stock)
                    cursor.execute('SELECT stock FROM productos WHERE id = ?', (producto_id,))
                    producto = cursor.fetchone()

                    if producto and producto['stock'] >= cantidad:
                        # Registrar la venta en la tabla 'ventas'
                        cursor.execute('''
                        INSERT INTO ventas (producto_id, cantidad, fecha, nombre_manual, precio_manual, tipo_pago, dni_cliente)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (producto_id, cantidad, fecha_actual, None, None, tipo_pago, dni_cliente))

                        # Actualizar el stock
                        cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cantidad, producto_id))
                    else:
                        conn.close()
                        return f"No hay suficiente stock para el producto: {nombre}"
                else:
                    # Registrar venta manual en la tabla 'reparaciones'
                    cursor.execute('''
                    INSERT INTO reparaciones (nombre_servicio, precio, cantidad, tipo_pago, dni_cliente, fecha)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (nombre, precio, cantidad, tipo_pago, dni_cliente, fecha_actual))

            conn.commit()
            conn.close()
            session.pop('carrito', None)  # Vaciar el carrito después de registrar la venta
            return redirect(url_for('index'))

        # Vaciar el carrito
        elif 'vaciar' in request.form:
            session.pop('carrito', None)
            return redirect(url_for('registrar_venta'))

    # Calcular el total del carrito
    total = sum(item['precio'] * item['cantidad'] for item in session['carrito'])

    # Si es GET, mostrar el formulario de búsqueda
    conn.close()
    return render_template('registrar_venta.html', productos=None, carrito=session['carrito'], total=total)

# Ruta para productos por agotarse---------------------------------------------
@app.route('/productos_por_agotarse')
def productos_por_agotarse():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener productos con stock menor o igual a 2
    cursor.execute('''
    SELECT id, nombre, codigo_barras, stock, precio, precio_costo
    FROM productos
    WHERE stock <= 2
    ORDER BY stock ASC
    ''')
    productos = cursor.fetchall()

    conn.close()
    return render_template('productos_por_agotarse.html', productos=productos)



# Ruta para ver las últimas 10 ventas del día----------------------------
@app.route('/ultimas_ventas')
def ultimas_ventas():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la fecha actual
    fecha_actual = datetime.now().strftime('%Y-%m-%d')

    # Consultar las últimas 10 ventas del día
    cursor.execute('''
    SELECT v.id, p.nombre, v.cantidad, p.precio, v.fecha
    FROM ventas v
    JOIN productos p ON v.producto_id = p.id
    WHERE DATE(v.fecha) = ?
    ORDER BY v.fecha DESC
    LIMIT 10
    ''', (fecha_actual,))
    ventas = cursor.fetchall()

    # Consultar las últimas 10 reparaciones del día
    cursor.execute('''
    SELECT id, nombre_servicio AS nombre, 1 AS cantidad, precio, fecha
    FROM reparaciones
    WHERE DATE(fecha) = ?
    ORDER BY fecha DESC
    LIMIT 10
    ''', (fecha_actual,))
    reparaciones = cursor.fetchall()

    # Combinar ventas y reparaciones
    transacciones = ventas + reparaciones
    # Ordenar por fecha (de más reciente a más antigua)
    transacciones.sort(key=lambda x: x['fecha'], reverse=True)

    conn.close()
    return render_template('ultimas_ventas.html', transacciones=transacciones)



#ruta egresos----------------------------------------------------
@app.route('/egresos', methods=['GET', 'POST'])
def egresos():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Agregar un nuevo egreso
    if request.method == 'POST' and 'agregar' in request.form:
        fecha = request.form['fecha']
        monto = float(request.form['monto'])
        descripcion = request.form['descripcion']
        tipo_pago = request.form['tipo_pago']  # Nuevo campo

        cursor.execute('''
        INSERT INTO egresos (fecha, monto, descripcion, tipo_pago)
        VALUES (?, ?, ?, ?)
        ''', (fecha, monto, descripcion, tipo_pago))
        conn.commit()
        conn.close()
        return redirect(url_for('egresos'))

    # Eliminar un egreso
    if request.method == 'POST' and 'eliminar' in request.form:
        egreso_id = request.form['egreso_id']
        cursor.execute('DELETE FROM egresos WHERE id = ?', (egreso_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('egresos'))

    # Obtener todos los egresos
    cursor.execute('SELECT id, fecha, monto, descripcion, tipo_pago FROM egresos ORDER BY fecha DESC')
    egresos = cursor.fetchall()
    conn.close()
    return render_template('egresos.html', egresos=egresos)

from datetime import datetime, timedelta


#dashboard--------------------------------------------------
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la fecha de inicio y fin de la semana actual
    hoy = datetime.now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).strftime('%Y-%m-%d')  # Lunes de esta semana
    fin_semana = (hoy + timedelta(days=(6 - hoy.weekday()))).strftime('%Y-%m-%d')  # Domingo de esta semana

    # Calcular el total de ventas de la semana (productos + reparaciones)
    cursor.execute('''
    SELECT 
        SUM(v.cantidad * COALESCE(p.precio, v.precio_manual)) AS total_ventas_productos,
        SUM(r.precio) AS total_ventas_reparaciones
    FROM ventas v
    LEFT JOIN productos p ON v.producto_id = p.id
    LEFT JOIN reparaciones r ON DATE(r.fecha) BETWEEN ? AND ?
    WHERE DATE(v.fecha) BETWEEN ? AND ?
    ''', (inicio_semana, fin_semana, inicio_semana, fin_semana))
    
    result = cursor.fetchone()
    total_ventas_productos = result['total_ventas_productos'] or 0
    total_ventas_reparaciones = result['total_ventas_reparaciones'] or 0
    total_ventas = total_ventas_productos + total_ventas_reparaciones

    # Calcular el total de egresos de la semana
    cursor.execute('''
    SELECT SUM(monto) AS total_egresos
    FROM egresos
    WHERE DATE(fecha) BETWEEN ? AND ?
    ''', (inicio_semana, fin_semana))
    total_egresos = cursor.fetchone()['total_egresos'] or 0

    # Calcular el costo de los productos vendidos en la semana
    cursor.execute('''
    SELECT SUM(v.cantidad * p.precio_costo) AS total_costo
    FROM ventas v
    JOIN productos p ON v.producto_id = p.id
    WHERE DATE(v.fecha) BETWEEN ? AND ?
    ''', (inicio_semana, fin_semana))
    total_costo = cursor.fetchone()['total_costo'] or 0

    # Calcular la ganancia de la semana
    ganancia_semana = total_ventas - total_egresos - total_costo

    conn.close()
    return render_template('dashboard.html', 
                          total_ventas=total_ventas, 
                          total_egresos=total_egresos, 
                          total_costo=total_costo, 
                          ganancia_semana=ganancia_semana,
                          inicio_semana=inicio_semana,
                          fin_semana=fin_semana)



#ruta caja----------------------------------
from datetime import datetime, timedelta

@app.route('/caja')
def caja():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la fecha de inicio y fin de la semana actual
    hoy = datetime.now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).strftime('%Y-%m-%d')  # Lunes de esta semana
    fin_semana = (hoy + timedelta(days=(6 - hoy.weekday()))).strftime('%Y-%m-%d')  # Domingo de esta semana

    # Obtener total de ventas por tipo de pago (semana actual)
    cursor.execute('''
    SELECT tipo_pago, SUM(total) as total_ventas
    FROM ventas
    WHERE fecha BETWEEN ? AND ?
    GROUP BY tipo_pago
    ''', (inicio_semana, fin_semana))
    ventas_por_tipo = cursor.fetchall()

    # Obtener total de egresos por tipo de pago (semana actual)
    cursor.execute('''
    SELECT tipo_pago, SUM(monto) as total_egresos
    FROM egresos
    WHERE fecha BETWEEN ? AND ?
    GROUP BY tipo_pago
    ''', (inicio_semana, fin_semana))
    egresos_por_tipo = cursor.fetchall()

    # Convertir los resultados en diccionarios para facilitar el acceso
    ventas = {row['tipo_pago']: row['total_ventas'] for row in ventas_por_tipo}
    egresos = {row['tipo_pago']: row['total_egresos'] for row in egresos_por_tipo}

    # Definir los tipos de pago que manejamos
    tipos_pago = ['efectivo', 'transferencia', 'debito', 'credito']

    # Calcular los totales para cada tipo de pago
    totales = {}
    for tipo in tipos_pago:
        total_ventas = ventas.get(tipo, 0)
        total_egresos = egresos.get(tipo, 0)
        totales[tipo] = total_ventas - total_egresos

    # Calcular el total general
    total_general = sum(totales.values())

    conn.close()

    # Pasar los datos a la plantilla
    return render_template('caja.html', 
                          totales=totales,
                          ventas=ventas,  # Pasar la variable 'ventas'
                          egresos=egresos,  # Pasar la variable 'egresos'
                          total_general=total_general,
                          inicio_semana=inicio_semana,
                          fin_semana=fin_semana)


# Ruta para agregar stock-----------------------------------
@app.route('/agregar_stock', methods=['GET', 'POST'])
def agregar_stock():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener el término de búsqueda (si existe)
    busqueda = request.args.get('busqueda', '')

    # Eliminar un producto
    if request.method == 'POST' and 'eliminar' in request.form:
        producto_id = request.form['producto_id']
        cursor.execute('DELETE FROM productos WHERE id = ?', (producto_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('agregar_stock'))

    # Editar un producto
    if request.method == 'POST' and 'editar' in request.form:
        producto_id = request.form['producto_id']
        nombre = request.form['nombre']
        codigo_barras = request.form['codigo_barras']
        stock = int(request.form['stock'])
        precio = float(request.form['precio'])
        precio_costo = float(request.form['precio_costo'])

        cursor.execute('''
        UPDATE productos
        SET nombre = ?, codigo_barras = ?, stock = ?, precio = ?, precio_costo = ?
        WHERE id = ?
        ''', (nombre, codigo_barras, stock, precio, precio_costo, producto_id))
        conn.commit()
        conn.close()
        return redirect(url_for('agregar_stock'))

    # Agregar un nuevo producto
    if request.method == 'POST' and 'agregar' in request.form:
        nombre = request.form['nombre']
        codigo_barras = request.form['codigo_barras']
        stock = int(request.form['stock'])
        precio = float(request.form['precio'])
        precio_costo = float(request.form['precio_costo'])

        cursor.execute('''
        INSERT INTO productos (nombre, codigo_barras, stock, precio, precio_costo)
        VALUES (?, ?, ?, ?, ?)
        ''', (nombre, codigo_barras, stock, precio, precio_costo))
        conn.commit()
        conn.close()
        return redirect(url_for('agregar_stock'))

    # Obtener productos filtrados por búsqueda (si existe)
    if busqueda:
        cursor.execute('''
        SELECT id, nombre, codigo_barras, stock, precio, precio_costo
        FROM productos
        WHERE nombre LIKE ? OR codigo_barras LIKE ?
        ''', (f'%{busqueda}%', f'%{busqueda}%'))
    else:
        # Si no hay búsqueda, obtener todos los productos
        cursor.execute('SELECT id, nombre, codigo_barras, stock, precio, precio_costo FROM productos')

    productos = cursor.fetchall()
    conn.close()
    return render_template('agregar_stock.html', productos=productos, busqueda=busqueda)

if __name__ == '__main__':
    app.run(debug=True)