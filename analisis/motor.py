import os
import json
import re
import requests
from supabase import create_client

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
        return None

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

        response.raise_for_status()
        data = response.json()
        content = data.get("content", [])
        if not content:
            return None
        return content[0].get("text", "")

    except Exception as e:
        print("❌ Claude error:", e)
        return None

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

def procesar_noticia(noticia):
    try:
        raw = llamar_claude("claude-haiku-4-5-20251001", prompt_haiku(noticia))
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

        if not analisis:
            analisis = "Sin análisis disponible"

        return {
            "analisis": analisis,
            "score": score,
            "titulo_es": data.get("titulo_es", noticia.get("titulo", ""))
        }

    except Exception as e:
        print("❌ Procesamiento error:", e)
        return None

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

            res = supabase.table("noticias").update({
                "analisis": resultado["analisis"],
                "capa": resultado["score"],
                "titulo": resultado["titulo_es"],
                "procesada": True
            }).eq("id", noticia["id"]).execute()

            print("✔ UPDATE OK")

    except Exception as e:
        print("❌ MAIN ERROR:", e)

if __name__ == "__main__":
    main()
