import os
import telebot
import sqlite3
import aspose.words as aw
import random

TOKEN = '7041510449:AAECwA7tOmc43RcpLbWXl-zlKrpOkZUnI20'
bot = telebot.TeleBot(TOKEN)

# Глобальные переменные для отслеживания текущего состояния развития диалога
current_task_theory = None
current_state = None
current_task_number = None
current_task_difficulty = None
current_task_prototype = None

# Подключение к базе данных
con = sqlite3.connect("sql_bd.db", check_same_thread=False)
cur = con.cursor()

# Словарь для соответствия названий сложности
difficulty_mapping = {
    "Лёгкие": "лёгкое",
    "Нормальные": "нормальное",
    "Сложные": "сложное",
    "Все сразу": "%"
}


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    global current_state
    current_state = None
    bot.reply_to(message, "Привет! Я - твой помощник для подготовки к экзамену по русскому языку. "
                          "Я предоставлю тебе теорию и прототипы заданий. Чтобы начать, напиши 'Теория' "
                          "для получения теории по выбранному заданию, или 'Прототипы' для выполнения упражнений.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global current_state, current_task_number, current_task_prototype
    text = message.text.lower()

    if text.startswith('теор'):
        current_state = 'теория'
        bot.reply_to(message, "Выберите номер задания от 1 до 9, к которому хотите получить теорию.")

    elif text.startswith('протот'):
        current_state = 'прототипы'
        bot.reply_to(message, "Выберите номер задания от 1 до 9, к которому хотите получить прототипы.")

    elif text.startswith('вариа'):
        current_state = 'варианты'
        bot.reply_to(message, "Выберите сложность варианта.")

    elif current_state == 'теория':
        if text.isdigit() and 1 <= int(text) <= 9:
            global current_task_number, current_task_theory
            current_task_number = int(text)
            current_task_theory = \
                cur.execute("""SELECT content FROM theory WHERE id = ?""", (current_task_number,)).fetchone()[0]
            bot.reply_to(message, "Теория успешно найдена. Выберите формат получаемой теории:",
                         reply_markup=create_theory_format_keyboard())
        else:
            bot.reply_to(message, "Не понял номер задания. Введите цифрой, пожалуйста.")

    elif current_state == 'прототипы':
        if text.isdigit() and 1 <= int(text) <= 9:
            current_task_number = int(text)
            bot.reply_to(message, "Прототипы успешно найдены. Выберите категорию сложности прототипов:",
                         reply_markup=create_prototype_difficulty_keyboard())
        else:
            bot.reply_to(message, "Некорректно введён номер задания для нахождения прототипов.")

    elif current_state == 'ответ_на_прототип':
        if text == 'ещё прототип':
            prototype = get_random_prototype(current_task_difficulty)
            current_task_prototype = prototype  # Выбираем прототип задачи
            bot.send_message(message.chat.id, f"Вы выбрали категорию сложности '{current_task_difficulty}'. "
                                              f"Вот прототип задания:\n\n{current_task_prototype[1]}\n")
        else:
            handle_user_answer(message)

    else:
        bot.reply_to(message, "Прости, я не понял ваш запрос. Попробуйте еще раз.")


def handle_user_answer(message):
    global current_state, current_task_prototype, current_task_difficulty
    user_answer = message.text.strip().lower()
    correct_answer = current_task_prototype[3].strip().lower()
    if user_answer == correct_answer:
        bot.send_message(message.chat.id, "Правильно! Ваш ответ верный.")
        bot.send_message(message.chat.id, f"Решение:\n{current_task_prototype[4]}")
    else:
        bot.send_message(message.chat.id, "Неправильно! Ознакомьтесь с решением и запомните его.")
        bot.send_message(message.chat.id,
                         f"Решение:\n{current_task_prototype[4]}\n\nПравильный ответ:"
                         f" {''.join(correct_answer.strip().split()[1:])}")


def create_theory_format_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    text_button = telebot.types.InlineKeyboardButton(text="Текстовое сообщение", callback_data="text_message")
    word_button = telebot.types.InlineKeyboardButton(text="Вордовский файл", callback_data="word_file")
    text_file_button = telebot.types.InlineKeyboardButton(text="Текстовый файл", callback_data="text_file")
    keyboard.row(text_button, word_button, text_file_button)
    return keyboard


def create_prototype_difficulty_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    for difficulty in difficulty_mapping.keys():
        keyboard.add(telebot.types.InlineKeyboardButton(text=difficulty, callback_data=difficulty))
    return keyboard


def get_random_prototype(difficulty):
    content = cur.execute("""SELECT * FROM practice WHERE id = ? AND exercise_type LIKE ?""",
                          (current_task_number, difficulty_mapping[difficulty])).fetchall()
    return random.choice(content)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global current_task_difficulty, current_task_prototype, current_state
    if call.data == "text_message":
        bot.send_message(call.message.chat.id, current_task_theory)
    elif call.data == "word_file":
        create_and_send_word_file(call.message.chat.id, current_task_theory, current_task_number)
    elif call.data == "text_file":
        create_and_send_text_file(call.message.chat.id, current_task_theory, current_task_number)
    elif call.data in difficulty_mapping.keys():
        current_task_difficulty = call.data
        prototype = get_random_prototype(current_task_difficulty)
        current_task_prototype = prototype  # Выбираем прототип задачи
        bot.send_message(call.message.chat.id, f"Вы выбрали категорию сложности '{current_task_difficulty}'. "
                                               f"Вот прототип задания:\n\n{current_task_prototype[1]}\n")
        current_state = 'ответ_на_прототип'
    else:
        bot.reply_to(call.message, "Прости, я не понял ваш запрос. Попробуйте еще раз.")


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
    os.remove(file_path)


bot.polling()
