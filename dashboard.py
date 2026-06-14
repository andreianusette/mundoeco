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
    # Intentar primero con created_at que es el más fiable para "lo último insertado"
    fecha_cruda = noticia_obj.get('created_at') or noticia_obj.get('fecha')
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

# FIX: Usa la primera frase del análisis como título (ya en español y contextualizado).
def titulo_mostrar(noticia):
    analisis = noticia.get('analisis', '')
    if analisis:
        for separador in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
            idx = analisis.find(separador)
            if idx != -1 and idx < 200:  
                return analisis[:idx + 1].strip()
        if len(analisis) > 150:
            return analisis[:150].strip() + '…'
        return analisis.strip()
    return noticia.get('titulo') or '(Sin título)'

# Inicializar Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CACHÉ DE DATOS OPTIMIZADA ---
# Reducimos el TTL a 30 segundos para garantizar frescura visual automática.
# Filtramos en la consulta para evitar colapsar la RAM.
@st.cache_data(ttl=30)
def cargar_noticias():
    todas = []
    PAGE_SIZE = 1000
    offset = 0
    
    # Ponemos un límite máximo de seguridad (ej. 3000 noticias) para no saturar Railway
    MAX_NOTICIAS_TOTALES = 3000 

    while offset < MAX_NOTICIAS_TOTALES:
        resultado = (
            supabase.table("noticias")
            .select("*")
            # CRÍTICO: Ordenamos por created_at para asegurar que lo NUEVO salga arriba siempre
            .order("created_at", desc=True) 
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resultado.data if resultado.data else []
        todas.extend(batch)

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    # FILTRADO DE CALIDAD EN MEMORIA:
    # Si la noticia tiene un puntaje muy bajo (< 3) y tiene más de 3 días, podrías descartarla aquí.
    # De momento, dejamos pasar todo lo que quepa en el rango ordenado por novedad.
    return todas

# Carga única de datos
noticias = cargar_noticias()

# --- EXTRACCIÓN DE FILTROS EN MEMORIA ---
fuentes_disponibles = sorted(list(set(n['fuente'] for n in noticias if n.get('fuente'))))
regiones_disponibles = sorted(list(set(n['region'] for n in noticias if n.get('region'))))

# --- INTERFAZ ---
st.title("🌍 MundoEco")
st.markdown("Análisis geopolítico y económico contextualizado para España")

# Botón para forzar recarga
if st.sidebar.button("🔄 Actualizar ahora"):
    st.cache_data.clear()
    st.rerun()

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
        
        # 1. Filtramos TODAS las candidatas que cumplen el criterio de calidad
        candidatas_relevantes = [n for n in noticias 
                                 if n.get('procesada') 
                                 and n.get('analisis') 
                                 and n.get('capa', 1) >= 15]
        
        # 2. Algoritmo de diversificación para evitar monopolio de fuentes
        noticias_relevantes = []
        conteo_fuentes = {}
        MAX_POR_FUENTE = 2  # Ajusta este número (2 o 3) según cuánta variedad quieras forzar
        
        for noticia in candidatas_relevantes:
            fuente = noticia.get('fuente', 'Desconocida')
            
            # Inicializamos el contador de la fuente si no existe
            if fuente not in conteo_fuentes:
                conteo_fuentes[fuente] = 0
                
            # Si la fuente aún no ha superado el límite, añadimos la noticia
            if conteo_fuentes[fuente] < MAX_POR_FUENTE:
                noticias_relevantes.append(noticia)
                conteo_fuentes[fuente] += 1
                
            # Si ya tenemos 8 noticias variadas, paramos el bucle
            if len(noticias_relevantes) >= 8:
                break
        
        # 3. Renderizado en la interfaz (igual que antes, pero con la lista ya diversificada)
        if not noticias_relevantes:
            st.info("No hay análisis geopolítico relevante en este momento.")
        else:
            for noticia in noticias_relevantes:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {titulo_mostrar(noticia)}")
                        fecha_txt = formatear_fecha_noticia(noticia)
                        st.caption(f"📰 {noticia['fuente']} | 🌍 {str(noticia.get('region','')).upper()} | 🕒 {fecha_txt}")
                    with col2:
                        st.metric("Puntaje", f"{noticia.get('capa', '?')}/25")
                    
                    st.markdown(noticia['analisis'])
                    st.markdown(f"[Leer fuente original →]({noticia['url']})")
    
    # ==================== VISTA: EXPLORAR TODAS ====================
    elif vista == "🔍 Explorar Todas":
        st.subheader("Todas las noticias (análisis completo)")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_fuente = st.multiselect("Filtrar por fuente:", fuentes_disponibles, default=None)
        with col2:
            filtro_region = st.multiselect("Filtrar por región:", regiones_disponibles, default=None)
        with col3:
            # CAMBIO DE COMPORTAMIENTO: Por defecto ocultamos el ruido (<5) para limpiar la vista principal
            filtro_puntaje = st.selectbox(
                "Filtrar por relevancia:",
                ["Relevantes e Intermedias (>=5)", "Solo Geopolítica (>=15)", "Solo Señales débiles (5-14)", "Ver todo (Incluye Ruido <5)"]
            )
        
        # Aplicar filtros
        noticias_filtered = noticias
        if filtro_fuente:
            noticias_filtered = [n for n in noticias_filtered if n.get('fuente') in filtro_fuente]
        if filtro_region:
            noticias_filtered = [n for n in noticias_filtered if n.get('region') in filtro_region]
        
        # Lógica inteligente de filtrado según la selección del usuario
        if filtro_puntaje == "Relevantes e Intermedias (>=5)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) >= 5]
        elif filtro_puntaje == "Solo Geopolítica (>=15)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) >= 15]
        elif filtro_puntaje == "Solo Señales débiles (5-14)":
            noticias_filtered = [n for n in noticias_filtered if 5 <= n.get('capa', 1) < 15]
        # Si selecciona "Ver todo", no se filtra el ruido.

        st.write(f"Total encontrados: **{len(noticias_filtered)}** noticias")
        
        # Paginación visual
        ITEMS_POR_PAGINA = 50
        total_paginas = max(1, (len(noticias_filtered) - 1) // ITEMS_POR_PAGINA + 1)
        pagina_actual = st.number_input(
            f"Página (1–{total_paginas})",
            min_value=1, max_value=total_paginas, value=1, step=1
        )
        inicio = (pagina_actual - 1) * ITEMS_POR_PAGINA
        fin = inicio + ITEMS_POR_PAGINA
        noticias_pagina = noticias_filtered[inicio:fin]

        for noticia in noticias_pagina:
            with st.container(border=True):
                st.markdown(f"**{titulo_mostrar(noticia)}**")
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
                # Solo mostrar noticias verdaderamente relevantes por región (>=15) para no ensuciar
                noticias_region = [n for n in noticias if n.get('region') == region and n.get('capa', 1) >= 15]
                if noticias_region:
                    with st.expander(f"**{region.upper()}** ({len(noticias_region)} relevantes)"):
                        for noticia in noticias_region[:5]:
                            fecha_txt = formatear_fecha_noticia(noticia)
                            st.markdown(f"- **{titulo_mostrar(noticia)}** (Puntaje: {noticia.get('capa', '?')} | 🕒 {fecha_txt})")
                            if noticia.get('procesada') and noticia.get('analisis'):
                                st.caption(noticia['analisis'][:250] + "...")
    
    # ==================== VISTA: ESTADÍSTICAS ====================
    elif vista == "📊 Estadísticas":
        st.subheader("Estadísticas geopolíticas")
        
        noticias_relevantes = [n for n in noticias if n.get('capa', 1) >= 15]
        noticias_debiles = [n for n in noticias if 5 <= n.get('capa', 1) < 15]
        noticias_ruido = [n for n in noticias if n.get('capa', 1) < 5]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total noticias en memoria", len(noticias))
        col2.metric("Geopolítica (>=15)", len(noticias_relevantes))
        col3.metric("Señales débiles", len(noticias_debiles))
        col4.metric("Ruido", len(noticias_ruido))
        
        st.write("**Noticias por clasificación de impacto:**")
        puntajes = {"Geopolítica (>=15)": len(noticias_relevantes), 
                    "Señales débiles (5-14)": len(noticias_debiles), 
                    "Ruido (<5)": len(noticias_ruido)}
        st.bar_chart(puntajes)

st.divider()
st.caption("MundoEco MVP • Análisis geopolítico para España")
