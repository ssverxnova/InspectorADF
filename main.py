from bot import run_bot, run_flask
import threading

# Запуск Flask в отдельном потоке
threading.Thread(target=run_flask).start()

# Запуск Telegram-бота
run_bot()
