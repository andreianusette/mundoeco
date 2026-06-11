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

PROMPT_SISTEMA_MASIVO = """Actúa como un analista geopolítico senior y estratega macroeconómico para el gobierno de España y la UE. 
Tu misión es recibir un lote masivo de noticias del día, conectar los puntos entre ellas, descartar el ruido (deportes, corazón, sucesos internos irrelevantes) y aislar los eventos de VERDADERO IMPACTO estructural.

Debes devolver obligatoriamente un JSON puro y duro, sin introducciones, sin bloques de código ```json, ni texto explicativo. Solo el objeto JSON con esta estructura exacta:

{
  "analisis_global": "Redacta aquí un informe geopolítico unificado y crudo (mínimo 300 palabras). No analices las noticias de una en una; conecta los datos. Explica qué intereses ocultos se están moviendo hoy en el tablero internacional, cómo se cruzan las distintas noticias del lote y qué hilos económicos se están tensando.",
  "impacto_espana": "Explica detalladamente cómo este conjunto de eventos afecta a los vectores críticos de España (rutas de suministro, inflación en la Eurozona, coste de la energía o seguridad en la frontera sur).",
  "bolsillo_ciudadano": "Traduce toda la macroeconomía anterior al bolsillo del ciudadano español de a pie (hipotecas, facturas, empleo, cesta de la compra).",
  "score_gravedad": 20, // Evalúa el lote completo del 1 al 25 basado en la crisis más grave detectada.
  "noticias_procesadas_ids": [123, 124, 125] // Lista con los IDs de TODAS las noticias del lote que has incluido en este análisis global.
}"""

def procesar_bloque_noticias():
    # 1. Traemos las últimas 50 noticias de la base de datos
    resultado = supabase.table("noticias")\
        .select("id, titulo, fuente, resumen, region, procesada")\
        .order("id", desc=True)\
        .limit(50)\
        .execute()

    todas = resultado.data
    
    # 2. Filtramos las que estén pendientes (por texto o booleano)
    pendientes = []
    for n in todas:
        estado = str(n.get('procesada', '')).lower().strip()
        if estado in ['false', 'f', '0', 'none', '']:
            pendientes.append(n)

    print(f"Noticias crudas en el pool: {len(todas)}")
    print(f"Noticias detectadas como pendientes para contexto: {len(pendientes)}")

    if len(pendientes) == 0:
        print("No hay material nuevo para analizar.")
        return

    # 3. Empaquetamos todo el lote en un único texto para que Claude tenga TODO el contexto
    bloque_noticias_texto = ""
    for n in pendientes:
        bloque_noticias_texto += f"--- NOTICIA ID: {n['id']} ---\n"
        bloque_noticias_texto += f"TITULAR: {n['titulo']}\n"
        bloque_noticias_texto += f"FUENTE: {n['fuente']} | REGIÓN: {n.get('region', 'global')}\n"
        bloque_noticias_texto += f"RESUMEN: {n['resumen']}\n\n"

    # 4. Llamada de Contexto Agregado a Sonnet
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 2500,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": PROMPT_SISTEMA_MASIVO + "\n\nAquí tienes el lote de noticias del día para analizar en conjunto:\n\n" + bloque_noticias_texto}
        ]
    }

    print("Enviando bloque masivo a Claude 3.5 Sonnet para análisis de contexto cruzado...")
    try:
        response = requests.post(CLAUDE_URL, headers=headers, json=body)
        
        if response.status_code != 200:
            print(f"Error de API (Código {response.status_code}): {response.text}")
            return

        respuesta_texto = response.json()["content"][0]["text"].strip()
        
        # Limpieza de seguridad por si Claude añade markdown de JSON
        if respuesta_texto.startswith("
```"):
            respuesta_texto = re.sub(r"^```json|```$", "", respuesta_texto, flags=re.IGNORECASE).strip()

        data_analisis = json.loads(respuesta_texto)
        print("✓ Análisis masivo generado y estructurado por Claude con éxito.")

        # 5. Formateamos el resultado final combinando las 3 preguntas macro
        analisis_formateado = f"""### 1. ¿POR QUÉ ESTÁ PASANDO ESTO REALMENTE?
{data_analisis['analisis_global']}

### 2. ¿CÓMO AFECTA A ESPAÑA?
{data_analisis['impacto_espana']}

### 3. ¿CÓMO ME AFECTA A MÍ EN PARTICULAR?
{data_analisis['bolsillo_ciudadano']}"""

        score = str(data_analisis.get('score_gravedad', 10))
        ids_utilizados = data_analisis.get('noticias_procesadas_ids', [n['id'] for n in pendientes])

        # 6. Guardamos el mega análisis en la noticia principal del grupo para que presida la portada
        id_principal = pendientes[0]['id']
        titulo_portada = f"INFORME GEOPOLÍTICO: Análisis de situación y riesgo macroeconómico"
        
        supabase.table("noticias").update({
            "titulo": titulo_portada,
            "analisis": analisis_formateado,
            "capa": score,
            "procesada": True
        }).eq("id", id_principal).execute()

        # 7. Marcamos todas las demás noticias del lote como procesadas para que no se repitan
        for n_id in ids_utilizados:
            if n_id != id_principal:
                supabase.table("noticias").update({"procesada": True, "capa": "0"}).eq("id", n_id).execute()
        
        print(f"✓ Sistema actualizado. El informe de contexto preside la portada con ID {id_principal} y score {score}/25.")

    except Exception as e:
        print(f"✗ Fallo en la integración del análisis masivo: {e}")

if __name__ == "__main__":
    procesar_bloque_noticias()
