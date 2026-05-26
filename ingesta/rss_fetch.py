import feedparser
import json
from datetime import datetime

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

if __name__ == "__main__":
    noticias = fetch_noticias()
    with open("noticias_raw.json", "w", encoding="utf-8") as f:
        json.dump(noticias, f, ensure_ascii=False, indent=2)
    print(f"\nTotal: {len(noticias)} noticias guardadas en noticias_raw.json")
