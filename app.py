from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)

# ============================================
# VALORES FIJOS DE LA EMPRESA
# ============================================
COSTO_FIJO = 13500
FACTOR_SEGURO = 2.08  # Porcentaje

# ============================================
# FILTRO PARA FORMATO DE NÚMEROS
# ============================================
@app.template_filter('format_number')
def format_number(value):
    """Formatea números con separadores de miles"""
    if value is None:
        return "0"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

# ============================================
# FUNCIONES DE CÁLCULO
# ============================================
def calcular_cuota_auto(monto, enganche, tasa, plazo_meses):
    """
    Calcula la cuota mensual usando la fórmula exacta de la financiera
    """
    financiamiento = monto - enganche
    
    # Validaciones
    if financiamiento <= 0:
        return None, "El enganche debe ser menor al valor del vehículo"
    
    if tasa < 0:
        return None, "La tasa no puede ser negativa"
    
    # Calcular cuota base (Sistema Francés)
    tasa_mensual = tasa / 100
    if tasa_mensual == 0:
        cuota_base = financiamiento / plazo_meses
    else:
        factor = (1 + tasa_mensual) ** plazo_meses
        cuota_base = financiamiento * (tasa_mensual * factor) / (factor - 1)
    
    # Agregar el costo fijo mensual
    costo_fijo_mensual = COSTO_FIJO / plazo_meses
    cuota_con_costo = cuota_base + costo_fijo_mensual
    
    # Aplicar factor de seguro
    factor_seguro_decimal = 1 + (FACTOR_SEGURO / 100)
    cuota_final = cuota_con_costo * factor_seguro_decimal
    
    return round(cuota_final, 2), None


def generar_tabla_amortizacion(monto, enganche, tasa, plazo_meses):
    """
    Genera la tabla de amortización
    """
    financiamiento = monto - enganche
    
    # Calcular cuota base (Sistema Francés)
    tasa_mensual = tasa / 100
    if tasa_mensual == 0:
        cuota_base = financiamiento / plazo_meses
    else:
        factor = (1 + tasa_mensual) ** plazo_meses
        cuota_base = financiamiento * (tasa_mensual * factor) / (factor - 1)
    
    # Agregar el costo fijo mensual
    costo_fijo_mensual = COSTO_FIJO / plazo_meses
    cuota_con_costo = cuota_base + costo_fijo_mensual
    
    # Aplicar factor de seguro
    factor_seguro_decimal = 1 + (FACTOR_SEGURO / 100)
    cuota_mensual = cuota_con_costo * factor_seguro_decimal
    
    tabla = []
    saldo = financiamiento
    
    for mes in range(1, plazo_meses + 1):
        interes = saldo * tasa_mensual
        capital = cuota_base - interes
        saldo -= capital
        
        tabla.append({
            'mes': mes,
            'cuota': round(cuota_mensual, 2),
            'interes': round(interes, 2),
            'capital': round(capital, 2),
            'saldo': round(saldo, 2)
        })
    
    return tabla

# ============================================
# RUTAS DE LA APLICACIÓN
# ============================================
@app.route('/')
def index():
    # Opciones de plazo en años
    opciones_plazo = [
        {'value': 12, 'label': '1 año'},
        {'value': 24, 'label': '2 años'},
        {'value': 36, 'label': '3 años'},
        {'value': 48, 'label': '4 años'},
        {'value': 60, 'label': '5 años'}
    ]
    return render_template('index.html', 
                         costo_fijo=COSTO_FIJO,
                         factor_seguro=FACTOR_SEGURO,
                         opciones_plazo=opciones_plazo)


@app.route('/calcular', methods=['POST'])
def calcular():
    try:
        # Limpiar el formato de los números antes de parsear
        monto_str = request.form['monto'].replace(',', '')
        enganche_str = request.form['enganche'].replace(',', '')
        
        monto = float(monto_str)
        enganche = float(enganche_str)
        tasa = float(request.form['tasa'])
        plazo_meses = int(request.form['plazo'])
        
        # Validaciones
        if monto <= 0 or enganche < 0 or tasa < 0 or plazo_meses <= 0:
            return jsonify({'error': 'Todos los valores deben ser positivos'}), 400
        
        if enganche >= monto:
            return jsonify({'error': 'El enganche debe ser menor al valor del vehículo'}), 400
        
        # Calcular cuota
        cuota, error = calcular_cuota_auto(monto, enganche, tasa, plazo_meses)
        if error:
            return jsonify({'error': error}), 400
        
        financiamiento = monto - enganche
        total_pagar = cuota * plazo_meses
        total_interes = total_pagar - financiamiento
        tabla = generar_tabla_amortizacion(monto, enganche, tasa, plazo_meses)
        
        return jsonify({
            'financiamiento': round(financiamiento, 2),
            'cuota_mensual': cuota,
            'total_pagar': round(total_pagar, 2),
            'total_interes': round(total_interes, 2),
            'tabla': tabla,
            'costo_fijo': COSTO_FIJO,
            'factor_seguro': FACTOR_SEGURO,
            'plazo_meses': plazo_meses
        })
    
    except ValueError:
        return jsonify({'error': 'Por favor ingrese valores numéricos válidos'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# EJECUCIÓN
# ============================================
if __name__ == '__main__':
    app.run(debug=True)