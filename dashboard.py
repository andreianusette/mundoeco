import streamlit as st
from supabase import create_client
from datetime import datetime

st.set_page_config(
    page_title="MundoEco",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# FUNCIÓN AUXILIAR: Formatea la fecha de Supabase a formato europeo legible (DD/MM/AAAA HH:MM)
def formatear_fecha_noticia(noticia_obj):
    fecha_cruda = noticia_obj.get('fecha') or noticia_obj.get('created_at')
    if not fecha_cruda:
        return "Fecha no disponible"
    
    try:
        if "T" in str(fecha_cruda):
            fecha_parte, hora_parte = str(fecha_cruda).split("T")
            hora_bonita = hora_parte[:5]
            año, mes, día = fecha_parte.split("-")
            return f"{día}/{mes}/{año} a las {hora_bonita}"
        elif " " in str(fecha_cruda):
            fecha_parte, hora_parte = str(fecha_cruda).split(" ")
            hora_bonita = hora_parte[:5]
            año, mes, día = fecha_parte.split("-")
            return f"{día}/{mes}/{año} a las {hora_bonita}"
        return str(fecha_cruda)
    except Exception:
        return str(fecha_cruda)

# Inicializar Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CACHÉ DE DATOS ---
@st.cache_data(ttl=300)
def cargar_noticias():
    # TODO: En el futuro podrías limitar aquí con .limit(200) para no saturar si la BD crece mucho
    resultado = supabase.table("noticias").select("*").order("fecha", desc=True).execute()
    return resultado.data if resultado.data else []

# Carga única de datos para toda la ejecución actual
noticias = cargar_noticias()

# --- EXTRACCIÓN DE FILTROS EN MEMORIA (¡Adiós lentitud!) ---
# Sacamos las fuentes y regiones directamente de las noticias ya cargadas, sin volver a llamar a la BD
fuentes_disponibles = sorted(list(set(n['fuente'] for n in noticias if n.get('fuente'))))
regiones_disponibles = sorted(list(set(n['region'] for n in noticias if n.get('region'))))

# --- INTERFAZ ---
st.title("🌍 MundoEco")
st.markdown("Análisis geopolítico y económico contextualizado para España")

st.sidebar.header("Filtros")
vista = st.sidebar.radio(
    "Selecciona vista:",
    ["📋 Lectura Rápida", "🔍 Explorar Todas", "🏷️ Por Región", "📊 Estadísticas"]
)

if not noticias:
    st.warning("No hay noticias aún. Espera a que se ejecute la ingesta.")
else:
    
    # ==================== VISTA: LECTURA RÁPIDA ====================
    if vista == "📋 Lectura Rápida":
        st.subheader("Geopolítica relevante para España (Puntaje >= 15)")
        
        noticias_relevantes = [n for n in noticias 
                               if n.get('procesada') 
                               and n.get('analisis') 
                               and n.get('capa', 1) >= 15][:8]
        
        if not noticias_relevantes:
            st.info("No hay análisis geopolítico relevante en este momento.")
        else:
            for noticia in noticias_relevantes:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {noticia['titulo']}")
                        fecha_txt = formatear_fecha_noticia(noticia)
                        st.caption(f"📰 {noticia['fuente']} | 🌍 {noticia['region'].upper()} | 🕒 {fecha_txt}")
                    with col2:
                        st.metric("Puntaje", f"{noticia.get('capa', '?')}/25")
                    
                    st.markdown(noticia['analisis'])
                    st.markdown(f"[Leer fuente original →]({noticia['url']})")
    
    # ==================== VISTA: EXPLORAR TODAS ====================
    elif vista == "🔍 Explorar Todas":
        st.subheader("Todas las noticias (análisis completo)")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_fuente = st.multiselect(
                "Filtrar por fuente:",
                fuentes_disponibles,
                default=None
            )
        with col2:
            filtro_region = st.multiselect(
                "Filtrar por región:",
                regiones_disponibles,
                default=None
            )
        with col3:
            filtro_puntaje = st.selectbox(
                "Mostrar:",
                ["Todas", "Geopolítica (>=15)", "Señales débiles (5-14)", "Ruido (<5)"]
            )
        
        # Aplicar filtros encadenados de forma eficiente
        noticias_filtered = noticias
        if filtro_fuente:
            noticias_filtered = [n for n in noticias_filtered if n.get('fuente') in filtro_fuente]
        if filtro_region:
            noticias_filtered = [n for n in noticias_filtered if n.get('region') in filtro_region]
        
        if filtro_puntaje == "Geopolítica (>=15)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) >= 15]
        elif filtro_puntaje == "Señales débiles (5-14)":
            noticias_filtered = [n for n in noticias_filtered if 5 <= n.get('capa', 1) < 15]
        elif filtro_puntaje == "Ruido (<5)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) < 5]
        
        st.write(f"Total encontrados: **{len(noticias_filtered)}** noticias")
        
        # Renderizado de noticias filtradas
        for noticia in noticias_filtered:
            with st.container(border=True):
                st.markdown(f"**{noticia['titulo']}**")
                col1, col2, col3, col4 = st.columns(4)
                
                fecha_txt = formatear_fecha_noticia(noticia)
                col1.caption(f"📰 {noticia['fuente']} | 🕒 {fecha_txt}")
                col2.caption(f"🌍 {str(noticia.get('region', '')).upper()}")
                col3.caption(f"{'✅ Analizado' if noticia.get('procesada') else '⏳ Pendiente'}")
                col4.metric("Puntaje", f"{noticia.get('capa', '?')}/25")
                
                if noticia.get('procesada') and noticia.get('analisis'):
                    with st.expander("Ver análisis completo"):
                        st.markdown(noticia['analisis'])
                
                if noticia.get('url'):
                    st.markdown(f"[Leer fuente original →]({noticia['url']})")
    
    # ==================== VISTA: POR REGIÓN ====================
    elif vista == "🏷️ Por Región":
        st.subheader("Geopolítica por región")
        
        if not regiones_disponibles:
            st.info("No hay regiones registradas.")
        else:
            for region in regiones_disponibles:
                noticias_region = [n for n in noticias if n.get('region') == region and n.get('capa', 1) >= 15]
                if noticias_region:
                    with st.expander(f"**{region.upper()}** ({len(noticias_region)} relevantes)"):
                        for noticia in noticias_region[:5]:
                            fecha_txt = formatear_fecha_noticia(noticia)
                            st.markdown(f"- **{noticia['titulo']}** (Puntaje: {noticia.get('capa', '?')} | 🕒 {fecha_txt})")
                            if noticia.get('procesada') and noticia.get('analisis'):
                                st.caption(noticia['analisis'][:300] + "...")
    
    # ==================== VISTA: ESTADÍSTICAS ====================
    elif vista == "📊 Estadísticas":
        st.subheader("Estadísticas geopolíticas")
        
        noticias_relevantes = [n for n in noticias if n.get('capa', 1) >= 15]
        noticias_debiles = [n for n in noticias if 5 <= n.get('capa', 1) < 15]
        noticias_ruido = [n for n in noticias if n.get('capa', 1) < 5]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total noticias", len(noticias))
        col2.metric("Geopolítica (>=15)", len(noticias_relevantes))
        col3.metric("Señales débiles", len(noticias_debiles))
        col4.metric("Ruido", len(noticias_ruido))
        
        # Gráfico por puntaje
        st.write("**Noticias por clasificación de impacto:**")
        puntajes = {"Geopolítica (>=15)": len(noticias_relevantes), 
                    "Señales débiles (5-14)": len(noticias_debiles), 
                    "Ruido (<5)": len(noticias_ruido)}
        st.bar_chart(puntajes)
        
        # Gráfico por fuentes relevantes
        st.write("**Fuentes con análisis relevante (Puntaje >= 15):**")
        fuentes_relevantes = {}
        for n in noticias_relevantes:
            f = n.get('fuente', 'Desconocida')
            fuentes_relevantes[f] = fuentes_relevantes.get(f, 0) + 1
        
        if fuentes_relevantes:
            st.bar_chart(fuentes_relevantes)
        else:
            st.info("No hay datos suficientes para mostrar el gráfico de fuentes.")

st.divider()
st.caption("MundoEco MVP • Análisis contextualizado para España • Filtrado por impacto geopolítico real")
