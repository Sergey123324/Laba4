import requests
from config import Config


class GoogleBooksAPI:
    def __init__(self):
        self.api_key = Config.GOOGLE_BOOKS_API_KEY
        self.base_url = Config.GOOGLE_BOOKS_URL

    def search_books(self, query: str, max_results: int = 5) -> dict:
        """Поиск книг"""
        try:
            params = {'q': query, 'maxResults': max_results}
            if self.api_key:
                params['key'] = self.api_key

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API error: {e}")
            return {'error': str(e), 'items': []}

    def get_book_details(self, book_id: str) -> dict:
        """Получение информации о книге"""
        try:
            url = f"{self.base_url}/{book_id}"
            params = {'key': self.api_key} if self.api_key else {}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API error: {e}")
            return {'error': str(e)}