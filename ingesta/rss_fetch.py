import feedparser
import os
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FUENTES = [
    # CAPA 1 — Discurso oficial
    {"nombre": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "capa": 1, "region": "global"},
    {"nombre": "El País Internacional", "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada", "capa": 1, "region": "españa"},
    
    # CAPA 2 — Análisis independiente
    {"nombre": "Financial Times", "url": "https://www.ft.com/rss/home", "capa": 2, "region": "global"},
    {"nombre": "The Economist", "url": "https://www.economist.com/finance-and-economics/rss.xml", "capa": 2, "region": "global"},
    {"nombre": "ECFR", "url": "https://ecfr.eu/feed/", "capa": 2, "region": "europa"},
    {"nombre": "Brussels Signal", "url": "https://brusselssignal.eu/feed/", "capa": 2, "region": "europa"},
    {"nombre": "Brookings Institution", "url": "https://www.brookings.edu/feeds/rss/research/", "capa": 2, "region": "global"},
    {"nombre": "Carnegie Endowment", "url": "https://carnegieendowment.org/rss/", "capa": 2, "region": "global"},
    {"nombre": "Bruegel", "url": "https://www.bruegel.org/publications/bruegel-blog", "capa": 2, "region": "europa"},
    {"nombre": "Geopolitical Futures", "url": "https://geopoliticalfutures.com/feed/", "capa": 2, "region": "global"},
    
    # CAPA 3 — Señales débiles (sur global)
    {"nombre": "Nikkei Asia", "url": "https://asia.nikkei.com/rss/feed/nar", "capa": 3, "region": "asia"},
    {"nombre": "The Africa Report", "url": "https://www.theafricareport.com/feed/", "capa": 3, "region": "africa"},
    {"nombre": "Al-Monitor", "url": "https://www.al-monitor.com/rss", "capa": 3, "region": "oriente_medio"},
    {"nombre": "The Diplomat", "url": "https://thediplomat.com/feed/", "capa": 3, "region": "asia"},
    {"nombre": "Middle East Eye", "url": "https://www.middleeasteye.net/rss.xml", "capa": 3, "region": "oriente_medio"},
    {"nombre": "Quartz Africa", "url": "https://qz.com/rss", "capa": 3, "region": "africa"},
    
    # CAPA 3 — Medios europeos especializados
    {"nombre": "The Objective", "url": "https://theobjective.com/feed", "capa": 3, "region": "españa"},
    {"nombre": "El Confidencial", "url": "https://rss.elconfidencial.com/mundo", "capa": 3, "region": "españa"},
    {"nombre": "Il Giornale", "url": "http://www.ilgiornale.it/rss", "capa": 3, "region": "italia"},
    {"nombre": "Süddeutsche Zeitung", "url": "https://rss.sueddeutsche.de/rss/Topthemen", "capa": 3, "region": "alemania"},
    {"nombre": "Der Spiegel", "url": "http://www.spiegel.de/schlagzeilen/index.rss", "capa": 3, "region": "alemania"},
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
