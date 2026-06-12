import os
import json
import re
import requests
import sys
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not CLAUDE_API_KEY:
    print("❌ ERROR: Faltan variables de entorno esenciales (Supabase o Claude).")
    sys.exit(1)

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

        if response.status_code != 200:
            print(f"❌ ERROR DE API CLAUDE (Código {response.status_code}): {response.text}")
            sys.exit(1) # Forzamos la parada del script para detectar fallos reales

        data = response.json()
        content = data.get("content", [])
        if not content:
            return None
        return content[0].get("text", "")

    except Exception as e:
        print("❌ Claude error crítico:", e)
        sys.exit(1)

def prompt_haiku(noticia):
    return f"""
INSTRUCCIONES ESTRICTAS - ANÁLISIS PROFUNDO

Tu tarea: analizar la noticia y devolver JSON válido con análisis DETALLADO.

NOTICIA:
Titular: {noticia.get('titulo','')}
Resumen: {noticia.get('resumen','')}
Región: {noticia.get('region','')}

---PASO 1: ¿ES GEOPOLÍTICA?---
¿Trata sobre geopolítica, seguridad, comercio, energía, alianzas, impacto económico global?
- SÍ → PASO 2
- NO (cultura, deportes, sociedad) → puntaje 1, fin

---PASO 2: IMPACTO ESPAÑA---
Evalúa en 3 vectores (0-10 cada uno):

1. CADENA SUMINISTRO: ¿Afecta materias primas, semiconductores, transporte, energía?
2. ECONOMÍA EUROZONA: ¿Afecta inflación, tipos, comercio, competitividad?
3. SEGURIDAD ESPAÑA: ¿Afecta OTAN, alianzas, migraciones, estabilidad UE?

Promedio = IMPACTO_ESPAÑA (0-10)

---PASO 3: PUNTAJE FINAL---
- Si NO es geopolítica: 1
- Si IMPACTO < 3: 5
- Si IMPACTO 3-6: 15
- Si IMPACTO > 6: 25

---ANÁLISIS DETALLADO (solo si puntaje >= 15)---
Si el puntaje es >= 15, responde EXACTAMENTE estas 3 preguntas:

P1: ¿POR QUÉ ESTÁ PASANDO REALMENTE?
- ¿Cuál es el interés de poder o dinero real detrás?
- ¿Quién gana, quién pierde?
- ¿Diferencia entre discurso y acción?
(200-250 palabras)

P2: ¿CÓMO AFECTA A ESPAÑA?
- Impactos concretos (comercio, energía, inversión, seguridad)
- Horizonte temporal (3 meses, 1 año, 5 años)
- Conexiones con los 3 vectores
(200-250 palabras)

P3: ¿Y A MÍ?
- Impacto cotidiano (precios, trabajo, hipoteca, ahorros)
- Empresas IBEX 35 afectadas
- ¿Debería cambiar inversiones?
(150-200 palabras)

---SALIDA JSON---
{{
  "es_geopolitica": true,
  "categoria": "geopolitica",
  "impacto_vector_suministro": 5,
  "impacto_vector_economia": 5,
  "impacto_vector_seguridad": 5,
  "impacto_españa_promedio": 5,
  "puntaje_final": 15,
  "razon_puntaje": "razon",
  "analisis_p1_por_que": "texto",
  "analisis_p2_como_afecta": "texto",
  "analisis_p3_y_a_mi": "texto"
}}

REGLAS EXTREMAS:
1. Devolver ÚNICAMENTE el objeto JSON. Sin textos introductorios, sin markdown ```json.
2. Si puntaje < 15, pon vacío en P1, P2, P3: ""
3. Si puntaje >= 15, TODAS las 3 preguntas deben estar completas.
4. Puntaje SOLO puede ser uno de estos números exactos: 1, 5, 15 ó 25.
"""

def procesar_noticia(noticia):
    try:
        # CAMBIO CLAVE: Usando el identificador oficial económico de Claude 3.5 Haiku con saldo
        raw = llamar_claude("claude-3-5-haiku-20241022", prompt_haiku(noticia))
        data = parse_json(raw)

        if not data:
            print("⚠️ JSON parsing falló en esta noticia.")
            return None

        puntaje = data.get("puntaje_final", 1)
        categoria = data.get("categoria", "desconocida")
        razon = data.get("razon_puntaje", "")

        print(f"  Puntaje calculado: {puntaje} | Categoría: {categoria}")

        if puntaje < 15:
            analisis_final = f"""CATEGORÍA: {categoria.upper()}
PUNTAJE IMPACTO ESPAÑA: {puntaje}/25

VECTORES: S={data.get('impacto_vector_suministro', '?')}/10, E={data.get('impacto_vector_economia', '?')}/10, Seg={data.get('impacto_vector_seguridad', '?')}/10

RAZÓN: {razon}

(No es geopolítica relevante para la portada de Lectura Rápida)
"""
        else:
            analisis_final = f"""CATEGORÍA: {categoria.upper()}
PUNTAJE IMPACTO ESPAÑA: {puntaje}/25

VECTORES DE IMPACTO:
- Cadena suministro: {data.get('impacto_vector_suministro', '?')}/10
- Economía eurozona: {data.get('impacto_vector_economia', '?')}/10
- Seguridad España: {data.get('impacto_vector_seguridad', '?')}/10
Promedio: {data.get('impacto_españa_promedio', '?')}/10

---

1️⃣ ¿POR QUÉ ESTÁ PASANDO REALMENTE?
{data.get('analisis_p1_por_que', '')}

2️⃣ ¿CÓMO AFECTA A ESPAÑA?
{data.get('analisis_p2_como_afecta', '')}

3️⃣ ¿Y A MÍ?
{data.get('analisis_p3_y_a_mi', '')}
"""

        return {
            "analisis": analisis_final,
            "puntaje": puntaje,
            "categoria": categoria
        }

    except Exception as e:
        print(f"❌ Error al procesar noticia: {e}")
        return None

def main():
    try:
        # Buscamos lotes de noticias no procesadas en Supabase
        response = supabase.table("noticias") \
            .select("*") \
            .eq("procesada", False) \
            .order("id", desc=False) \
            .limit(20) \
            .execute()

        noticias = response.data or []

        print(f"📦 Noticias pendientes encontradas en Supabase: {len(noticias)}")

        if len(noticias) == 0:
            print("💤 No hay noticias pendientes de procesar en este momento.")
            return

        for noticia in noticias:
            print(f"-> Analizando ID {noticia['id']}: {noticia.get('titulo', 'Sin título')[:40]}...")
            resultado = procesar_noticia(noticia)

            if not resultado:
                print("⚠️ Saltando noticia debido a un error de respuesta.")
                continue

            # Actualizamos la fila en Supabase marcándola como procesada de forma segura
            supabase.table("noticias").update({
                "analisis": resultado["analisis"],
                "capa": resultado["puntaje"],
                "procesada": True
            }).eq("id", noticia["id"]).execute()

            print(f"✔ Guardada correctamente con puntaje {resultado['puntaje']}")

    except Exception as e:
        print(f"❌ MAIN ERROR CRÍTICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
