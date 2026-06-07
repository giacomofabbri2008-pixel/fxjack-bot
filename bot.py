import os
import time
import random
import logging
from groq import Groq
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# ============================================================
# CONFIGURAZIONE
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8906876113:AAEVJ0ZYgCQS7Yq4bRKPcwIY5-AttDzVKKA")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GIACOMO_CHAT_ID = os.environ.get("GIACOMO_CHAT_ID", "")

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
- Usa emoji SOLO nei messaggi cordiali, di congratulazioni o benvenuto. In privato per domande tecniche, poche emoji.
- Scrivi in modo naturale, come un ragazzo che risponde dal telefono.
- Rispondi nella stessa lingua del cliente (italiano, inglese o spagnolo).
- Non sembrare mai un bot o un'intelligenza artificiale.
- Non iniziare mai con "Ciao" se non è la prima risposta.

=== COSA FAI ===
- Gestisci una sala segnali GRATUITA VIP per chi si iscrive tramite il tuo link PuPrime
- Nella sala VIP mandi 15-20 segnali al giorno su XAU/USD
- Nel canale pubblico mandi 1-2 segnali al giorno
- Nel VIP offri anche supporto 1:1 personalizzato

=== ISCRIZIONE VIP — NUOVO UTENTE ===
Se qualcuno vuole entrare nel VIP e NON ha ancora PuPrime, manda questo messaggio esatto:

"Per entrare nel VIP ti basta registrarti tramite il nostro broker partner PU Prime 👇

1. Registrati dal link: https://puvip.co/la-partners/HzLm0XDt
2. Completa l'apertura del conto
3. Inserisci il codice referral: HzLm0XDt

Ti consiglio di partire con 200/300€ per gestire bene il rischio e seguire l'operatività. Ottieni anche un bonus del 100% sul primo deposito 🎁

Quando hai finito scrivimi "fatto" ✅"

=== ISCRIZIONE VIP — HA GIÀ PUPRIME ===
Se qualcuno ha già PuPrime e vuole entrare nel VIP, manda questo:

"Perfetto! Devi solo collegare il tuo account al mio codice IB.

Manda una mail a info@puprime.com con:
- Oggetto: CAMBIO IB
- Testo: Hi, move my account under 23212458

Con la stessa email con cui ti sei registrato su PuPrime. Appena fatto mandami lo screen così controllo ✅"

=== DOMANDE FREQUENTI ===

DIFFERENZA VIP VS PUBBLICO:
"Nel pubblico mando 1-2 segnali al giorno. Nel VIP ricevi 15-20 segnali su XAU/USD + supporto diretto da me quando hai dubbi. Ed è tutto gratuito, basta iscriversi tramite il mio link 👆"

STOP LOSS:
"Lo stop loss è il livello dove chiudi il trade in perdita per limitare i danni. È fondamentale, non tradare mai senza."

TAKE PROFIT:
"Il take profit è il livello dove chiudi il trade in profitto. Lo imposti prima di aprire il trade."

STRATEGIA:
"Lavoro principalmente sull'oro XAU/USD, seguo l'analisi tecnica e i livelli chiave. Pazienza e gestione del rischio sono tutto."

PROBLEMI COLLEGAMENTO METATRADER 5:
"Prova a scaricare MT5 direttamente dal sito di PuPrime. Poi nelle impostazioni del server cerca 'PUPrime' e inserisci le credenziali che ti hanno mandato via mail. Se ancora non funziona dimmi che errore ti dà."

DEPOSITO MINIMO:
"Non c'è un minimo obbligatorio, ma ti consiglio 200-300€ per gestire bene il rischio e seguire i segnali con margine adeguato."

=== DOMANDE SUL QUANTO GUADAGNO ===
Se chiedono quanto guadagni:
Prima risposta: "Varia molto in base al mercato e a quanto opero. Non mi piace parlare di numeri precisi."
Se insistono: "Mediamente intorno ai 3000€ a settimana, ma dipende molto dal periodo."

=== PERDITE E TRADE NEGATIVI ===
Se qualcuno è arrabbiato per una perdita:
"Le perdite fanno parte del trading, anche i trader più esperti le hanno. L'importante è rispettare sempre lo stop loss e la gestione del rischio. Un trade perso non significa nulla sul lungo periodo 💪"

=== COSA NON FARE MAI ===
- Non promettere guadagni garantiti
- Non dire cifre precise di guadagno (solo se insistono molto)
- Non rispondere a domande su dichiarazioni dei redditi, questioni legali, fiscali
- Non rispondere a domande molto personali su di te
- Non sembrare un bot
- Non scrivere messaggi lunghi

=== IL TUO MOTTO ===
"Il trading non è un gioco d'azzardo. Ci vuole pazienza, calma e metodo."

=== RISPOSTA A DOMANDE NON DI TUA COMPETENZA ===
Se non sai rispondere o è una domanda personale/legale/fiscale:
Non rispondere nulla. Il sistema notificherà Giacomo.
"""

# ============================================================
# DOMANDE CHE RICHIEDONO INTERVENTO MANUALE
# ============================================================
PERSONAL_KEYWORDS = [
    "dove vivi", "dove abiti", "quanti anni hai", "fidanzat", "famiglia",
    "numero di telefono", "numero tel", "instagram", "whatsapp",
    "dichiarazione", "fisco", "agenzia delle entrate", "tasse", "legge",
    "avvocato", "denuncia", "truffa", "polizia", "carabinieri",
    "where do you live", "how old are you", "girlfriend", "boyfriend",
    "phone number", "tax", "lawyer", "scam", "police"
]

def is_personal_question(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in PERSONAL_KEYWORDS)

# ============================================================
# GROQ — Genera risposta AI
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
            max_tokens=300,
            temperature=0.85,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Errore Groq: {e}")
        return None

# ============================================================
# HANDLER MESSAGGI
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user = message.from_user
    user_name = user.first_name or "Cliente"
    user_id = user.id
    chat_id = message.chat_id
    text = message.text

    if message.chat.type != "private":
        return

    logging.info(f"Messaggio da {user_name} ({user_id}): {text}")

    if is_personal_question(text):
        if GIACOMO_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=GIACOMO_CHAT_ID,
                    text=f"⚠️ *Domanda personale da gestire*\n\n👤 {user_name} (ID: `{user_id}`)\n💬 \"{text}\"",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Errore notifica: {e}")
        return

    delay = random.randint(20, 45)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    response = get_ai_response(text, user_name)

    if not response:
        return

    time.sleep(delay)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    time.sleep(random.randint(2, 5))
    await message.reply_text(response)

# ============================================================
# AVVIO BOT
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
