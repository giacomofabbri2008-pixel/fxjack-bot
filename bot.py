import os
import time
import random
import logging
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# ============================================================
# CONFIGURAZIONE
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8906876113:AAEVJ0ZYgCQS7Yq4bRKPcwIY5-AttDzVKKA")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GIACOMO_CHAT_ID = os.environ.get("GIACOMO_CHAT_ID", "1075363140")

# Audio files
AUDIO1_PATH = "audio1_trading.mp3"   # "Da quanto fai trading?"
AUDIO2_PATH = "audio2_vip.mp3"       # "Benefici del VIP"
AUDIO3_PATH = "audio3_cambioib.mp3"  # "Come spostare account PuPrime"

# Testo iscrizione VIP
TESTO_LINK_VIP = """Per entrare nel VIP ti basta registrarti tramite il nostro broker partner PU Prime 👇

1. Registrati dal link: https://puvip.co/la-partners/HzLm0XDt
2. Completa l'apertura del conto
3. Inserisci il codice referral: HzLm0XDt

Ti consiglio di partire con 200/300€ per gestire bene il rischio e seguire l'operatività. Ottieni anche un bonus del 100% sul primo deposito 🎁

Quando hai finito scrivimi "fatto" ✅"""

# Testo cambio IB
TESTO_CAMBIO_IB = """Questa è la mail che devi inviare a PuPrime con la stessa email della registrazione, fai copia e incolla il messaggio di sotto 👇

Oggetto: CAMBIO IB
A: info@puprime.com

Hi, move my account under 23212458

Appena fatto mandami lo screen così controllo che sia tutto a posto ✅"""

# Stato conversazione per ogni utente
# Valori: None, "asked_trading", "sent_vip_benefits", "sent_link", "has_puprime"
user_states = {}

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
Sei Jack, un trader di 18 anni con 4 anni di esperienza nel trading, specializzato in XAU/USD (oro).
Gestisci una community su Telegram chiamata "FXjack segnali free" e una sala VIP esclusiva.
Lavori con il broker PuPrime come introducing broker.

=== IL TUO STILE ===
- Rispondi SEMPRE in modo molto corto e diretto. Mai più di 3-4 righe.
- Dai del TU a tutti.
- Usa emoji SOLO nei messaggi cordiali, di congratulazioni o benvenuto.
- Scrivi in modo naturale, come un ragazzo che risponde dal telefono.
- Rispondi nella stessa lingua del cliente (italiano, inglese o spagnolo).
- Non sembrare mai un bot o un'intelligenza artificiale.

=== DOMANDE FREQUENTI ===

DIFFERENZA VIP VS PUBBLICO:
"Nel pubblico mando 1-2 segnali al giorno. Nel VIP ricevi 15-20 segnali su XAU/USD + supporto diretto da me. Ed è tutto gratuito 👆"

STOP LOSS:
"Lo stop loss è il livello dove chiudi il trade in perdita per limitare i danni. Fondamentale, non tradare mai senza."

TAKE PROFIT:
"Il take profit è il livello dove chiudi il trade in profitto. Lo imposti prima di aprire il trade."

STRATEGIA:
"Lavoro sull'oro XAU/USD, seguo l'analisi tecnica e i livelli chiave. Pazienza e gestione del rischio sono tutto."

PROBLEMI METATRADER 5:
"Scarica MT5 dal sito di PuPrime. Nelle impostazioni cerca il server 'PUPrime' e inserisci le credenziali che ti hanno mandato via mail. Dimmi che errore ti dà se non funziona."

DEPOSITO MINIMO:
"Non c'è un minimo, ma consiglio 200-300€ per gestire bene il rischio."

=== GUADAGNI ===
Prima risposta: "Varia molto in base al mercato. Non mi piace parlare di numeri."
Se insistono: "Mediamente intorno ai 3000€ a settimana, dipende dal periodo."

=== PERDITE ===
"Le perdite fanno parte del trading, anche i migliori le hanno. L'importante è rispettare sempre lo stop loss. Un trade perso non significa nulla sul lungo periodo 💪"

=== NON FARE MAI ===
- Non promettere guadagni garantiti
- Non rispondere su tasse, leggi, dichiarazioni
- Non rispondere a domande personali
- Non scrivere messaggi lunghi
"""

# ============================================================
# KEYWORDS
# ============================================================
VIP_KEYWORDS = [
    "vip", "voglio entrare", "voglio accedere", "interessato", "sono interessato",
    "fammi entrare", "come entro", "come si entra", "segnali vip", "sala vip",
    "join vip", "i want to join", "interested", "quiero entrar", "interesado"
]

ALREADY_PUPRIME_KEYWORDS = [
    "ho già puprime", "ho gia puprime", "ho già un account", "ho già il conto",
    "already have", "ya tengo", "già registrato", "gia registrato",
    "ho puprime", "ce l'ho già", "ho già l'account"
]

FATTO_KEYWORDS = [
    "fatto", "done", "ho fatto", "completato", "finito", "registrato",
    "ho completato", "listo", "hecho", "ok fatto", "fatto ✅"
]

PERSONAL_KEYWORDS = [
    "dove vivi", "dove abiti", "fidanzat", "famiglia", "numero di telefono",
    "dichiarazione", "fisco", "tasse", "legge", "avvocato", "denuncia",
    "where do you live", "girlfriend", "boyfriend", "phone number", "tax", "lawyer"
]

def contains_keyword(text: str, keywords: list) -> bool:
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)

# ============================================================
# GROQ
# ============================================================
def get_ai_response(user_message: str, user_name: str) -> str:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Messaggio da {user_name}: {user_message}"}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            temperature=0.85,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Errore Groq: {e}")
        return None

# ============================================================
# DELAY UMANO
# ============================================================
async def human_delay(context, chat_id, seconds=None):
    if seconds is None:
        seconds = random.randint(20, 45)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    time.sleep(seconds)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    time.sleep(random.randint(2, 4))

async def audio_delay(context, chat_id):
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
    time.sleep(random.randint(15, 25))

# ============================================================
# HANDLER MESSAGGI
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return
    if message.chat.type != "private":
        return

    user = message.from_user
    user_name = user.first_name or "Cliente"
    user_id = user.id
    chat_id = message.chat_id
    text = message.text

    logging.info(f"Messaggio da {user_name} ({user_id}): {text}")

    state = user_states.get(user_id, None)

    # ---- DOMANDA PERSONALE ----
    if contains_keyword(text, PERSONAL_KEYWORDS):
        if GIACOMO_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=GIACOMO_CHAT_ID,
                    text=f"⚠️ *Domanda personale*\n\n👤 {user_name} (ID: `{user_id}`)\n💬 \"{text}\"",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Errore notifica: {e}")
        return

    # ---- VUOLE ENTRARE NEL VIP ----
    if contains_keyword(text, VIP_KEYWORDS) and state is None:
        await audio_delay(context, chat_id)
        with open(AUDIO1_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        user_states[user_id] = "asked_trading"
        return

    # ---- HA RISPOSTO A "DA QUANTO FAI TRADING?" ----
    if state == "asked_trading":
        await audio_delay(context, chat_id)
        with open(AUDIO2_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        user_states[user_id] = "sent_vip_benefits"
        return

    # ---- VUOLE PROCEDERE DOPO I BENEFICI VIP ----
    if state == "sent_vip_benefits":
        # Se ha già PuPrime
        if contains_keyword(text, ALREADY_PUPRIME_KEYWORDS):
            await audio_delay(context, chat_id)
            with open(AUDIO3_PATH, "rb") as audio:
                await context.bot.send_voice(chat_id=chat_id, voice=audio)
            await human_delay(context, chat_id, 5)
            await context.bot.send_message(chat_id=chat_id, text=TESTO_CAMBIO_IB)
            user_states[user_id] = "has_puprime"
            return
        else:
            # Manda il link di iscrizione
            await human_delay(context, chat_id)
            await context.bot.send_message(chat_id=chat_id, text=TESTO_LINK_VIP)
            user_states[user_id] = "sent_link"
            return

    # ---- DOPO IL LINK — HA GIÀ PUPRIME ----
    if state == "sent_link":
        if contains_keyword(text, ALREADY_PUPRIME_KEYWORDS):
            await audio_delay(context, chat_id)
            with open(AUDIO3_PATH, "rb") as audio:
                await context.bot.send_voice(chat_id=chat_id, voice=audio)
            await human_delay(context, chat_id, 5)
            await context.bot.send_message(chat_id=chat_id, text=TESTO_CAMBIO_IB)
            user_states[user_id] = "has_puprime"
            return

        # Ha fatto la registrazione
        if contains_keyword(text, FATTO_KEYWORDS):
            await human_delay(context, chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Perfetto! Sto controllando tutto su PuPrime, appena verifico ti mando il link per accedere al VIP 🔍"
            )
            # Notifica Giacomo
            if GIACOMO_CHAT_ID:
                await context.bot.send_message(
                    chat_id=GIACOMO_CHAT_ID,
                    text=f"✅ *Nuovo iscritto da verificare!*\n\n👤 {user_name} (ID: `{user_id}`)\n\nControlla su PuPrime e manda il link VIP!",
                    parse_mode="Markdown"
                )
            user_states[user_id] = "waiting_verification"
            return

    # ---- DOPO CAMBIO IB — HA MANDATO LO SCREEN ----
    if state == "has_puprime":
        if contains_keyword(text, FATTO_KEYWORDS) or "screen" in text.lower():
            await human_delay(context, chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Perfetto! Sto controllando, appena verifico ti mando il link per accedere al VIP 🔍"
            )
            if GIACOMO_CHAT_ID:
                await context.bot.send_message(
                    chat_id=GIACOMO_CHAT_ID,
                    text=f"✅ *Cambio IB da verificare!*\n\n👤 {user_name} (ID: `{user_id}`)\n\nControlla su PuPrime e manda il link VIP!",
                    parse_mode="Markdown"
                )
            user_states[user_id] = "waiting_verification"
            return

    # ---- RISPOSTA GENERICA AI ----
    await human_delay(context, chat_id)
    response = get_ai_response(text, user_name)
    if response:
        await message.reply_text(response)

# ============================================================
# AVVIO
# ============================================================
def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("✅ FXJack Bot avviato!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
