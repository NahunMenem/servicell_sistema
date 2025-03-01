from flask import Flask, render_template, request, redirect, url_for, session,flash,jsonify
import sqlite3
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Necesario para usar sesiones
# Función para conectar a la base de datos
def get_db_connection():
    conn = sqlite3.connect('negocio.db')
    conn.row_factory = sqlite3.Row
    return conn

# Crear tabla de usuarios si no existe
def crear_tabla_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')
    conn.commit()
    conn.close()

# Llamar a la función para crear la tabla de usuarios al iniciar la aplicación
# Crear tabla de usuarios si no existe
#prueba
def crear_tabla_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')
    conn.commit()
    conn.close()

# Llamar a la función para crear la tabla de usuarios al iniciar la aplicación
crear_tabla_usuarios()



# Proteger rutas que requieren autenticación
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



# Función para conectar a la base de datos
def get_db_connection():
    conn = sqlite3.connect('negocio.db')
    conn.row_factory = sqlite3.Row
    return conn

# Función para crear la tabla `equipos` si no existe
def crear_tabla_equipos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_reparacion TEXT NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            tecnico TEXT NOT NULL,
            monto REAL NOT NULL,
            nombre_cliente TEXT NOT NULL,
            telefono TEXT NOT NULL,
            nro_orden TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Llamar a la función para crear la tabla al iniciar la aplicación
crear_tabla_equipos()

# Ruta principal (redirige al login si no está autenticado)
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('inicio'))  # Redirige a la página principal del sistema
    return redirect(url_for('login'))  # Redirige al login si no está autenticado

# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('inicio'))  # Redirige a la página principal si ya está autenticado

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user['password'] == password:
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login exitoso!', 'success')
            return redirect(url_for('inicio'))  # Redirige a la página principal después del login
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')

# Ruta para la página principal del sistema (después del login)
@app.route('/inicio')
def inicio():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirige al login si no está autenticado
    return render_template('inicio.html')

# Ruta para el logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))

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
            argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
            fecha_actual = datetime.now(argentina_tz).strftime('%Y-%m-%d %H:%M:%S')

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

# Ruta para mostrar los productos más vendidos
@app.route('/productos_mas_vendidos')
def productos_mas_vendidos():
    # Conectar a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta para obtener los 5 productos más vendidos
    cursor.execute('''
        SELECT nombre, precio, cantidad_vendida 
        FROM productos 
        ORDER BY cantidad_vendida DESC 
        LIMIT 5
    ''')
    productos = cursor.fetchall()

    # Calcular el total de ventas
    cursor.execute('SELECT SUM(cantidad_vendida) FROM productos')
    total_ventas = cursor.fetchone()[0]

    # Calcular el porcentaje de ventas para cada producto
    productos_con_porcentaje = []
    for producto in productos:
        nombre, precio, cantidad_vendida = producto
        porcentaje = (cantidad_vendida / total_ventas) * 100 if total_ventas > 0 else 0
        productos_con_porcentaje.append({
            'nombre': nombre,
            'precio': precio,
            'cantidad_vendida': cantidad_vendida,
            'porcentaje': round(porcentaje, 2)  # Redondear a 2 decimales
        })

    # Cerrar la conexión
    conn.close()

    # Renderizar la plantilla HTML con los productos y el total de ventas
    return render_template('productos_mas_vendidos.html', productos=productos_con_porcentaje, total_ventas=total_ventas)


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

    # Obtener la fecha actual en la zona horaria de Argentina
    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_actual = datetime.now(argentina_tz).strftime('%Y-%m-%d')  # Solo la fecha, sin la hora

    # Consultar todas las ventas del día
    cursor.execute('''
        SELECT 
            v.id AS venta_id,
            p.nombre AS nombre_producto,
            v.cantidad,
            p.precio AS precio_unitario,
            (v.cantidad * p.precio) AS total,
            v.fecha,
            v.tipo_pago
        FROM ventas v
        JOIN productos p ON v.producto_id = p.id
        WHERE DATE(v.fecha) = ?
        ORDER BY v.fecha DESC
    ''', (fecha_actual,))
    ventas = cursor.fetchall()

    # Consultar todas las reparaciones del día
    cursor.execute('''
        SELECT 
            id AS reparacion_id,
            nombre_servicio AS nombre_servicio,
            cantidad,
            precio AS precio_unitario,
            (cantidad * precio) AS total,
            fecha,
            tipo_pago
        FROM reparaciones
        WHERE DATE(fecha) = ?
        ORDER BY fecha DESC
    ''', (fecha_actual,))
    reparaciones = cursor.fetchall()

    # Calcular el total por tipo de pago para ventas
    total_ventas_por_pago = {}
    for venta in ventas:
        tipo_pago = venta['tipo_pago']
        total = venta['total']
        if tipo_pago in total_ventas_por_pago:
            total_ventas_por_pago[tipo_pago] += total
        else:
            total_ventas_por_pago[tipo_pago] = total

    # Calcular el total por tipo de pago para reparaciones
    total_reparaciones_por_pago = {}
    for reparacion in reparaciones:
        tipo_pago = reparacion['tipo_pago']
        total = reparacion['total']
        if tipo_pago in total_reparaciones_por_pago:
            total_reparaciones_por_pago[tipo_pago] += total
        else:
            total_reparaciones_por_pago[tipo_pago] = total

    conn.close()

    # Pasar los datos a la plantilla
    return render_template(
        'ultimas_ventas.html',
        ventas=ventas,
        reparaciones=reparaciones,
        fecha_actual=fecha_actual,
        total_ventas_por_pago=total_ventas_por_pago,
        total_reparaciones_por_pago=total_reparaciones_por_pago
    )

# Ruta para egresos----------------------------------------------------
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

# Ruta para el dashboard--------------------------------------------------
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la fecha seleccionada o usar la fecha actual por defecto
    fecha_seleccionada = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))

    # Calcular el total de ventas de productos del día seleccionado
    cursor.execute('''
    SELECT SUM(v.cantidad * COALESCE(p.precio, v.precio_manual)) AS total_ventas_productos
    FROM ventas v
    LEFT JOIN productos p ON v.producto_id = p.id
    WHERE DATE(v.fecha) = ?
    ''', (fecha_seleccionada,))
    total_ventas_productos_dia = cursor.fetchone()['total_ventas_productos'] or 0

    # Calcular el total de ventas de reparaciones del día seleccionado
    cursor.execute('''
    SELECT SUM(precio) AS total_ventas_reparaciones
    FROM reparaciones
    WHERE DATE(fecha) = ?
    ''', (fecha_seleccionada,))
    total_ventas_reparaciones_dia = cursor.fetchone()['total_ventas_reparaciones'] or 0

    total_ventas_dia = total_ventas_productos_dia + total_ventas_reparaciones_dia

    # Calcular el total de egresos del día seleccionado
    cursor.execute('''
    SELECT SUM(monto) AS total_egresos
    FROM egresos
    WHERE DATE(fecha) = ?
    ''', (fecha_seleccionada,))
    total_egresos_dia = cursor.fetchone()['total_egresos'] or 0

    # Calcular el costo de los productos vendidos en el día seleccionado
    cursor.execute('''
    SELECT SUM(v.cantidad * p.precio_costo) AS total_costo
    FROM ventas v
    JOIN productos p ON v.producto_id = p.id
    WHERE DATE(v.fecha) = ?
    ''', (fecha_seleccionada,))
    total_costo_dia = cursor.fetchone()['total_costo'] or 0

    # Calcular la ganancia del día seleccionado
    ganancia_dia = total_ventas_dia - total_egresos_dia - total_costo_dia

    # Obtener la fecha de inicio y fin de la semana actual
    hoy = datetime.now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).strftime('%Y-%m-%d')  # Lunes de esta semana
    fin_semana = (hoy + timedelta(days=(6 - hoy.weekday()))).strftime('%Y-%m-%d')  # Domingo de esta semana

    # Calcular el total de ventas de productos de la semana
    cursor.execute('''
    SELECT SUM(v.cantidad * COALESCE(p.precio, v.precio_manual)) AS total_ventas_productos
    FROM ventas v
    LEFT JOIN productos p ON v.producto_id = p.id
    WHERE DATE(v.fecha) BETWEEN ? AND ?
    ''', (inicio_semana, fin_semana))
    total_ventas_productos = cursor.fetchone()['total_ventas_productos'] or 0

    # Calcular el total de ventas de reparaciones de la semana
    cursor.execute('''
    SELECT SUM(precio) AS total_ventas_reparaciones
    FROM reparaciones
    WHERE DATE(fecha) BETWEEN ? AND ?
    ''', (inicio_semana, fin_semana))
    total_ventas_reparaciones = cursor.fetchone()['total_ventas_reparaciones'] or 0

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
                          fin_semana=fin_semana,
                          total_ventas_dia=total_ventas_dia,
                          total_egresos_dia=total_egresos_dia,
                          total_costo_dia=total_costo_dia,
                          ganancia_dia=ganancia_dia,
                          fecha_seleccionada=fecha_seleccionada)
#prueba----------------------------------------------------
@app.route('/resumen_semanal')
def resumen_semanal():
    # Obtener la fecha de inicio de la semana (lunes)
    hoy = datetime.now()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_semana_str = inicio_semana.strftime('%Y-%m-%d')

    # Conectar a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consultar las ventas de la semana actual
    cursor.execute('''
        SELECT tipo_pago, SUM(total) as total
        FROM ventas
        WHERE fecha >= ?
        GROUP BY tipo_pago
    ''', (inicio_semana_str,))

    resumen = cursor.fetchall()

    # Cerrar la conexión
    conn.close()

    # Renderizar la plantilla con el resumen
    return render_template('resumen_semanal.html', resumen=resumen)


# Ruta para la caja----------------------------------
@app.route('/caja')
def caja():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la fecha actual en la zona horaria de Argentina
    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_actual = datetime.now(argentina_tz).strftime('%Y-%m-%d')  # Solo la fecha, sin la hora

    # Consultar todas las ventas del día
    cursor.execute('''
        SELECT 
            v.id AS venta_id,
            p.nombre AS nombre_producto,
            v.cantidad,
            p.precio AS precio_unitario,
            (v.cantidad * p.precio) AS total,
            v.fecha,
            v.tipo_pago
        FROM ventas v
        JOIN productos p ON v.producto_id = p.id
        WHERE DATE(v.fecha) = ?
        ORDER BY v.fecha DESC
    ''', (fecha_actual,))
    ventas = cursor.fetchall()

    # Consultar todas las reparaciones del día
    cursor.execute('''
        SELECT 
            id AS reparacion_id,
            nombre_servicio AS nombre_servicio,
            cantidad,
            precio AS precio_unitario,
            (cantidad * precio) AS total,
            fecha,
            tipo_pago
        FROM reparaciones
        WHERE DATE(fecha) = ?
        ORDER BY fecha DESC
    ''', (fecha_actual,))
    reparaciones = cursor.fetchall()

    # Consultar todos los egresos del día
    cursor.execute('''
        SELECT 
            id AS egreso_id,
            descripcion,
            monto,
            tipo_pago,
            fecha
        FROM egresos
        WHERE DATE(fecha) = ?
        ORDER BY fecha DESC
    ''', (fecha_actual,))
    egresos = cursor.fetchall()

    # Calcular el total por tipo de pago para ventas
    total_ventas_por_pago = {}
    for venta in ventas:
        tipo_pago = venta['tipo_pago']
        total = venta['total']
        if tipo_pago in total_ventas_por_pago:
            total_ventas_por_pago[tipo_pago] += total
        else:
            total_ventas_por_pago[tipo_pago] = total

    # Calcular el total por tipo de pago para reparaciones
    total_reparaciones_por_pago = {}
    for reparacion in reparaciones:
        tipo_pago = reparacion['tipo_pago']
        total = reparacion['total']
        if tipo_pago in total_reparaciones_por_pago:
            total_reparaciones_por_pago[tipo_pago] += total
        else:
            total_reparaciones_por_pago[tipo_pago] = total

    # Calcular el total combinado por tipo de pago (ventas + reparaciones)
    total_combinado_por_pago = {}
    for tipo_pago, total in total_ventas_por_pago.items():
        total_combinado_por_pago[tipo_pago] = total_combinado_por_pago.get(tipo_pago, 0) + total
    for tipo_pago, total in total_reparaciones_por_pago.items():
        total_combinado_por_pago[tipo_pago] = total_combinado_por_pago.get(tipo_pago, 0) + total

    # Calcular el total de egresos por tipo de pago
    total_egresos_por_pago = {}
    for egreso in egresos:
        tipo_pago = egreso['tipo_pago']
        monto = egreso['monto']
        if tipo_pago in total_egresos_por_pago:
            total_egresos_por_pago[tipo_pago] += monto
        else:
            total_egresos_por_pago[tipo_pago] = monto

    # Calcular el neto por tipo de pago (total combinado - egresos correspondientes)
    neto_por_pago = {}
    for tipo_pago, total in total_combinado_por_pago.items():
        # Obtener los egresos para este tipo de pago (si no hay, usar 0)
        egresos_tipo_pago = total_egresos_por_pago.get(tipo_pago, 0)
        # Calcular el neto
        neto_por_pago[tipo_pago] = total - egresos_tipo_pago

    conn.close()

    # Pasar los datos a la plantilla
    return render_template(
        'caja.html',
        fecha_actual=fecha_actual,
        total_ventas_por_pago=total_ventas_por_pago,
        total_reparaciones_por_pago=total_reparaciones_por_pago,
        total_combinado_por_pago=total_combinado_por_pago,
        total_egresos_por_pago=total_egresos_por_pago,
        neto_por_pago=neto_por_pago
    )


@app.route('/caja_semanal')
def caja_semanal():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la fecha actual en la zona horaria de Argentina
    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
    hoy = datetime.now(argentina_tz)

    # Obtener parámetros de la URL (semana o mes)
    periodo = request.args.get('periodo', 'semana_actual')  # Por defecto: semana actual
    if periodo == 'semana_pasada':
        inicio_semana = hoy - timedelta(days=hoy.weekday() + 7)  # Lunes de la semana pasada
        fin_semana = inicio_semana + timedelta(days=6)  # Domingo de la semana pasada
    elif periodo == 'mes_actual':
        inicio_semana = hoy.replace(day=1)  # Primer día del mes actual
        fin_semana = (inicio_semana + timedelta(days=32)).replace(day=1) - timedelta(days=1)  # Último día del mes actual
    elif periodo == 'mes_anterior':
        primer_dia_mes_actual = hoy.replace(day=1)
        inicio_semana = (primer_dia_mes_actual - timedelta(days=1)).replace(day=1)  # Primer día del mes anterior
        fin_semana = primer_dia_mes_actual - timedelta(days=1)  # Último día del mes anterior
    else:  # Semana actual (por defecto)
        inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes de la semana actual
        fin_semana = inicio_semana + timedelta(days=6)  # Domingo de la semana actual

    # Formatear fechas para la consulta SQL
    inicio_semana_str = inicio_semana.strftime('%Y-%m-%d')
    fin_semana_str = fin_semana.strftime('%Y-%m-%d')

    # Consultar todas las ventas del período seleccionado
    cursor.execute('''
        SELECT 
            v.id AS venta_id,
            p.nombre AS nombre_producto,
            v.cantidad,
            p.precio AS precio_unitario,
            (v.cantidad * p.precio) AS total,
            v.fecha,
            v.tipo_pago
        FROM ventas v
        JOIN productos p ON v.producto_id = p.id
        WHERE DATE(v.fecha) BETWEEN ? AND ?
        ORDER BY v.fecha DESC
    ''', (inicio_semana_str, fin_semana_str))
    ventas = cursor.fetchall()

    # Consultar todas las reparaciones del período seleccionado
    cursor.execute('''
        SELECT 
            id AS reparacion_id,
            nombre_servicio AS nombre_servicio,
            cantidad,
            precio AS precio_unitario,
            (cantidad * precio) AS total,
            fecha,
            tipo_pago
        FROM reparaciones
        WHERE DATE(fecha) BETWEEN ? AND ?
        ORDER BY fecha DESC
    ''', (inicio_semana_str, fin_semana_str))
    reparaciones = cursor.fetchall()

    # Consultar todos los egresos del período seleccionado
    cursor.execute('''
        SELECT 
            id AS egreso_id,
            descripcion,
            monto,
            tipo_pago,
            fecha
        FROM egresos
        WHERE DATE(fecha) BETWEEN ? AND ?
        ORDER BY fecha DESC
    ''', (inicio_semana_str, fin_semana_str))
    egresos = cursor.fetchall()

    # Calcular el total por tipo de pago para ventas
    total_ventas_por_pago = {}
    for venta in ventas:
        tipo_pago = venta['tipo_pago']
        total = venta['total']
        if tipo_pago in total_ventas_por_pago:
            total_ventas_por_pago[tipo_pago] += total
        else:
            total_ventas_por_pago[tipo_pago] = total

    # Calcular el total por tipo de pago para reparaciones
    total_reparaciones_por_pago = {}
    for reparacion in reparaciones:
        tipo_pago = reparacion['tipo_pago']
        total = reparacion['total']
        if tipo_pago in total_reparaciones_por_pago:
            total_reparaciones_por_pago[tipo_pago] += total
        else:
            total_reparaciones_por_pago[tipo_pago] = total

    # Calcular el total combinado por tipo de pago (ventas + reparaciones)
    total_combinado_por_pago = {}
    for tipo_pago, total in total_ventas_por_pago.items():
        total_combinado_por_pago[tipo_pago] = total_combinado_por_pago.get(tipo_pago, 0) + total
    for tipo_pago, total in total_reparaciones_por_pago.items():
        total_combinado_por_pago[tipo_pago] = total_combinado_por_pago.get(tipo_pago, 0) + total

    # Calcular el total de egresos por tipo de pago
    total_egresos_por_pago = {}
    for egreso in egresos:
        tipo_pago = egreso['tipo_pago']
        monto = egreso['monto']
        if tipo_pago in total_egresos_por_pago:
            total_egresos_por_pago[tipo_pago] += monto
        else:
            total_egresos_por_pago[tipo_pago] = monto

    # Calcular el neto por tipo de pago (total combinado - egresos correspondientes)
    neto_por_pago = {}
    for tipo_pago, total in total_combinado_por_pago.items():
        # Obtener los egresos para este tipo de pago (si no hay, usar 0)
        egresos_tipo_pago = total_egresos_por_pago.get(tipo_pago, 0)
        # Calcular el neto
        neto_por_pago[tipo_pago] = total - egresos_tipo_pago

    # Obtener ventas mensuales para el gráfico
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', fecha) AS mes,
            SUM(total) AS total_ventas
        FROM ventas
        WHERE strftime('%Y', fecha) = strftime('%Y', 'now')
        GROUP BY mes
        ORDER BY mes
    ''')
    ventas_mensuales = cursor.fetchall()

    # Obtener ventas semanales para el gráfico (últimas 4 semanas)
    cursor.execute('''
        SELECT 
            strftime('%Y-%W', fecha) AS semana,
            SUM(total) AS total_ventas
        FROM ventas
        WHERE fecha >= date('now', '-28 days')
        GROUP BY semana
        ORDER BY semana
        LIMIT 4
    ''')
    ventas_semanales = cursor.fetchall()

    conn.close()

    # Pasar los datos a la plantilla
    return render_template(
        'caja_semanal.html',
        inicio_semana=inicio_semana_str,
        fin_semana=fin_semana_str,
        total_ventas_por_pago=total_ventas_por_pago,
        total_reparaciones_por_pago=total_reparaciones_por_pago,
        total_combinado_por_pago=total_combinado_por_pago,
        total_egresos_por_pago=total_egresos_por_pago,
        neto_por_pago=neto_por_pago,
        periodo_seleccionado=periodo,
        ventas_mensuales=ventas_mensuales,
        ventas_semanales=ventas_semanales
    )
# Ruta para reparaciones----------------------------------
@app.route('/reparaciones', methods=['GET', 'POST'])
def reparaciones():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Obtener los datos del formulario
        tipo_reparacion = request.form['tipo_reparacion']
        marca = request.form['equipo']
        modelo = request.form['modelo']
        tecnico = request.form['tecnico']
        monto = float(request.form['monto'])
        nombre_cliente = request.form['nombre_cliente']
        telefono = request.form['telefono']
        nro_orden = request.form['nro_orden']
        fecha = datetime.now().strftime('%Y-%m-%d')
        hora = datetime.now().strftime('%H:%M:%S')

        # Insertar los datos en la base de datos
        cursor.execute('''
            INSERT INTO equipos (
                tipo_reparacion, marca, modelo, tecnico, monto, nombre_cliente, telefono, nro_orden, fecha, hora
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tipo_reparacion, marca, modelo, tecnico, monto, nombre_cliente, telefono, nro_orden, fecha, hora))
        conn.commit()

    # Obtener los últimos equipos cargados en la semana actual
    fecha_inicio = datetime.now() - timedelta(days=7)
    cursor.execute("SELECT * FROM equipos WHERE fecha >= ?", (fecha_inicio.strftime('%Y-%m-%d'),))
    ultimos_equipos = cursor.fetchall()

    # Obtener la cantidad de equipos por técnico
    cursor.execute('''
        SELECT tecnico, COUNT(*) as cantidad
        FROM equipos
        GROUP BY tecnico
    ''')
    datos_tecnicos = cursor.fetchall()

    conn.close()

    # Preparar los datos para la vista
    equipos_por_tecnico = {row['tecnico']: row['cantidad'] for row in datos_tecnicos}

    return render_template(
        'reparaciones.html',
        ultimos_equipos=ultimos_equipos,
        equipos_por_tecnico=equipos_por_tecnico
    )

# Ruta para eliminar reparaciones----------------------------------
@app.route('/eliminar_reparacion/<int:id>', methods=['POST'])
def eliminar_reparacion(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Eliminar el equipo por su ID
    cursor.execute('DELETE FROM equipos WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    # Redirigir a la página de reparaciones después de eliminar
    return redirect(url_for('reparaciones'))

 

#ruta para actualizar estado de reparaciones
@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    data = request.get_json()
    nro_orden = data['nro_orden']
    estado = data['estado']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE equipos
        SET estado = ?
        WHERE nro_orden = ?
    ''', (estado, nro_orden))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/mercaderia_fallada', methods=['GET', 'POST'])
def mercaderia_fallada():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar productos
    if request.method == 'POST' and 'buscar' in request.form:
        busqueda = request.form['busqueda']
        cursor.execute('''
        SELECT id, nombre, codigo_barras, stock, precio, precio_costo
        FROM productos
        WHERE nombre LIKE ? OR codigo_barras LIKE ?
        ''', (f'%{busqueda}%', f'%{busqueda}%'))
        productos = cursor.fetchall()
        conn.close()
        return render_template('mercaderia_fallada.html', productos=productos)

    # Registrar mercadería fallada
    if request.method == 'POST' and 'registrar_fallada' in request.form:
        producto_id = request.form['producto_id']
        cantidad = int(request.form['cantidad'])
        descripcion = request.form['descripcion']
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Verificar si hay suficiente stock
        cursor.execute('SELECT stock FROM productos WHERE id = ?', (producto_id,))
        producto = cursor.fetchone()

        if producto and producto['stock'] >= cantidad:
            # Registrar en la tabla `mercaderia_fallada`
            cursor.execute('''
            INSERT INTO mercaderia_fallada (producto_id, cantidad, fecha, descripcion)
            VALUES (?, ?, ?, ?)
            ''', (producto_id, cantidad, fecha, descripcion))

            # Actualizar el stock en la tabla `productos`
            cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cantidad, producto_id))
            conn.commit()
            conn.close()
            return redirect(url_for('mercaderia_fallada'))
        else:
            conn.close()
            return f"No hay suficiente stock para el producto seleccionado."

    # Obtener historial de mercadería fallada
    cursor.execute('''
    SELECT mf.id, p.nombre, mf.cantidad, mf.fecha, mf.descripcion
    FROM mercaderia_fallada mf
    JOIN productos p ON mf.producto_id = p.id
    ORDER BY mf.fecha DESC
    ''')
    historial = cursor.fetchall()

    conn.close()
    return render_template('mercaderia_fallada.html', historial=historial)


# Ruta para productos----------------------------------
@app.route('/agregar_stock', methods=['GET', 'POST'])
def agregar_stock():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener el término de búsqueda (si existe)
    busqueda = request.args.get('busqueda', '')

    try:
        # Eliminar un producto
        if request.method == 'POST' and 'eliminar' in request.form:
            producto_id = request.form['producto_id']
            cursor.execute('DELETE FROM productos WHERE id = ?', (producto_id,))
            conn.commit()
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
            return redirect(url_for('agregar_stock'))

        # Agregar stock a un producto existente
        if request.method == 'POST' and 'agregar_stock' in request.form:
            producto_id = request.form['producto_id']
            cantidad = int(request.form['cantidad'])

            cursor.execute('''
            UPDATE productos
            SET stock = stock + ?
            WHERE id = ?
            ''', (cantidad, producto_id))
            conn.commit()
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
    except Exception as e:
        conn.rollback()
        return f"Error: {str(e)}"
    finally:
        conn.close()

    return render_template('agregar_stock.html', productos=productos, busqueda=busqueda)
if __name__ == '__main__':
    app.run(debug=True)
    app.run(debug=True)