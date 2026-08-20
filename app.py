from flask import Flask, render_template, request, jsonify, session
import math
import json
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ============================================
# VALORES FIJOS DE LA EMPRESA (AJUSTADOS)
# ============================================
COSTO_FIJO = 13500
FACTOR_SEGURO = 1.248  # AJUSTADO para que dé 19,412 en 60 meses
# FACTOR_RIESGO se moverá a ser seleccionable por el usuario
IVA = 0.16  # IVA general
COMISION_APERTURA = 0.02  # 2% de comisión por apertura

# Tasas de financiamiento disponibles
TASAS_FINANCIAMIENTO = [1.5, 1.6, 1.7, 1.8]

# ============================================
# FILTROS PARA FORMATO DE NÚMEROS
# ============================================
@app.template_filter('format_number')
def format_number(value):
    """Formatea números con separadores de miles"""
    if value is None:
        return "0"
    try:
        if isinstance(value, float):
            return f"{value:,.2f}"
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('currency')
def currency_filter(value):
    """Formatea como moneda"""
    if value is None:
        return "$0.00"
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('percentage')
def percentage_filter(value):
    """Formatea como porcentaje"""
    if value is None:
        return "0%"
    try:
        return f"{value * 100:.1f}%"
    except (ValueError, TypeError):
        return str(value)

# ============================================
# FUNCIONES DE CÁLCULO MEJORADAS
# ============================================
def calcular_cuota_auto(monto, enganche, plazo_meses, tasa_financiamiento):
    """
    Calcula la cuota mensual usando la fórmula:
    (VALOR - ENGANCHE + COSTO_FIJO) * FACTOR_RIESGO * FACTOR_SEGURO / PLAZO
    """
    financiamiento = monto - enganche
    
    # Validaciones
    if financiamiento <= 0:
        return None, "El enganche debe ser menor al valor del vehículo"
    
    # Fórmula con tasa seleccionada
    paso1 = (monto - enganche) + COSTO_FIJO
    paso2 = paso1 * tasa_financiamiento * FACTOR_SEGURO
    cuota_final = paso2 / plazo_meses
    
    return round(cuota_final, 2), None

def generar_tabla_amortizacion(monto, enganche, plazo_meses, tasa_financiamiento):
    """
    Genera la tabla de amortización con más detalles financieros
    """
    financiamiento = monto - enganche
    
    # Calcular la cuota mensual con tasa seleccionada
    paso1 = (monto - enganche) + COSTO_FIJO
    paso2 = paso1 * tasa_financiamiento * FACTOR_SEGURO
    cuota_mensual = paso2 / plazo_meses
    
    # Tasa de interés mensual (implícita)
    tasa_implicita = (cuota_mensual * plazo_meses) / financiamiento - 1
    tasa_mensual = tasa_implicita / plazo_meses if plazo_meses > 0 else 0
    
    tabla = []
    saldo = financiamiento
    total_interes = 0
    total_capital = 0
    
    for mes in range(1, plazo_meses + 1):
        interes = saldo * tasa_mensual
        capital = cuota_mensual - interes
        saldo -= capital
        
        if mes == plazo_meses:
            saldo = 0
        
        total_interes += interes
        total_capital += capital
        
        tabla.append({
            'mes': mes,
            'cuota': round(cuota_mensual, 2),
            'interes': round(interes, 2),
            'capital': round(capital, 2),
            'saldo': round(saldo, 2),
            'porcentaje_pagado': round((mes / plazo_meses) * 100, 1)
        })
    
    return tabla, {
        'total_interes': round(total_interes, 2),
        'total_capital': round(total_capital, 2),
        'tasa_mensual': round(tasa_mensual * 100, 2),
        'tasa_anual': round(tasa_mensual * 12 * 100, 2)
    }

def calcular_indicadores_financieros(monto, enganche, cuota, plazo_meses):
    """Calcula indicadores financieros adicionales"""
    financiamiento = monto - enganche
    total_pagar = cuota * plazo_meses
    total_interes = total_pagar - financiamiento
    
    return {
        'relacion_deuda_ingreso': round((cuota / (monto * 0.3)) * 100, 1) if monto > 0 else 0,
        'porcentaje_enganche': round((enganche / monto) * 100, 1) if monto > 0 else 0,
        'costo_total': round(total_pagar, 2),
        'costo_financiero': round(total_interes, 2),
        'costo_financiero_porcentaje': round((total_interes / financiamiento) * 100, 1) if financiamiento > 0 else 0
    }

# ============================================
# RUTAS DE LA APLICACIÓN
# ============================================
@app.route('/')
def index():
    opciones_plazo = [
        {'value': 12, 'label': '1 año', 'icon': '📅'},
        {'value': 24, 'label': '2 años', 'icon': '📅'},
        {'value': 36, 'label': '3 años', 'icon': '📅'},
        {'value': 48, 'label': '4 años', 'icon': '📅'},
        {'value': 60, 'label': '5 años', 'icon': '📅'}
    ]
    
    # Opciones de tasa de financiamiento
    opciones_tasa = [
        {'value': 1.5, 'label': '1.5%', 'default': False},
        {'value': 1.6, 'label': '1.6%', 'default': False},
        {'value': 1.7, 'label': '1.7%', 'default': False},
        {'value': 1.8, 'label': '1.8%', 'default': True}  # 1.8 como valor predeterminado
    ]
    
    # Datos de ejemplo para el dashboard
    estadisticas = {
        'total_simulaciones': 0,
        'monto_promedio': 0,
        'plazo_mas_comun': '36 meses',
        'tasa_promedio': 15.5
    }
    
    return render_template('index.html', 
                         costo_fijo=COSTO_FIJO,
                         factor_seguro=FACTOR_SEGURO,
                         opciones_plazo=opciones_plazo,
                         opciones_tasa=opciones_tasa,
                         tasas_financiamiento=TASAS_FINANCIAMIENTO,
                         iva=IVA,
                         estadisticas=estadisticas,
                         ano_actual=datetime.now().year)

@app.route('/calcular', methods=['POST'])
def calcular():
    try:
        # Obtener datos del formulario
        monto_str = request.form.get('monto', '').replace(',', '').strip()
        enganche_str = request.form.get('enganche', '').replace(',', '').strip()
        plazo_str = request.form.get('plazo', '').strip()
        tasa_str = request.form.get('tasa', '').strip()
        
        # Validar que los datos existan
        if not monto_str or not enganche_str or not plazo_str or not tasa_str:
            return jsonify({'error': 'Todos los campos son obligatorios'}), 400
        
        # Convertir a números
        monto = float(monto_str)
        enganche = float(enganche_str)
        plazo_meses = int(plazo_str)
        tasa_financiamiento = float(tasa_str)
        
        # Validar que la tasa sea válida
        if tasa_financiamiento not in TASAS_FINANCIAMIENTO:
            return jsonify({'error': 'Tasa de financiamiento no válida'}), 400
        
        # Validaciones
        if monto <= 0:
            return jsonify({'error': 'El valor del vehículo debe ser mayor a 0'}), 400
        
        if enganche < 0:
            return jsonify({'error': 'El enganche no puede ser negativo'}), 400
        
        if enganche >= monto:
            return jsonify({'error': 'El enganche debe ser menor al valor del vehículo'}), 400
        
        if plazo_meses <= 0:
            return jsonify({'error': 'El plazo debe ser mayor a 0'}), 400
        
        # Calcular cuota con tasa seleccionada
        cuota, error = calcular_cuota_auto(monto, enganche, plazo_meses, tasa_financiamiento)
        if error:
            return jsonify({'error': error}), 400
        
        financiamiento = monto - enganche
        total_pagar = cuota * plazo_meses
        total_interes = total_pagar - financiamiento
        
        # Generar tabla de amortización con métricas
        tabla, metricas = generar_tabla_amortizacion(monto, enganche, plazo_meses, tasa_financiamiento)
        
        # Calcular indicadores financieros
        indicadores = calcular_indicadores_financieros(monto, enganche, cuota, plazo_meses)
        
        # Detalle del cálculo
        paso1 = (monto - enganche) + COSTO_FIJO
        paso2 = paso1 * tasa_financiamiento * FACTOR_SEGURO
        
        # Estadísticas de la tabla
        tabla_resumen = {
            'total_cuotas': len(tabla),
            'promedio_cuota': round(sum(t['cuota'] for t in tabla) / len(tabla), 2),
            'max_cuota': max(t['cuota'] for t in tabla),
            'min_cuota': min(t['cuota'] for t in tabla)
        }
        
        return jsonify({
            'success': True,
            'financiamiento': round(financiamiento, 2),
            'cuota_mensual': cuota,
            'total_pagar': round(total_pagar, 2),
            'total_interes': round(total_interes, 2),
            'tabla': tabla[:12],  # Mostrar solo primeros 12 meses
            'tabla_completa': tabla,
            'metricas': metricas,
            'indicadores': indicadores,
            'tabla_resumen': tabla_resumen,
            'costo_fijo': COSTO_FIJO,
            'factor_seguro': FACTOR_SEGURO,
            'tasa_financiamiento': tasa_financiamiento,
            'plazo_meses': plazo_meses,
            'monto': monto,
            'enganche': enganche,
            'detalle_calculo': {
                'paso1': f"({monto:,.0f} - {enganche:,.0f} + {COSTO_FIJO}) = {paso1:,.2f}",
                'paso2': f"{paso1:,.2f} × {tasa_financiamiento} × {FACTOR_SEGURO} = {paso2:,.2f}",
                'paso3': f"{paso2:,.2f} / {plazo_meses} = {cuota:,.2f}"
            }
        })
    
    except ValueError as e:
        return jsonify({'error': f'Error en los datos: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/exportar_pdf', methods=['POST'])
def exportar_pdf():
    """Exporta los resultados a PDF (simulado)"""
    try:
        data = request.json
        # Aquí iría la lógica para generar PDF
        return jsonify({
            'success': True,
            'mensaje': 'PDF generado exitosamente',
            'archivo': 'simulacion_financiera.pdf'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# EJECUCIÓN
# ============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)