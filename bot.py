import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import Config
from database import Database
from api_client import GoogleBooksAPI

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class BookBot:
    def __init__(self):
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

    async def show_book_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        book_id = None
        if update.message:
            text = update.message.text
            if text.startswith('/book_'):
                book_id = text.replace('/book_', '')
        elif update.callback_query:
            query = update.callback_query
            await query.answer()
            if query.data.startswith('details_'):
                book_id = query.data.replace('details_', '')

        if not book_id:
            return

        await update.effective_message.reply_chat_action(action="typing")

        book_data = self.api.get_book_details(book_id)

        if 'error' in book_data:
            error_msg = "Не удалось загрузить информацию о книге."
            await update.effective_message.reply_text(error_msg)
            return

        volume_info = book_data.get('volumeInfo', {})

        title = volume_info.get('title', 'Без названия')
        authors = ', '.join(volume_info.get('authors', ['Неизвестен']))
        publisher = volume_info.get('publisher', 'Неизвестно')
        published_date = volume_info.get('publishedDate', 'Неизвестно')
        description = volume_info.get('description', 'Нет описания')
        if len(description) > 1000:
            description = description[:1000] + '...'

        image_links = volume_info.get('imageLinks', {})
        thumbnail = image_links.get('thumbnail', '')

        rating = volume_info.get('averageRating', 0)
        ratings_count = volume_info.get('ratingsCount', 0)

        page_count = volume_info.get('pageCount', 0)

        # ISBN
        isbn = ''
        for identifier in volume_info.get('industryIdentifiers', []):
            if identifier.get('type') in ['ISBN_10', 'ISBN_13']:
                isbn = identifier.get('identifier', '')
                break

        message_text = f""" *{title}*

    *Автор(ы):* {authors}
    *Издательство:* {publisher}
    *Дата публикации:* {published_date}
    *Страниц:* {page_count if page_count else 'Нет данных'}
    *Рейтинг:*  {rating if rating else 'Нет'} ({ratings_count if ratings_count else 0} оценок)
    *ISBN:* `{isbn if isbn else 'Нет'}`

    *Описание:*
    {description}

    [Ссылка на Google Books]({volume_info.get('infoLink', '')})"""

        keyboard = [
            [InlineKeyboardButton(" Открыть в Google Books", url=volume_info.get('infoLink', ''))],
            [InlineKeyboardButton(" Новый поиск", callback_data="new_search")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if thumbnail:
            try:
                await update.effective_message.reply_photo(
                    photo=thumbnail,
                    caption=message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                return
            except Exception as e:
                logger.error(f"Error sending photo: {e}")

        await update.effective_message.reply_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "new_search":
            await query.edit_message_text("Введите название книги, автора или тему:")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text

        if text.startswith('/'):
            return

        await self.handle_search(update, context)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")

        try:
            if update and update.message:
                await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте еще раз.")
        except:
            pass

    def run(self):
        application = Application.builder().token(self.config.BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search", self.search_command))

        application.add_handler(CallbackQueryHandler(self.handle_callback))

        application.add_handler(MessageHandler(filters.Regex(r'^/book_\w+'), self.show_book_details))

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        application.add_error_handler(self.error_handler)

        print("Бот запущен...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':


    if not Config.GOOGLE_BOOKS_API_KEY:
        print("GOOGLE_BOOKS_API_KEY не установлен. Работа без ключа ограничена.")

    bot = BookBot()
    bot.run()