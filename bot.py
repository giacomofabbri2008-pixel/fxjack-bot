import os
import time
import random
import logging
import datetime
from groq import Groq
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ChatAction
import base64
import json

# ============================================================
# CONFIGURAZIONE
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8906876113:AAEVJ0ZYgCQS7Yq4bRKPcwIY5-AttDzVKKA")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GIACOMO_CHAT_ID = os.environ.get("GIACOMO_CHAT_ID", "1075363140")
CANALE_ID = -3762151852
LINK_VIP = "https://t.me/+0QGldo1oEdhlZDRk"

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
user_conversations = {}
user_states = {}
weekly_stats = {"messages": 0, "new_vip": 0}
bot_paused_global = False
paused_users = set()
pending_verification = {}

# ============================================================
# SYSTEM PROMPT — IL CERVELLO DEL BOT
# ============================================================
SYSTEM_PROMPT = """Sei Jack, trader di 18 anni con 4 anni di esperienza su XAU/USD (oro).
Gestisci la community "FX Jack | SEGNALI FREE" su Telegram e una sala VIP esclusiva.
Lavori con PuPrime come introducing broker — guadagni dalle commissioni dei clienti che operano.

=== IL TUO OBIETTIVO PRINCIPALE ===
Convertire ogni persona che ti scrive in un iscritto al VIP che deposita e opera su PuPrime tramite il tuo link.
Ogni conversazione deve portare il cliente verso questo obiettivo, in modo naturale e mai forzato.

=== IL TUO STILE ===
- Sei un ragazzo di 18 anni che scrive dal telefono — naturale, diretto, corto
- Max 2-3 righe per messaggio, mai di più
- Dai del TU a tutti
- Rispondi SEMPRE nella stessa lingua del cliente (italiano, inglese, spagnolo)
- Emoji solo quando sono naturali — celebrare un profitto, dare energia. Mai emoji decorative
- Non sembrare mai un bot. Non usare frasi formali o robotiche
- Leggi SEMPRE tutta la cronologia della chat prima di rispondere

=== MEMORIA E CONTESTO ===
Ricordi tutto quello che è stato detto nella conversazione.
Non ripetere mai cose già dette.
Se il cliente ha già risposto a una domanda, non rigliela.
Adatta sempre la risposta al punto in cui si trova il cliente nel suo percorso.

=== IL PERCORSO DI CONVERSIONE ===
Ogni cliente passa per questi step. Tu sai sempre a che punto è e vai avanti:

STEP 1 — INTERESSE: il cliente chiede del VIP o dei segnali
→ Rispondi con curiosità, chiedigli da quanto fa trading (per capire il suo livello)
→ NON mandare link, NON spiegare tutto subito

STEP 2 — QUALIFICA: il cliente risponde da quanto fa trading
→ Mostra entusiasmo, digli che nel VIP migliorerà molto
→ Chiedigli se ha già PuPrime o no

STEP 3A — NON HA PUPRIME:
→ Digli che per entrare nel VIP deve aprire un conto PuPrime tramite il tuo link
→ Usa SEMPRE e SOLO questo testo esatto, non inventare mai link diversi:
[INVIA_TESTO_VIP]

STEP 3B — HA GIÀ PUPRIME:
→ Digli che deve collegare l'account al tuo codice IB
→ Usa SEMPRE e SOLO questo testo esatto:
[INVIA_TESTO_CAMBIO_IB]

STEP 4 — HA COMPLETATO LA REGISTRAZIONE (dice "fatto" o simile):
→ Chiedigli nome e cognome per verificare su PuPrime
→ Usa esattamente: "Perfetto! Dimmi il tuo nome e cognome così verifico tutto su PuPrime"

STEP 5 — HA DATO NOME E COGNOME:
→ Digli che stai verificando e lo aggiungi presto
→ Usa esattamente: "Perfetto! Sto controllando tutto, appena verifico ti mando il link per accedere al VIP"
→ [NOTIFICA_GIACOMO]

=== GESTIONE CASI SPECIALI ===

SE È INDECISO ("ci penso", "forse", "non so"):
→ Non spingere, chiedigli cosa non lo convince
→ Ascolta la risposta e gestisci l'obiezione in modo cordiale
→ Obiezioni comuni:
   - "Costa" → "è completamente gratuito, ti basta il link"
   - "Non mi fido" → "guarda i risultati nel canale pubblico ogni giorno, zero rischi"
   - "Non ho esperienza" → "perfetto, nel VIP impari passo per passo"
   - "Non ho tempo" → "i segnali arrivano pronti, 5 minuti al giorno"

SE È ARRABBIATO PER UNA PERDITA:
→ Cordiale e rassicurante: "Le perdite fanno parte del trading, anche i migliori le hanno. L'importante è lo stop loss — un trade perso non cambia nulla sul lungo periodo"

SE CHIEDE QUANTO GUADAGNI:
→ Prima risposta: "Varia molto, non mi piace parlare di numeri precisi"
→ Se insiste: "Mediamente intorno ai 3000€ a settimana, dipende dal periodo"

SE HA PROBLEMI CON MT5:
→ "Scarica MT5 dal sito di PuPrime, cerca il server PUPrime e inserisci le credenziali ricevute via mail. Dimmi che errore ti dà"

SE CHIEDE STOP LOSS / TAKE PROFIT / STRATEGIA:
→ Rispondi brevemente e poi riporta la conversazione verso il VIP

=== COSA NON FARE MAI ===
- Non inventare o modificare link di PuPrime — usa SEMPRE [INVIA_TESTO_VIP] o [INVIA_TESTO_CAMBIO_IB]
- Non promettere guadagni garantiti
- Non rispondere su tasse, leggi, dichiarazioni fiscali
- Non rispondere a domande private su di te (dove vivi, fidanzata, ecc.) → [DOMANDA_PERSONALE]
- Non scrivere messaggi lunghi
- Non ripetere cose già dette nella chat

=== FORMATO RISPOSTA ===
Rispondi SEMPRE con un JSON così:
{
  "action": "TEXT" | "AUDIO1" | "AUDIO2" | "AUDIO3" | "TESTO_VIP" | "TESTO_CAMBIO_IB" | "CHIEDI_NOME" | "VERIFICA" | "PERSONALE" | "NOTIFICA_GIACOMO",
  "text": "il tuo messaggio qui (solo se action è TEXT)",
  "next_state": "interest" | "qualified" | "sent_link" | "has_puprime" | "waiting_name" | "waiting_verification" | "vip_member" | null
}

Usa "action: AUDIO1" quando vuoi mandare l'audio "da quanto fai trading"
Usa "action: AUDIO2" quando vuoi mandare l'audio "benefici VIP"
Usa "action: AUDIO3" quando vuoi mandare l'audio "cambio IB"
Usa "action: TESTO_VIP" quando vuoi mandare il testo con il link di iscrizione
Usa "action: TESTO_CAMBIO_IB" quando vuoi mandare il testo cambio IB
Usa "action: CHIEDI_NOME" quando devi chiedere nome e cognome
Usa "action: VERIFICA" quando il cliente ha dato nome e cognome
Usa "action: PERSONALE" per domande private da ignorare e notificare Giacomo
Usa "action: TEXT" per qualsiasi altro messaggio testuale
"""

# ============================================================
# GROQ — CERVELLO PRINCIPALE
# ============================================================
def get_bot_action(user_message, user_name, conversation_history, user_state):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        state_context = f"\nSTATO ATTUALE DEL CLIENTE: {user_state or 'nuovo'}\n" if user_state else ""
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT + state_context}]
        
        # Aggiungi cronologia
        for msg in conversation_history[-10:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": f"{user_name}: {user_message}"})
        
        result = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            temperature=0.7,
        )
        
        response_text = result.choices[0].message.content.strip()
        
        # Pulisci il JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(response_text)
        return parsed
        
    except Exception as e:
        logging.error(f"Errore get_bot_action: {e}")
        return {"action": "TEXT", "text": None, "next_state": None}

# ============================================================
# GROQ — ANALISI IMMAGINI
# ============================================================
def get_ai_response_image(image_data, user_name):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        result = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Sei Jack, trader 18 anni. Analizza questo screenshot e rispondi in modo corto e diretto per aiutare il cliente a risolvere il problema. Max 3 righe. Parla in modo naturale."},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        {"type": "text", "text": f"{user_name} ti ha mandato questo screenshot, aiutalo."}
                    ]
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=200,
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Errore immagine: {e}")
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

def add_to_history(user_id, role, content):
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    user_conversations[user_id].append({"role": role, "content": content})
    if len(user_conversations[user_id]) > 20:
        user_conversations[user_id] = user_conversations[user_id][-20:]

# ============================================================
# FOLLOW UP
# ============================================================
async def followup_no_risposta(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]
    expected_state = job_data["expected_state"]

    if bot_paused_global or user_id in paused_users:
        return
    if user_states.get(user_id) != expected_state:
        return

    await human_delay(context, chat_id, random.randint(5, 15))
    msg = "Ehi, magari ci stai ancora pensando. Ti dico solo che è rimasto 1 posto nel VIP, non voglio che te lo perdi"
    await context.bot.send_message(chat_id=chat_id, text=msg)
    add_to_history(user_id, "assistant", msg)

async def followup_indeciso(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]

    if bot_paused_global or user_id in paused_users:
        return
    if user_states.get(user_id) != "indeciso":
        return

    await human_delay(context, chat_id, random.randint(5, 15))
    msg = "Tra l'altro oggi abbiamo chiuso ottimi trade sull'oro nel VIP. Se hai ancora dubbi sono qui"
    await context.bot.send_message(chat_id=chat_id, text=msg)
    add_to_history(user_id, "assistant", msg)

# ============================================================
# MESSAGGI CANALE AUTOMATICI
# ============================================================
async def manda_buongiorno(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(chat_id=CANALE_ID, text=random.choice(MESSAGGI_BUONGIORNO))
    except Exception as e:
        logging.error(f"Errore buongiorno: {e}")

async def manda_us_session(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(chat_id=CANALE_ID, text=random.choice(MESSAGGI_US_SESSION))
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
# COMANDI GIACOMO
# ============================================================
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_paused_global
    if str(update.effective_user.id) != str(GIACOMO_CHAT_ID):
        return
    bot_paused_global = True
    await update.message.reply_text("⏸ Bot in pausa globale. Scrivi /start per riattivarlo.")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_paused_global
    if str(update.effective_user.id) != str(GIACOMO_CHAT_ID):
        return
    bot_paused_global = False
    await update.message.reply_text("▶️ Bot riattivato!")

async def cmd_pausa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(GIACOMO_CHAT_ID):
        return
    if not context.args:
        await update.message.reply_text("Usa: /pausa USER_ID")
        return
    user_id = int(context.args[0])
    paused_users.add(user_id)
    await update.message.reply_text(f"⏸ Bot in pausa per utente {user_id}")

async def cmd_riprendi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(GIACOMO_CHAT_ID):
        return
    if not context.args:
        await update.message.reply_text("Usa: /riprendi USER_ID")
        return
    user_id = int(context.args[0])
    paused_users.discard(user_id)
    await update.message.reply_text(f"▶️ Bot riattivato per utente {user_id}")

async def cmd_approva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(GIACOMO_CHAT_ID):
        return
    if not context.args:
        await update.message.reply_text("Usa: /approva USER_ID")
        return
    user_id = int(context.args[0])
    if user_id in pending_verification:
        data = pending_verification[user_id]
        chat_id = data["chat_id"]
        user_name = data["user_name"]
        await human_delay(context, chat_id, random.randint(5, 15))
        msg = f"Tutto verificato! Benvenuto nel VIP 🎉\n\nEcco il link: {LINK_VIP}"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        del pending_verification[user_id]
        user_states[user_id] = "vip_member"
        weekly_stats["new_vip"] += 1
        await update.message.reply_text(f"✅ {user_name} approvato!")
    else:
        await update.message.reply_text(f"Utente {user_id} non trovato.")

async def cmd_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(GIACOMO_CHAT_ID):
        return
    if not pending_verification:
        await update.message.reply_text("Nessun utente in attesa.")
        return
    msg = "📋 *In attesa di verifica:*\n\n"
    for uid, data in pending_verification.items():
        msg += f"👤 {data['full_name']} — ID: `{uid}`\n📅 {data['date']}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ============================================================
# HANDLER FOTO
# ============================================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or message.chat.type != "private":
        return
    user = message.from_user
    user_name = user.first_name or "Cliente"
    user_id = user.id
    chat_id = message.chat_id
    if bot_paused_global or user_id in paused_users:
        return
    weekly_stats["messages"] += 1
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_data = await file.download_as_bytearray()
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    time.sleep(random.randint(20, 35))
    response = get_ai_response_image(bytes(image_data), user_name)
    if response:
        await message.reply_text(response)
        add_to_history(user_id, "assistant", response)

# ============================================================
# HANDLER MESSAGGI PRINCIPALE
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

    if bot_paused_global or user_id in paused_users:
        return

    weekly_stats["messages"] += 1
    logging.info(f"[{user_name} | {user_id}]: {text}")

    add_to_history(user_id, "user", text)
    history = user_conversations.get(user_id, [])
    state = user_states.get(user_id)

    # Chiedi al cervello AI cosa fare
    result = get_bot_action(text, user_name, history[:-1], state)
    action = result.get("action", "TEXT")
    response_text = result.get("text")
    next_state = result.get("next_state")

    logging.info(f"Action: {action} | State: {state} -> {next_state}")

    # Aggiorna stato
    if next_state:
        user_states[user_id] = next_state

    # ---- ESEGUI L'AZIONE ----

    if action == "PERSONALE":
        if GIACOMO_CHAT_ID:
            await context.bot.send_message(
                chat_id=GIACOMO_CHAT_ID,
                text=f"⚠️ *Domanda personale*\n\n👤 {user_name} (ID: `{user_id}`)\n💬 \"{text}\"",
                parse_mode="Markdown"
            )
        return

    elif action == "AUDIO1":
        await audio_delay(context, chat_id)
        with open(AUDIO1_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        add_to_history(user_id, "assistant", "[Audio: da quanto fai trading?]")
        context.job_queue.run_once(
            followup_no_risposta, 3600,
            data={"user_id": user_id, "chat_id": chat_id, "expected_state": next_state or state}
        )

    elif action == "AUDIO2":
        await audio_delay(context, chat_id)
        with open(AUDIO2_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        add_to_history(user_id, "assistant", "[Audio: benefici VIP]")

    elif action == "AUDIO3":
        await audio_delay(context, chat_id)
        with open(AUDIO3_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        add_to_history(user_id, "assistant", "[Audio: cambio IB]")
        await human_delay(context, chat_id, 5)
        await context.bot.send_message(chat_id=chat_id, text=TESTO_CAMBIO_IB)
        add_to_history(user_id, "assistant", TESTO_CAMBIO_IB)

    elif action == "TESTO_VIP":
        await human_delay(context, chat_id)
        await context.bot.send_message(chat_id=chat_id, text=TESTO_LINK_VIP)
        add_to_history(user_id, "assistant", TESTO_LINK_VIP)
        context.job_queue.run_once(
            followup_no_risposta, 3600,
            data={"user_id": user_id, "chat_id": chat_id, "expected_state": next_state or state}
        )

    elif action == "TESTO_CAMBIO_IB":
        await human_delay(context, chat_id)
        await context.bot.send_message(chat_id=chat_id, text=TESTO_CAMBIO_IB)
        add_to_history(user_id, "assistant", TESTO_CAMBIO_IB)

    elif action == "CHIEDI_NOME":
        await human_delay(context, chat_id)
        msg = "Perfetto! Dimmi il tuo nome e cognome così verifico tutto su PuPrime"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        user_states[user_id] = "waiting_name"

    elif action == "VERIFICA":
        full_name = text.strip()
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        pending_verification[user_id] = {
            "chat_id": chat_id,
            "user_name": user_name,
            "full_name": full_name,
            "date": now
        }
        await human_delay(context, chat_id)
        msg = "Perfetto! Sto controllando tutto, appena verifico ti mando il link per accedere al VIP"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        user_states[user_id] = "waiting_verification"
        if GIACOMO_CHAT_ID:
            await context.bot.send_message(
                chat_id=GIACOMO_CHAT_ID,
                text=f"✅ *Account da verificare su PuPrime!*\n\n"
                     f"👤 Nome: *{full_name}*\n"
                     f"🆔 ID: `{user_id}`\n"
                     f"📅 {now}\n\n"
                     f"Scrivi: `/approva {user_id}`",
                parse_mode="Markdown"
            )

    elif action == "TEXT" and response_text:
        await human_delay(context, chat_id)
        await message.reply_text(response_text)
        add_to_history(user_id, "assistant", response_text)
        # Follow up se indeciso
        if next_state == "indeciso":
            context.job_queue.run_once(
                followup_indeciso, 86400,
                data={"user_id": user_id, "chat_id": chat_id}
            )

# ============================================================
# AVVIO
# ============================================================
def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pausa", cmd_pausa))
    app.add_handler(CommandHandler("riprendi", cmd_riprendi))
    app.add_handler(CommandHandler("approva", cmd_approva))
    app.add_handler(CommandHandler("lista", cmd_lista))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    job_queue = app.job_queue
    job_queue.run_daily(manda_buongiorno, time=datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc))
    job_queue.run_daily(manda_us_session, time=datetime.time(hour=13, minute=30, tzinfo=datetime.timezone.utc))
    job_queue.run_daily(manda_report_settimanale, time=datetime.time(hour=7, minute=0, tzinfo=datetime.timezone.utc), days=(0,))

    logging.info("✅ FXJack Bot avviato!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
