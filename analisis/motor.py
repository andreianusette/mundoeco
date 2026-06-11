import os
import json
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
# CLAUDE CALL
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
        if not content or not isinstance(content, list):
            return None

        text = content[0].get("text") if isinstance(content[0], dict) else None

        return text

    except Exception as e:
        print("ERROR CLAUDE:", e)
        return None


# ==============================
# PROMPTS (JSON OBLIGATORIO)
# ==============================

def prompt_haiku(noticia):
    return f"""
Eres un analista geopolítico.

Responde SOLO en JSON válido, sin texto adicional.

Formato obligatorio:
{{
  "titulo_es": "string",
  "nivel_impacto": 1,
  "analisis": "string claro y directo"
}}

NOTICIA:
Titulo: {noticia.get('titulo','')}
Fuente: {noticia.get('fuente','')}
Región: {noticia.get('region','')}
"""


def prompt_sonnet(noticia):
    return f"""
Eres un analista geopolítico senior.

Haz un análisis profundo.

Responde SOLO en JSON válido:

{{
  "analisis_profundo": "texto claro, sin relleno"
}}

NOTICIA:
{noticia.get('titulo','')}
Región: {noticia.get('region','')}
"""


# ==============================
# PARSER SEGURO
# ==============================

def parse_json(texto):
    try:
        if not texto:
            return None
        return json.loads(texto)
    except Exception as e:
        print("JSON PARSE ERROR:", e)
        return None


# ==============================
# PROCESAMIENTO
# ==============================

def procesar_noticia(noticia):
    try:
        raw = llamar_claude(
            "claude-3-5-haiku-latest",
            prompt_haiku(noticia)
        )

        data = parse_json(raw)

        if not data:
            print("❌ Haiku inválido")
            return None

        nivel = data.get("nivel_impacto", 1)

        try:
            score = int(nivel) * 5
        except:
            score = 10

        analisis_final = data.get("analisis", "")

        # 🔵 SONNET solo si relevante
        if score >= 20:
            raw2 = llamar_claude(
                "claude-3-5-sonnet-latest",
                prompt_sonnet(noticia)
            )

            data2 = parse_json(raw2)

            if data2:
                analisis_final += "\n\n" + data2.get("analisis_profundo", "")

        return {
            "analisis": analisis_final or "",
            "score": score,
            "titulo_es": data.get("titulo_es", "")
        }

    except Exception as e:
        print("ERROR procesando noticia:", e)
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

            if not resultado:
                print("⚠️ Noticia omitida")
                continue

            supabase.table("noticias").update({
                "analisis": resultado["analisis"],
                "capa": resultado["score"],
                "titulo": resultado["titulo_es"],
                "procesada": True
            }).eq("id", noticia["id"]).execute()

            print(f"✔ Procesada: {noticia.get('titulo')}")

    except Exception as e:
        print("ERROR MAIN:", e)


if __name__ == "__main__":
    main()
