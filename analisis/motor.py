import os
import json
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

PROMPT_SISTEMA = """Eres un analista geopolítico y económico experto. 
Tu misión es analizar noticias internacionales respondiendo siempre tres preguntas concretas, 
de forma clara y directa, sin rodeos ni lenguaje académico.
Responde SIEMPRE en español."""

def analizar_noticia(noticia):
    prompt = f"""Analiza esta noticia internacional:

TITULAR: {noticia['titulo']}
FUENTE: {noticia['fuente']}
RESUMEN: {noticia['resumen']}

Responde exactamente estas tres preguntas:

1. ¿POR QUÉ ESTÁ PASANDO ESTO REALMENTE?
Explica las causas profundas, no solo lo superficial. Detecta si hay diferencia entre lo que dicen los actores y lo que realmente está ocurriendo.

2. ¿CÓMO AFECTA A ESPAÑA COMO PAÍS?
Consecuencias concretas: economía, energía, comercio, política exterior, empleo, sectores específicos.

3. ¿CÓMO ME PUEDE AFECTAR A MÍ EN PARTICULAR?
Impacto en el día a día de un ciudadano español: precios, trabajo, ahorros, hipoteca, coste de vida.

Si la noticia no tiene impacto relevante en España o en el ciudadano, dilo claramente.
Sé directo y concreto. Máximo 300 palabras en total."""

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-haiku-4-20250514",
        "max_tokens": 500,
        "messages": [
            {
                "role": "user",
                "content": PROMPT_SISTEMA + "\n\n" + prompt
            }
        ]
    }

    try:
        response = requests.post(CLAUDE_URL, headers=headers, json=body)
        data = response.json()
        
        if "error" in data:
            print(f"  Error Claude completo: {json.dumps(data)}")
            return None
        
        texto = data["content"][0]["text"]
        return texto
    except Exception as e:
        print(f"✗ Error llamando a Claude: {e}")
        return None

def procesar_noticias():
    resultado = supabase.table("noticias")\
        .select("*")\
        .eq("procesada", False)\
        .limit(10)\
        .execute()

    noticias = resultado.data
    print(f"Noticias pendientes de analizar: {len(noticias)}")

    for noticia in noticias:
        print(f"\nAnalizando: {noticia['titulo'][:60]}...")
        analisis = analizar_noticia(noticia)

        if analisis:
            supabase.table("noticias")\
                .update({"analisis": analisis, "procesada": True})\
                .eq("id", noticia["id"])\
                .execute()
            print(f"✓ Análisis guardado")
        else:
            print(f"✗ No se pudo analizar")

if __name__ == "__main__":
    procesar_noticias()
