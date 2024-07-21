import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
import hashlib

# Configuración de la página
st.set_page_config(page_title="Reporte de Venta Pérdida Cigarros y RRPS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Título de la aplicación
st.title("📊 Reporte de Venta Perdida Cigarros y RRPS")
st.markdown("En esta página podrás visualizar la venta pérdida día con día, por plaza, división, proveedor y otros datos que desees. Esto con el fin de dar acción y reducir la Venta pérdida")

# File paths
folder_path = "Base."
venta_pr_path = "Base./Venta PR.xlsx"

# Function to read a CSV file from the local folder
def read_csv_from_local(file_path):
    return pd.read_csv(file_path, encoding='ISO-8859-1')

# Function to get the current hash of the files in the folder
def get_files_hash(files):
    files_str = ''.join(sorted(files))
    return hashlib.md5(files_str.encode()).hexdigest()

# Function to process CSV files
@st.cache_data
def process_data(folder_path, files_hash):
    all_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    all_data = []
    for file in all_files:
        try:
            date_str = file.split('.')[0]
            date = datetime.strptime(date_str, '%d%m%Y')
            df = read_csv_from_local(f"{folder_path}/{file}")
            df['Fecha'] = date
            all_data.append(df)
        except Exception as e:
            st.write(f"Error leyendo el archivo {file}: {e}")
    if not all_data:
        return None
    data = pd.concat(all_data)
    data['Fecha'] = pd.to_datetime(data['Fecha'])
    data['Semana'] = data['Fecha'].dt.isocalendar().week
    data.loc[data['DESC_ARTICULO'].str.contains('VUSE', case=False, na=False), 'CATEGORIA'] = '062 RRPs (Vapor y tabaco calentado)'
    # Renombrar proveedores y eliminar proveedor dummy
    proveedores_renombrados = {
        "1822 PHILIP MORRIS MEXICO, S.A. DE C.V.": "PMI",
        "1852 BRITISH AMERICAN TOBACCO MEXICO COMERCIAL, S.A. DE C.V.": "BAT",
        "6247 MAS BODEGA Y LOGISTICA, S.A. DE C.V.": "JTI",
        "21864 ARTICUN DISTRIBUIDORA S.A. DE C.V.": "Articun",
        "2216 NUEVA DISTABAC, S.A. DE C.V.": "Nueva Distabac",
        "8976 DRUGS EXPRESS, S.A DE C.V.": "Drugs Express",
        "1 PROVEEDOR DUMMY MIGRACION": "Eliminar"
    }
    data['PROVEEDOR'] = data['PROVEEDOR'].replace(proveedores_renombrados)
    data = data[data['PROVEEDOR'] != "Eliminar"]
    return data

# Function to process Venta PR file
def load_venta_pr(file_path):
    df = pd.read_excel(file_path)
    df['Día Contable'] = pd.to_datetime(df['Día Contable'], format='%d/%m/%Y')
    df['Semana'] = df['Día Contable'].dt.isocalendar().week
    return df

# Load Venta PR data
venta_pr_data = load_venta_pr(venta_pr_path)

# Function to apply filters
def apply_filters(data, proveedor, plaza, categoria, fecha, semana, division, articulo):
    if proveedor: data = data[data['PROVEEDOR'] == proveedor]
    if plaza: data = data[data['PLAZA'] == plaza]
    if categoria: data = data[data['CATEGORIA'] == categoria]
    if fecha: data = data[data['Fecha'] == fecha]
    if semana: data = data[data['Semana'] == semana]
    if division: data = data[data['DIVISION'] == division]
    if articulo: data = data[data['DESC_ARTICULO'].str.contains(articulo, case=False, na=False)]
    return data

# Function to apply weekly view
def apply_weekly_view(data):
    weekly_data = data.groupby(['Semana', 'PROVEEDOR', 'PLAZA', 'CATEGORIA', 'DIVISION', 'DESC_ARTICULO', 'MERCADO']).agg({'VENTA_PERDIDA_PESOS': 'sum'}).reset_index()
    return weekly_data

# Function to plot venta perdida por plaza
def plot_venta_perdida_plaza(data):
    fig = go.Figure()
    grouped_data = data.groupby('PLAZA')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    
    fig.add_trace(go.Bar(
        x=grouped_data['PLAZA'], 
        y=grouped_data['VENTA_PERDIDA_PESOS'], 
        marker_color='rgb(26, 118, 255)'
    ))
    
    fig.update_layout(
        title='Venta Perdida por Plaza',
        xaxis_title='Plaza',
        yaxis_title='Venta Perdida (Pesos)',
        yaxis=dict(tickformat="$,d")
    )
    
    return fig

# Function to plot top 10 artículos con mayor venta perdida
def plot_articulos_venta_perdida(data):
    fig = go.Figure()
    grouped_data = data.groupby('DESC_ARTICULO')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    grouped_data = grouped_data.sort_values(by='VENTA_PERDIDA_PESOS', ascending=False).head(10)
    fig.add_trace(go.Bar(x=grouped_data['DESC_ARTICULO'], y=grouped_data['VENTA_PERDIDA_PESOS'], marker_color='rgb(55, 83, 109)'))
    fig.update_layout(title='Top 10 Artículos con mayor Venta Perdida', xaxis_title='Artículo', yaxis_title='Venta Perdida (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Function to plot venta perdida por día/semana
def plot_venta_perdida(data, view):
    fig = go.Figure()
    if view == "semanal":
        grouped_data = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana'
    else:
        grouped_data = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Fecha'
    fig.add_trace(go.Scatter(x=grouped_data[x_title], y=grouped_data['VENTA_PERDIDA_PESOS'], mode='lines+markers', name='Venta Perdida', line=dict(color='rgb(219, 64, 82)')))
    fig.update_layout(title=f'Venta Perdida por {x_title}', xaxis_title=x_title, yaxis_title='Monto (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Function to plot venta perdida con tendencia
def plot_venta_perdida_con_tendencia(data, view):
    if view == "semanal":
        grouped_data = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana'
    else:
        grouped_data = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Fecha'
    grouped_data['Cambio (%)'] = grouped_data['VENTA_PERDIDA_PESOS'].pct_change() * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=grouped_data[x_title], y=grouped_data['VENTA_PERDIDA_PESOS'], name='Venta Perdida', marker_color='rgb(219, 64, 82)'))
    fig.add_trace(go.Scatter(x=grouped_data[x_title], y=grouped_data['Cambio (%)'], mode='lines+markers', name='Cambio Porcentual', line=dict(color='white'), yaxis='y2'))
    fig.update_layout(title=f'Venta Perdida por {x_title} y Cambio Porcentual', xaxis_title=x_title, yaxis=dict(title='Monto (Pesos)', tickformat="$,d"), yaxis2=dict(title='Cambio Porcentual (%)', overlaying='y', side='right', tickformat=".2f", showgrid=False), legend=dict(x=0, y=1.1, orientation='h'), barmode='group')
    return fig

# Function to plot venta perdida por proveedor
def plot_venta_perdida_proveedor(data, selected_proveedor=None):
    grouped_data = data.groupby('PROVEEDOR')['VENTA_PERDIDA_PESOS'].sum().reset_index()
    colors = ['gold', 'mediumturquoise', 'darkorange', 'lightgreen', 'lightblue', 'pink', 'red', 'purple', 'brown', 'gray']
    pull = [0.2 if proveedor == selected_proveedor else 0 for proveedor in grouped_data['PROVEEDOR']]
    fig = go.Figure(data=[go.Pie(labels=grouped_data['PROVEEDOR'], values=grouped_data['VENTA_PERDIDA_PESOS'], pull=pull)])
    fig.update_traces(hoverinfo='label+percent', textinfo='value', texttemplate='$%{value:,.0f}', textfont_size=20, marker=dict(colors=colors, line=dict(color='#000000', width=2)))
    fig.update_layout(title='Venta Perdida por Proveedor')
    return fig

# Function to plot venta perdida vs venta neta total
def plot_comparacion_venta_perdida_vs_neta(data, venta_pr_data, filtro_fechas, view):
    if view == "semanal":
        venta_pr_data_grouped = venta_pr_data.groupby('Semana')['Venta Neta Total'].sum().reset_index()
        comparacion_diaria = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion_diaria = comparacion_diaria.merge(venta_pr_data_grouped, left_on='Semana', right_on='Semana', how='left')
    else:
        venta_pr_data_grouped = venta_pr_data.groupby('Día Contable')['Venta Neta Total'].sum().reset_index()
        comparacion_diaria = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion_diaria = comparacion_diaria.merge(venta_pr_data_grouped, left_on='Fecha', right_on='Día Contable', how='left')

    venta_perdida_total = data['VENTA_PERDIDA_PESOS'].sum()
    venta_neta_total = comparacion_diaria['Venta Neta Total'].sum()
    venta_no_perdida = venta_neta_total - venta_perdida_total

    fig = go.Figure(data=[go.Bar(name='Venta Perdida', x=['Venta Total'], y=[venta_perdida_total], marker_color='red', text=f'${venta_perdida_total:,.0f}', textposition='inside'), go.Bar(name='Venta Neta Total', x=['Venta Total'], y=[venta_no_perdida], marker_color='blue', text=f'${venta_no_perdida:,.0f}', textposition='inside')])
    fig.update_layout(barmode='stack', title='Venta Perdida vs Venta Neta Total', yaxis=dict(tickformat="$,d", title='Monto (Pesos)'), xaxis=dict(title='Tipo de Venta'))
    return fig

# Function to plot venta perdida vs venta neta total diaria
def plot_comparacion_venta_perdida_vs_neta_diaria(data, venta_pr_data, filtro_fechas, view, view_percentage=False):
    if view == "semanal":
        filtered_venta_pr = venta_pr_data[venta_pr_data['Semana'].isin(filtro_fechas)]
        comparacion_diaria = data.groupby('Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion_diaria = comparacion_diaria.merge(filtered_venta_pr.groupby('Semana')['Venta Neta Total'].sum().reset_index(), left_on='Semana', right_on='Semana', how='left')
        x_title = 'Semana'
    else:
        filtered_venta_pr = venta_pr_data[venta_pr_data['Día Contable'].isin(filtro_fechas)]
        comparacion_diaria = data.groupby('Fecha')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion_diaria = comparacion_diaria.merge(filtered_venta_pr.groupby('Día Contable')['Venta Neta Total'].sum().reset_index(), left_on='Fecha', right_on='Día Contable', how='left')
        x_title = 'Fecha'

    if view_percentage:
        comparacion_diaria['Venta Perdida (%)'] = (comparacion_diaria['VENTA_PERDIDA_PESOS'] / comparacion_diaria['Venta Neta Total']) * 100
        comparacion_diaria['Venta Neta Total (%)'] = (comparacion_diaria['Venta Neta Total'] / comparacion_diaria['VENTA_PERDIDA_PESOS']) * 100
        fig = go.Figure(data=[go.Bar(name='Venta Perdida (%)', x=comparacion_diaria[x_title], y=comparacion_diaria['Venta Perdida (%)'], marker_color='red'), go.Bar(name='Venta Neta Total (%)', x=comparacion_diaria[x_title], y=comparacion_diaria['Venta Neta Total (%)'], marker_color='blue')])
        fig.update_layout(barmode='stack', title=f'Venta Perdida vs Venta Neta Total ({x_title})', xaxis_title=x_title, yaxis_title='Porcentaje (%)')
    else:
        fig = go.Figure(data=[go.Bar(name='Venta Perdida', x=comparacion_diaria[x_title], y=comparacion_diaria['VENTA_PERDIDA_PESOS'], marker_color='red'), go.Bar(name='Venta Neta Total', x=comparacion_diaria[x_title], y=comparacion_diaria['Venta Neta Total'], marker_color='blue')])
        fig.update_layout(barmode='stack', title=f'Venta Perdida vs Venta Neta Total ({x_title})', xaxis_title=x_title, yaxis_title='Monto (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Function to make a donut chart
def make_donut_chart(value, total, title, color):
    fig = go.Figure(go.Pie(values=[value, total - value], labels=[title, 'Restante'], marker_colors=[color, '#E2E2E2'], hole=0.7, textinfo='label', hoverinfo='label+percent'))
    fig.update_traces(texttemplate='', textposition='inside')
    fig.update_layout(
        title="Proporción de la Venta Perdida Filtrada respecto al Total",
        showlegend=True,
        margin=dict(t=50, b=0, l=0, r=0),  # Adjust top margin to make room for the title
        height=300,
        width=300
    )
    return fig

# Function to plot venta perdida por mercado
def plot_venta_perdida_mercado(data, view):
    fig = go.Figure()
    if view == "semanal":
        grouped_data = data.groupby(['Semana', 'MERCADO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Semana'
    else:
        grouped_data = data.groupby(['Fecha', 'MERCADO'])['VENTA_PERDIDA_PESOS'].sum().reset_index()
        x_title = 'Fecha'
    mercados = grouped_data['MERCADO'].unique()
    for mercado in mercados:
        mercado_data = grouped_data[grouped_data['MERCADO'] == mercado]
        fig.add_trace(go.Scatter(x=mercado_data[x_title], y=mercado_data['VENTA_PERDIDA_PESOS'], mode='lines+markers', name=mercado))
    fig.update_layout(title=f'Venta Perdida por {x_title} y por Mercado', xaxis_title=x_title, yaxis_title='Venta Perdida (Pesos)', yaxis=dict(tickformat="$,d"))
    return fig

# Fetch all CSV files and their hash
all_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
files_hash = get_files_hash(all_files)

# Procesar archivos en la carpeta especificada
data = process_data(folder_path, files_hash)

# Show dashboard if data is available
if data is not None:
    st.sidebar.title('📈📉 Dashboard de Venta Perdida')
    articulo = st.sidebar.text_input("Buscar artículo o familia de artículos 🚬")
    proveedores = st.sidebar.selectbox("Selecciona un proveedor 🏳️🏴🚩", options=[None] + data['PROVEEDOR'].unique().tolist())
    division = st.sidebar.selectbox("Selecciona una división 🗺️", options=[None] + data['DIVISION'].unique().tolist())
    plaza = st.sidebar.selectbox("Selecciona una plaza 🏙️", options=[None] + data['PLAZA'].unique().tolist())
    categoria = st.sidebar.selectbox("Selecciona una categoría 🗃️", options=[None] + data['CATEGORIA'].unique().tolist())
    semana_opciones = [None] + sorted(data['Semana'].unique())
    semana_seleccionada = st.sidebar.selectbox("Selecciona una semana 🗓️", options=semana_opciones)
    view = st.sidebar.radio("Selecciona la vista:", ("diaria", "semanal"))
    filtered_data = apply_filters(data, proveedores, plaza, categoria, None, semana_seleccionada, division, articulo)
    if view == "semanal":
        filtered_data = apply_weekly_view(filtered_data)
    col1, col2 = st.columns((1, 1))
    with col1:
        st.markdown('#### 🧮 KPI´s de Venta Perdida ')
        total_venta_perdida = data['VENTA_PERDIDA_PESOS'].sum()
        total_venta_perdida_filtrada = filtered_data['VENTA_PERDIDA_PESOS'].sum()
        porcentaje_acumulado = (total_venta_perdida_filtrada / total_venta_perdida) * 100
        comparacion_diaria = filtered_data.groupby('Fecha' if view == "diaria" else 'Semana')['VENTA_PERDIDA_PESOS'].sum().reset_index()
        comparacion_diaria = comparacion_diaria.merge(venta_pr_data.groupby('Día Contable' if view == "diaria" else 'Semana')['Venta Neta Total'].sum().reset_index(), left_on='Fecha' if view == "diaria" else 'Semana', right_on='Día Contable' if view == "diaria" else 'Semana', how='left')
        if not comparacion_diaria.empty:
            porcentaje_venta_perdida_dia = (total_venta_perdida_filtrada / comparacion_diaria['Venta Neta Total'].sum()) * 100
            st.metric(label="Total Venta Perdida (21/6/2024-Presente)", value=f"${total_venta_perdida_filtrada:,.0f}")
            st.metric(label="Proporción de la Venta Perdida Filtrada al Total", value=f"{porcentaje_acumulado:.2f}%")
            st.metric(label="Proporción de Venta Perdida respecto a la Venta Neta Total", value=f"{porcentaje_venta_perdida_dia:.2f}%")
        else:
            st.metric(label="Total Venta Perdida", value=f"${total_venta_perdida_filtrada:,.0f}")
            st.metric(label="% Acumulado", value=f"{porcentaje_acumulado:.2f}%")
            st.metric(label="% Venta Perdida del Día", value="N/A")
        st.markdown(f'#### 🕰️ Venta Perdida {view} ')
        st.plotly_chart(plot_venta_perdida(filtered_data, view), use_container_width=True)
    with col2:
        st.markdown('#### 📅 Venta Perdida Acumulada ')
        st.plotly_chart(make_donut_chart(filtered_data['VENTA_PERDIDA_PESOS'].sum(), total_venta_perdida, 'Acumulada', 'orange'), use_container_width=True)
    col3, col4 = st.columns((1, 1))
    with col3:
        st.markdown('#### ⚖️ Venta Perdida vs Venta Neta Total ')
        st.plotly_chart(plot_comparacion_venta_perdida_vs_neta(filtered_data, venta_pr_data, filtered_data['Fecha' if view == "diaria" else 'Semana'], view), use_container_width=True)
    with col4:
        st.markdown('#### 🏝️ Venta Perdida por Plaza ')
        st.plotly_chart(plot_venta_perdida_plaza(filtered_data), use_container_width=True)
    col5, col6 = st.columns((1, 1))
    with col5:
        st.markdown('#### 🔝 Top 10 Artículos con Mayor Venta Perdida ')
        st.plotly_chart(plot_articulos_venta_perdida(filtered_data), use_container_width=True)
    with col6:
        st.markdown('#### 🚩 Venta Perdida por Proveedor ')
        st.plotly_chart(plot_venta_perdida_proveedor(filtered_data, proveedores), use_container_width=True)
    col7, col8 = st.columns((1, 1))
    with col7:
        st.markdown('#### 🎢 Cambio porcentual de venta perdida ')
        st.plotly_chart(plot_venta_perdida_con_tendencia(filtered_data, view), use_container_width=True)
    with col8:
        st.markdown('#### 📶 Venta Perdida vs Venta Neta Total ')
        st.plotly_chart(plot_comparacion_venta_perdida_vs_neta_diaria(filtered_data, venta_pr_data, filtered_data['Fecha' if view == "diaria" else 'Semana'], view), use_container_width=True)
    st.markdown(f'#### Venta Perdida {view} por Mercado')
    st.plotly_chart(plot_venta_perdida_mercado(filtered_data, view), use_container_width=True)
else:
    st.warning("No se encontraron datos en la carpeta especificada.")

