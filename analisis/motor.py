import os
import json
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

PONDERACION_ESPAÑA = {
    "EEUU": 9,
    "China": 8,
    "UE": 9,
    "Oriente Medio": 7,
    "Rusia": 7,
    "Indo-Pacífico": 5,
    "Africa": 3,
    "Latinoamérica": 4,
    "global": 6,
}

PROMPT_SISTEMA = """Eres un analista geopolítico y económico especializado en impacto España.
Tu misión es analizar noticias internacionales respondiendo siempre tres preguntas concretas,
de forma clara y directa, sin rodeos ni lenguaje académico.
Recuerda: no ignores el sur global o regiones lejanas, pero sé honesto sobre el impacto real en España.
Responde SIEMPRE en español."""

def obtener_relevancia_region(region):
    return PONDERACION_ESPAÑA.get(region, 5)

def analizar_noticia(noticia):
    region = noticia.get('region', 'global')
    relevancia = obtener_relevancia_region(region)
    
    prompt = f"""Analiza esta noticia internacional:

TITULAR: {noticia['titulo']}
FUENTE: {noticia['fuente']}
REGIÓN: {region} (relevancia para España: {relevancia}/10)
RESUMEN: {noticia['resumen']}

Responde exactamente estas tres preguntas:

1. ¿POR QUÉ ESTÁ PASANDO ESTO REALMENTE?
Explica las causas profundas, no solo lo superficial. Detecta si hay diferencia entre lo que dicen los actores y lo que realmente está ocurriendo.

2. ¿CÓMO AFECTA A ESPAÑA?
Sé específico y honesto:
- Impacto directo: comercio, energía, inversión, seguridad, empleo, sectores específicos
- Impacto indirecto: cambios en alianzas, decisiones de la UE, competencia geoestratégica
- Horizonte temporal: ¿en 3 meses, 1 año, 5 años?
- Si el impacto es bajo, dilo claramente. No todo afecta igual a España.

3. ¿Y A MÍ?
Impacto en el día a día: precios, trabajo, ahorros, hipoteca, coste de vida, seguridad.
Si no hay impacto directo, explica por qué igualmente debería estar en el radar.

NOTA IMPORTANTE: A veces lo que parece lejano (inversión china en Africa, tratados en Asia)
afecta más que lo obvio. Sé inteligente: conecta puntos cuando sea relevante.

Sé directo y concreto. Máximo 400 palabras en total."""

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
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
            print(f"  Error Claude: {data['error']['message']}")
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
