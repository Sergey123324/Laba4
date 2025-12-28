import os

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')
    GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"