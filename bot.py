import os
import time
import random
import logging
import datetime
import requests
import json
from groq import Groq
from telegram.ext import Application, ContextTypes

# ============================================================
# CONFIGURAZIONE
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8906876113:AAEVJ0ZYgCQS7Yq4bRKPcwIY5-AttDzVKKA")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "93ae96c7437f496ca3c8b1da40848972")
CANALE_ID = int(os.environ.get("CANALE_ID", "-3762151852"))

published_news = set()

# ============================================================
# MESSAGGI
# ============================================================
MESSAGGI_BUONGIORNO = [
    "GM 🔥 Siete pronti? Iniziamo?",
    "Buongiorno a tutti! Mercato aperto, siamo operativi 💹",
    "GM! E voi ci siete? Pronti per oggi? 👀",
    "Nuova giornata, nuove opportunità. Pronti? 🎯",
    "GM a tutti! Il mercato non aspetta, siamo già al lavoro 🔥",
    "Buongiorno! Occhi aperti oggi, ci sono ottime opportunità 💰",
    "GM! Una nuova sessione ci aspetta. Pronti a operare? 📊",
]

MESSAGGI_US_SESSION = [
    "🇺🇸 US Session aperta! Il momento più caldo della giornata, massima attenzione 🔥",
    "Attenzione! Apre la sessione americana, volatilità in arrivo 📈 Tenetevi pronti",
    "🇺🇸 Sessione USA operativa! Adesso si muove tutto, occhi sul grafico 👀",
    "US Session live! I movimenti più importanti della giornata iniziano adesso 🚀",
    "🇺🇸 Apre Wall Street! Massima concentrazione, il mercato si sveglia davvero adesso 🔥",
    "Sessione americana aperta! Chi è pronto? Questo è il momento 💥",
    "🇺🇸 US Session — il mercato entra nel vivo adesso. Attenti ai livelli chiave 📊",
]

# ============================================================
# NOTIZIE
# ============================================================
def fetch_gold_news():
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "gold XAU USD OR gold price OR Federal Reserve gold",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": NEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("status") == "ok":
            return data.get("articles", [])
        logging.error(f"NewsAPI error: {data}")
        return []
    except Exception as e:
        logging.error(f"Errore fetch notizie: {e}")
        return []

def is_news_relevant(title, description):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        result = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """Analista di mercato. Valuta se questa notizia è importante per chi fa trading su XAU/USD.
Rispondi SOLO con JSON senza markdown: {"relevant": true o false, "reason": "motivo breve"}
È rilevante se riguarda: Fed/tassi, CPI/inflazione, NFP, movimenti oro, tensioni geopolitiche, DXY.
NON è rilevante se è generica o non correlata all'oro."""
                },
                {"role": "user", "content": f"Titolo: {title}\nDescrizione: {description}"}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=80,
            temperature=0.1,
        )
        response = result.choices[0].message.content.strip()
        response = response.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(response)
        return parsed.get("relevant", False)
    except Exception as e:
        logging.error(f"Errore rilevanza: {e}")
        return False

def format_news(title, description):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        result = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """Sei Jack, trader 18 anni su XAU/USD. Riformatta questa notizia per il tuo canale Telegram.
- Inizia con *⚡️ NOTIZIA* o *📊 AGGIORNAMENTO* in grassetto
- Usa grassetto con *testo* per le parti importanti
- Emoji pertinenti
- Max 3-4 righe
- Spiega l'impatto sull'oro
- Stile ragazzo 18 anni, non robot"""
                },
                {"role": "user", "content": f"Titolo: {title}\nDescrizione: {description}"}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            temperature=0.7,
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Errore format notizia: {e}")
        return None

# ============================================================
# JOBS
# ============================================================
async def manda_buongiorno(context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = random.choice(MESSAGGI_BUONGIORNO)
        await context.bot.send_message(chat_id=CANALE_ID, text=msg)
        logging.info(f"Buongiorno inviato: {msg}")
    except Exception as e:
        logging.error(f"Errore buongiorno: {e}")

async def manda_us_session(context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = random.choice(MESSAGGI_US_SESSION)
        await context.bot.send_message(chat_id=CANALE_ID, text=msg)
        logging.info(f"US Session inviato: {msg}")
    except Exception as e:
        logging.error(f"Errore US session: {e}")

async def controlla_notizie(context: ContextTypes.DEFAULT_TYPE):
    logging.info("Controllo notizie in corso...")
    articles = fetch_gold_news()
    logging.info(f"Trovati {len(articles)} articoli")
    
    count = 0
    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "") or ""
        article_id = article.get("url", title)[:100]
        
        if article_id in published_news:
            continue
        
        if is_news_relevant(title, description):
            formatted = format_news(title, description)
            if formatted:
                try:
                    await context.bot.send_message(
                        chat_id=CANALE_ID,
                        text=formatted,
                        parse_mode="Markdown"
                    )
                    published_news.add(article_id)
                    count += 1
                    logging.info(f"Notizia pubblicata: {title}")
                    time.sleep(5)
                except Exception as e:
                    logging.error(f"Errore invio notizia: {e}")
    
    logging.info(f"Notizie pubblicate: {count}")

# Test immediato all'avvio
async def test_avvio(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=CANALE_ID,
            text="✅ Bot avviato e operativo!"
        )
        logging.info("Messaggio di test inviato al canale")
    except Exception as e:
        logging.error(f"Errore test avvio: {e}")

# ============================================================
# MAIN
# ============================================================
def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    job_queue = app.job_queue

    # Test immediato — manda messaggio al canale dopo 10 secondi
    job_queue.run_once(test_avvio, when=10)

    # Buongiorno alle 8:00 Italia (6:00 UTC)
    job_queue.run_daily(
        manda_buongiorno,
        time=datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc)
    )

    # US Session alle 15:30 Italia (13:30 UTC)
    job_queue.run_daily(
        manda_us_session,
        time=datetime.time(hour=13, minute=30, tzinfo=datetime.timezone.utc)
    )

    # Notizie ogni ora
    job_queue.run_repeating(controlla_notizie, interval=3600, first=60)

    logging.info("✅ FXJack Bot avviato!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
