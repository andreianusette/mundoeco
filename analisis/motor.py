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
                "max_tokens": 1200,
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
INSTRUCCIONES ESTRICTAS - NO IMPROVISES

Tu tarea: analizar la noticia y devolver JSON válido. NADA MÁS.

NOTICIA:
Titular: {noticia.get('titulo','')}
Resumen: {noticia.get('resumen','')}
Región: {noticia.get('region','')}
Fuente: {noticia.get('fuente','')}

---PASO 1: CATEGORIZACIÓN (SÍ/NO GEOPOLÍTICA)---
¿Es esta noticia sobre geopolítica, seguridad, comercio, energía, alianzas internacionales, o impacto económico global?
- SÍ = Sigue al PASO 2
- NO (es cultura, deportes, sociedad frívola, entretenimiento) = Puntúa 1 y termina

---PASO 2: IMPACTO ESPAÑA (Si es geopolítica)---
Evalúa SOLO en estos 3 vectores. SIN INVENTAR:

Vector 1: CADENA SUMINISTRO
- ¿Afecta materias primas, semiconductores, transporte, energía?
- Puntuación: 0 (no afecta) a 10 (afecta mucho)

Vector 2: ECONOMÍA EUROZONA
- ¿Afecta inflación, tipos interés, comercio, competitividad?
- Puntuación: 0 a 10

Vector 3: SEGURIDAD ESPAÑA
- ¿Afecta OTAN, alianzas, migraciones, estabilidad UE?
- Puntuación: 0 a 10

Promedio de los 3 vectores = IMPACTO_ESPAÑA (0-10)

---PASO 3: PUNTAJE FINAL---
Fórmula:
- Si NO es geopolítica: puntaje = 1
- Si es geopolítica pero IMPACTO_ESPAÑA < 3: puntaje = 5
- Si es geopolítica e IMPACTO_ESPAÑA 3-6: puntaje = 15
- Si es geopolítica e IMPACTO_ESPAÑA > 6: puntaje = 25

---SALIDA JSON REQUERIDA---
{{
  "es_geopolitica": true/false,
  "categoria": "cultura|deportes|geopolitica|economia|seguridad|otro",
  "impacto_vector_suministro": 0-10,
  "impacto_vector_economia": 0-10,
  "impacto_vector_seguridad": 0-10,
  "impacto_españa_promedio": 0-10,
  "puntaje_final": 1,
  "razon_puntaje": "Explicación breve (máximo 30 palabras)",
  "analisis_breve": "Si puntaje >= 15, análisis de 2-3 líneas. Si no, escribe: No es geopolítica relevante"
}}

REGLAS OBLIGATORIAS:
1. Devuelve SOLO JSON. Nada de texto extra.
2. Si no puedes evaluar algo, usa 0, no inventes.
3. El puntaje SOLO puede ser: 1, 5, 15 ó 25.
4. Si la noticia no es geopolítica, termina con puntaje 1.
5. No analices si no tiene impacto en España.
"""

def procesar_noticia(noticia):
    """
    Procesa TODAS las noticias, devuelve resultado incluso si puntaje < 15.
    El dashboard filtrará luego (mostrar solo >= 15)
    """
    try:
        raw = llamar_claude("claude-haiku-4-5-20251001", prompt_haiku(noticia))
        data = parse_json(raw)

        if not data:
            print("⚠️ JSON parsing falló")
            return None

        puntaje = data.get("puntaje_final", 1)
        categoria = data.get("categoria", "desconocida")
        analisis_breve = data.get("analisis_breve", "")
        razon = data.get("razon_puntaje", "")

        print(f"  Puntaje: {puntaje} | Categoría: {categoria}")

        # Guardar análisis SIEMPRE, sea relevante o no
        analisis_final = f"""CATEGORÍA: {categoria.upper()}
PUNTAJE IMPACTO ESPAÑA: {puntaje}/25

VECTORES DE IMPACTO:
- Cadena suministro: {data.get('impacto_vector_suministro', '?')}/10
- Economía eurozona: {data.get('impacto_vector_economia', '?')}/10
- Seguridad España: {data.get('impacto_vector_seguridad', '?')}/10
Promedio: {data.get('impacto_españa_promedio', '?')}/10

RAZÓN: {razon}

ANÁLISIS:
{analisis_breve}
"""

        return {
            "analisis": analisis_final,
            "puntaje": puntaje,
            "categoria": categoria
        }

    except Exception as e:
        print(f"❌ Error: {e}")
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
                print("⚠️ Skip (error parsing)")
                continue

            # GUARDAR SIEMPRE, independientemente del puntaje
            res = supabase.table("noticias").update({
                "analisis": resultado["analisis"],
                "capa": resultado["puntaje"],
                "procesada": True
            }).eq("id", noticia["id"]).execute()

            print(f"✔ Guardada (puntaje {resultado['puntaje']})")

    except Exception as e:
        print(f"❌ MAIN ERROR: {e}")

if __name__ == "__main__":
    main()
