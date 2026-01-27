"""
Utilities for interacting with the Steam API.

Documentation:
https://partner.steamgames.com/doc/webapi/ISteamApps
https://partner.steamgames.com/doc/store/getreviews
"""
import requests
import logging
from itertools import islice
from rapidfuzz import process, fuzz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SteamHelper:

    def __init__(self, api_key: str=None):
        self.api_key = api_key # Not necessary for all API functions
        self.app_list = self.get_all_steam_apps()
        if self.app_list is None:
            raise Exception("SteamHelper: Failed to get all Steam apps; see logs for more details.")
        self.app_list_lower_names = self.get_app_lower_names_from_app_list(self.app_list)
        self.app_list_ids = self.get_app_ids_from_app_list(self.app_list)
        logger.info(f"SteamHelper: Loaded {len(self.app_list)} Steam apps.")

    def get_steam_review_info(self, app_id) -> dict:
        """
        Get review info for a given Steam app ID.
        You can find the app ID via the game's Steam store page URL,
        or by using the search functions in this file.

        Note that to get all reviews, you will need to apply pagination
        via the "cursor" response parameter.
        """
        url = 'https://store.steampowered.com/appreviews/'
        params = {
            'json' : 1,
            'filter' : 'all',
            'language' : 'all',
            # 'day_range': day_range,
            'review_type' : 'all',
            'purchase_type' : 'all'
        }
        response = requests.get(
            url=url+app_id,
            params=params,
            headers={'User-Agent': 'Mozilla/5.0'})
        response.encoding='utf-8-sig'
        raw_dict = response.json()

        review_info = {
            'total_reviews': raw_dict['query_summary']['total_reviews'],
            'total_positive_reviews': raw_dict['query_summary']['total_positive'],
            'total_negative_reviews': raw_dict['query_summary']['total_negative'],
            'review_score': raw_dict['query_summary']['review_score'],
            'review_score_desc': raw_dict['query_summary']['review_score_desc']
        }
        return review_info

    def get_app_info(self, app_id: str) -> dict:
        """Return high-level info about a given Steam app."""
        details_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        app_data = requests.get(details_url).json()
        logger.info(f"SteamHelper: Raw app info: {app_data}")

        if app_data[app_id]["success"] == False:
            return None

        app_data_dict = app_data[app_id]["data"]
        review_info = self.get_steam_review_info(app_id)

        info_dict = {
            "app_type": app_data_dict["type"],
            "release_date": app_data_dict["release_date"]["date"],
            "coming_soon": app_data_dict["release_date"]["coming_soon"],
            "num_reviews": review_info['total_reviews'],
            "review_score": review_info['review_score'],
            "review_score_desc": review_info['review_score_desc'],
            "total_positive_reviews": review_info['total_positive_reviews'],
            "total_negative_reviews": review_info['total_negative_reviews'],
            "header_image_url": app_data_dict["header_image"]
        }
        logger.info(f"SteamHelper: App info: {info_dict}")
        return info_dict
        
    def get_all_steam_apps(self) -> list:
        """
        Returns a list of all public Steam apps, with each element
        in the form: {"appid": "...", "name": "..."}
        """
        if self.api_key:
            # NOTE: This endpoint appears to not return DLC apps. It may also be missing some non-DLC games.

            max_results_per_page = 50_000
            last_app_id = 0 # For pagination; providing this means the first app in the next "page" will be the app after this one.
            app_list = []
            num_results = max_results_per_page

            while num_results >= max_results_per_page:
                endpoint = f"https://api.steampowered.com/IStoreService/GetAppList/v1/?key={self.api_key}" \
                           f"&max_results={max_results_per_page}&last_appid={last_app_id}"
                response = requests.get(url=endpoint)
                if response.status_code == 200:
                    new_apps = response.json()["response"]["apps"] # Note "response" instead of "applist" with the v2 API
                    app_list.extend(new_apps)
                    num_results = len(new_apps)
                    last_app_id = new_apps[-1]['appid']
                else:
                    logger.error(f"SteamHelper: GetAppList request failed with status code {response.status_code}: {response.text}")
                    break

            logger.info(f"SteamHelper: Total apps retrieved: {len(app_list)}")
            return app_list
        else:
            # Attempt to use the old endpoint that did not require an API key.
            # Note: If this endpoint is still not back by Jan 2026, remove this section and assume
            # an API key is always required.
            response = requests.get(url="https://api.steampowered.com/ISteamApps/GetAppList/v2/")
            if response.status_code != 200:
                logger.error(f"SteamHelper: Failed to get all Steam apps; Steam API response status code: {response.status_code}")
                return None
            return response.json()["applist"]["apps"]

    def search_for_steam_game(self, game_name: str, app_list: list[dict]=None, max_matches_limit: int=None) -> list[dict]:    
        """
        Searches for Steam games (apps) in the given app_list, and returns a list of matches
        in the form: [{"appid": "...", "name": "..."}, ...]

        If game_name consists of all numbers, the search will be done on app IDs instead.
        """
        app_lower_names = None
        if app_list is None:
            app_list = self.app_list
            app_lower_names = self.app_list_lower_names
        else:
            app_lower_names = self.get_app_lower_names_from_app_list(app_list)

        # Search for the game name (case-insensitive)
        matches = []
        if game_name.isdigit():
            # Search by app ID
            if max_matches_limit is None:
                matches = [app for app in app_list if str(app['appid']).startswith(game_name)]
            else:
                matches = list(islice(
                (app for app in app_list if str(app['appid']).startswith(game_name)),
                max_matches_limit
            ))
        else:
            # Search by game name
            fuzzy_score_cutoff = 86 # 0 to 100, 100 is a perfect match
            matches_with_scores = process.extract(
                game_name.lower(), app_lower_names, 
                limit=max_matches_limit, score_cutoff=fuzzy_score_cutoff)
            matches_indices = [match[2] for match in matches_with_scores]
            logger.info(f"SteamHelper: Matches with fuzzy search scores: {matches_with_scores}")
            matches = [app_list[i] for i in matches_indices]

            ## Previous non-fuzzy search method:
            # if max_matches_limit is None:
            #     matches = [app for app in app_list if game_name.lower() in app['name'].lower()]
            # else:
            #     matches = list(islice(
            #     (app for app in app_list if game_name.lower() in app['name'].lower()),
            #     max_matches_limit
            # ))

        # Print matches (name and appid)
        if len(matches) > 0:
            logger.info(f"SteamHelper: Found {len(matches)}{'+' if len(matches) == max_matches_limit else ''} "
                        f"match{'es' if len(matches) != 1 else ''} for search: {game_name}")
        else:
            logger.info(f"SteamHelper: No matches found for search: {game_name}")
        return matches
    
    def get_app_lower_names_from_app_list(self, app_list: list[dict]) -> list[str]:
        return [app['name'].lower() for app in app_list]
    
    def get_app_ids_from_app_list(self, app_list: list[dict]) -> list[str]:
        return [app['appid'] for app in app_list]
    
    @staticmethod
    def get_app_store_page_url(app_id: str) -> str:
        return f"https://store.steampowered.com/app/{app_id}"