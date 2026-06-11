import os
import json
import re
import requests
from supabase import create_client

# Configuración segura de credenciales
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
CLAUDE_URL = "https://api.anthropic.com/v1/messages"

PROMPT_SISTEMA_MASIVO = """Actúa como un analista geopolítico senior y estratega macroeconómico para el gobierno de España y la UE. 
Tu misión es recibir un lote masivo de noticias del día, conectar los puntos entre ellas, descartar el ruido (deportes, corazón, sucesos internos irrelevantes) y aislar los eventos de VERDADERO IMPACTO estructural.

Debes devolver obligatoriamente un JSON puro y duro, sin introducciones, sin bloques de código markdown, ni texto explicativo. Solo el objeto JSON con esta estructura exacta:

{
  "analisis_global": "Redacta aquí un informe geopolítico unificado y crudo (mínimo 300 palabras). No analices las noticias de una en una; conecta los datos. Explica qué intereses ocultos se están moviendo hoy en el tablero internacional, cómo se cruzan las distintas noticias del lote y qué hilos económicos se están tensando.",
  "impacto_espana": "Explica detalladamente cómo este conjunto de eventos afecta a los vectores críticos de España (rutas de suministro, inflación en la Eurozona, coste de la energía o seguridad en la frontera sur).",
  "bolsillo_ciudadano": "Traduce toda la macroeconomía anterior al bolsillo del ciudadano español de a pie (hipotecas, facturas, empleo, cesta de la compra).",
  "score_gravedad": 20,
  "noticias_procesadas_ids": [123, 124, 125]
}"""

def procesar_bloque_noticias():
    try:
        # Descarga de las últimas 50 noticias para mantener el corpus vivo
        resultado = supabase.table("noticias")\
            .select("id, titulo, fuente, resumen, region, procesada")\
            .order("id", desc=True)\
            .limit(50)\
            .execute()

        todas = resultado.data
        if not todas:
            print("No se pudieron descargar noticias de Supabase.")
            return
            
        # Filtro seguro en Python para evitar problemas de formato de base de datos
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

        bloque_noticias_texto = ""
        for n in pendientes:
            tit = n.get('titulo') or "Sin título"
            fuente = n.get('fuente') or "Fuente desconocida"
            reg = n.get('region') or "global"
            res = n.get('resumen') or "Sin resumen disponible"
            
            bloque_noticias_texto += f"--- NOTICIA ID: {n['id']} ---\n"
            bloque_noticias_texto += f"TITULAR: {tit}\n"
            bloque_noticias_texto += f"FUENTE: {fuente} | REGIÓN: {reg}\n"
            bloque_noticias_texto += f"RESUMEN: {res}\n\n"

        # Preparación de la llamada a la API Oficial de Claude
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        body = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 3000,
            "temperature": 0.3,
            "messages": [
                {"role": "user", "content": PROMPT_SISTEMA_MASIVO + "\n\nAquí tienes el lote de noticias del día:\n\n" + bloque_noticias_texto}
            ]
        }

        print("Enviando bloque masivo a Claude 3.5 Sonnet...")
        response = requests.post(CLAUDE_URL, headers=headers, json=body)
        
        if response.status_code != 200:
            print(f"Error de API (Código {response.status_code}): {response.text}")
            return

        respuesta_texto = response.json()["content"][0].get("text", "").strip()
        
        # TRUCO EVASIVO: Representamos comillas invertidas con códigos hexadecimales (\x60)
        # para que el renderizador de Markdown del chat no rompa la lógica del archivo
        comillas_markdown = "\x60\x60\x60"
        
        if comillas_markdown in respuesta_texto:
            # Si Claude devuelve bloques con markdown, extraemos directamente el JSON contenido entre llaves
            match = re.search(r"\{.*\}", respuesta_texto, re.DOTALL)
            if match:
                respuesta_texto = match.group(0).strip()

        try:
            data_analisis = json.loads(respuesta_texto)
        except Exception as json_err:
            print(f"Error intentando parsear el JSON directo. Texto recibido corto: {respuesta_texto[:150]}")
            # Intento de rescate por si Claude mete texto fuera del JSON
            match_llaves = re.search(r"(\{.*\})", respuesta_texto, re.DOTALL)
            if match_llaves:
                data_analisis = json.loads(match_llaves.group(1))
            else:
                raise json_err

        print("✓ Análisis masivo de contexto completado con éxito.")

        analisis_formateado = f"""### 1. ¿POR QUÉ ESTÁ PASANDO ESTO REALMENTE?
{data_analisis.get('analisis_global', 'No disponible')}

### 2. ¿CÓMO AFECTA A ESPAÑA?
{data_analisis.get('impacto_espana', 'No disponible')}

### 3. ¿CÓMO ME AFECTA A MÍ EN PARTICULAR?
{data_analisis.get('bolsillo_ciudadano', 'No disponible')}"""

        score = str(data_analisis.get('score_gravedad', 15))
        ids_utilizados = data_analisis.get('noticias_procesadas_ids', [n['id'] for n in pendientes])

        # Publicamos el informe global en el primer registro libre de la base de datos para liderar la portada
        id_principal = pendientes[0]['id']
        titulo_portada = "INFORME GEOPOLÍTICO: Análisis de situación y riesgo macroeconómico"
        
        supabase.table("noticias").update({
            "titulo": titulo_portada,
            "analisis": analisis_formateado,
            "capa": score,
            "procesada": True
        }).eq("id", id_principal).execute()

        # Marcamos como procesadas y con puntuación cero el resto de noticias para que salgan del radar de portada
        for n_id in ids_utilizados:
            if n_id != id_principal:
                supabase.table("noticias").update({"procesada": True, "capa": "0"}).eq("id", n_id).execute()
        
        print(f"✓ Base de datos sincronizada. Portada actualizada con ID {id_principal} y Score {score}/25.")

    except Exception as e:
        print(f"✗ CRASH CONTROLADO: El script de análisis ha fallado por la siguiente razón técnica: {e}")

if __name__ == "__main__":
    procesar_bloque_noticias()
```
`
