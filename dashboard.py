import streamlit as st
from supabase import create_client
from datetime import datetime

st.set_page_config(
    page_title="MundoEco",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNCIÓN AUXILIAR: Formatear Fechas ---
def formatear_fecha_noticia(noticia_obj):
    fecha_cruda = noticia_obj.get('created_at') or noticia_obj.get('fecha')
    if not fecha_cruda:
        return "Fecha no disponible"
    try:
        if "T" in str(fecha_cruda):
            fecha_parte, hora_parte = str(fecha_cruda).split("T")
            return f"{fecha_parte.split('-')[2]}/{fecha_parte.split('-')[1]}/{fecha_parte.split('-')[0]} a las {hora_parte[:5]}"
        elif " " in str(fecha_cruda):
            fecha_parte, hora_parte = str(fecha_cruda).split(" ")
            return f"{fecha_parte.split('-')[2]}/{fecha_parte.split('-')[1]}/{fecha_parte.split('-')[0]} a las {hora_parte[:5]}"
        return str(fecha_cruda)
    except Exception:
        return str(fecha_cruda)

# --- FIX ROBUSTO: Generar Títulos Atractivos ---
def titulo_mostrar(noticia):
    analisis = noticia.get('analisis', '')
    titulo_original = noticia.get('titulo', '').strip()
    
    if analisis:
        # Intentamos extraer la primera frase del análisis de Claude
        for separador in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
            idx = analisis.find(separador)
            # Si encuentra un punto en los primeros 120 caracteres, asumimos que es un buen titular
            if idx != -1 and 15 < idx < 120:  
                return analisis[:idx + 1].strip()
        
        # Si no hay un punto limpio al inicio, generamos un extracto corto del análisis
        if len(analisis) > 80:
            return analisis[:80].strip() + '...'
            
    # Si todo lo anterior falla o no hay análisis, usamos el título original
    return titulo_original if titulo_original else "(Noticia sin título)"

# --- INICIALIZAR SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CACHÉ DE DATOS ---
@st.cache_data(ttl=30)
def cargar_noticias():
    todas = []
    PAGE_SIZE = 1000
    offset = 0
    MAX_NOTICIAS_TOTALES = 2500 

    while offset < MAX_NOTICIAS_TOTALES:
        resultado = (
            supabase.table("noticias")
            .select("*")
            .order("created_at", desc=True) 
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resultado.data if resultado.data else []
        todas.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return todas

noticias = cargar_noticias()

# Extracción de filtros
fuentes_disponibles = sorted(list(set(n['fuente'] for n in noticias if n.get('fuente'))))
regiones_disponibles = sorted(list(set(n['region'] for n in noticias if n.get('region'))))

# --- INTERFAZ FRONTEND ---
st.title("🌍 MundoEco")
st.markdown("### *Inteligencia Geopolítica y Económica Contextualizada para España*")
st.write("---")

# Botón de actualización forzada en el Sidebar con estilo estético
if st.sidebar.button("🔄 Sincronizar con Supabase"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.header("Navegación y Filtros")
vista = st.sidebar.radio(
    "Selecciona sección:",
    ["📋 Portada: Lectura Rápida", "🔍 Explorar Hemeroteca", "🏷️ Análisis por Región", "📊 Panel de Impacto"]
)

if not noticias:
    st.warning("Aún no hay noticias indexadas. Comprueba el script de ingesta.")
else:
    
    # ==================== VISTA: LECTURA RÁPIDA (PORTADA NUEVA) ====================
    if vista == "📋 Portada: Lectura Rápida":
        st.subheader("⚡ Lo más relevante del panorama internacional")
        st.caption("Últimos análisis críticos diversificados por procedencia (Filtrado de Impacto >= 15/25)")
        
        candidatas = [n for n in noticias if n.get('procesada') and n.get('analisis') and n.get('capa', 1) >= 15]
        
        # Diversificación inteligente
        noticias_portada = []
        conteo_fuentes = {}
        MAX_POR_FUENTE = 2  
        
        for noticia in candidatas:
            fuente = noticia.get('fuente', 'Desconocida')
            if fuente not in conteo_fuentes:
                conteo_fuentes[fuente] = 0
            if conteo_fuentes[fuente] < MAX_POR_FUENTE:
                noticias_portada.append(noticia)
                conteo_fuentes[fuente] += 1
            if len(noticias_portada) >= 8:
                break
        
        if not noticias_portada:
            st.info("No se han detectado alertas geopolíticas de alto impacto en las últimas horas.")
        else:
            # Renderizado en cuadrícula o tarjetas individuales con reborde limpio
            for noticia in noticias_portada:
                # CREACIÓN DE LA TARJETA CON REBORDE
                with st.container(border=True):
                    # Diseño asimétrico: Título e Info a la izquierda, Métrica de impacto a la derecha
                    col_texto, col_metrica = st.columns([5, 1])
                    
                    with col_texto:
                        # Forzamos un emoticón según la región para darle dinamismo visual
                        region_flag = "🌐"
                        reg = str(noticia.get('region', '')).lower()
                        if 'ue' in reg or 'europa' in reg: region_flag = "🇪🇺"
                        elif 'usa' in reg or 'eeuu' in reg: region_flag = "🇺🇸"
                        elif 'china' in reg: region_flag = "🇨🇳"
                        
                        st.markdown(f"#### {region_flag} {titulo_mostrar(noticia)}")
                        
                        fecha_txt = formatear_fecha_noticia(noticia)
                        st.caption(f"**Fuente:** {noticia['fuente']}  |  **Actualizado:** {fecha_txt}")
                    
                    with col_metrica:
                        # El puntaje actúa como un "badge" o medidor de temperatura de la noticia
                        st.metric(label="Relevancia", value=f"{noticia.get('capa', '?')}/25")
                    
                    # --- GESTIÓN DEL TEXTO LARGO (ENTRADILLA) ---
                    analisis_completo = noticia['analisis']
                    
                    # Mostramos solo los primeros 250 caracteres como gancho de lectura
                    entradilla = analisis_completo[:250] + "..." if len(analisis_completo) > 250 else analisis_completo
                    st.markdown(f"*{entradilla}*")
                    
                    # El resto del análisis queda elegantemente recogido
                    with st.expander("🔎 Desplegar análisis estratégico completo e implicaciones"):
                        st.markdown(analisis_completo)
                        st.markdown(f"🔗 [Leer artículo original en {noticia['fuente']}]({noticia['url']})")

    # ==================== VISTA: EXPLORAR HEMEROTECA ====================
    elif vista == "🔍 Explorar Hemeroteca":
        st.subheader("🔍 Buscador general de registros analizados")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_fuente = st.multiselect("Filtrar por origen:", fuentes_disponibles, default=None)
        with col2:
            filtro_region = st.multiselect("Filtrar por área geopolítica:", regiones_disponibles, default=None)
        with col3:
            filtro_puntaje = st.selectbox(
                "Rango de alertas:",
                ["Relevancia Media y Alta (>=5)", "Solo Alertas Críticas (>=15)", "Solo Señales Débiles (5-14)", "Ver todo el histórico (Incluye Ruido)"]
            )
        
        noticias_filtered = noticias
        if filtro_fuente:
            noticias_filtered = [n for n in noticias_filtered if n.get('fuente') in filtro_fuente]
        if filtro_region:
            noticias_filtered = [n for n in noticias_filtered if n.get('region') in filtro_region]
        
        if filtro_puntaje == "Relevancia Media y Alta (>=5)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) >= 5]
        elif filtro_puntaje == "Solo Alertas Críticas (>=15)":
            noticias_filtered = [n for n in noticias_filtered if n.get('capa', 1) >= 15]
        elif filtro_puntaje == "Solo Señales Débiles (5-14)":
            noticias_filtered = [n for n in noticias_filtered if 5 <= n.get('capa', 1) < 15]
        
        st.write(f"Registros encontrados: **{len(noticias_filtered)}**")
        
        ITEMS_POR_PAGINA = 30
        total_paginas = max(1, (len(noticias_filtered) - 1) // ITEMS_POR_PAGINA + 1)
        pagina_actual = st.number_input(f"Página", min_value=1, max_value=total_paginas, value=1, step=1)
        
        inicio = (pagina_actual - 1) * ITEMS_POR_PAGINA
        fin = inicio + ITEMS_POR_PAGINA
        
        for noticia in noticias_filtered[inicio:fin]:
            with st.container(border=True):
                st.markdown(f"##### {titulo_mostrar(noticia)}")
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.caption(f"📰 {noticia['fuente']} | 🕒 {formatear_fecha_noticia(noticia)}")
                c2.caption(f"🌍 Región: {str(noticia.get('region', '')).upper()}")
                c3.caption(f"Impacto: **{noticia.get('capa', '?')}/25**")
                
                if noticia.get('procesada') and noticia.get('analisis'):
                    with st.expander("Revisar informe de IA"):
                        st.markdown(noticia['analisis'])
                        if noticia.get('url'):
                            st.markdown(f"[Enlace original →]({noticia['url']})")

    # ==================== VISTA: POR REGIÓN ====================
    elif vista == "🏷️ Análisis por Región":
        st.subheader("📌 Cuadro de mando por demarcación geográfica")
        if not regiones_disponibles:
            st.info("Asignando regiones a los flujos entrantes...")
        else:
            for region in regiones_disponibles:
                noticias_region = [n for n in noticias if n.get('region') == region and n.get('capa', 1) >= 15]
                if noticias_region:
                    with st.expander(f"🗺️ **{region.upper()}** — ({len(noticias_region)} análisis de impacto elevado)"):
                        for noticia in noticias_region[:5]:
                            st.markdown(f"• **{titulo_mostrar(noticia)}** ({noticia.get('capa')} pts)")
                            st.caption(noticia['analisis'][:180] + "...")

    # ==================== VISTA: ESTADÍSTICAS ====================
    elif vista == "📊 Panel de Impacto":
        st.subheader("Metrística de flujo de información")
        n_relevantes = len([n for n in noticias if n.get('capa', 1) >= 15])
        n_debiles = len([n for n in noticias if 5 <= n.get('capa', 1) < 15])
        n_ruido = len([n for n in noticias if n.get('capa', 1) < 5])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Alertas Geopolíticas", n_relevantes)
        col2.metric("Tendencias / Señales Débiles", n_debiles)
        col3.metric("Ruido Informativo Filtrado", n_ruido)
        
        st.bar_chart({"Críticas": n_relevantes, "Intermedias": n_debiles, "Descartadas": n_ruido})
