import os
import json
import re
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

PROMPT_SISTEMA = """Actúa como un analista geopolítico senior y estratega macroeconómico especializado en España y la Unión Europea. 
Tu estilo es pragmático, directo y profundamente realista. Evita introducciones redundantes.

Tu misión es realizar tres tareas con la noticia proporcionada:
1. Traducir el titular original al español con un estilo periodístico y atractivo. Envuélvelo entre las etiquetas <titulo_es> y </titulo_es>.
2. Evaluar el impacto real para España y asignar una PUNTUACIÓN DE GRAVEDAD GEOPOLÍTICA del 1 al 25 (donde 1 es irrelevante y 25 es una crisis crítica de suministros, inflación o seguridad para España). Envuélvela entre las etiquetas <score> y </score>.
3. Responder a tres preguntas concretas analizando el impacto real para España (Suministros, Eurozona, y Ciudadano).

Responde siempre en español y sé directo."""

def analizar_noticia(noticia):
    region = noticia.get('region', 'global')
    
    prompt = f"""Analiza esta noticia internacional considerando su impacto potencial en España:

TITULAR ORIGINAL: {noticia['titulo']}
FUENTE: {noticia['fuente']}
REGIÓN DE ORIGEN: {region}
RESUMEN: {noticia['resumen']}

Estructura tu respuesta EXACTAMENTE con este formato:

<titulo_es>Traducción del titular al español</titulo_es>
<score>Escribe aquí solo un número entero del 1 al 25</score>

1. ¿POR QUYÉ ESTÁ PASANDO ESTO REALMENTE?
[Tu análisis crudo aquí]

2. ¿CÓMO AFECTA A ESPAÑA?
[Tu análisis de vectores aquí]

3. ¿CÓMO ME AFECTA A MÍ EN PARTICULAR?
[Tu análisis ciudadano aquí]"""

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": PROMPT_SISTEMA + "\n\n" + prompt}]
    }

    try:
        response = requests.post(CLAUDE_URL, headers=headers, json=body)
        data = response.json()
        
        if "error" in data:
            print(f"  Error Claude: {data['error']['message']}")
            return None, None, None
        
        texto_completo = data["content"][0]["text"]
        
        titulo_es = None
        score = "0"
        
        # Extraer Título
        match_tit = re.search(r"<titulo_es>(.*?)</titulo_es>", texto_completo, re.DOTALL)
        if match_tit:
            titulo_es = match_tit.group(1).strip()
            
        # Extraer Score
        match_sco = re.search(r"<score>(.*?)</score>", texto_completo, re.DOTALL)
        if match_sco:
            score = match_sco.group(1).strip()
            
        # Limpiar el texto para dejar solo las preguntas
        analisis_limpio = re.sub(r"<titulo_es>.*?</titulo_es>", "", texto_completo, flags=re.DOTALL)
        analisis_limpio = re.sub(r"<score>.*?</score>", "", analisis_limpio, flags=re.DOTALL).strip()
            
        return titulo_es, score, analisis_limpio
        
    except Exception as e:
        print(f"✗ Error llamando a Claude: {e}")
        return None, None, None

def procesar_noticias():
    resultado = supabase.table("noticias")\
        .select("*")\
        .eq("procesada", False)\
        .execute()

    noticias = resultado.data
    print(f"Noticias pendientes de analizar: {len(noticias)}")

    for noticia in noticias:
        print(f"\nAnalizando: {noticia['titulo'][:60]}...")
        titulo_es, score, analisis = analizar_noticia(noticia)

        if analisis:
            # Aprovechamos la columna 'capa' para guardar el score numérico del 1 al 25
            datos_update = {
                "analisis": analisis,
                "capa": score, 
                "procesada": True
            }
            if titulo_es:
                datos_update["titulo"] = titulo_es
                
            supabase.table("noticias")\
                .update(datos_update)\
                .eq("id", noticia["id"])\
                .execute()
            print(f"✓ Guardado: Titular traducido y Score [{score}/25] en columna 'capa'")
        else:
            print(f"✗ No se pudo analizar")

if __name__ == "__main__":
    procesar_noticias()
