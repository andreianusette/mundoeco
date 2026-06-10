import streamlit as st
from supabase import create_client
from datetime import datetime
from email.utils import parsedate_to_datetime

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
    return resultado.data

noticias = cargar_noticias()

if not noticias:
    st.warning("No hay noticias aún. Espera a que se ejecute la ingesta.")
else:
    
    # VISTA 1: Lectura Rápida
    if vista == "📋 Lectura Rápida":
        st.subheader("5-8 Noticias clave del día")
        
        noticias_analizadas = [n for n in noticias if n.get('procesada') and n.get('analisis')][:8]
        
        if not noticias_analizadas:
            st.info("No hay análisis completados aún.")
        else:
            for noticia in noticias_analizadas:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {noticia['titulo']}")
                        st.caption(f"📰 {noticia['fuente']} | 🌍 {noticia['region'].upper()}")
                    with col2:
                        st.metric("Capa", noticia['capa'])
                    
                    st.markdown("**Análisis:**")
                    st.markdown(noticia['analisis'])
                    st.markdown(f"[Leer original →]({noticia['url']})")
    
    # VISTA 2: Explorar Todas
    elif vista == "🔍 Explorar Todas":
        st.subheader("Todas las noticias")
        
        fuentes_unicas = list(set(n['fuente'] for n in noticias))
        regiones_unicas = list(set(n['region'] for n in noticias))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_fuente = st.multiselect("Filtrar por fuente:", fuentes_unicas, default=None)
        with col2:
            filtro_region = st.multiselect("Filtrar por región:", regiones_unicas, default=None)
        with col3:
            procesada = st.selectbox("Estado:", ["Todas", "Con análisis", "Sin análisis"])
        
        # Aplicar filtros
        noticias_filtered = noticias
        if filtro_fuente:
            noticias_filtered = [n for n in noticias_filtered if n['fuente'] in filtro_fuente]
        if filtro_region:
            noticias_filtered = [n for n in noticias_filtered if n['region'] in filtro_region]
        if procesada == "Con análisis":
            noticias_filtered = [n for n in noticias_filtered if n.get('procesada')]
        elif procesada == "Sin análisis":
            noticias_filtered = [n for n in noticias_filtered if not n.get('procesada')]
        
        st.write(f"Total: **{len(noticias_filtered)}** noticias")
        
        for noticia in noticias_filtered:
            with st.container(border=True):
                st.markdown(f"**{noticia['titulo']}**")
                col1, col2, col3 = st.columns(3)
                col1.caption(f"📰 {noticia['fuente']}")
                col2.caption(f"🌍 {noticia['region']}")
                col3.caption(f"{'✅ Analizado' if noticia.get('procesada') else '⏳ Pendiente'}")
                
                if noticia.get('procesada') and noticia.get('analisis'):
                    with st.expander("Ver análisis"):
                        st.markdown(noticia['analisis'])
                
                st.markdown(f"[Leer →]({noticia['url']})")
    
    # VISTA 3: Por Región
    elif vista == "🏷️ Por Región":
        st.subheader("Noticias por región")
        
        regiones = sorted(set(n['region'] for n in noticias))
        for region in regiones:
            noticias_region = [n for n in noticias if n['region'] == region]
            with st.expander(f"**{region.upper()}** ({len(noticias_region)} noticias)"):
                for noticia in noticias_region[:5]:
                    st.markdown(f"- **{noticia['titulo']}** ({noticia['fuente']})")
                    if noticia.get('procesada') and noticia.get('analisis'):
                        st.caption(noticia['analisis'][:200] + "...")
    
    # VISTA 4: Estadísticas
    elif vista == "📊 Estadísticas":
        st.subheader("Estadísticas")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total noticias", len(noticias))
        col2.metric("Con análisis", len([n for n in noticias if n.get('procesada')]))
        col3.metric("Fuentes activas", len(set(n['fuente'] for n in noticias)))
        col4.metric("Regiones cubiertas", len(set(n['region'] for n in noticias)))
        
        st.write("**Noticias por fuente:**")
        fuentes = {}
        for n in noticias:
            fuentes[n['fuente']] = fuentes.get(n['fuente'], 0) + 1
        st.bar_chart(fuentes)
        
        st.write("**Noticias por región:**")
        regiones = {}
        for n in noticias:
            regiones[n['region']] = regiones.get(n['region'], 0) + 1
        st.bar_chart(regiones)

# Footer
st.divider()
st.caption("MundoEco MVP • Datos actualizados • Análisis con Claude API")
