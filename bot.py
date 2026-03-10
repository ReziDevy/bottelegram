import os
import requests
from telegram import Update, LinkPreviewOptions
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
CANAL = int(os.environ.get("CANAL"))

def encurtar_link(url):
    if "amzn.to" in url or "meli.la" in url or "tinyurl.com" in url:
        return url
    try:
        r = requests.get(f"http://tinyurl.com/api-create.php?url={url}", timeout=10)
        return r.text if r.status_code == 200 else url
    except:
        return url

def montar_legenda(produto, preco, link):
    return (f"🔥 {produto}\n🛒 Produto Amazon disponível agora\n"
            f"⚡ Confira detalhes no link abaixo\n\n💰 {preco}\n🔗 {link}\n\n"
            f"🚀 Aproveite no Z3 Ofertas & Tech!")

async def postar_com_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[LOG] Foto recebida!")
    try:
        linhas = (update.message.caption or "").strip().split("\n")
        if len(linhas) < 3:
            await update.message.reply_text("⚠️ Legenda incompleta!\nNome\nPreço\nLink")
            return
        link = encurtar_link(linhas[2].strip())
        await context.bot.send_photo(
            chat_id=CANAL,
            photo=update.message.photo[-1].file_id,
            caption=montar_legenda(linhas[0].strip(), linhas[1].strip(), link)
        )
        await update.message.reply_text(f"✅ Foto postada! Link: {link}")
    except Exception as e:
        print(f"[ERRO] {e}")
        await update.message.reply_text(f"❌ Erro: {e}")

async def postar_sem_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[LOG] Texto recebido!")
    try:
        linhas = (update.message.text or "").strip().split("\n")
        if len(linhas) < 3:
            await update.message.reply_text("⚠️ Formato inválido!\nNome\nPreço\nLink")
            return
        link = encurtar_link(linhas[2].strip())
        await context.bot.send_message(
            chat_id=CANAL,
            text=montar_legenda(linhas[0].strip(), linhas[1].strip(), link),
            link_preview_options=LinkPreviewOptions(is_disabled=False)
        )
        await update.message.reply_text(f"✅ Postado! Link: {link}")
    except Exception as e:
        print(f"[ERRO] {e}")
        await update.message.reply_text(f"❌ Erro: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.PHOTO, postar_com_foto))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, postar_sem_foto))
print("🤖 Bot rodando...")
if __name__ == "__main__":
    app.run_polling()