import os
import json
import re
import requests
from supabase import create_client

# Mantener las variables de entorno intactas para Railway y Supabase
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

PROMPT_SISTEMA = """Actúa como un analista geopolítico senior y estratega macroeconómico especializado en España y la Unión Europea. 
Tu estilo es pragmático, directo y profundamente realista, incluso cínico. Evita el buenismo y las introducciones redundantes. Ve directo al grano.

Tu misión es realizar dos tareas con la noticia proporcionada:
1. Traducir el titular original al español con un estilo periodístico, riguroso y atractivo. Debes envolver esta traducción STRICTAMENTE entre las etiquetas <titulo_es> y </titulo_es>.
2. Evaluar críticamente la noticia y responder a tres preguntas concretas analizando el impacto real para España basándote en tres vectores fundamentales (Suministros/Logística, Eurozona/Inflación, y Seguridad/Alianzas).

Responde SIEMPRE en español, sé directo y concreto, limitando tu análisis a un máximo de 400 palabras en total."""


def analizar_noticia(noticia):
    region = noticia.get('region', 'global')
    
    prompt = f"""Analiza esta noticia internacional considerando su impacto potencial en España:

TITULAR ORIGINAL: {noticia['titulo']}
FUENTE: {noticia['fuente']}
REGIÓN DE ORIGEN: {region}
RESUMEN: {noticia['resumen']}

Estructura tu respuesta EXACTAMENTE con este formato (no inventes otras etiquetas ni uses viñetas):

<titulo_es>Aquí pones la traducción del titular al español</titulo_es>

1. ¿POR QUÉ ESTÁ PASANDO ESTO REALMENTE?
[Detecta el interés real u oculto, contrastando el discurso oficial con los movimientos de dinero o poder].

2. ¿CÓMO AFECTA A ESPAÑA?
[Cruza la noticia con los 3 vectores de análisis, define si el impacto es directo o indirecto y establece un horizonte temporal explícito].

3. ¿CÓMO ME AFECTA A MÍ EN PARTICULAR?
[Traduce la macroeconomía a la cesta de la compra, facturas, hipotecas o empleo del ciudadano en España]."""

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-3-haiku-20240307",
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
            return None, None
        
        texto_completo = data["content"][0]["text"]
        
        # Procesamiento inteligente con expresiones regulares para separar el título del análisis
        titulo_es = None
        analisis_limpio = texto_completo
        
        match = re.search(r"<titulo_es>(.*?)</titulo_es>", texto_completo, re.DOTALL)
        if match:
            titulo_es = match.group(1).strip()
            # Quitamos el fragmento del título del texto general para que el análisis quede limpio
            analisis_limpio = re.sub(r"<titulo_es>.*?</titulo_es>", "", texto_completo, flags=re.DOTALL).strip()
            
        return titulo_es, analisis_limpio
        
    except Exception as e:
        print(f"✗ Error llamando a Claude: {e}")
        return None, None


def procesar_noticias():
    resultado = supabase.table("noticias")\
        .select("*")\
        .eq("procesada", False)\
        .execute()

    noticias = resultado.data
    print(f"Noticias pendientes de analizar: {len(noticias)}")

    for noticia in noticias:
        print(f"\nAnalizando: {noticia['titulo'][:60]}...")
        titulo_es, analisis = analizar_noticia(noticia)

        if analisis:
            # Si Claude no logró generar el título por algún motivo, usamos el original como respaldo
            if not titulo_es:
                titulo_es = noticia['titulo']
                
            # MEJORA: Guardamos tanto el análisis como el nuevo título traducido en la base de datos
            supabase.table("noticias")\
                .update({
                    "analisis": analisis, 
                    "titulo_es": titulo_es,
                    "procesada": True
                })\
                .eq("id", noticia["id"])\
                .execute()
            print(f"✓ Análisis y título traducido guardados")
        else:
            print(f"✗ No se pudo analizar")


if __name__ == "__main__":
    procesar_noticias()
