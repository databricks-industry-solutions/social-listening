from ingestion_utils.data_ingestor import DataIngestor
import requests
from datetime import date
import time
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as PSF
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType, LongType, MapType, TimestampType

class SteamIngestor(DataIngestor):
    def __init__(self, spark: SparkSession):
        super().__init__(spark)
        self._set_content_type()
        self.full_steam_schema = StructType([
            StructField("author", MapType(StringType(), StringType()), True),
            StructField("comment_count", LongType(), True),
            StructField("language", StringType(), True),
            StructField("received_for_free", BooleanType(), True),
            StructField("recommendationid", StringType(), True),
            StructField("review", StringType(), True),
            StructField("steam_purchase", BooleanType(), True),
            StructField("timestamp_created", LongType(), True),
            StructField("timestamp_updated", LongType(), True),
            StructField("voted_up", BooleanType(), True),
            StructField("votes_funny", LongType(), True),
            StructField("votes_up", LongType(), True),
            StructField("weighted_vote_score", StringType(), True),
            StructField("written_during_early_access", BooleanType(), True),
            StructField("primarily_steam_deck", BooleanType(), True)
        ])

    def ingest(self, app_id: str, game_name: str, num_reviews: int=10_000, sample: bool=True, over_past_days: float=None) -> DataFrame:
        """
        Get reviews via Steam API. App ID can found from the corresponding Steam store page URL.
        Set num_reviews to zero or None to get all available reviews.
        Set over_past_days to get reviews from the last X days (supercedes num_reviews), UTC time.
            - e.g. over_past_days=0.5 will get reviews from the last 12 hours, calculated by second.
        """
        reviews = self._get_n_reviews(app_id, num_reviews, over_past_days)
    
        if len(reviews) == 0:
            print("Warning: No reviews found.")
            return None
        
        # Sample reviews (to reduce data/compute for speed/demo purposes)
        if sample:
            reviews = self._sample_content(reviews)

        reviews_df = self._spark_session.createDataFrame(data=reviews, schema=self.full_steam_schema)

        # Add a new columns
        reviews_df = reviews_df.withColumn("game_name", PSF.lit(game_name).cast(StringType()))
        reviews_df = reviews_df.withColumn("content_type", PSF.lit(self.content_type).cast(StringType()))
        reviews_df = reviews_df.withColumn("steamid", PSF.col("author").getItem("steamid").cast(StringType()))
        reviews_df = reviews_df.withColumn("timestamp_created_formatted", PSF.from_unixtime("timestamp_created").cast(TimestampType()))

        # Add unified metadata column
        metadata_cols = [
            "author", "comment_count", "language", "received_for_free", "steam_purchase", "timestamp_created", "timestamp_updated",
            "voted_up", "votes_funny", "votes_up", "weighted_vote_score", "written_during_early_access", "primarily_steam_deck"
        ]
        reviews_df = reviews_df.withColumn(
            "content_metadata",
            PSF.to_json(PSF.struct(metadata_cols))
        )

        output_df = reviews_df.select(
            PSF.col("recommendationid").alias("content_id"),
            PSF.col("content_type"),
            PSF.col("game_name"),
            PSF.col("review").alias("content_text"),
            PSF.col("timestamp_created_formatted").alias("timestamp"),
            PSF.col("steamid").alias("author_id"),
            PSF.col("content_metadata")
        )
        return output_df

    def _get_n_reviews(self, app_id: str, num_reviews: int=10_000, over_past_days: float=None) -> list:
        """
        Retrieve the specified number of reviews from Steam.
        Set num_reviews to zero or None to get all available reviews.
        Currently the reviews are sorted by most recent creation time.

        If over_past_days is provided, only get reviews from the last X days, UTC time.
        Note that the Steam API has a "day_range" parameter, but it only works for filter="all"
        and has a max value of 365.

        For more documentation on the Steam API params, see:
        https://partner.steamgames.com/doc/store/getreviews
        """
        params = {
            'json' : 1,
            'filter' : 'recent', # all, recent, updated (with pagination, "recent"/"updated" should be used (see Steam API docs))
            'language' : 'all',
            'review_type' : 'all',
            'purchase_type' : 'all'
        }

        if num_reviews is None or num_reviews == 0:
            num_reviews = 10_000_000 # Arbitrary large number to get all reviews

        over_past_secs = 0
        time_now_s = int(time.time())
        if over_past_days is not None and over_past_days > 0:
            num_reviews = 10_000_000 # Arbitrary large number to get all reviews
            over_past_secs = over_past_days * 24 * 60 * 60
            
        reviews = []
        cursor = '*' # For pagination
        max_reviews_per_page = 100
        reviews_fetched = 0
        while reviews_fetched < num_reviews:
            params['cursor'] = cursor.encode()
            params['num_per_page'] = min(max_reviews_per_page, num_reviews - reviews_fetched)

            response = self._get_reviews(app_id, params)

            if over_past_days is not None and over_past_days > 0:
                if time_now_s - response['reviews'][-1]['timestamp_created'] > over_past_secs:
                    # Oldest review in this page is outside the over_past_days range,
                    # so check all reviews in this page and break.
                    response_valid = [review for review in response['reviews'] if time_now_s - review['timestamp_created'] <= over_past_secs]
                    reviews += response_valid
                    print("Reached over_past_days limit")
                    break

            reviews += response['reviews']
            reviews_fetched += len(response['reviews'])

            if (len(response['reviews']) == 0): # < params['num_per_page']):
                print("No more reviews available")
                break
            cursor = response['cursor']
        return reviews
    
    def _get_reviews(self, app_id: str, params={'json':1}):
        reviews_url = "https://store.steampowered.com/appreviews/" + app_id
        response = requests.get(
            url=reviews_url,
            params=params,
            headers={'User-Agent': 'Mozilla/5.0'})
        response.encoding='utf-8-sig'
        raw_dict = response.json()
        return raw_dict
    
    def _get_unique_review_ids(self, reviews: list) -> set:
        """Converts the output from _get_n_reviews() into a set of unique review IDs."""
        return set([review['recommendationid'] for review in reviews])

    def _set_content_type(self) -> None:
        self.content_type = "Steam Review"