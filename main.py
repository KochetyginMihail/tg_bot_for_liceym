import os
import telebot
import sqlite3
import aspose.words as aw

TOKEN = '7041510449:AAECwA7tOmc43RcpLbWXl-zlKrpOkZUnI20'
bot = telebot.TeleBot(TOKEN)

# Глобальная переменная для отслеживания текущего состояния развития диалога
current_state = None
current_task_number = None
current_task_theory = None

# Подключение к базе данных
con = sqlite3.connect("sql_bd.db", check_same_thread=False)
cur = con.cursor()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global current_state
    current_state = None  # Сбрасываем состояние при каждом новом запуске бота
    bot.reply_to(message, "Привет! Я - твой помощник для подготовки к экзамену по русскому языку. "
                          "Я предоставлю тебе теорию и прототипы заданий. Чтобы начать, напиши 'Теория' "
                          "для получения теории по выбранному заданию или 'Практика' для выполнения практических заданий.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global current_state
    text = message.text.lower()

    if text == 'теория':
        current_state = 'теория'
        bot.reply_to(message, "Выберите номер задания от 1 до 9, к которому хотите получить теорию.")

    elif text == 'практика':
        current_state = 'практика'
        bot.reply_to(message, "Выберите номер задания от 1 до 9:\n"
                              "1. Прототипы задания 1\n"
                              "2. Прототипы задания 2\n"
                              "...\n"
                              "9. Прототипы задания 9")

    elif current_state == 'теория':
        if text.isdigit() and 1 <= int(text) <= 9:
            global current_task_number, current_task_theory
            current_task_number = int(text)
            current_task_theory = \
                cur.execute("""SELECT content FROM theory WHERE id = ?""", (current_task_number,)).fetchone()[0]
            bot.reply_to(message, "Теория успешно найдена. Выберите формат получаемой теории:",
                         reply_markup=create_theory_format_keyboard())

    elif current_state == 'практика':
        if text.isdigit() and 1 <= int(text) <= 9:
            bot.reply_to(message, f"Здесь будут прототипы задания {text}.")
        else:
            bot.reply_to(message, "Прости, я не понял ваш запрос. Попробуйте ввести номер задания от 1 до 9.")

    else:
        bot.reply_to(message, "Прости, я не понял ваш запрос. Попробуйте еще раз.")


def create_theory_format_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    text_button = telebot.types.InlineKeyboardButton(text="Текстовое сообщение", callback_data="text_message")
    word_button = telebot.types.InlineKeyboardButton(text="Вордовский файл", callback_data="word_file")
    text_file_button = telebot.types.InlineKeyboardButton(text="Текстовый файл", callback_data="text_file")
    keyboard.row(text_button, word_button, text_file_button)
    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data == "text_message":
        bot.send_message(call.message.chat.id, current_task_theory)
    elif call.data == "word_file":
        create_and_send_word_file(call.message.chat.id, current_task_theory, current_task_number)
    elif call.data == "text_file":
        create_and_send_text_file(call.message.chat.id, current_task_theory, current_task_number)


def create_and_send_word_file(chat_id, content, task_number):
    doc = aw.Document()
    builder = aw.DocumentBuilder(doc)
    builder.write(content)
    doc.save(f"Теория к заданию {task_number}.docx")
    with open(f"Теория к заданию {task_number}.docx", 'rb') as file:
        bot.send_document(chat_id, file)
    os.remove(f"Теория к заданию {task_number}.docx")


def create_and_send_text_file(chat_id, content, task_number):
    file_path = f"Теория к заданию {task_number}.txt"
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    with open(file_path, 'rb') as file:
        bot.send_document(chat_id, file)
    os.remove(file_path)  # Удаляем временный файл


bot.polling()
