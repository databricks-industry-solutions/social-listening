"""
Utilities for interacting with the Google Play API.

Documentation:
https://github.com/JoMingyu/google-play-scraper
"""
import requests
import logging
import google_play_scraper as GPS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GooglePlayHelper:
    def __init__(self):
        pass

    def get_app_info(self, appId: str) -> dict:
        """
        Get info for a given Google Play app ID.
        (You can find the app ID via the game's Google Play store page URL)
        """
        app_info = GPS.app(
            appId,
            lang="en",  # defaults to 'en'
            country="us",  # defaults to 'us'
        )
        return app_info

    def search_for_google_play_app(self, search_term: str) -> list:
        """
        Searches the Google Play store and returns a list of matches
        in the form: [{"appId": "...", "title": "..."}, ...]
        (see repo above for more details)

        Note that "search_term" does not have to be the app name, it can be any string
        (e.g. "best pikachu game")
        """
        search_results = GPS.search(
            search_term,
            lang="en",  # defaults to 'en'
            country="us",  # defaults to 'us'
            n_hits=30  # defaults to 30 (Google's maximum)
        )
        return search_results

    @staticmethod
    def get_store_page_url(appId: str) -> str:
        return f"https://play.google.com/store/apps/details?id={appId}"