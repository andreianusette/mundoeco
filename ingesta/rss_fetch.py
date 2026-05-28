import feedparser
import os
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FUENTES = [
    {"nombre": "Reuters World", "url": "https://feeds.reuters.com/reuters/worldNews", "capa": 1, "region": "global"},
    {"nombre": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "capa": 1, "region": "global"},
    {"nombre": "Financial Times", "url": "https://www.ft.com/rss/home", "capa": 2, "region": "global"},
    {"nombre": "The Economist", "url": "https://www.economist.com/finance-and-economics/rss.xml", "capa": 2, "region": "global"},
    {"nombre": "CFR", "url": "https://www.cfr.org/rss.xml", "capa": 2, "region": "global"},
    {"nombre": "Nikkei Asia", "url": "https://asia.nikkei.com/rss/feed/nar", "capa": 3, "region": "asia"},
    {"nombre": "The Africa Report", "url": "https://www.theafricareport.com/feed/", "capa": 3, "region": "africa"},
    {"nombre": "Al-Monitor", "url": "https://www.al-monitor.com/rss", "capa": 3, "region": "oriente_medio"},
    {"nombre": "ECFR", "url": "https://ecfr.eu/feed/", "capa": 2, "region": "europa"},
    {"nombre": "Brussels Signal", "url": "https://brusselssignal.eu/feed/", "capa": 2, "region": "europa"},
    {"nombre": "El País Internacional", "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada", "capa": 1, "region": "españa"},
]

def fetch_noticias():
    noticias = []
    for fuente in FUENTES:
        try:
            feed = feedparser.parse(fuente["url"])
            for entry in feed.entries[:5]:
                noticia = {
                    "titulo": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "resumen": entry.get("summary", ""),
                    "fecha": entry.get("published", datetime.now().isoformat()),
                    "fuente": fuente["nombre"],
                    "capa": fuente["capa"],
                    "region": fuente["region"],
                    "procesada": False,
                }
                noticias.append(noticia)
            print(f"✓ {fuente['nombre']}: {len(feed.entries[:5])} noticias")
        except Exception as e:
            print(f"✗ {fuente['nombre']}: error — {e}")
    return noticias

def guardar_en_supabase(noticias):
    nuevas = 0
    for noticia in noticias:
        try:
            existente = supabase.table("noticias").select("id").eq("url", noticia["url"]).execute()
            if not existente.data:
                supabase.table("noticias").insert(noticia).execute()
                nuevas += 1
        except Exception as e:
            print(f"✗ Error guardando noticia: {e}")
    print(f"\n✓ {nuevas} noticias nuevas guardadas en Supabase")

if __name__ == "__main__":
    noticias = fetch_noticias()
    guardar_en_supabase(noticias)
