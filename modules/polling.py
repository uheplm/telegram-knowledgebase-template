import time
from types import SimpleNamespace
from modules import jsondb

# Загрузка конфиурации бота
config_yaml = jsondb.JSONDB('config/bot_config.yaml')
config = SimpleNamespace(**config_yaml.get())


class Polling(object):
    def __init__(self, bot):
            self._bot = bot

    def start(self):
        try:
            self._bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            self._bot.send_message(config.admin_account, 'Ошибка: ' + str(e))
            self._bot.stop_polling()
            time.sleep(2)
            self.start()

    def stop(self):
        self._bot.stop_polling()
