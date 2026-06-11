import os
import sys
import json
import re
import logging
import requests
from supabase import create_client

# ---------------- CONFIG ----------------

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, CLAUDE_API_KEY]):
print("❌ ERROR: Faltan variables de entorno")
sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CLAUDE_URL = "https://api.anthropic.com/v1/messages"

MODEL = "claude-sonnet-4-5-20251001"  # más fiable que haiku

MAX_NOTICIAS = 20

logging.basicConfig(level=logging.INFO)

# ---------------- PROMPT ----------------

PROMPT = """Actúa como un analista geopolítico senior.

IMPORTANTE:

* Devuelve SOLO JSON válido
* SIN texto fuera del JSON
* Si fallas, el sistema se rompe

Formato obligatorio:

{
"analisis_global": "texto (mínimo 300 palabras)",
"impacto_espana": "texto",
"bolsillo_ciudadano": "texto",
"score_gravedad": 20
}
"""

# ---------------- FUNCIONES ----------------

def obtener_noticias():
logging.info("📡 Descargando noticias...")

```
res = supabase.table("noticias")\
    .select("*")\
    .order("id", desc=True)\
    .limit(50)\
    .execute()

return res.data or []
```

def filtrar_pendientes(noticias):
pendientes = [n for n in noticias if not n.get("procesada")]
logging.info(f"🧹 Pendientes: {len(pendientes)}")
return pendientes[:MAX_NOTICIAS]

def construir_bloque(noticias):
texto = ""

```
for n in noticias:
    texto += f"""
```

--- NOTICIA ID: {n.get('id')} ---
TITULAR: {n.get('titulo', '')}
FUENTE: {n.get('fuente', '')}
REGION: {n.get('region', '')}
RESUMEN: {n.get('resumen', '')}
"""

```
return texto
```

def llamar_claude(texto):
logging.info("🤖 Llamando a Claude...")

```
headers = {
    "x-api-key": CLAUDE_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

body = {
    "model": MODEL,
    "max_tokens": 3000,
    "temperature": 0.3,
    "messages": [
        {
            "role": "user",
            "content": PROMPT + "\n\nNOTICIAS:\n" + texto
        }
    ]
}

response = requests.post(CLAUDE_URL, headers=headers, json=body, timeout=30)

if response.status_code != 200:
    logging.error(response.text)
    raise Exception("Error en API Claude")

data = response.json()

if "content" not in data:
    raise Exception("Respuesta inválida de Claude")

return data["content"][0].get("text", "").strip()
```

def extraer_json(texto):
try:
return json.loads(texto)
except:
match = re.search(r"{.*?}", texto, re.DOTALL)
if match:
return json.loads(match.group(0))
raise Exception("No se pudo parsear JSON")

def validar_json(data):
keys = ["analisis_global", "impacto_espana", "bolsillo_ciudadano", "score_gravedad"]

```
for k in keys:
    if k not in data:
        raise Exception(f"Falta clave: {k}")
```

def guardar_resultado(data, noticias):
logging.info("💾 Guardando resultado...")

```
analisis = f"""### 1. CONTEXTO GLOBAL
```

{data["analisis_global"]}

### 2. IMPACTO EN ESPAÑA

{data["impacto_espana"]}

### 3. IMPACTO EN TU VIDA

{data["bolsillo_ciudadano"]}"""

```
score = int(data.get("score_gravedad", 10))

# 👉 Usamos la primera noticia como contenedor (simple)
main_id = noticias[0]["id"]

supabase.table("noticias").update({
    "titulo": "INFORME GEOECONÓMICO AUTOMÁTICO",
    "analisis": analisis,
    "capa": score,
    "procesada": True
}).eq("id", main_id).execute()

# marcar resto como procesadas
for n in noticias:
    if n["id"] != main_id:
        supabase.table("noticias").update({
            "procesada": True,
            "capa": 0
        }).eq("id", n["id"]).execute()
```

# ---------------- MAIN ----------------

def main():
try:
noticias = obtener_noticias()

```
    if not noticias:
        logging.info("⚠️ No hay noticias")
        return

    pendientes = filtrar_pendientes(noticias)

    if not pendientes:
        logging.info("✅ Nada nuevo que procesar")
        return

    bloque = construir_bloque(pendientes)

    respuesta = llamar_claude(bloque)

    data = extraer_json(respuesta)

    validar_json(data)

    guardar_resultado(data, pendientes)

    logging.info("🚀 TODO OK")

except Exception as e:
    logging.error(f"💥 ERROR REAL: {e}")
    sys.exit(1)
```

if **name** == "**main**":
main()
