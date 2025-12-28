import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import Config
from database import Database
from api_client import GoogleBooksAPI

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(name)


class BookBot:
    def init(self):
        self.config = Config()
        self.db = Database()
        self.api = GoogleBooksAPI()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.add_or_update_user(user.id, user.username, user.first_name, user.last_name or '')

        welcome_text = f""" Привет, {user.first_name}!

Я помогу найти информацию о книгах.

*Поиск книг* - просто отправьте название, автора или тему
*Подробная информация* - нажмите на кнопку при просмотре книги

Примеры запросов:
• Гарри Поттер
• Стивен Кинг
• Программирование Python
• 9785171202442 (ISBN)

Попробуйте!"""

        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """*Справка по боту*

*Доступные команды:*
/start - Начать работу
/search - Поиск книг
/help - Эта справка

*Как использовать:*
1. Отправьте название книги, автора или тему
2. Выберите книгу из результатов
3. Нажмите "Подробнее" для детальной информации

*Примеры запросов:*
• "Война и мир"
• Автор: Толстой
• Фантастика
• 9785171202442

*API:* Google Books"""

        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Введите название книги, автора или тему:")

    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.message.text

        if not query or len(query) < 2:
            await update.message.reply_text("Введите запрос длиной не менее 2 символов")
            return

        await update.message.reply_chat_action(action="typing")

        results = self.api.search_books(query, max_results=5)

        if 'error' in results:
            await update.message.reply_text("Ошибка при поиске. Попробуйте позже.")
            return

        items = results.get('items', [])
        total_items = results.get('totalItems', 0)

        if not items:
            await update.message.reply_text(f"По запросу '{query}' ничего не найдено.")
            return

        message = f"*Найдено книг:* {total_items}\n*Запрос:* `{query}`\n\n"

        for i, item in enumerate(items, 1):
            volume_info = item.get('volumeInfo', {})
            title = volume_info.get('title', 'Без названия')
            authors = ', '.join(volume_info.get('authors', ['Неизвестен']))
            year = volume_info.get('publishedDate', '')[:4]

            message += f"{i}. *{title}*\n"
            message += f"   {authors}\n"
            if year:
                message += f"   {year}\n"
            message += f"   [Подробнее](buttonurl://t.me/{context.bot.username}?start=book_{item['id']})\n\n"

        keyboard = [[InlineKeyboardButton("Новый поиск", callback_data="new_search")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
