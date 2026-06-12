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
        # Si viene en formato ISO de Supabase (ej: 2026-06-12T14:30:00...)
        if "T" in str(fecha_cruda):
            fecha_parte, hora_parte = str(fecha_cruda).split("T")
            hora_bonita = hora_parte[:5]
            año, mes, día = fecha_parte.split("-")
            return f"{día}/{mes}/{año} a las {hora_bonita}"
        # Si viene en formato plano (ej: 2026-06-12 14:30:00)
        elif " " in str(fecha_cruda):
            fecha_parte, hora_parte = str(fecha_cruda).split(" ")
            hora_bonita = hora_parte[:5]
            año, mes, día = fecha_parte.split("-")
            return f"{día}/{mes}/{año} a las {hora_bonita}"
        return str(fecha_cruda)
    except Exception:
        return str(fecha_cruda)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🌍 MundoEco")
st.markdown("Análisis geopolítico y económico contextualizado para España")

st.sidebar.header("Filtros")
vista = st.sidebar.radio(
    "Selecciona vista:",
    ["📋 Lectura Rápida", "🔍 Explorar Todas", "🏷️ Por Región", "📊 Estadísticas"]
)

@st.cache_data(ttl=300)
def cargar_noticias():
    resultado = supabase.table("noticias").select("*").order("fecha", desc=True).execute()
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
    
    if vista == "📋 Lectura Rápida":
        st.subheader("Geopolítica relevante para España (Puntaje >= 15)")
        
        # FILTRAR: Solo noticias con puntaje >= 15 y procesadas
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
                        # CAMBIO AQUÍ: Añadida la fecha formateada en la Lectura Rápida
                        fecha_txt = formatear_fecha_noticia(noticia)
                        st.caption(f"📰 {noticia['fuente']} | 🌍 {noticia['region'].upper()} | 🕒 {fecha_txt}")
                    with col2:
                        st.metric("Puntaje", f"{noticia.get('capa', '?')}/25")
                    
                    st.markdown(noticia['analisis'])
                    st.markdown(f"[Leer fuente original →]({noticia['url']})")
    
    elif vista == "🔍 Explorar Todas":
        st.subheader("Todas las noticias (análisis completo)")
        
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
            filtro_puntaje = st.selectbox(
                "Mostrar:",
                ["Todas", "Geopolítica (>=15)", "Señales débiles (5-14)", "Ruido (<5)"]
            )
        
        noticias_filtered = noticias
        if filtro_fuente:
            noticias_filtered = [n for n in noticias_filtered if n['fuente'] in filtro_fuente]
        if filtro_region:
            noticias_filtered = [n for n in noticias_filtered if n['region'] in filtro_region]
        
        if filtro_puntaje == "Geopolítica (>=15)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) >= 15]
        elif filtro_puntaje == "Señales débiles (5-14)":
            noticias_filtered = [n for n in noticias_filtered if 5 <= n.get('capa', 1) < 15]
        elif filtro_puntaje == "Ruido (<5)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) < 5]
        
        st.write(f"Total: **{len(noticias_filtered)}** noticias")
        
        for noticia in noticias_filtered:
            with st.container(border=True):
                st.markdown(f"**{noticia['titulo']}**")
                col1, col2, col3, col4 = st.columns(4)
                
                # CAMBIO AQUÍ: Añadida la fecha formateada en la pestaña Explorar Todas
                fecha_txt = formatear_fecha_noticia(noticia)
                col1.caption(f"📰 {noticia['fuente']} | 🕒 {fecha_txt}")
                col2.caption(f"🌍 {noticia['region']}")
                col3.caption(f"{'✅ Analizado' if noticia.get('procesada') else '⏳ Pendiente'}")
                col4.metric("Puntaje", f"{noticia.get('capa', '?')}/25")
                
                if noticia.get('procesada') and noticia.get('analisis'):
                    with st.expander("Ver análisis completo"):
                        st.markdown(noticia['analisis'])
                
                st.markdown(f"[Leer →]({noticia['url']})")
    
    elif vista == "🏷️ Por Región":
        st.subheader("Geopolítica por región")
        
        regiones = sorted(set(n['region'] for n in noticias))
        for region in regiones:
            noticias_region = [n for n in noticias if n['region'] == region and n.get('capa', 1) >= 15]
            if noticias_region:
                with st.expander(f"**{region.upper()}** ({len(noticias_region)} relevantes)"):
                    for noticia in noticias_region[:5]:
                        fecha_txt = formatear_fecha_noticia(noticia)
                        st.markdown(f"- **{noticia['titulo']}** (Puntaje: {noticia.get('capa', '?')} | 🕒 {fecha_txt})")
                        if noticia.get('procesada') and noticia.get('analisis'):
                            st.caption(noticia['analisis'][:300] + "...")
    
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
        
        st.write("**Noticias por puntaje:**")
        puntajes = {}
        for n in noticias:
            capa = n.get('capa', 1)
            if capa >= 15:
                cat = "Geopolítica (>=15)"
            elif capa >= 5:
                cat = "Señales débiles (5-14)"
            else:
                cat = "Ruido (<5)"
            puntajes[cat] = puntajes.get(cat, 0) + 1
        st.bar_chart(puntajes)
        
        st.write("**Fuentes con análisis relevante:**")
        fuentes_relevantes = {}
        for n in noticias_relevantes:
            fuentes_relevantes[n['fuente']] = fuentes_relevantes.get(n['fuente'], 0) + 1
        st.bar_chart(fuentes_relevantes)

st.divider()
st.caption("MundoEco MVP • Análisis contextualizado para España • Filtrado por impacto geopolítico real")
