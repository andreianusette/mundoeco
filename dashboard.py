import streamlit as st
from supabase import create_client
from datetime import datetime

# Configurar página
st.set_page_config(
    page_title="MundoEco",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para reducir tamaño de letras de preguntas
st.markdown("""
<style>
    h3 { font-size: 1.2rem !important; }
    .stMarkdown h3 { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

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

# MEJORA FRONTLEND: Forzamos a Supabase a traer solo las 300 noticias MÁS RECIENTES.
# Tu base de datos sigue guardando las miles de noticias de tu corpus intactas,
# pero la web solo lee y procesa el bloque fresco para no saturar el navegador.
@st.cache_data(ttl=300)
def cargar_noticias():
    resultado = supabase.table("noticias")\
        .select("*")\
        .order("fecha", desc=True)\
        .limit(300)\
        .execute()
    return resultado.data

@st.cache_data(ttl=300)
def obtener_fuentes():
    noticias = cargar_noticias()
    return sorted(list(set(n['fuente'] for n in noticias)))

@st.cache_data(ttl=300)
def obtener_regiones():
    noticias = cargar_noticias()
    return sorted(list(set(n['region'] for n in noticias)))

noticias = cargar_noticias()

if not noticias:
    st.warning("No hay noticias aún. Espera a que se ejecute la ingesta.")
else:
    
    # VISTA 1: Lectura Rápida (Adaptada al nuevo motor)
    if vista == "📋 Lectura Rápida":
        st.subheader("Análisis estratégico del día para España")
        
        # Filtra las noticias que ya tienen el nuevo análisis listo
        noticias_analizadas = [n for n in noticias if n.get('procesada') and n.get('analisis')][:8]
        
        if not noticias_analizadas:
            st.info("No hay análisis completados en las últimas horas.")
        else:
            for noticia in noticias_analizadas:
                with st.container(border=True):
                    # Eliminamos la columna de la métrica 'capa' para dar espacio a un diseño más limpio
                    st.markdown(f"### {noticia['titulo']}")
                    st.caption(f"📰 {noticia['fuente']} | 🌍 {noticia['region'].upper()}")
                    st.markdown("---")
                    
                    # Mostrar las 3 preguntas con el formato dinámico y limpio en párrafos
                    analisis_text = noticia['analisis']
                    st.markdown(f"""
<div style="font-size: 0.95rem; line-height: 1.6; text-align: justify;">
{analisis_text}
</div>
""", unsafe_allow_html=True)
                    st.markdown(f"[Leer fuente original →]({noticia['url']})")
    
    # VISTA 2: Explorar Todas
    elif vista == "🔍 Explorar Todas":
        st.subheader("Últimas noticias añadidas al corpus")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_fuente = st.multiselect(
                "Filtrar por fuente:",
                obtener_fuentes(),
                default=None
            )
        with col2:
            filtro_region = st.multiselect(
                "Filtrar por región:",
                obtener_regiones(),
                default=None
            )
        with col3:
            procesada = st.selectbox(
                "Estado:",
                ["Todas", "Con análisis", "Sin análisis"]
            )
        
        # Aplicar filtros sobre la marcha
        noticias_filtered = noticias
        if filtro_fuente:
            noticias_filtered = [n for n in noticias_filtered if n['fuente'] in filtro_fuente]
        if filtro_region:
            noticias_filtered = [n for n in noticias_filtered if n['region'] in filtro_region]
        if procesada == "Con análisis":
            noticias_filtered = [n for n in noticias_filtered if n.get('procesada')]
        elif procesada == "Sin análisis":
            noticias_filtered = [n for n in noticias_filtered if not n.get('procesada')]
        
        st.write(f"Mostrando **{len(noticias_filtered)}** noticias recientes del hilo temporal")
        
        for noticia in noticias_filtered:
            with st.container(border=True):
                st.markdown(f"**{noticia['titulo']}**")
                col1, col2, col3 = st.columns(3)
                col1.caption(f"📰 {noticia['fuente']}")
                col2.caption(f"🌍 {noticia['region']}")
                col3.caption(f"{'✅ Analizado' if noticia.get('procesada') else '⏳ Pendiente'}")
                
                if noticia.get('procesada') and noticia.get('analisis'):
                    with st.expander("Ver análisis de impacto"):
                        st.markdown(noticia['analisis'])
                
                st.markdown(f"[Leer →]({noticia['url']})")
    
    # VISTA 3: Por Región
    elif vista == "🏷️ Por Región":
        st.subheader("Distribución geográfica reciente")
        
        regiones = sorted(set(n['region'] for n in noticias))
        for region in regiones:
            noticias_region = [n for n in noticias if n['region'] == region]
            with st.expander(f"**{region.upper()}** ({len(noticias_region)} noticias recientes)"):
                for noticia in noticias_region[:5]:
                    st.markdown(f"- **{noticia['titulo']}** ({noticia['fuente']})")
                    if noticia.get('procesada') and noticia.get('analisis'):
                        st.caption(noticia['analisis'][:200] + "...")
    
    # VISTA 4: Estadísticas
    elif vista == "📊 Estadísticas":
        st.subheader("Métricas de los últimos lotes")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ventana de análisis", len(noticias))
        col2.metric("Completadas", len([n for n in noticias if n.get('procesada')]))
        col3.metric("Fuentes activas", len(set(n['fuente'] for n in noticias)))
        col4.metric("Regiones cubiertas", len(set(n['region'] for n in noticias)))
        
        st.write("**Noticias recientes por fuente:**")
        fuentes = {}
        for n in noticias:
            fuentes[n['fuente']] = fuentes.get(n['fuente'], 0) + 1
        st.bar_chart(fuentes)
        
        st.write("**Noticias recientes por región:**")
        regiones = {}
        for n in noticias:
            regiones[n['region']] = regiones.get(n['region'], 0) + 1
        st.bar_chart(regiones)

# Footer
st.divider()
st.caption("MundoEco MVP • Análisis geopolítico dinámico • Powered by Claude Haiku")
