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
Tu estilo es pragmático, directo y profundamente realista. Evita saludos, introducciones o títulos redundantes.

Tu misión es analizar la noticia y rellenar STRICTAMENTE el siguiente esquema de etiquetas. No puedes inventar etiquetas nuevas ni escribir nada fuera de ellas:

<titulo_es>Escribe aquí una traducción periodística y atractiva del titular al español</titulo_es>
<nivel_impacto>Escribe un único número del 1 al 5 evaluando la gravedad potencial para España basándote en estos criterios:
  1: Ruido de fondo (Eventos internos de otros países sin impacto en Europa).
  2: Impacto Bajo (Titulares llamativos pero que no alteran mercados ni seguridad).
  3: Impacto Moderado (Afecta indirectamente a la inflación de la Eurozona o tensiona diplomacia).
  4: Impacto Alto (Amenaza directa a rutas de suministro de España, crisis energética inminente o tensiones graves en socios como Marruecos/Argelia).
  5: Impacto Crítico (Guerra abierta que corta el gas/petróleo, rescates financieros en la Eurozona o amenaza militar directa).</nivel_impacto>
<analisis_preguntas>
1. ¿POR QUÉ ESTÁ PASANDO ESTO REALMENTE?
[Tu análisis crudo aquí, desenmascarando intereses ocultos, dinero o poder].

2. ¿CÓMO AFECTA A ESPAÑA?
[Análisis de impacto basado en los vectores de suministro, inflación o alianzas].

3. ¿CÓMO ME AFECTA A MÍ EN PARTICULAR?
[Traducción macroeconómica al bolsillo, empleo o facturas del ciudadano español].
</analisis_preguntas>"""

def analizar_noticia(noticia):
    region = noticia.get('region', 'global')
    
    prompt = f"""Rellena el esquema analítico para esta noticia:

TITULAR ORIGINAL: {noticia['titulo']}
FUENTE: {noticia['fuente']}
REGIÓN DE ORIGEN: {region}
RESUMEN: {noticia['resumen']}"""

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-3-5-haiku-latest",
        "max_tokens": 1000,
        "temperature": 0.2, # Bajamos la temperatura para que sea más estricto con el formato
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
        score_final = "5" # Puntuación por defecto si falla
        
        # 1. Extraer Título Traducido
        match_tit = re.search(r"<titulo_es>(.*?)</titulo_es>", texto_completo, re.DOTALL)
        if match_tit:
            titulo_es = match_tit.group(1).strip()
            
        # 2. Extraer Nivel (1 al 5) y multiplicarlo por 5 para llevarlo a la escala 1-25
        match_niv = re.search(r"<nivel_impacto>(.*?)</nivel_impacto>", texto_completo, re.DOTALL)
        if match_niv:
            try:
                nivel = int(match_niv.group(1).strip())
                # Forzamos que esté entre 1 y 5
                nivel = max(1, min(5, nivel))
                score_final = str(nivel * 5) # 1->5, 2->10, 3->15, 4->20, 5->25
            except:
                score_final = "10"
                
        # 3. Extraer las preguntas limpias
        match_ana = re.search(r"<analisis_preguntas>(.*?)</analisis_preguntas>", texto_completo, re.DOTALL)
        if match_ana:
            analisis_limpio = match_ana.group(1).strip()
        else:
            # Plan B por si no pone la etiqueta del análisis pero sí las otras
            analisis_limpio = re.sub(r"<titulo_es>.*?</titulo_es>", "", texto_completo, flags=re.DOTALL)
            analisis_limpio = re.sub(r"<nivel_impacto>.*?</nivel_impacto>", "", analisis_limpio, flags=re.DOTALL).strip()
            
        return titulo_es, score_final, analisis_limpio
        
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
            datos_update = {
                "analisis": analisis,
                "capa": score, 
                "procesada": True
            }
            # Sobreescribimos la columna 'titulo' original con la versión en español limpia
            if titulo_es:
                datos_update["titulo"] = titulo_es
                
            supabase.table("noticias")\
                .update(datos_update)\
                .eq("id", noticia["id"])\
                .execute()
            print(f"✓ Guardado con éxito. Score final: {score}/25")
        else:
            print(f"✗ No se pudo analizar")

if __name__ == "__main__":
    procesar_noticias()
