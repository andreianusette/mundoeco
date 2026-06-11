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

# Función para formatear la fecha de forma bonita
# FUNCIÓN DE FECHA MEJORADA: Detecta formatos de base de datos y formatos de texto RSS inglés
def formatear_fecha(fecha_str):
    if not fecha_str:
        return "Fecha reciente"
    
    # Limpiamos el texto por si trae microsegundos o zonas horarias molestas
    fecha_limpia = str(fecha_str).split(".")[0].split("+")[0].strip()
    
    # Diccionario para traducir los meses en inglés si vienen del RSS directo
    meses_en = {"Jan": "Ene", "Apr": "Abr", "Aug": "Ago", "Dec": "Dic"}
    
    try:
        # Intento 1: Formato estándar de base de datos con "T" (Ej: 2026-06-11T12:00:00)
        dt = datetime.strptime(fecha_limpia, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        try:
            # Intento 2: Formato estándar con espacio (Ej: 2026-06-11 12:00:00)
            dt = datetime.strptime(fecha_limpia, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            try:
                # Intento 3: Si viene el formato típico de RSS inglés (Ej: Thu, 11 Jun 2026 12:00:00)
                # Le quitamos el día de la semana (los primeros 5 caracteres "Thu, ")
                if "," in fecha_limpia:
                    fecha_limpia = fecha_limpia.split(",", 1)[1].strip()
                
                # Cortamos para quedarnos solo con "11 Jun 2026 12:00"
                partes = fecha_limpia.split(" ")
                if len(partes) >= 4:
                    dia = partes[0].zfill(2)
                    mes = partes[1]
                    mes = meses_en.get(mes, mes) # Traduce si es Jan, Apr, Aug o Dec
                    año = partes[2]
                    hora = partes[3][:5] # Coge solo HH:MM
                    return f"{dia} {mes} {año} - {hora}"
                return fecha_str
            except Exception:
                # Si todo falla, muestra los caracteres centrales para que al menos se entienda
                return str(fecha_str).replace("T", " ")[:16]

@st.cache_data(ttl=300)
def cargar_noticias():
    resultado = supabase.table("noticias")\
        .select("*")\
        .order("id", desc=True)\
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
    
    # VISTA 1: Lectura Rápida
    if vista == "📋 Lectura Rápida":
        st.subheader("Análisis estratégico del día para España")
        
        noticias_analizadas = [n for n in noticias if n.get('procesada') and n.get('analisis')][:8]
        
        if not noticias_analizadas:
            st.info("No hay análisis completados en las últimas horas.")
        else:
            for noticia in noticias_analizadas:
                with st.container(border=True):
                    # MEJORA 1: Muestra el título traducido si existe, si no el original
                    titulo_mostrar = noticia.get('titulo_es') if noticia.get('titulo_es') else noticia['titulo']
                    st.markdown(f"### {titulo_mostrar}")
                    
                    # MEJORA 2: Inclusión de Fecha y Hora en los créditos
                    fecha_bonita = formatear_fecha(noticia.get('fecha'))
                    st.caption(f"📰 {noticia['fuente']} | 🌍 {noticia['region'].upper()} | 🕒 {fecha_bonita}")
                    st.markdown("---")
                    
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
                titulo_mostrar = noticia.get('titulo_es') if noticia.get('titulo_es') else noticia['titulo']
                st.markdown(f"**{titulo_mostrar}**")
                
                col1, col2, col3 = st.columns(3)
                fecha_bonita = formatear_fecha(noticia.get('fecha'))
                col1.caption(f"📰 {noticia['fuente']} | 🕒 {fecha_bonita}")
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
                    titulo_mostrar = noticia.get('titulo_es') if noticia.get('titulo_es') else noticia['titulo']
                    st.markdown(f"- **{titulo_mostrar}** ({noticia['fuente']})")
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
