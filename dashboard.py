import streamlit as st
import pandas as pd
from supabase import create_client
import os
from datetime import datetime, timedelta

# Configurar página
st.set_page_config(
    page_title="MundoEco",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Conectar a Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Título
st.title("🌍 MundoEco")
st.markdown("Análisis geopolítico y económico contextualizado para España")

# Sidebar
st.sidebar.header("Filtros")
vista = st.sidebar.radio(
    "Selecciona vista:",
    ["📋 Lectura Rápida", "🔍 Explorar Todas", "🏷️ Por Región", "📊 Estadísticas"]
)

# Cargar noticias
@st.cache_data(ttl=300)
def cargar_noticias():
    resultado = supabase.table("noticias").select("*").order("fecha", desc=True).execute()
    return pd.DataFrame(resultado.data)

df = cargar_noticias()

if df.empty:
    st.warning("No hay noticias aún. Espera a que se ejecute la ingesta.")
else:
    
    # VISTA 1: Lectura Rápida
    if vista == "📋 Lectura Rápida":
        st.subheader("5-8 Noticias clave del día")
        hoy = datetime.now().date()
        df_hoy = df[pd.to_datetime(df['fecha']).dt.date == hoy]
        df_hoy = df_hoy[df_hoy['procesada'] == True].head(8)
        
        if df_hoy.empty:
            st.info("No hay análisis completados para hoy aún.")
        else:
            for idx, row in df_hoy.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {row['titulo']}")
                        st.caption(f"📰 {row['fuente']} | 🌍 {row['region'].upper()}")
                    with col2:
                        st.metric("Capa", row['capa'])
                    
                    if row['procesada'] and row['analisis']:
                        st.markdown("**Análisis:**")
                        st.markdown(row['analisis'])
                    
                    st.markdown(f"[Leer original →]({row['url']})")
    
    # VISTA 2: Explorar Todas
    elif vista == "🔍 Explorar Todas":
        st.subheader("Todas las noticias")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_fuente = st.multiselect(
                "Filtrar por fuente:",
                df['fuente'].unique(),
                default=None
            )
        with col2:
            filtro_region = st.multiselect(
                "Filtrar por región:",
                df['region'].unique(),
                default=None
            )
        with col3:
            procesada = st.selectbox(
                "Estado:",
                ["Todas", "Con análisis", "Sin análisis"]
            )
        
        # Aplicar filtros
        df_filtered = df.copy()
        if filtro_fuente:
            df_filtered = df_filtered[df_filtered['fuente'].isin(filtro_fuente)]
        if filtro_region:
            df_filtered = df_filtered[df_filtered['region'].isin(filtro_region)]
        if procesada == "Con análisis":
            df_filtered = df_filtered[df_filtered['procesada'] == True]
        elif procesada == "Sin análisis":
            df_filtered = df_filtered[df_filtered['procesada'] == False]
        
        st.write(f"Total: **{len(df_filtered)}** noticias")
        
        for idx, row in df_filtered.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['titulo']}**")
                col1, col2, col3 = st.columns(3)
                col1.caption(f"📰 {row['fuente']}")
                col2.caption(f"🌍 {row['region']}")
                col3.caption(f"{'✅ Analizado' if row['procesada'] else '⏳ Pendiente'}")
                
                if row['procesada'] and row['analisis']:
                    with st.expander("Ver análisis"):
                        st.markdown(row['analisis'])
                
                st.markdown(f"[Leer →]({row['url']})")
    
    # VISTA 3: Por Región
    elif vista == "🏷️ Por Región":
        st.subheader("Noticias por región")
        
        regiones = df['region'].unique()
        for region in sorted(regiones):
            df_region = df[df['region'] == region]
            with st.expander(f"**{region.upper()}** ({len(df_region)} noticias)"):
                for idx, row in df_region.head(5).iterrows():
                    st.markdown(f"- **{row['titulo']}** ({row['fuente']})")
                    if row['procesada'] and row['analisis']:
                        st.caption(row['analisis'][:200] + "...")
    
    # VISTA 4: Estadísticas
    elif vista == "📊 Estadísticas":
        st.subheader("Estadísticas")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total noticias", len(df))
        col2.metric("Con análisis", len(df[df['procesada'] == True]))
        col3.metric("Fuentes activas", df['fuente'].nunique())
        col4.metric("Regiones cubiertas", df['region'].nunique())
        
        st.write("**Noticias por fuente:**")
        fuentes = df['fuente'].value_counts()
        st.bar_chart(fuentes)
        
        st.write("**Noticias por región:**")
        regiones = df['region'].value_counts()
        st.bar_chart(regiones)

# Footer
st.divider()
st.caption("MundoEco MVP • Datos actualizados cada 6 horas • Análisis con Claude API")
