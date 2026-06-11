import os
import json
import re
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
# HELPERS
# ==============================

def clean_text(texto):
    if not texto:
        return ""
    texto = texto.strip()
    texto = re.sub(r"```json", "", texto)
    texto = re.sub(r"```", "", texto)
    return texto.strip()


def parse_json(texto):
    try:
        texto = clean_text(texto)
        return json.loads(texto)
    except Exception as e:
        print("❌ JSON parse error:", e)
        print("RAW:", texto)
        return None


# ==============================
# CLAUDE CALL
# ==============================

def llamar_claude(modelo, prompt):
    try:
        response = requests.post(
            CLAUDE_URL,
            headers=HEADERS,
            json={
                "model": modelo,
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        print("STATUS:", response.status_code)
        print("RAW RESPONSE:", response.text)

        response.raise_for_status()

        data = response.json()

        content = data.get("content", [])
        if not content:
            return None

        return content[0].get("text", "")

    except Exception as e:
        print("❌ Claude error:", e)
        return None


# ==============================
# PROMPTS (JSON FORZADO)
# ==============================

def prompt_haiku(noticia):
    return f"""
Devuelve SOLO JSON válido, sin texto adicional.

Formato EXACTO:
{{
  "titulo_es": "string",
  "nivel_impacto": 1,
  "analisis": "string claro"
}}

NOTICIA:
{noticia.get('titulo','')}
REGION:
{noticia.get('region','')}
"""


def prompt_sonnet(noticia):
    return f"""
Devuelve SOLO JSON válido.

{{
  "analisis_profundo": "texto claro sin relleno"
}}

NOTICIA:
{noticia.get('titulo','')}
"""


# ==============================
# PROCESO
# ==============================

def procesar_noticia(noticia):
    try:
        raw = llamar_claude("claude-3-5-haiku-20240307", prompt_haiku(noticia))
        data = parse_json(raw)

        if not data:
            print("⚠️ Haiku inválido")
            return None

        nivel = data.get("nivel_impacto", 1)

        try:
            score = int(nivel) * 5
        except:
            score = 10

        analisis = data.get("analisis", "")

        # 🔥 blindaje extra
        if not analisis:
            analisis = "Sin análisis disponible"

        # SONNET solo si relevante
        if score >= 20:
            raw2 = llamar_claude("claude-3-5-sonnet-20241022", prompt_sonnet(noticia))
            data2 = parse_json(raw2)

            if data2 and data2.get("analisis_profundo"):
                analisis += "\n\n" + data2["analisis_profundo"]

        return {
            "analisis": analisis,
            "score": score,
            "titulo_es": data.get("titulo_es", noticia.get("titulo", ""))
        }

    except Exception as e:
        print("❌ Procesamiento error:", e)
        return None


# ==============================
# MAIN
# ==============================

def main():
    try:
        response = supabase.table("noticias") \
            .select("*") \
            .eq("procesada", False) \
            .order("id", desc=False) \
            .limit(20) \
            .execute()

        noticias = response.data or []

        print(f"📦 Noticias encontradas: {len(noticias)}")

        for noticia in noticias:

            resultado = procesar_noticia(noticia)

            if not resultado:
                print("⚠️ Skip noticia")
                continue

            # 🔥 UPDATE blindado
            res = supabase.table("noticias").update({
                "analisis": resultado["analisis"],
                "capa": resultado["score"],
                "titulo": resultado["titulo_es"],
                "procesada": True
            }).eq("id", noticia["id"]).execute()

            print("✔ UPDATE:", res)

    except Exception as e:
        print("❌ MAIN ERROR:", e)


if __name__ == "__main__":
    main()
