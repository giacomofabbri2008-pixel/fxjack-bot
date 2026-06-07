import os
import time
import random
import logging
import datetime
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, JobQueue
from telegram.constants import ChatAction

# ============================================================
# CONFIGURAZIONE
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8906876113:AAEVJ0ZYgCQS7Yq4bRKPcwIY5-AttDzVKKA")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GIACOMO_CHAT_ID = os.environ.get("GIACOMO_CHAT_ID", "1075363140")
CANALE_ID = -3762151852

AUDIO1_PATH = "audio1_trading.mp3"
AUDIO2_PATH = "audio2_vip.mp3"
AUDIO3_PATH = "audio3_cambioib.mp3"

TESTO_LINK_VIP = """Per entrare nel VIP ti basta registrarti tramite il nostro broker partner PU Prime 👇

1. Registrati dal link: https://puvip.co/la-partners/HzLm0XDt
2. Completa l'apertura del conto
3. Inserisci il codice referral: HzLm0XDt

Ti consiglio di partire con 200/300€ per gestire bene il rischio e seguire l'operatività. Ottieni anche un bonus del 100% sul primo deposito 🎁

Quando hai finito scrivimi "fatto" ✅"""

TESTO_CAMBIO_IB = """Questa è la mail che devi inviare a PuPrime con la stessa email della registrazione, fai copia e incolla il messaggio di sotto 👇

Oggetto: CAMBIO IB
A: info@puprime.com

Hi, move my account under 23212458

Appena fatto mandami lo screen così controllo che sia tutto a posto ✅"""

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
# STATO UTENTI
# ============================================================
user_states = {}
user_last_message_time = {}
weekly_stats = {"messages": 0, "new_vip": 0}

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """
Sei Jack, un trader di 18 anni con 4 anni di esperienza nel trading, specializzato in XAU/USD (oro).
Gestisci una community su Telegram chiamata "FX Jack | SEGNALI FREE" e una sala VIP esclusiva.
Lavori con il broker PuPrime come introducing broker.

=== IL TUO STILE ===
- Rispondi SEMPRE in modo molto corto e diretto. Mai più di 3-4 righe.
- Dai del TU a tutti.
- Usa emoji SOLO nei messaggi cordiali, di congratulazioni o benvenuto.
- Scrivi in modo naturale, come un ragazzo che risponde dal telefono.
- Rispondi nella stessa lingua del cliente (italiano, inglese o spagnolo).
- Non sembrare mai un bot o un'intelligenza artificiale.

=== GESTIONE INDECISI ===
Se qualcuno dice "ci penso", "non so", "forse", "magari", "non sono sicuro":
Chiedigi in modo cordiale e amichevole cosa non lo convince e come puoi aiutarlo.
Esempio: "Dimmi, c'è qualcosa che non ti convince? Magari posso aiutarti"
Poi in base alla risposta gestisci l'obiezione in modo naturale e rassicurante.

=== GESTIONE OBIEZIONI ===
- "Costa troppo" / "non ho soldi" → "Non c'è nessun costo, il VIP è completamente gratuito. Ti basta aprire un conto tramite il mio link"
- "Non mi fido" → "Capisco, è normale avere dubbi. Puoi vedere i risultati nel canale pubblico ogni giorno, zero obblighi"
- "Non ho esperienza" → "Perfetto, il VIP è ideale per chi inizia — imparerai capendo come funziona il mercato passo per passo"
- "Non ho tempo" → "I segnali arrivano già pronti, devi solo seguirli. Ci vogliono 5 minuti al giorno"

=== DOMANDE FREQUENTI ===
DIFFERENZA VIP VS PUBBLICO: "Nel pubblico mando 1-2 segnali al giorno. Nel VIP ricevi 15-20 segnali su XAU/USD + supporto diretto da me. Ed è tutto gratuito 👆"
STOP LOSS: "Lo stop loss è il livello dove chiudi il trade in perdita per limitare i danni. Fondamentale, non tradare mai senza."
TAKE PROFIT: "Il take profit è il livello dove chiudi il trade in profitto. Lo imposti prima di aprire il trade."
STRATEGIA: "Lavoro sull'oro XAU/USD, seguo l'analisi tecnica e i livelli chiave. Pazienza e gestione del rischio sono tutto."
PROBLEMI METATRADER 5: "Scarica MT5 dal sito di PuPrime. Nelle impostazioni cerca il server 'PUPrime' e inserisci le credenziali che ti hanno mandato via mail. Dimmi che errore ti dà se non funziona."
DEPOSITO MINIMO: "Non c'è un minimo, ma consiglio 200-300€ per gestire bene il rischio."

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
- Non sembrare un bot

=== MOTTO ===
Il trading non è un gioco d'azzardo. Ci vuole pazienza, calma e metodo.
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
INDECISO_KEYWORDS = [
    "ci penso", "non so", "forse", "magari", "non sono sicuro", "non sono sicura",
    "devo pensarci", "vedremo", "maybe", "not sure", "i'll think", "no se",
    "pensarci", "ci devo pensare"
]
PERSONAL_KEYWORDS = [
    "dove vivi", "dove abiti", "fidanzat", "famiglia", "numero di telefono",
    "dichiarazione", "fisco", "tasse", "legge", "avvocato", "denuncia",
    "where do you live", "girlfriend", "boyfriend", "phone number", "tax", "lawyer"
]

def contains_keyword(text, keywords):
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)

# ============================================================
# GROQ
# ============================================================
def get_ai_response(user_message, user_name, extra_context=""):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        prompt = SYSTEM_PROMPT
        if extra_context:
            prompt += f"\n\nCONTESTO EXTRA: {extra_context}"
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
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
# FOLLOW UP AUTOMATICI
# ============================================================
async def followup_no_risposta(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]
    user_name = job_data["user_name"]
    followup_type = job_data["type"]

    current_state = user_states.get(user_id)

    if followup_type == "audio1" and current_state == "asked_trading":
        await human_delay(context, chat_id, random.randint(5, 15))
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ehi, magari ci stai ancora pensando. Ti dico solo che è rimasto 1 posto nel VIP, non voglio che te lo perdi"
        )
    elif followup_type == "link" and current_state == "sent_link":
        await human_delay(context, chat_id, random.randint(5, 15))
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ehi, magari ci stai ancora pensando. Ti dico solo che è rimasto 1 posto nel VIP, non voglio che te lo perdi"
        )

async def followup_indeciso(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]

    current_state = user_states.get(user_id)
    if current_state == "indeciso":
        await human_delay(context, chat_id, random.randint(5, 15))
        await context.bot.send_message(
            chat_id=chat_id,
            text="Tra l'altro oggi abbiamo chiuso ottimi trade sull'oro nel VIP. Se hai ancora dubbi sono qui, dimmi pure"
        )
        user_states[user_id] = "followup_indeciso_sent"

# ============================================================
# MESSAGGI CANALE AUTOMATICI
# ============================================================
async def manda_buongiorno(context: ContextTypes.DEFAULT_TYPE):
    msg = random.choice(MESSAGGI_BUONGIORNO)
    try:
        await context.bot.send_message(chat_id=CANALE_ID, text=msg)
        logging.info("Buongiorno mandato al canale")
    except Exception as e:
        logging.error(f"Errore buongiorno: {e}")

async def manda_us_session(context: ContextTypes.DEFAULT_TYPE):
    msg = random.choice(MESSAGGI_US_SESSION)
    try:
        await context.bot.send_message(chat_id=CANALE_ID, text=msg)
        logging.info("US Session mandato al canale")
    except Exception as e:
        logging.error(f"Errore US session: {e}")

async def manda_report_settimanale(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=GIACOMO_CHAT_ID,
            text=f"📊 *Report settimanale FXJack Bot*\n\n"
                 f"💬 Messaggi ricevuti: {weekly_stats['messages']}\n"
                 f"✅ Nuovi iscritti VIP: {weekly_stats['new_vip']}\n\n"
                 f"Settimana: {datetime.datetime.now().strftime('%d/%m/%Y')}",
            parse_mode="Markdown"
        )
        weekly_stats["messages"] = 0
        weekly_stats["new_vip"] = 0
    except Exception as e:
        logging.error(f"Errore report: {e}")

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

    weekly_stats["messages"] += 1
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
        # Follow up dopo 1 ora se non risponde
        context.job_queue.run_once(
            followup_no_risposta,
            3600,
            data={"user_id": user_id, "chat_id": chat_id, "user_name": user_name, "type": "audio1"}
        )
        return

    # ---- HA RISPOSTO A "DA QUANTO FAI TRADING?" ----
    if state == "asked_trading":
        await audio_delay(context, chat_id)
        with open(AUDIO2_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        user_states[user_id] = "sent_vip_benefits"
        return

    # ---- DOPO I BENEFICI VIP ----
    if state == "sent_vip_benefits":
        if contains_keyword(text, ALREADY_PUPRIME_KEYWORDS):
            await audio_delay(context, chat_id)
            with open(AUDIO3_PATH, "rb") as audio:
                await context.bot.send_voice(chat_id=chat_id, voice=audio)
            await human_delay(context, chat_id, 5)
            await context.bot.send_message(chat_id=chat_id, text=TESTO_CAMBIO_IB)
            user_states[user_id] = "has_puprime"
            return
        elif contains_keyword(text, INDECISO_KEYWORDS):
            await human_delay(context, chat_id)
            response = get_ai_response(text, user_name, "L'utente è indeciso sul VIP. Chiedigli cosa non lo convince in modo cordiale e amichevole.")
            if response:
                await context.bot.send_message(chat_id=chat_id, text=response)
            user_states[user_id] = "indeciso"
            context.job_queue.run_once(
                followup_indeciso,
                86400,
                data={"user_id": user_id, "chat_id": chat_id}
            )
            return
        else:
            await human_delay(context, chat_id)
            await context.bot.send_message(chat_id=chat_id, text=TESTO_LINK_VIP)
            user_states[user_id] = "sent_link"
            context.job_queue.run_once(
                followup_no_risposta,
                3600,
                data={"user_id": user_id, "chat_id": chat_id, "user_name": user_name, "type": "link"}
            )
            return

    # ---- DOPO IL LINK ----
    if state == "sent_link":
        if contains_keyword(text, ALREADY_PUPRIME_KEYWORDS):
            await audio_delay(context, chat_id)
            with open(AUDIO3_PATH, "rb") as audio:
                await context.bot.send_voice(chat_id=chat_id, voice=audio)
            await human_delay(context, chat_id, 5)
            await context.bot.send_message(chat_id=chat_id, text=TESTO_CAMBIO_IB)
            user_states[user_id] = "has_puprime"
            return
        elif contains_keyword(text, INDECISO_KEYWORDS):
            await human_delay(context, chat_id)
            response = get_ai_response(text, user_name, "L'utente è indeciso sul VIP. Chiedigli cosa non lo convince in modo cordiale e amichevole.")
            if response:
                await context.bot.send_message(chat_id=chat_id, text=response)
            user_states[user_id] = "indeciso"
            context.job_queue.run_once(
                followup_indeciso,
                86400,
                data={"user_id": user_id, "chat_id": chat_id}
            )
            return
        elif contains_keyword(text, FATTO_KEYWORDS):
            await human_delay(context, chat_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Perfetto! Sto controllando tutto su PuPrime, appena verifico ti mando il link per accedere al VIP 🔍"
            )
            if GIACOMO_CHAT_ID:
                await context.bot.send_message(
                    chat_id=GIACOMO_CHAT_ID,
                    text=f"✅ *Nuovo iscritto da verificare!*\n\n👤 {user_name} (ID: `{user_id}`)\n\nControlla su PuPrime e manda il link VIP!",
                    parse_mode="Markdown"
                )
            weekly_stats["new_vip"] += 1
            user_states[user_id] = "waiting_verification"
            return

    # ---- DOPO CAMBIO IB ----
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
            weekly_stats["new_vip"] += 1
            user_states[user_id] = "waiting_verification"
            return

    # ---- INDECISO — GESTIONE OBIEZIONE ----
    if state in ["indeciso", "followup_indeciso_sent"]:
        await human_delay(context, chat_id)
        response = get_ai_response(text, user_name, "L'utente era indeciso sul VIP. Gestisci la sua obiezione in modo cordiale, rassicurante e spingi verso l'iscrizione senza essere aggressivo.")
        if response:
            await context.bot.send_message(chat_id=chat_id, text=response)
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

    # Messaggi automatici canale
    job_queue = app.job_queue

    # Buongiorno ogni giorno alle 8:00 (UTC+2 Italia = 6:00 UTC)
    job_queue.run_daily(
        manda_buongiorno,
        time=datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc)
    )

    # US Session alle 15:30 (UTC+2 = 13:30 UTC)
    job_queue.run_daily(
        manda_us_session,
        time=datetime.time(hour=13, minute=30, tzinfo=datetime.timezone.utc)
    )

    # Report settimanale ogni lunedì alle 9:00 (7:00 UTC)
    job_queue.run_daily(
        manda_report_settimanale,
        time=datetime.time(hour=7, minute=0, tzinfo=datetime.timezone.utc),
        days=(0,)  # 0 = lunedì
    )

    logging.info("✅ FXJack Bot avviato con tutti i miglioramenti!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
