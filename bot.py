import pandas as pd
import re
import difflib
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ---- Прайс-лист ----
products = {}

def load_products():
    global products

    # читаем файл, поддерживаем запятую, табуляцию и т.п.
    df = pd.read_csv("products.csv", encoding="utf-8-sig", sep=None, engine="python")

    # приводим названия колонок в нормальный вид
    df.columns = [re.sub(r"\s+", "", col.strip().lower()) for col in df.columns]

    # проверка, что есть нужные колонки
    if "name" not in df.columns or "weight_kg" not in df.columns:
        raise ValueError(f"В CSV должны быть колонки 'name' и 'weight_kg', а сейчас: {df.columns.tolist()}")

    # приводим веса к float (заменяем запятую на точку, пустые = 0)
    df["weight_kg"] = (
        df["weight_kg"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .replace("nan", "0")
        .astype(float)
        .fillna(0)
    )

    # создаём словарь {товар: вес}
    products = {
        str(row["name"]).strip().lower(): row["weight_kg"]
        for _, row in df.iterrows()
    }

    print("Загружено товаров:", len(products))

# ---- Команды ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я считаю вес заказа.\n"
        "Отправь товары в формате (каждый с новой строки):\n"
        "Fix PRO 5\nRed 3"
    )

# ---- Поиск похожего названия ----
def find_best_match(query: str):
    names = list(products.keys())
    match = difflib.get_close_matches(query, names, n=1, cutoff=0.5)  # cutoff = точность (0.5–1.0)
    return match[0] if match else None

# ---- Обработка сообщений ----
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower().splitlines()
    total_weight = 0
    details = []

    for line in text:
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        name = parts[0].strip().lower()
        qty_str = parts[1].strip()

        # сначала ищем точное совпадение
        found_key = products.get(name)

        # если нет — пробуем подобрать ближайшее название
        if not found_key:
            best_match = find_best_match(name)
            if best_match:
                name = best_match
            else:
                continue

        try:
            qty = float(qty_str.replace(",", "."))
        except ValueError:
            continue

        weight = products[name] * qty
        total_weight += weight
        details.append(f"{name} × {qty} = {weight:.2f} кг")

    if details:
        reply = "\n".join(details) + f"\n\nИТОГО: {total_weight:.2f} кг"
    else:
        reply = "Не понял формат. Пример:\nRed 5"

    await update.message.reply_text(reply)

# ---- Запуск бота ----
def main():
    load_products()
    token = "8168700754:AAGPN6TJXmBQHbouZ1P92i9uITc-uLVbMns"  # твой ключ
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()

