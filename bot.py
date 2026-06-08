import os
import time
import random
import logging
import datetime
import requests
from groq import Groq
from telegram.ext import Application, ContextTypes
from telegram.constants import ChatAction

# ============================================================
# CONFIGURAZIONE
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8906876113:AAEVJ0ZYgCQS7Yq4bRKPcwIY5-AttDzVKKA")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
CANALE_ID = os.environ.get("CANALE_ID", "-3762151852")

# Tiene traccia delle notizie già pubblicate
published_news = set()

# ============================================================
# MESSAGGI CANALE
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
# GROQ — VALUTA SE LA NOTIZIA È RILEVANTE
# ============================================================
def is_news_relevant(title, description):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        result = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """Sei un analista di mercato. Valuta se questa notizia è importante e rilevante per chi fa trading su XAU/USD (oro).
                    
Rispondi SOLO con JSON:
{"relevant": true/false, "reason": "breve motivo"}

È rilevante se riguarda:
- Decisioni Fed / tassi di interesse
- Inflazione (CPI, PPI)
- NFP (Non-Farm Payrolls)
- Movimenti significativi del prezzo dell'oro
- Tensioni geopolitiche importanti
- Dati economici USA importanti
- Dollar index (DXY) movimenti forti

NON è rilevante se riguarda:
- Notizie generiche di economia
- Altre valute o asset non correlati
- Notizie vecchie o già note"""
                },
                {
                    "role": "user",
                    "content": f"Titolo: {title}\nDescrizione: {description}"
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=100,
            temperature=0.1,
        )
        import json
        response = result.choices[0].message.content.strip()
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        parsed = json.loads(response)
        return parsed.get("relevant", False), parsed.get("reason", "")
    except Exception as e:
        logging.error(f"Errore valutazione notizia: {e}")
        return False, ""

# ============================================================
# GROQ — FORMATTA LA NOTIZIA PER IL CANALE
# ============================================================
def format_news_for_channel(title, description):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        result = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """Sei Jack, trader 18 anni specializzato su XAU/USD.
Riformatta questa notizia per il tuo canale Telegram in modo breve, diretto e con il tuo stile.
REGOLE IMPORTANTI:
- Usa il grassetto Telegram: *testo in grassetto*
- Usa emoji pertinenti alla notizia
- Max 3-4 righe
- Spiega brevemente l'impatto sull'oro
- Inizia sempre con una riga in grassetto tipo "*⚡️ NOTIZIA IMPORTANTE*" o "*📊 AGGIORNAMENTO MERCATO*"
- Il testo deve sembrare scritto da un ragazzo di 18 anni, non da un robot"""
                },
                {
                    "role": "user",
                    "content": f"Titolo: {title}\nDescrizione: {description}"
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            temperature=0.7,
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Errore formattazione notizia: {e}")
        return None

# ============================================================
# FETCH NOTIZIE XAU/USD
# ============================================================
def fetch_gold_news():
    try:
        # Usa NewsAPI gratuita
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "gold XAU USD OR gold price OR Federal Reserve gold OR gold trading",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": NEWS_API_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "ok":
            return data.get("articles", [])
        return []
    except Exception as e:
        logging.error(f"Errore fetch notizie: {e}")
        return []

# ============================================================
# JOB: CONTROLLA NOTIZIE OGNI ORA
# ============================================================
async def controlla_notizie(context: ContextTypes.DEFAULT_TYPE):
    if not NEWS_API_KEY:
        logging.warning("NEWS_API_KEY non configurata")
        return

    articles = fetch_gold_news()
    
    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "") or ""
        url = article.get("url", "")
        article_id = article.get("url", title)[:100]
        
        # Salta se già pubblicata
        if article_id in published_news:
            continue
            
        # Valuta se è rilevante
        relevant, reason = is_news_relevant(title, description)
        
        if relevant:
            # Formatta per il canale
            formatted = format_news_for_channel(title, description)
            if formatted:
                try:
                    await context.bot.send_message(
                        chat_id=CANALE_ID,
                        text=formatted,
                        parse_mode="Markdown"
                    )
                    published_news.add(article_id)
                    logging.info(f"Notizia pubblicata: {title}")
                    # Aspetta un po' tra una notizia e l'altra
                    time.sleep(5)
                except Exception as e:
                    logging.error(f"Errore invio notizia: {e}")

# ============================================================
# JOB: BUONGIORNO ORE 8:00
# ============================================================
async def manda_buongiorno(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=CANALE_ID,
            text=random.choice(MESSAGGI_BUONGIORNO)
        )
        logging.info("Buongiorno inviato")
    except Exception as e:
        logging.error(f"Errore buongiorno: {e}")

# ============================================================
# JOB: US SESSION ORE 15:30
# ============================================================
async def manda_us_session(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=CANALE_ID,
            text=random.choice(MESSAGGI_US_SESSION)
        )
        logging.info("US Session inviato")
    except Exception as e:
        logging.error(f"Errore US session: {e}")

# ============================================================
# AVVIO
# ============================================================
def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    job_queue = app.job_queue

    # Buongiorno alle 8:00 (6:00 UTC = 8:00 Italia)
    job_queue.run_daily(
        manda_buongiorno,
        time=datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc)
    )

    # US Session alle 15:30 (13:30 UTC = 15:30 Italia)
    job_queue.run_daily(
        manda_us_session,
        time=datetime.time(hour=13, minute=30, tzinfo=datetime.timezone.utc)
    )

    # Controlla notizie ogni ora
    job_queue.run_repeating(
        controlla_notizie,
        interval=3600,
        first=30
    )

    logging.info("✅ FXJack Bot avviato — buongiorno, US session e notizie attivi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
