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
user_states = {}
user_conversations = {}  # Storico conversazione per ogni utente
weekly_stats = {"messages": 0, "new_vip": 0}
bot_paused_global = False
paused_users = set()
pending_verification = {}

# ============================================================
# SYSTEM PROMPT PRINCIPALE
# ============================================================
SYSTEM_PROMPT = """
Sei Jack, un trader di 18 anni con 4 anni di esperienza nel trading, specializzato in XAU/USD (oro).
Gestisci una community su Telegram chiamata "FX Jack | SEGNALI FREE" e una sala VIP esclusiva.
Lavori con il broker PuPrime come introducing broker.

=== IL TUO STILE ===
- Rispondi SEMPRE in modo molto corto e diretto. Mai più di 3-4 righe.
- Dai del TU a tutti.
- Usa emoji SOLO quando aggiungono qualcosa di vero al messaggio — tipo celebrare un bel profitto o dare energia nel canale. Mai emoji decorative o inutili come lenti, frecce, orologi. Un ragazzo di 18 anni non le usa così.
- Scrivi in modo naturale, come un ragazzo che risponde dal telefono.
- Rispondi nella stessa lingua del cliente (italiano, inglese o spagnolo).
- Non sembrare mai un bot o un'intelligenza artificiale.
- Leggi sempre il contesto della conversazione prima di rispondere.

=== ANALISI SCREENSHOT ===
Se ti mandano uno screenshot con un errore o problema:
- Analizzalo e dai istruzioni corte e chiare per risolvere
- Sii sempre rassicurante

=== GESTIONE INDECISI ===
Se qualcuno dice "ci penso", "non so", "forse", "magari":
Chiedigi in modo cordiale cosa non lo convince.

=== GESTIONE OBIEZIONI ===
- "Costa troppo" → "Il VIP è completamente gratuito, ti basta il link"
- "Non mi fido" → "Puoi vedere i risultati nel canale pubblico ogni giorno, zero obblighi"
- "Non ho esperienza" → "Perfetto, nel VIP imparerai passo per passo"
- "Non ho tempo" → "I segnali arrivano già pronti, ci vogliono 5 minuti al giorno"

=== DOMANDE FREQUENTI ===
STOP LOSS: "Il livello dove chiudi il trade in perdita per limitare i danni. Non tradare mai senza."
TAKE PROFIT: "Il livello dove chiudi il trade in profitto. Lo imposti prima di aprire."
STRATEGIA: "Oro XAU/USD, analisi tecnica e livelli chiave. Pazienza e gestione del rischio."
MT5: "Scarica MT5 dal sito di PuPrime. Cerca server 'PUPrime' e inserisci le credenziali ricevute via mail."
DEPOSITO: "Non c'è un minimo, ma consiglio 200-300€ per gestire bene il rischio."

=== GUADAGNI ===
Prima risposta: "Varia molto in base al mercato. Non mi piace parlare di numeri."
Se insistono: "Mediamente intorno ai 3000€ a settimana, dipende dal periodo."

=== PERDITE ===
"Le perdite fanno parte del trading. L'importante è rispettare sempre lo stop loss 💪"

=== NON FARE MAI ===
- Non promettere guadagni garantiti
- Non rispondere su tasse, leggi, dichiarazioni
- Non rispondere a domande personali
- Non scrivere messaggi lunghi
- Non sembrare un bot
"""

# ============================================================
# PROMPT CLASSIFICATORE
# ============================================================
CLASSIFIER_PROMPT = """Sei un classificatore. Analizza il messaggio del cliente e la cronologia della conversazione e rispondi con UNA SOLA di queste categorie:

CATEGORIE:
- VUOLE_VIP: vuole entrare nel VIP, è interessato, chiede come fare
- HA_FATTO_REGISTRAZIONE: dice di aver fatto la registrazione a PuPrime tramite link, ha depositato, ha completato tutto
- HA_GIA_PUPRIME: dice di avere già un account PuPrime esistente prima di oggi
- RISPOSTA_TRADING: sta rispondendo alla domanda "da quanto fai trading"
- VUOLE_PROCEDERE: dopo aver sentito i benefici del VIP vuole andare avanti
- INDECISO: non è sicuro, ci deve pensare, forse, magari
- DATO_NOME: sta fornendo il suo nome e cognome
- DOMANDA_GENERICA: domanda normale su trading, segnali, ecc.
- PROBLEMA_TECNICO: ha un problema tecnico con MT5 o PuPrime
- PERSONALE: domanda personale su Jack (dove vivi, fidanzata, ecc.)
- NEGATIVO: arrabbiato per perdite

Rispondi con SOLO la categoria, nient'altro."""

def classify_message(text, conversation_history, user_name):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        messages = [{"role": "system", "content": CLASSIFIER_PROMPT}]
        if conversation_history:
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history[-6:]])
            messages.append({"role": "user", "content": f"Cronologia conversazione:\n{history_text}\n\nNuovo messaggio di {user_name}: {text}"})
        else:
            messages.append({"role": "user", "content": f"Messaggio di {user_name}: {text}"})
        
        result = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            max_tokens=20,
            temperature=0.1,
        )
        category = result.choices[0].message.content.strip().upper()
        logging.info(f"Classificazione: {category}")
        return category
    except Exception as e:
        logging.error(f"Errore classificatore: {e}")
        return "DOMANDA_GENERICA"

# ============================================================
# GROQ — RISPOSTA TESTO
# ============================================================
def get_ai_response(user_message, user_name, extra_context="", conversation_history=None):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        prompt = SYSTEM_PROMPT
        if extra_context:
            prompt += f"\n\nCONTESTO: {extra_context}"
        
        messages = [{"role": "system", "content": prompt}]
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)
        messages.append({"role": "user", "content": f"Messaggio da {user_name}: {user_message}"})
        
        result = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            temperature=0.85,
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Errore Groq: {e}")
        return None

# ============================================================
# GROQ — IMMAGINI
# ============================================================
def get_ai_response_image(image_data, user_name):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        result = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        {"type": "text", "text": f"{user_name} ti ha mandato questo screenshot. Analizzalo e aiutalo in modo corto e diretto."}
                    ]
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=300,
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Errore Groq immagine: {e}")
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
    followup_type = job_data["type"]
    current_state = user_states.get(user_id)

    if bot_paused_global or user_id in paused_users:
        return

    if followup_type == "audio1" and current_state == "asked_trading":
        await human_delay(context, chat_id, random.randint(5, 15))
        msg = "Ehi, magari ci stai ancora pensando. Ti dico solo che è rimasto 1 posto nel VIP, non voglio che te lo perdi"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
    elif followup_type == "link" and current_state == "sent_link":
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
    if user_states.get(user_id) == "indeciso":
        await human_delay(context, chat_id, random.randint(5, 15))
        msg = "Tra l'altro oggi abbiamo chiuso ottimi trade sull'oro nel VIP. Se hai ancora dubbi sono qui, dimmi pure"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        user_states[user_id] = "followup_indeciso_sent"

# ============================================================
# MESSAGGI CANALE
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
        msg = f"Tutto verificato! Benvenuto nel VIP 🎉\n\nEcco il link per accedere: {LINK_VIP}"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        del pending_verification[user_id]
        user_states[user_id] = "vip_member"
        weekly_stats["new_vip"] += 1
        await update.message.reply_text(f"✅ {user_name} approvato e link VIP inviato!")
    else:
        await update.message.reply_text(f"Utente {user_id} non trovato in lista verifica.")

async def cmd_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(GIACOMO_CHAT_ID):
        return
    if not pending_verification:
        await update.message.reply_text("Nessun utente in attesa di verifica.")
        return
    msg = "📋 *Utenti in attesa di verifica:*\n\n"
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
# HANDLER MESSAGGI — LOGICA INTELLIGENTE
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
    logging.info(f"Messaggio da {user_name} ({user_id}): {text}")

    add_to_history(user_id, "user", text)
    history = user_conversations.get(user_id, [])
    state = user_states.get(user_id, None)

    # Classifica il messaggio con AI
    category = classify_message(text, history, user_name)

    # ---- DOMANDA PERSONALE ----
    if category == "PERSONALE":
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

    # ---- HA GIA FATTO TUTTO (registrazione + deposito) ----
    if category == "HA_FATTO_REGISTRAZIONE" and state not in ["waiting_name", "waiting_verification", "vip_member"]:
        await human_delay(context, chat_id)
        msg = "Perfetto! Dimmi il tuo nome e cognome così verifico tutto su PuPrime"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        user_states[user_id] = "waiting_name"
        return

    # ---- VUOLE ENTRARE NEL VIP ----
    if category == "VUOLE_VIP" and state is None:
        await audio_delay(context, chat_id)
        with open(AUDIO1_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        add_to_history(user_id, "assistant", "[Audio inviato: da quanto fai trading?]")
        user_states[user_id] = "asked_trading"
        context.job_queue.run_once(
            followup_no_risposta, 3600,
            data={"user_id": user_id, "chat_id": chat_id, "user_name": user_name, "type": "audio1"}
        )
        return

    # ---- HA RISPOSTO A DA QUANTO FAI TRADING ----
    if category == "RISPOSTA_TRADING" or (state == "asked_trading" and category not in ["VUOLE_VIP", "HA_FATTO_REGISTRAZIONE", "PERSONALE"]):
        await audio_delay(context, chat_id)
        with open(AUDIO2_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        add_to_history(user_id, "assistant", "[Audio inviato: benefici VIP]")
        user_states[user_id] = "sent_vip_benefits"
        return

    # ---- HA GIA PUPRIME ----
    if category == "HA_GIA_PUPRIME" and state not in ["waiting_name", "waiting_verification", "vip_member"]:
        await audio_delay(context, chat_id)
        with open(AUDIO3_PATH, "rb") as audio:
            await context.bot.send_voice(chat_id=chat_id, voice=audio)
        add_to_history(user_id, "assistant", "[Audio inviato: cambio IB]")
        await human_delay(context, chat_id, 5)
        await context.bot.send_message(chat_id=chat_id, text=TESTO_CAMBIO_IB)
        add_to_history(user_id, "assistant", TESTO_CAMBIO_IB)
        user_states[user_id] = "has_puprime"
        return

    # ---- VUOLE PROCEDERE DOPO I BENEFICI ----
    if category == "VUOLE_PROCEDERE" or (state == "sent_vip_benefits" and category not in ["INDECISO", "HA_GIA_PUPRIME", "PERSONALE"]):
        await human_delay(context, chat_id)
        await context.bot.send_message(chat_id=chat_id, text=TESTO_LINK_VIP)
        add_to_history(user_id, "assistant", TESTO_LINK_VIP)
        user_states[user_id] = "sent_link"
        context.job_queue.run_once(
            followup_no_risposta, 3600,
            data={"user_id": user_id, "chat_id": chat_id, "user_name": user_name, "type": "link"}
        )
        return

    # ---- INDECISO ----
    if category == "INDECISO":
        await human_delay(context, chat_id)
        response = get_ai_response(text, user_name, "L'utente è indeciso. Chiedigli cosa non lo convince in modo cordiale.", history)
        if response:
            await context.bot.send_message(chat_id=chat_id, text=response)
            add_to_history(user_id, "assistant", response)
        user_states[user_id] = "indeciso"
        context.job_queue.run_once(followup_indeciso, 86400, data={"user_id": user_id, "chat_id": chat_id})
        return

    # ---- ASPETTA NOME E COGNOME ----
    if state == "waiting_name" and category == "DATO_NOME":
        full_name = text.strip()
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        pending_verification[user_id] = {
            "chat_id": chat_id,
            "user_name": user_name,
            "full_name": full_name,
            "date": now
        }
        await human_delay(context, chat_id)
        msg = "Perfetto! Sto controllando tutto su PuPrime, appena verifico ti mando il link per accedere al VIP"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        if GIACOMO_CHAT_ID:
            await context.bot.send_message(
                chat_id=GIACOMO_CHAT_ID,
                text=f"✅ *Account da verificare su PuPrime!*\n\n"
                     f"👤 Nome: *{full_name}*\n"
                     f"🆔 ID: `{user_id}`\n"
                     f"📅 Data: {now}\n\n"
                     f"Controlla su PuPrime e scrivi:\n`/approva {user_id}`",
                parse_mode="Markdown"
            )
        user_states[user_id] = "waiting_verification"
        return

    # ---- DOPO CAMBIO IB — MANDA SCREEN ----
    if state == "has_puprime":
        await human_delay(context, chat_id)
        msg = "Perfetto! Dimmi il tuo nome e cognome così verifico tutto su PuPrime"
        await context.bot.send_message(chat_id=chat_id, text=msg)
        add_to_history(user_id, "assistant", msg)
        user_states[user_id] = "waiting_name"
        return

    # ---- RISPOSTA GENERICA AI ----
    await human_delay(context, chat_id)
    response = get_ai_response(text, user_name, "", history)
    if response:
        await message.reply_text(response)
        add_to_history(user_id, "assistant", response)

# ============================================================
# AVVIO
# ============================================================
def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
