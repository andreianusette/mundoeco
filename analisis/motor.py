import os
import json
import requests
from supabase import create_client

# Mantener las variables de entorno intactas para Railway y Supabase
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

# MEJORA 3: Re-ingeniería completa del Prompt de Sistema para un perfil Senior y Afilado
PROMPT_SISTEMA = """Actúa como un analista geopolítico senior y estratega macroeconómico especializado en España y la Unión Europea. 
Tu estilo es pragmático, directo y profundamente realista, incluso cínico. Evita el buenismo, la jerga académica corporativa vacía y las introducciones redundantes (como "Es importante destacar que..." o "Como podemos ver..."). Ve directo al grano desde la primera palabra.

Tu misión es evaluar críticamente la noticia proporcionada y responder STRICTAMENTE a tres preguntas, analizando el impacto real para los intereses españoles basándote en estos 3 vectores dinámicos fundamentales:
Vector A. Cadenas de suministro y logística (materias primas, energía, semiconductores, transporte marítimo).
Vector B. Estabilidad económica e inflación en la eurozona (tipos de interés, decisiones del BCE, comercio exterior, costes).
Vector C. Seguridad, flujos migratorios y alianzas estratégicas de España (OTAN, Norte de África, flancos vulnerables de la UE).

Responde SIEMPRE en español, sé directo y concreto, limitando tu análisis a un máximo de 400 palabras en total."""


def analizar_noticia(noticia):
    region = noticia.get('region', 'global')
    
    # MEJORA 2: Sustitución de ponderación fija por orden de evaluación dinámica en el prompt
    prompt = f"""Analiza esta noticia internacional considerando su impacto potencial en España:

TITULAR: {noticia['titulo']}
FUENTE: {noticia['fuente']}
REGIÓN DE ORIGEN: {region}
RESUMEN: {noticia['resumen']}

Estructura tu respuesta EXACTAMENTE con este formato de tres bloques de texto (no uses viñetas ni guiones en las respuestas, responde en párrafos directos y limpios):

1. ¿POR QUÉ ESTÁ PASANDO ESTO REALMENTE?
[Detecta el 'delta' o la hipocresía geopolítica: contrasta el discurso oficial o las declaraciones institucionales con los movimientos reales de dinero, recursos, sanciones o poder de los países implicados. ¿Cuál es el interés real u oculto?]

2. ¿CÓMO AFECTA A ESPAÑA?
[Cruza la noticia con los 3 vectores dinámicos de análisis (suministros, inflación/economía o seguridad). Define si el impacto es directo o indirecto, y establece un horizonte temporal explícito: corto plazo (<1 año), medio plazo (1-3 años) o largo plazo (>3 años). Sé muy específico con la posición geopolítica de España o sus intereses sectoriales].

3. ¿CÓMO ME AFECTA A MÍ EN PARTICULAR?
[Traduce la macroeconomía a la vida cotidiana del ciudadano en España. Explica el impacto potencial en: la cesta de la compra, facturas de luz/gas, hipotecas/créditos, empleo en sectores clave, o variables de inversión concretas como empresas del IBEX 35]."""

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
    # Mantiene la conexión exacta a la tabla "noticias" de Supabase
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
