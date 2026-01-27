"""
Utilities for interacting with the Reddit API.

Documentation:
https://praw.readthedocs.io/en/stable/
"""
import praw
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditHelper:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            check_for_async=False
        )

    def get_subreddit_info(self, subreddit_name: str) -> dict:
        """
        Get info for a given subreddit.
        """
        subreddit = self.reddit.subreddit(subreddit_name)
        info_dict = {
            "display_name": subreddit.display_name,
            "id": subreddit.fullname,
            "subscribers": subreddit.subscribers,
            "url": subreddit.url,
            "created": datetime.fromtimestamp(subreddit.created_utc, timezone.utc).date(),
            "nsfw": subreddit.over18
        }
        # Get icon image url
        icon_img_url = None
        if subreddit.community_icon:
            icon_img_url = subreddit.community_icon
        elif subreddit.icon_img:
            icon_img_url = subreddit.icon_img
        info_dict["icon_image_url"] = icon_img_url
        logger.info(f"RedditHelper: Got subreddit info for {subreddit_name}: {info_dict}, community_icon={subreddit.community_icon}, icon_img={subreddit.icon_img}")
        return info_dict

    def search_subreddits(self, search_term: str, limit: int=100, include_nsfw: bool=False) -> list:
        """
        Search for subreddits. Both subreddit title and description are used for the search.
        Returns a list of subreddit names.
        """
        # Note: it appears that the search will already remove NSFW subreddits.
        # In the results there may be some clearly NSFW subreddits that are marked "False" for NSFW,
        # but these appear to all be because they have not been verified yet by Reddit.
        subreddits = self.reddit.subreddits.search(search_term, limit=limit)
        subreddit_names = [subreddit.display_name for subreddit in subreddits]
        return subreddit_names