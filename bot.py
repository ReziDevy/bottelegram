import os
import re
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
CANAL = int(os.environ.get("CANAL"))
AMAZON_ACCESS_KEY = os.environ.get("AMAZON_ACCESS_KEY")
AMAZON_SECRET_KEY = os.environ.get("AMAZON_SECRET_KEY")
AMAZON_ASSOCIATE_TAG = os.environ.get("AMAZON_ASSOCIATE_TAG")
ML_APP_ID = os.environ.get("ML_APP_ID")
ML_SECRET_KEY = os.environ.get("ML_SECRET_KEY")

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def resolver_url(url):
    try:
        r = requests.get(url, allow_redirects=True, timeout=10, headers=HEADERS)
        return r.url
    except Exception as e:
        print(f"[ERRO] resolver_url: {e}")
        return url

def extrair_asin(url):
    for pattern in [r'/dp/([A-Z0-9]{10})', r'/gp/product/([A-Z0-9]{10})', r'asin=([A-Z0-9]{10})']:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extrair_item_ml(url):
    match = re.search(r'(MLB\d+)', url.upper())
    return match.group(1) if match else None

def get_amazon_token():
    try:
        r = requests.post('https://api.amazon.com/auth/o2/token', data={
            'grant_type': 'client_credentials',
            'client_id': AMAZON_ACCESS_KEY,
            'client_secret': AMAZON_SECRET_KEY,
            'scope': 'advertising::test:traffic:external'
        }, timeout=10)
        if r.status_code == 200:
            return r.json().get('access_token')
        print(f"[ERRO] Token Amazon: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[ERRO] get_amazon_token: {e}")
    return None

def buscar_amazon(link_original, asin):
    try:
        token = get_amazon_token()
        if not token:
            return None
        r = requests.get(
            'https://affiliate-program.amazon.com/api/v1/products',
            params={'asin': asin, 'associateId': AMAZON_ASSOCIATE_TAG},
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        print(f"[LOG] Amazon API: {r.status_code} {r.text[:200]}")
        if r.status_code == 200:
            data = r.json()
            produto = data.get('title') or data.get('name', 'Produto Amazon')
            preco = data.get('price', {}).get('displayAmount', 'Confira no link')
            foto = data.get('mainImage', {}).get('url')
            return {'produto': produto, 'preco': preco, 'foto': foto, 'link': link_original}
    except Exception as e:
        print(f"[ERRO] buscar_amazon: {e}")
    return None

def buscar_ml(link_original, item_id):
    try:
        r = requests.get(f'https://api.mercadolibre.com/items/{item_id}', timeout=10)
        print(f"[LOG] ML API: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            produto = data.get('title', 'Produto ML')
            preco = f"R${data.get('price', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            foto = None
            if data.get('pictures'):
                foto = data['pictures'][0].get('url')
            return {'produto': produto, 'preco': preco, 'foto': foto, 'link': link_original}
    except Exception as e:
        print(f"[ERRO] buscar_ml: {e}")
    return None

def montar_legenda(produto, preco, link):
    return (
        f"🔥 {produto}\n\n"
        f"🛒 Produto disponível agora\n"
        f"⚡ Confira detalhes no link abaixo\n\n"
        f"💰 {preco}\n"
        f"🔗 {link}\n\n"
        f"🚀 Aproveite no Z3 Ofertas & Tech!"
    )

async def processar_link(update: Update, context):
    link = (update.message.text or "").strip()
    print(f"[LOG] Link recebido: {link}")

    await update.message.reply_text("⏳ Buscando produto...")

    # Resolve o link curto
    url_final = resolver_url(link)
    print(f"[LOG] URL final: {url_final}")

    dados = None

    # Amazon
    if 'amazon' in url_final.lower() or 'amzn' in link.lower():
        asin = extrair_asin(url_final)
        print(f"[LOG] ASIN: {asin}")
        if asin:
            dados = buscar_amazon(link, asin)

    # Mercado Livre
    elif 'mercadolivre' in url_final.lower() or 'mercadolibre' in url_final.lower() or 'meli.la' in link.lower():
        item_id = extrair_item_ml(url_final)
        print(f"[LOG] Item ML: {item_id}")
        if item_id:
            dados = buscar_ml(link, item_id)

    if not dados:
        await update.message.reply_text("❌ Não consegui buscar o produto. Tente no formato manual:\nNome\nPreço\nLink")
        return

    legenda = montar_legenda(dados['produto'], dados['preco'], dados['link'])

    try:
        if dados.get('foto'):
            await context.bot.send_photo(
                chat_id=CANAL,
                photo=dados['foto'],
                caption=legenda
            )
        else:
            await context.bot.send_message(
                chat_id=CANAL,
                text=legenda
            )
        await update.message.reply_text(f"✅ Postado!\n{dados['produto']}\n{dados['preco']}")
    except Exception as e:
        print(f"[ERRO] envio: {e}")
        await update.message.reply_text(f"❌ Erro ao postar: {e}")

async def postar_com_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[LOG] Foto recebida!")
    try:
        linhas = (update.message.caption or "").strip().split("\n")
        if len(linhas) < 3:
            await update.message.reply_text("⚠️ Legenda incompleta!\nNome\nPreço\nLink")
            return
        link = linhas[2].strip()
        legenda = montar_legenda(linhas[0].strip(), linhas[1].strip(), link)
        foto = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=CANAL, photo=foto, caption=legenda)
        await update.message.reply_text(f"✅ Foto postada!")
    except Exception as e:
        print(f"[ERRO] {e}")
        await update.message.reply_text(f"❌ Erro: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.PHOTO, postar_com_foto))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_link))
print("🤖 Bot rodando...")
if __name__ == "__main__":
    app.run_polling()