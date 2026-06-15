import streamlit as st
from supabase import create_client
from datetime import datetime
import re

st.set_page_config(
    page_title="MundoEco",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# UTILIDADES
# ============================================================

def score(noticia):
    try:
        return int(noticia.get("capa") or 0)
    except Exception:
        return 0

def impacto_badge(valor):
    if valor >= 20: return "🔴 CRÍTICA"
    if valor >= 15: return "🟠 ALTA"
    if valor >= 10: return "🟡 MEDIA"
    if valor >= 5:  return "🟢 BAJA"
    return "⚪ RUIDO"

def formatear_fecha_noticia(noticia_obj):
    fecha_cruda = noticia_obj.get('created_at') or noticia_obj.get('fecha')
    if not fecha_cruda:
        return "Fecha no disponible"
    try:
        fecha_limpia = str(fecha_cruda).replace("Z", "+00:00")
        dt = datetime.fromisoformat(fecha_limpia)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(fecha_cruda)[:16]

def titulo_mostrar(noticia):
    titulo_es = noticia.get('titulo_es', '').strip()
    if titulo_es:
        return titulo_es
    titulo_original = noticia.get('titulo', '').strip()
    return titulo_original if titulo_original else "(Noticia sin título)"

PATRONES_METADATOS = [
    r"^CATEGORÍA:.*",
    r"^PUNTAJE IMPACTO.*",
    r"^VECTORES.*",
    r"^- Cadena suministro.*",
    r"^- Economía eurozona.*",
    r"^- Seguridad España.*",
    r"^Promedio:.*",
    r"^RAZÓN:.*",
    r"^\(No es geopolítica.*",
    r"^---.*",
    r"^S=.*",
]

def limpiar_lineas(texto):
    lineas = texto.split('\n')
    resultado = []
    for linea in lineas:
        linea_strip = linea.strip()
        if not any(re.match(p, linea_strip) for p in PATRONES_METADATOS):
            resultado.append(linea)
    return '\n'.join(resultado)

def extracto_card(analisis):
    if not analisis:
        return ""
    texto = limpiar_lineas(analisis)
    texto = re.sub(r"[123]️⃣ .*?\?", "", texto)
    palabras = ' '.join(texto.split()).split()
    if len(palabras) <= 50:
        return ' '.join(palabras)
    return ' '.join(palabras[:50]) + '...'

def analisis_formateado(analisis):
    if not analisis:
        return ""
    resultado = limpiar_lineas(analisis)
    resultado = re.sub(r"1️⃣ ¿POR QUÉ ESTÁ PASANDO REALMENTE\?", "**¿Por qué pasa esto?**", resultado)
    resultado = re.sub(r"2️⃣ ¿CÓMO AFECTA A ESPAÑA\?", "**¿Cómo afecta a España?**", resultado)
    resultado = re.sub(r"3️⃣ ¿Y A MÍ\?", "**¿Y a mí?**", resultado)
    return resultado.strip()

MAPA_REGIONES = {
    "europa": "🇪🇺", "union europea": "🇪🇺", "ue": "🇪🇺",
    "eu": "🇪🇺", "europa occidental": "🇪🇺",
    "usa": "🇺🇸", "eeuu": "🇺🇸", "estados unidos": "🇺🇸",
    "china": "🇨🇳", "rusia": "🇷🇺",
    "oriente medio": "🌙", "medio oriente": "🌙",
    "africa": "🌍", "áfrica": "🌍",
    "asia": "🌏", "asia pacifico": "🌏",
    "latinoamerica": "🌎", "america latina": "🌎",
}

def flag_region(noticia):
    reg = str(noticia.get('region', '')).lower().strip()
    for clave, emoji in MAPA_REGIONES.items():
        if clave in reg:
            return emoji
    return "🌐"

# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=300)
def cargar_noticias():
    try:
        todas = []
        PAGE_SIZE = 1000
        offset = 0
        MAX_NOTICIAS_TOTALES = 1500
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
    except Exception as e:
        st.error(f"Error conectando con Supabase: {e}")
        return []

noticias = cargar_noticias()

fuentes_disponibles = sorted(set(n.get('fuente') for n in noticias if n.get('fuente')))
regiones_disponibles = sorted(set(n.get('region') for n in noticias if n.get('region')))

# ============================================================
# INTERFAZ
# ============================================================

st.title("🌍 MundoEco")
st.markdown("### *Inteligencia Geopolítica y Económica para España*")
st.write("---")

if st.sidebar.button("🔄 Sincronizar"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.header("Navegación")
vista = st.sidebar.radio(
    "Sección:",
    ["⚡ Portada", "🔍 Hemeroteca", "🌎 Regiones"]
)

if not noticias:
    st.warning("Aún no hay noticias indexadas. Comprueba el script de ingesta.")
else:

    # ==================== PORTADA ====================
    if vista == "⚡ Portada":

        candidatas = [
            n for n in noticias
            if n.get('procesada') and n.get('analisis') and score(n) >= 15
        ]
        candidatas = sorted(candidatas, key=lambda x: (score(x)), reverse=True)

        criticas = [n for n in candidatas if score(n) >= 20]
        altas    = [n for n in candidatas if 15 <= score(n) < 20]

        def mostrar_cards(lista, limite=4):
            mostradas = 0
            conteo_fuentes = {}
            for noticia in lista:
                if mostradas >= limite:
                    break
                fuente = noticia.get('fuente', 'Desconocida')
                conteo_fuentes.setdefault(fuente, 0)
                if conteo_fuentes[fuente] >= 2:
                    continue
                conteo_fuentes[fuente] += 1
                with st.container(border=True):
                    st.markdown(f"#### {flag_region(noticia)} {titulo_mostrar(noticia)}")
                    valor = score(noticia)
                    st.caption(
                        f"📰 {noticia.get('fuente', '?')} · "
                        f"{impacto_badge(valor)} · "
                        f"⚡ {valor}/25 · "
                        f"🕒 {formatear_fecha_noticia(noticia)}"
                    )
                    extracto = extracto_card(noticia.get('analisis', ''))
                    if extracto:
                        st.markdown(f"*{extracto}*")
                    with st.expander("📖 Ver análisis completo"):
                        st.markdown(analisis_formateado(noticia.get('analisis', '')))
                        if noticia.get('url'):
                            st.markdown(f"🔗 [Leer artículo original en {noticia.get('fuente', 'Fuente')}]({noticia.get('url')})")
                mostradas += 1

        if criticas:
            st.subheader("🚨 Alertas críticas")
            mostrar_cards(criticas, limite=4)

        if altas:
            st.subheader("🟠 Alta relevancia")
            mostrar_cards(altas, limite=4)

        if not criticas and not altas:
            st.info("No se han detectado alertas de alto impacto en las últimas horas.")

    # ==================== HEMEROTECA ====================
    elif vista == "🔍 Hemeroteca":
        st.subheader("🔍 Buscador de registros analizados")

        busqueda_texto = st.text_input(
            "Buscar por palabra clave:",
            placeholder="Ej. Aranceles, Gas, OTAN, Semiconductores..."
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_fuente = st.multiselect("Origen:", fuentes_disponibles)
        with col2:
            filtro_region = st.multiselect("Área geopolítica:", regiones_disponibles)
        with col3:
            filtro_puntaje = st.selectbox(
                "Relevancia:",
                ["Media y Alta (≥5)", "Solo Críticas (≥15)", "Señales Débiles (5-14)", "Todo el histórico"]
            )

        noticias_filtered = list(noticias)

        if busqueda_texto:
            terminos = busqueda_texto.lower().split()
            def contiene_terminos(n):
                haystack = (
                    n.get("analisis", "") + " " +
                    n.get("titulo", "") + " " +
                    n.get("titulo_es", "")
                ).lower()
                return all(t in haystack for t in terminos)
            noticias_filtered = [n for n in noticias_filtered if contiene_terminos(n)]

        if filtro_fuente:
            noticias_filtered = [n for n in noticias_filtered if n.get('fuente') in filtro_fuente]
        if filtro_region:
            noticias_filtered = [n for n in noticias_filtered if n.get('region') in filtro_region]

        if filtro_puntaje == "Media y Alta (≥5)":
            noticias_filtered = [n for n in noticias_filtered if score(n) >= 5]
        elif filtro_puntaje == "Solo Críticas (≥15)":
            noticias_filtered = [n for n in noticias_filtered if score(n) >= 15]
        elif filtro_puntaje == "Señales Débiles (5-14)":
            noticias_filtered = [n for n in noticias_filtered if 5 <= score(n) < 15]

        st.write(f"Registros encontrados: **{len(noticias_filtered)}**")

        ITEMS_POR_PAGINA = 30
        total_paginas = max(1, (len(noticias_filtered) - 1) // ITEMS_POR_PAGINA + 1)
        pagina_actual = st.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1)
        inicio = (pagina_actual - 1) * ITEMS_POR_PAGINA
        fin = inicio + ITEMS_POR_PAGINA

        for noticia in noticias_filtered[inicio:fin]:
            with st.container(border=True):
                st.markdown(f"##### {flag_region(noticia)} {titulo_mostrar(noticia)}")
                valor = score(noticia)
                st.caption(
                    f"📰 {noticia.get('fuente', '?')} · "
                    f"{impacto_badge(valor)} · "
                    f"⚡ {valor}/25 · "
                    f"🕒 {formatear_fecha_noticia(noticia)}"
                )
                if noticia.get('procesada') and noticia.get('analisis'):
                    with st.expander("Ver análisis"):
                        st.markdown(analisis_formateado(noticia.get('analisis', '')))
                        if noticia.get('url'):
                            st.markdown(f"[Leer artículo original →]({noticia.get('url')})")

    # ==================== REGIONES ====================
    elif vista == "🌎 Regiones":
        st.subheader("📌 Análisis por área geopolítica")
        if not regiones_disponibles:
            st.info("Asignando regiones a los flujos entrantes...")
        else:
            for region in regiones_disponibles:
                noticias_region = [
                    n for n in noticias
                    if n.get('region') == region and score(n) >= 15
                ]
                noticias_region = sorted(noticias_region, key=score, reverse=True)
                if noticias_region:
                    flag = flag_region(noticias_region[0])
                    with st.expander(f"{flag} **{region.upper()}** — {len(noticias_region)} análisis de alto impacto"):
                        for noticia in noticias_region[:5]:
                            valor = score(noticia)
                            st.markdown(f"**{impacto_badge(valor)} · {titulo_mostrar(noticia)}**")
                            extracto = extracto_card(noticia.get('analisis', ''))
                            if extracto:
                                st.caption(extracto)
                            st.write("")

# ============================================================
st.divider()
st.caption("MundoEco MVP · v6.0 · Inteligencia geopolítica para España")
