import os
import requests
from supabase import create_client

# ==============================
# CONFIG
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

HEADERS = {
    "x-api-key": CLAUDE_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# ==============================
# CLAUDE API
# ==============================

def llamar_claude(modelo, prompt):
    data = {
        "model": modelo,
        "max_tokens": 800,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(CLAUDE_URL, headers=HEADERS, json=data)

        print("STATUS:", response.status_code)
        print("RAW RESPONSE:", response.text)

        response.raise_for_status()

        data = response.json()

        content = data.get("content", [])
        if not isinstance(content, list) or len(content) == 0:
            return None

        first = content[0]
        if isinstance(first, dict):
            return first.get("text", "")

        return None

    except Exception as e:
        print("ERROR CLAUDE:", e)
        return None


# ==============================
# PROMPTS
# ==============================

def prompt_haiku(noticia):
    return f"""
Analiza esta noticia geopolítica y económica.

TITULAR: {noticia.get('titulo', '')}
FUENTE: {noticia.get('fuente', '')}
REGIÓN: {noticia.get('region', '')}

Responde SIEMPRE en este formato XML:

<titulo_es>Traducción al español</titulo_es>

<nivel_impacto>1-5</nivel_impacto>

<analisis>
1. ¿Por qué está pasando esto realmente?
2. ¿Cómo afecta a España?
3. ¿Cómo afecta al ciudadano medio?
</analisis>
"""


def prompt_sonnet(noticia):
    return f"""
Eres un analista geopolítico senior.

Analiza en profundidad esta noticia:

TITULAR: {noticia.get('titulo', '')}
REGIÓN: {noticia.get('region', '')}

Haz un análisis AVANZADO:

- Explica causas ocultas
- Conecta con dinámicas globales
- Identifica consecuencias indirectas
- Evalúa impacto real para España

Formato:

<analisis_profundo>
Texto claro, directo y sin relleno.
</analisis_profundo>
"""


# ==============================
# UTILIDADES
# ==============================

def extraer_tag(texto, tag):
    try:
        if not texto:
            return ""

        inicio = texto.split(f"<{tag}>")[1]
        return inicio.split(f"</{tag}>")[0].strip()
    except Exception:
        return ""


# ==============================
# PROCESAMIENTO
# ==============================

def procesar_noticia(noticia):
    try:
        resultado_haiku = llamar_claude(
            "claude-3-5-haiku-latest",
            prompt_haiku(noticia)
        )

        if not resultado_haiku:
            return None

        nivel = extraer_tag(resultado_haiku, "nivel_impacto")

        try:
            score = int(nivel) * 5
        except:
            score = 0

        analisis_final = resultado_haiku

        if score >= 20:
            resultado_sonnet = llamar_claude(
                "claude-3-5-sonnet-latest",
                prompt_sonnet(noticia)
            )

            if resultado_sonnet:
                analisis_final += "\n\n" + resultado_sonnet

        return {
            "analisis": analisis_final,
            "score": score,
            "titulo_es": extraer_tag(resultado_haiku, "titulo_es")
        }

    except Exception as e:
        print("Error procesando noticia:", e)
        return None


# ==============================
# MAIN
# ==============================

def main():
    try:
        response = supabase.table("noticias") \
            .select("*") \
            .eq("procesada", False) \
            .limit(20) \
            .execute()

        noticias = response.data or []

        print(f"Procesando {len(noticias)} noticias...")

        for noticia in noticias:
            resultado = procesar_noticia(noticia)

            if resultado:
                supabase.table("noticias").update({
                    "analisis": resultado["analisis"],
                    "capa": resultado["score"],
                    "titulo": resultado["titulo_es"],
                    "procesada": True
                }).eq("id", noticia["id"]).execute()

                print(f"✔ Procesada: {noticia.get('titulo')}")

    except Exception as e:
        print("ERROR GENERAL MAIN:", e)


if __name__ == "__main__":
    main()
