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
# FUNCIONES CLAUDE
# ==============================

def llamar_claude(modelo, prompt):
    data = {
        "model": modelo,
        "max_tokens": 800,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(CLAUDE_URL, headers=HEADERS, json=data)

    print("STATUS:", response.status_code)
    print("RAW RESPONSE:", response.text)

    try:
        return response.json()["content"][0]["text"]
    except Exception as e:
        print("ERROR PARSEANDO CLAUDE:", e)
        return None


# ==============================
# PROMPTS
# ==============================

def prompt_haiku(noticia):
    return f"""
Analiza esta noticia geopolítica y económica.

TITULAR: {noticia['titulo']}
FUENTE: {noticia['fuente']}
REGIÓN: {noticia['region']}

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

TITULAR: {noticia['titulo']}
REGIÓN: {noticia['region']}

Haz un análisis AVANZADO:

- Explica causas ocultas
- Conecta con dinámicas globales
- Identifica consecuencias indirectas
- Evalúa impacto real para España (corto y medio plazo)

Formato:

<analisis_profundo>
Texto claro, directo y sin relleno.
</analisis_profundo>
"""


# ==============================
# PROCESAMIENTO
# ==============================

def procesar_noticia(noticia):
    try:
        # 🟢 1. HAiku (base)
        resultado_haiku = llamar_claude(
            "claude-3-5-haiku-latest",
            prompt_haiku(noticia)
        )

        # Extraer nivel impacto (simple)
        nivel = extraer_tag(resultado_haiku, "nivel_impacto")
        score = int(nivel) * 5

        analisis_final = resultado_haiku

        # 🔵 2. SONNET solo si importante
        if score >= 20:
            resultado_sonnet = llamar_claude(
                "claude-3-5-sonnet-latest",
                prompt_sonnet(noticia)
            )

            analisis_final += "\n\n" + resultado_sonnet

        return {
            "analisis": analisis_final,
            "score": score,
            "titulo_es": extraer_tag(resultado_haiku, "titulo_es")
        }

    except Exception as e:
        print("Error:", e)
        return None


# ==============================
# UTILIDADES
# ==============================

def extraer_tag(texto, tag):
    try:
        inicio = texto.split(f"<{tag}>")[1]
        return inicio.split(f"</{tag}>")[0].strip()
    except:
        return ""


# ==============================
# MAIN
# ==============================

def main():
    # Obtener noticias sin procesar
    response = supabase.table("noticias") \
        .select("*") \
        .eq("procesada", False) \
        .limit(20) \
        .execute()

    noticias = response.data

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

            print(f"✔ Procesada: {noticia['titulo']}")


if __name__ == "__main__":
    main()
