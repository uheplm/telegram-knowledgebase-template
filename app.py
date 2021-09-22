from telebot import types, apihelper
from types import SimpleNamespace
from modules import jsondb, polling
import requests
import telebot
import base64
import json
import re

# Автор: Роман Сергеев
# Электронная почта: grzd.me@gmail.com
# Telegram: @uheplm
# ------------------------------------
# Если вы - программист, который занимается
# поддержкой этого бота, направляйте любые
# вопросы на электронную почту или телеграм.
# ------------------------------------
# Загрузка конфиурации бота
config_yaml = jsondb.JSONDB('config/bot_config.yaml')
config = SimpleNamespace(**config_yaml.get())

# Создание экземпляра бота
bot = telebot.TeleBot(config.api_token)

# Загрузка файла сценария
scenario = jsondb.JSONDB('config/script.yaml')

# Загрузка строк локализации
string_yaml = jsondb.JSONDB('config/strings.yaml')
strings = SimpleNamespace(**string_yaml.get())

# Инициализация обьекта прослушивания сервера
polling = polling.Polling(bot)

# Переменные для хранения состояний пользователя
# user_states - хранение текущего положения в меню
# user_registration - хранение данных о регистрации
user_states = {}
user_registration = {}


# Обработчик ошибок, связанных с незапланированной
# остановкой бота при переходе по меню
def on_restart_error(bot_obj):
    def decorator(fn):
        def wrapper(call):
            try:
                fn(call)
            except KeyError:
                bot_obj.delete_message(call.from_user.id, call.message.message_id)
                bot_obj.send_message(call.from_user.id, strings.ErrorMessage)
        return wrapper
    return decorator


# Обработчик события: Новый пльзователь в чате
@bot.message_handler(content_types=['new_chat_members'])
def new_member(msg):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            text=strings.OpenButton,
            url="https://t.me/" + config.bot_link + "?start"
        )
    )
    bot.reply_to(msg, strings.WelcomeMessage, reply_markup=keyboard)


# Обработчик события: команда help, start
@bot.message_handler(commands=['help', 'start'])
def help_cmd(msg):
    keyboard = types.InlineKeyboardMarkup()
    keys = list(scenario.get().keys())
    user_states[msg.from_user.id] = []
    for i in scenario.get():
        keyboard.row(
            types.InlineKeyboardButton(
                text=str(i),
                callback_data="open_" + str(keys.index(i))
            )
        )
    bot.send_message(
        msg.from_user.id,
        strings.StartHeader,
        reply_markup=keyboard,
        parse_mode='HTML'
    )


# Обработчик события: нажатие кнопки
@bot.callback_query_handler(func=lambda call: call)
@on_restart_error(bot)
def callback_inline(call):
    bot.answer_callback_query(call.id, strings.ToastLoading, show_alert=False)

    # Обработчик кнопок перхода по меню
    if call.data.startswith('open_'):
        load = call.data.replace("open_", '')
        open(call, load)

    # Обработчик кнопки назад
    if call.data.startswith('back_'):
        load = call.data.replace("back_", '')
        keyboard = types.InlineKeyboardMarkup()
        user_states[call.from_user.id] = user_states[call.from_user.id][:-1]
        if user_states[call.from_user.id]:
            open(call)
        else:
            keys = list(scenario.get().keys())
            user_states[call.from_user.id] = []
            keyboard = types.InlineKeyboardMarkup()
            for i in scenario.get():
                keyboard.row(
                    types.InlineKeyboardButton(
                        text=str(i),
                        callback_data="open_" + str(keys.index(i))
                    )
                )
                bot.edit_message_text(
                    chat_id=call.from_user.id,
                    message_id=call.message.message_id,
                    text=strings.StartHeader,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )

    # Обработчик кнопки регистрации
    if call.data.startswith('reg_'):
        keyboard = types.InlineKeyboardMarkup()
        user = {
            "msg": call.message.message_id,
            "state": 0,
            "name": '',
            "email": '',
            "phone": ''
        }
        keyboard.row(
            types.InlineKeyboardButton(
                text='Cancel',
                callback_data="cancel_"
            )
        )
        user_registration[call.from_user.id] = user
        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=strings.RegPhone,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    # Обработчик кнопки завершения регистрации
    if call.data.startswith('compreg_'):
        if call.from_user.id in user_registration:
            userdata = {
                'phone': user_registration[call.from_user.id]['phone'],
                'email': user_registration[call.from_user.id]['email'],
                'first_name': (
                    user_registration[call.from_user.id]['name']
                    .split(' ')[0]
                ),
                'last_name': (
                    user_registration[call.from_user.id]['name']
                    .split(' ')[1]
                )
            }
            complete = register(userdata, call)
            keyboard = types.InlineKeyboardMarkup()
            if complete['success']:
                keyboard.row(
                    types.InlineKeyboardButton(
                        text=strings.RegOpen,
                        url=strings.RegLink
                    ),
                    types.InlineKeyboardButton(
                        text='to menu',
                        callback_data='open_'
                    )
                )
            else:
                keyboard.row(
                    types.InlineKeyboardButton(
                        text='to menu',
                        callback_data='open_'
                    )
                )
            bot.edit_message_text(
                chat_id=call.from_user.id,
                message_id=user_registration[call.from_user.id]['msg'],
                text=(
                    strings.RegComplete if
                    complete['success'] else
                    strings.RegFailed.format(complete['error'])),
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            raise KeyError

    # Обработчик кнопки отмены регистрации
    if call.data.startswith('cancel_'):
        if call.from_user.id in user_registration:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton(
                    text='to menu',
                    callback_data='open_'
                )
            )
            bot.edit_message_text(
                chat_id=call.from_user.id,
                message_id=user_registration[call.from_user.id]['msg'],
                text=strings.RegCanceled,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            del user_registration[call.from_user.id]


# Обработчик текстовых сообщений боту
# Используется во время регистрации
@bot.message_handler(content_types=['text'])
@on_restart_error(bot)
def reg_handler(msg):
    # Паттерны регулярных выражений
    phone_pattern = re.compile(config.regex_phone)
    email_pattern = re.compile(config.regex_email)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            text='Cancel',
            callback_data="cancel_"
        )
    )
    if msg.from_user.id in user_registration:
        if user_registration[msg.from_user.id]['state'] == 0:
            if re.match(phone_pattern, msg.text):
                user_registration[msg.from_user.id]['phone'] = msg.text
                bot.edit_message_text(
                    chat_id=msg.from_user.id,
                    message_id=user_registration[msg.from_user.id]['msg'],
                    text=strings.RegEmail,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                user_registration[msg.from_user.id]['state'] += 1
            else:
                bot.edit_message_text(
                    chat_id=msg.from_user.id,
                    message_id=user_registration[msg.from_user.id]['msg'],
                    text=strings.ErrorReg,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        elif user_registration[msg.from_user.id]['state'] == 1:
            if re.match(email_pattern, msg.text):
                user_registration[msg.from_user.id]['email'] = msg.text
                bot.edit_message_text(
                    chat_id=msg.from_user.id,
                    message_id=user_registration[msg.from_user.id]['msg'],
                    text=strings.RegName,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                user_registration[msg.from_user.id]['state'] += 1
            else:
                bot.edit_message_text(
                    chat_id=msg.from_user.id,
                    message_id=user_registration[msg.from_user.id]['msg'],
                    text=strings.ErrorReg,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        elif user_registration[msg.from_user.id]['state'] == 2:
            if len(msg.text.split(' ')) == 2:
                user_registration[msg.from_user.id]['name'] = msg.text
                accept = types.InlineKeyboardMarkup()
                accept.row(
                    types.InlineKeyboardButton(
                        text='Yes',
                        callback_data="compreg_"
                    ),
                    types.InlineKeyboardButton(
                        text='No',
                        callback_data="cancel_"
                    )
                )
                bot.delete_message(
                    msg.from_user.id,
                    user_registration[msg.from_user.id]['msg'],
                )
                bot.send_message(
                    chat_id=msg.from_user.id,
                    text=strings.RegEnd.format(
                        name=user_registration[msg.from_user.id]['name'],
                        email=user_registration[msg.from_user.id]['email'],
                        phone=user_registration[msg.from_user.id]['phone']
                    ),
                    reply_markup=accept,
                    parse_mode='HTML'
                )
                user_registration[msg.from_user.id]['state'] = 0
            else:
                bot.edit_message_text(
                    chat_id=msg.from_user.id,
                    message_id=user_registration[msg.from_user.id]['msg'],
                    text=strings.ErrorReg,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )


# Функция перехода по меню
def open(call, load=False):
    keyboard = types.InlineKeyboardMarkup()
    if load:
        user_states[call.from_user.id].append(int(load))

    keys_request = []
    if user_states[call.from_user.id]:
        keys = list(scenario.get().keys())
        for i in user_states[call.from_user.id]:
            keys_request.append(keys[i])
            keys = (
                list(scenario.get(keys_request).keys()) if
                isinstance(scenario.get(keys_request), dict)
                else []
            )

    if isinstance(scenario.get(keys_request), str):
        if '$perform_reg' in scenario.get(keys_request):
            keyboard.row(
                types.InlineKeyboardButton(
                    text=strings.PerformRegButton,
                    callback_data='reg_'
                )
            )
        keyboard.row(
            types.InlineKeyboardButton(
                text='Back',
                callback_data='back_'
            )
        )
        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=scenario.get(keys_request).replace('$perform_reg', ''),
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    if isinstance(scenario.get(keys_request), dict):
        keys_top = list(scenario.get(keys_request).keys())
        for i in scenario.get(keys_request):
            keyboard.row(
                types.InlineKeyboardButton(
                    text=str(i),
                    callback_data="open_" + str(keys_top.index(i))
                )
            )
        keyboard.row(
            types.InlineKeyboardButton(
                text='Back',
                callback_data='back_'
            )
        )
        bot.edit_message_text(
            chat_id=call.from_user.id,
            message_id=call.message.message_id,
            text=strings.PageHeader,
            reply_markup=keyboard,
            parse_mode='HTML'
        )


# Построение запроса на сайт GetCourse
def register(userdata, call):
    bot.send_message(call.from_user.id, userdata)
    return {"success": True}


# Запуск прослушивания
polling.start()
