from dotenv import load_dotenv
import os
import asyncio
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ❗ Убедись, что этот токен задан в Render

YOUR_TELEGRAM_ID = 6118019853  # Замени на свой Telegram ID

# Состояния
VIN, BRAND, MODEL, YEAR, COMMENT, EXTRA = range(6)

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в автоМаркет!\nЧтобы оформить заказ, напиши /start"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Введите VIN (17 символов):")
    return VIN

async def vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin_text = update.message.text.strip()
    if len(vin_text) != 17:
        await update.message.reply_text("Неверный VIN. Повторите (17 символов):")
        return VIN
    context.user_data['vin'] = vin_text
    await update.message.reply_text("Введите марку авто:")
    return BRAND

async def brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    brand = update.message.text.strip()
    if not brand.isalpha():
        await update.message.reply_text("Марка должна содержать только буквы. Повторите:")
        return BRAND
    context.user_data['brand'] = brand
    await update.message.reply_text("Введите модель авто:")
    return MODEL

async def model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    model = update.message.text.strip()
    if not model.isalnum():
        await update.message.reply_text("Модель должна быть без спецсимволов. Повторите:")
        return MODEL
    context.user_data['model'] = model
    await update.message.reply_text("Введите год выпуска (например, 2015):")
    return YEAR

async def year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year_text = update.message.text.strip()
    if not year_text.isdigit() or not (1980 <= int(year_text) <= 2025):
        await update.message.reply_text("Год должен быть числом от 1980 до 2025. Повторите:")
        return YEAR
    context.user_data['year'] = year_text
    await update.message.reply_text("Какие запчасти или что нужно найти?")
    return COMMENT

async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['comment'] = update.message.text.strip()
    await update.message.reply_text("Хочешь что-то ДОБАВИТЬ к заказу? Напиши или нажми /skip")
    return EXTRA

async def extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['extra'] = update.message.text.strip()
    return await finish_order(update, context)

async def skip_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['extra'] = "—"
    return await finish_order(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"user_photo_{update.message.from_user.id}.jpg"
    await file.download_to_drive(file_path)
    context.user_data['photo'] = file_path
    await update.message.reply_text("Фото получено. Оно будет добавлено к заказу.")

async def finish_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data

    msg = (
        f"🧾 Новая заявка:\n"
        f"VIN: {data['vin']}\n"
        f"Марка: {data['brand']}\n"
        f"Модель: {data['model']}\n"
        f"Год: {data['year']}\n"
        f"Комментарий: {data['comment']}\n"
        f"Дополнительно: {data.get('extra', '-')}"
    )

    await context.bot.send_message(chat_id=YOUR_TELEGRAM_ID, text=msg)

    if 'photo' in data:
        with open(data['photo'], 'rb') as f:
            await context.bot.send_photo(chat_id=YOUR_TELEGRAM_ID, photo=InputFile(f))
        os.remove(data['photo'])

    await update.message.reply_text("✅ Заказ оформлен! Чтобы начать новый — нажми /start")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён.")
    return ConversationHandler.END

async def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN не установлен! Убедись, что переменная окружения задана.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Удаляем возможный webhook, чтобы избежать конфликта с polling
    await app.bot.delete_webhook(drop_pending_updates=True)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            VIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, vin)],
            BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, brand)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, year)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment)],
            EXTRA: [
                CommandHandler("skip", skip_extra),
                MessageHandler(filters.TEXT & ~filters.COMMAND, extra),
                MessageHandler(filters.PHOTO, handle_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, welcome))

    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
