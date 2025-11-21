import streamlit as st
import pandas as pd
from pulp import *

st.markdown("""
<style>
div[data-testid="stMetricValue"] {font-size: 40px;}
.st-emotion-cache-1jm69f1 {font-size: 18px;}
h1 { font-size: 32px !important; }
h2 { font-size: 28px !important; }
</style>
""", 
unsafe_allow_html=True)

def resolver_modelo_transporte(costos_df, oferta_sr, demanda_sr):
    """
    Modela y resuelve el problema de transporte.
    :return: DataFrame con la asignación óptima y el costo mínimo, o None si no es factible.
    """
    origenes = list(costos_df.index)
    destinos = list(costos_df.columns)
    
    problema = LpProblem("Problema de Transporte", LpMinimize)

    rutas = [(i, j) for i in origenes for j in destinos]
    x = LpVariable.dicts("Ruta", rutas, lowBound=0, cat=LpInteger)
    costo_total = sum(costos_df.loc[i, j] * x[(i, j)] for i, j in rutas)
    problema += costo_total, "Costo_Total"

    for i in origenes:
        problema += sum(x[(i, j)] for j in destinos) <= oferta_sr[i], f"Oferta_{i}"

    for j in destinos:
        problema += sum(x[(i, j)] for i in origenes) >= demanda_sr[j], f"Demanda_{j}"

    try:
        problema.solve()
    except Exception as e:
        st.error(f"Error fatal del solver: {e}")
        return None, None

    if LpStatus[problema.status] == "Optimal":
        solucion = pd.DataFrame(0.0, index=origenes, columns=destinos)
        for i, j in rutas:

            if x[(i, j)].varValue > 0.001: 
                solucion.loc[i, j] = x[(i, j)].varValue

        costo_minimo = value(problema.objective)
        return solucion.astype(int), costo_minimo
    else:
    
        return None, None

def highlight_positive(val):
    """Aplica color de fondo y texto si el valor es positivo."""
    if isinstance(val, (int, float)) and val > 0:
        return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
    return ''

st.set_page_config(page_title="Practica 2: Modelo de Transporte", layout="wide")
st.markdown("### **Configuración del Problema**")

if 'costos' not in st.session_state:
    st.session_state.num_origenes = 3
    st.session_state.num_destinos = 4
    st.session_state.origenes = [f"Planta {i+1}" for i in range(3)]
    st.session_state.destinos = [f"Cliente {j+1}" for j in range(4)]
    
    st.session_state.costos = pd.DataFrame(
        [[10, 15, 20, 12], [8, 11, 14, 9], [16, 10, 18, 13]], 
        columns=st.session_state.destinos, 
        index=st.session_state.origenes
    )
    st.session_state.oferta = pd.Series([100, 150, 75], index=st.session_state.origenes)
    st.session_state.demanda = pd.Series([50, 60, 80, 100], index=st.session_state.destinos)

col1, col2 = st.columns(2)

new_num_origenes = col1.number_input("Número de Orígenes", min_value=1, value=st.session_state.num_origenes, key="input_origenes_simple")
new_num_destinos = col2.number_input("Número de Destinos", min_value=1, value=st.session_state.num_destinos, key="input_destinos_simple")

if (new_num_origenes != st.session_state.num_origenes) or (new_num_destinos != st.session_state.num_destinos):
    st.session_state.num_origenes = new_num_origenes
    st.session_state.num_destinos = new_num_destinos
    
    st.session_state.origenes = [f"Planta {i+1}" for i in range(new_num_origenes)]
    st.session_state.destinos = [f"Cliente {j+1}" for j in range(new_num_destinos)]
    
    st.session_state.costos = pd.DataFrame(0, columns=st.session_state.destinos, index=st.session_state.origenes)
    st.session_state.oferta = pd.Series(0, index=st.session_state.origenes)
    st.session_state.demanda = pd.Series(0, index=st.session_state.destinos)
    st.rerun()

st.markdown("---")
st.markdown("### **1. Matriz de Costos Unitarios**")
st.caption("Ingrese el costo de envío unitario de cada Origen (filas) a cada Destino (columnas).")

costos_df_edit = st.data_editor(
    st.session_state.costos,
    key="editor_costos_simple",
    column_config={col: st.column_config.NumberColumn(format="%d", min_value=0) for col in st.session_state.costos.columns},
    use_container_width=True,
    num_rows="fixed"
)
st.session_state.costos = costos_df_edit


st.markdown("### **2. Oferta y Demanda**")

col_oferta, col_demanda = st.columns(2)

with col_oferta:
    st.caption("Capacidad disponible en cada Origen.")
    oferta_df_edit = st.data_editor(
        pd.DataFrame({'Oferta': st.session_state.oferta.values}, index=st.session_state.origenes),
        column_config={'Oferta': st.column_config.NumberColumn(format="%d", min_value=0)},
        hide_index=False,
        key="editor_oferta_simple",
        num_rows="fixed"
    )
    st.session_state.oferta = pd.Series(oferta_df_edit['Oferta'].values, index=st.session_state.origenes)

with col_demanda:
    st.caption("Requerimiento de unidades de cada Destino.")
    demanda_df_edit = st.data_editor(
        pd.DataFrame({'Demanda': st.session_state.demanda.values}, index=st.session_state.destinos),
        column_config={'Demanda': st.column_config.NumberColumn(format="%d", min_value=0)},
        hide_index=False,
        key="editor_demanda_simple",
        num_rows="fixed"
    )
    st.session_state.demanda = pd.Series(demanda_df_edit['Demanda'].values, index=st.session_state.destinos)

st.markdown("---")
if st.button("CALCULAR", type="primary"):

    sum_oferta = st.session_state.oferta.sum()
    sum_demanda = st.session_state.demanda.sum()
    st.markdown("## 3. Resultados de la Optimización")
    st.info(f"**Balance General:** Oferta Total = **{sum_oferta}** | Demanda Total = **{sum_demanda}**")
    
    if sum_oferta < sum_demanda:
        st.error(f"¡INFACTIBILIDAD! La Oferta ({sum_oferta}) es menor que la Demanda ({sum_demanda}). Esto deja **{sum_demanda - sum_oferta}** unidades de Demanda Insatisfecha.")
    elif sum_oferta > sum_demanda:
        st.info(f"ℹ**Exceso de Oferta:** Hay un excedente de **{sum_oferta - sum_demanda}**. Este inventario se quedará sin enviar en los orígenes.")
    with st.spinner('Procesando... ¡Minimizando el costo!'):
        solucion_df, costo_minimo = resolver_modelo_transporte(
            st.session_state.costos, 
            st.session_state.oferta, 
            st.session_state.demanda
        )

    if solucion_df is not None:
        st.success("Solución Óptima Encontrada.")
        
        st.markdown("### Asignación de Envío Óptima")
        st.caption("Las rutas activas se muestran resaltadas con un fondo rojo claro.")
        
        solucion_styled = solucion_df.style.applymap(highlight_positive).format(precision=0)
        st.dataframe(solucion_styled, use_container_width=True)

        st.markdown("### Costo Mínimo Logrado")
        st.metric(label="Costo Total Mínimo", value=f"${costo_minimo:,.2f}")
        
        with st.expander("Detalles del Cumplimiento de Restricciones"):
            st.markdown(f"**Función Objetivo:** Minimizar $Costo = {costo_minimo:,.2f}$")
            
            st.markdown("**Uso de Oferta:**")
            oferta_uso = solucion_df.sum(axis=1)
            for origen in st.session_state.origenes:
                st.write(f"- **{origen}** Usado: {int(oferta_uso[origen])} de {int(st.session_state.oferta[origen])} ($\leq$)")
            
            st.markdown("**Cobertura de Demanda:**")
            demanda_cobertura = solucion_df.sum(axis=0)
            for destino in st.session_state.destinos:
                st.write(f"- **{destino}** Cubierto: {int(demanda_cobertura[destino])} de {int(st.session_state.demanda[destino])} ($\geq$)")
    else:
        st.error("El solver no pudo encontrar una solución. Verifique los datos ingresados.")

st.markdown("---")