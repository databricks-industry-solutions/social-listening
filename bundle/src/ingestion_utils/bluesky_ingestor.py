from ingestion_utils.data_ingestor import DataIngestor
import re
import requests
import time
from datetime import datetime, timedelta, timezone
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as PSF
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    TimestampType,
)

class BlueskyIngestor(DataIngestor):
    def __init__(self, spark: SparkSession, service_url: str="https://api.bsky.app",
                 user_agent: str="games-social-listening-demo"):
        """
        Ingests posts from Bluesky via the app.bsky.feed.searchPosts endpoint.
        No API key is required: the default service_url is Bluesky's AppView, which
        accepts unauthenticated search requests. (The documented public host,
        public.api.bsky.app, currently returns 403 for searchPosts from some
        networks — see bluesky-social/bsky-docs#332.)
        """
        super().__init__(spark)
        self._set_content_type()
        self.service_url = service_url.rstrip("/")
        self._user_agent = user_agent
        self.full_bluesky_schema = StructType(
            [
                StructField("uri", StringType(), True),
                StructField("cid", StringType(), True),
                StructField("text", StringType(), True),
                StructField("author_handle", StringType(), True),
                StructField("author_did", StringType(), True),
                StructField("created_at", TimestampType(), True),
                StructField("indexed_at", TimestampType(), True),
                StructField("clamped_timestamp", TimestampType(), True),
                StructField("like_count", IntegerType(), True),
                StructField("repost_count", IntegerType(), True),
                StructField("reply_count", IntegerType(), True),
                StructField("quote_count", IntegerType(), True),
                StructField("langs", StringType(), True),
                StructField("reply_parent_uri", StringType(), True),
                StructField("reply_root_uri", StringType(), True),
                StructField("matched_term", StringType(), True),
                StructField("url", StringType(), True),
            ]
        )

    def ingest(self, search_terms: str, game_name: str, time_filter: str="week",
               max_posts_per_term: int=1000, sample: bool=True, sort: str="latest",
               lang: str=None) -> DataFrame:
        """
        Get posts via the Bluesky search API.

        search_terms is a semicolon-delimited list of keywords/phrases, e.g.
        'pokemon go; "pokemon sleep"; #PokemonGO'. Each term is searched separately
        (Bluesky's query syntax has no reliable boolean OR) and results are de-duplicated.
        Quoted phrases and other Bluesky query syntax (from:, lang:, hashtags) pass through as-is.

        Matching is case- and diacritic-insensitive ('pokemon' matches 'Pokémon'), so
        don't list case/accent variants as separate terms — redundant variants are
        de-duplicated but each term costs a full paginated search pass. Note that
        Bluesky's search index also covers image alt text, link-card titles, and post
        tags, so a matched post's content_text may not visibly contain the term.

        time_filter options: "all", "hour", "day", "week", "month", "year"
        sort options: "latest", "top"
        Set max_posts_per_term to zero or None to get all available posts per term.
        Posts with no text (e.g. image-only) are skipped.

        The output "timestamp" column is min(createdAt, indexedAt). createdAt is
        client-declared and can be arbitrary (backdated imports, clock skew, future
        dates), while indexedAt is when Bluesky's AppView first saw the post. Taking
        the earlier of the two mirrors Bluesky's own "sortAt" logic: legitimate
        backdated content keeps its historical date, but nothing can claim a future
        timestamp. Raw createdAt/indexedAt are preserved in content_metadata.
        """
        terms = [term.strip() for term in search_terms.split(";") if term.strip()]
        if not terms:
            raise ValueError("search_terms must contain at least one non-empty term")

        since_dt = self._time_filter_to_since(time_filter)
        if max_posts_per_term is None or max_posts_per_term == 0:
            max_posts_per_term = 10_000_000 # Arbitrary large number to get all posts

        # Fetch per term, de-duplicating across terms (a post can match several)
        rows = []
        seen_uris = set()
        for term in terms:
            term_rows = self._get_content(term, since_dt=since_dt, max_posts=max_posts_per_term,
                                          sort=sort, lang=lang)
            if len(term_rows) == 0:
                print(f"Warning: No posts found for term: {term}")
            for row in term_rows:
                if row["uri"] not in seen_uris:
                    seen_uris.add(row["uri"])
                    rows.append(row)

        if len(rows) == 0:
            print("Warning: No posts found.")
            return None

        # Sample posts (to reduce data/compute for speed/demo purposes)
        if sample:
            rows = self._sample_content(rows)

        data = [tuple(row[field.name] for field in self.full_bluesky_schema.fields) for row in rows]
        posts_df = self._spark_session.createDataFrame(data=data, schema=self.full_bluesky_schema)

        # Add new columns for static values
        posts_df = posts_df.withColumn("game_name", PSF.lit(game_name).cast(StringType()))
        posts_df = posts_df.withColumn("content_type", PSF.lit(self.content_type).cast(StringType()))

        # Add unified metadata column
        metadata_cols = [
            "cid", "author_did", "created_at", "indexed_at", "like_count", "repost_count",
            "reply_count", "quote_count", "langs", "reply_parent_uri", "reply_root_uri",
            "matched_term", "url"
        ]
        posts_df = posts_df.withColumn(
            "content_metadata",
            PSF.to_json(PSF.struct(metadata_cols))
        )

        output_df = posts_df.select(
            PSF.col("uri").alias("content_id"),
            PSF.col("content_type"),
            PSF.col("game_name"),
            PSF.col("text").alias("content_text"),
            PSF.col("clamped_timestamp").alias("timestamp"),
            PSF.col("author_handle").alias("author_id"),
            PSF.col("content_metadata"),
        )
        return output_df

    def _get_content(self, term: str, since_dt: datetime=None, max_posts: int=1000,
                     sort: str="latest", lang: str=None) -> list:
        """
        Fetch and parse all pages of search results for a single term.
        Returns a list of dicts keyed by full_bluesky_schema field names.

        Passes "since" to the API when a time window is set, but also filters
        client-side: the AppView rejects since/until for some broad queries
        (see bluesky-social/atproto#3258), in which case we retry without it.

        Pagination uses the API cursor when allowed. Unauthenticated cursor requests
        are 403-blocked on some networks (see bluesky-social/atproto#3583); in that
        case, for "latest" sort, we page by sliding an "until" boundary down to the
        oldest timestamp seen so far instead.
        """
        rows = []
        seen_uris = set() # "until" paging re-returns the boundary post despite being documented as exclusive
        cursor = None
        use_since = since_dt is not None
        paginate_by_time = False # Set when cursor pagination is blocked
        until_dt = None
        last_page_oldest = None
        max_posts_per_page = 100
        while len(rows) < max_posts:
            params = {
                "q": term,
                "sort": sort,
                "limit": min(max_posts_per_page, max_posts - len(rows)),
            }
            if lang:
                params["lang"] = lang
            if use_since:
                params["since"] = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            if paginate_by_time and until_dt is not None:
                # "until" is exclusive on sortAt, so the boundary post itself is not re-fetched
                params["until"] = until_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            elif cursor:
                params["cursor"] = cursor

            try:
                response = self._search_page(params)
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if use_since and status == 400:
                    print(f"'since' rejected for term '{term}'; falling back to client-side time filtering")
                    use_since = False
                    cursor = None
                    rows = []
                    continue
                if cursor and not paginate_by_time and status == 403:
                    if sort != "latest":
                        print(f"Warning: cursor pagination blocked and 'until'-based paging requires "
                              f"sort='latest'; returning first page only for term: {term}")
                        break
                    print(f"Cursor pagination blocked for term '{term}'; paging by 'until' timestamp instead")
                    if last_page_oldest is None:
                        break
                    paginate_by_time = True
                    cursor = None
                    until_dt = last_page_oldest
                    continue
                raise

            posts = response.get("posts", [])
            reached_window_edge = False
            last_page_oldest = None
            for post in posts:
                row = self._parse_post(post, matched_term=term)
                if row is None:
                    continue
                if last_page_oldest is None or row["clamped_timestamp"] < last_page_oldest:
                    last_page_oldest = row["clamped_timestamp"]
                if since_dt is not None and row["clamped_timestamp"] < since_dt:
                    reached_window_edge = True
                    continue
                if row["uri"] in seen_uris:
                    continue
                seen_uris.add(row["uri"])
                rows.append(row)
                if len(rows) >= max_posts:
                    break

            cursor = response.get("cursor")
            if len(posts) == 0:
                break
            if reached_window_edge and sort == "latest":
                # Results are newest-first, so remaining pages are older still
                break
            if paginate_by_time:
                if last_page_oldest is None or (until_dt is not None and last_page_oldest >= until_dt):
                    break # Boundary is not advancing; avoid an infinite loop
                until_dt = last_page_oldest
            elif cursor is None:
                break
        return rows

    def _search_page(self, params: dict) -> dict:
        """Call searchPosts for one page, retrying on rate limits and server errors."""
        url = f"{self.service_url}/xrpc/app.bsky.feed.searchPosts"
        max_attempts = 3
        for attempt in range(max_attempts):
            response = requests.get(
                url=url,
                params=params,
                headers={"User-Agent": self._user_agent})
            if (response.status_code == 429 or response.status_code >= 500) and attempt < max_attempts - 1:
                try:
                    sleep_s = float(response.headers.get("Retry-After", ""))
                except ValueError:
                    sleep_s = 2 ** (attempt + 1)
                time.sleep(sleep_s)
                continue
            response.raise_for_status()
            return response.json()

    def _parse_post(self, post: dict, matched_term: str) -> dict:
        """
        Map one searchPosts postView to a row dict. Returns None for posts that
        should be skipped (no text, or no usable timestamp).
        """
        record = post.get("record", {})
        text = record.get("text")
        if not text or not text.strip():
            return None

        created_at = self._parse_datetime(record.get("createdAt"))
        indexed_at = self._parse_datetime(post.get("indexedAt"))
        clamped = self._clamp_timestamp(created_at, indexed_at)
        if clamped is None:
            return None

        author = post.get("author", {})
        uri = post.get("uri")
        handle = author.get("handle")
        web_url = None
        if uri and handle:
            web_url = f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}"
        reply = record.get("reply") or {}

        return {
            "uri": uri,
            "cid": post.get("cid"),
            "text": text,
            "author_handle": handle,
            "author_did": author.get("did"),
            "created_at": created_at,
            "indexed_at": indexed_at,
            "clamped_timestamp": clamped,
            "like_count": post.get("likeCount", 0),
            "repost_count": post.get("repostCount", 0),
            "reply_count": post.get("replyCount", 0),
            "quote_count": post.get("quoteCount", 0),
            "langs": ",".join(record.get("langs") or []),
            "reply_parent_uri": (reply.get("parent") or {}).get("uri"),
            "reply_root_uri": (reply.get("root") or {}).get("uri"),
            "matched_term": matched_term,
            "url": web_url,
        }

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """
        Parse an ISO 8601 timestamp to an aware UTC datetime, or None if unparseable.
        createdAt is client-declared, so tolerate nonstandard fractional-second
        precision and missing timezones rather than failing the whole ingestion.
        """
        if not value:
            return None
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        # Pad/truncate fractional seconds to the 6 digits fromisoformat expects
        normalized = re.sub(
            r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), normalized, count=1)
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _clamp_timestamp(created_at: datetime, indexed_at: datetime) -> datetime:
        """
        min(createdAt, indexedAt): keeps legitimate backdated dates but caps
        future-dated/skewed createdAt at the time the AppView first saw the post.
        """
        if created_at is None:
            return indexed_at
        if indexed_at is None:
            return created_at
        return min(created_at, indexed_at)

    @staticmethod
    def _time_filter_to_since(time_filter: str) -> datetime:
        """Convert a Reddit-style time_filter string to a UTC "since" datetime (None for "all")."""
        if time_filter == "all":
            return None
        windows = {
            "hour": timedelta(hours=1),
            "day": timedelta(days=1),
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
            "year": timedelta(days=365),
        }
        if time_filter not in windows:
            raise ValueError(f"Invalid time_filter: {time_filter}. Options: all, {', '.join(windows)}")
        return datetime.now(timezone.utc) - windows[time_filter]

    def _get_unique_post_ids(self, rows: list) -> set:
        """Returns a set of unique post URIs from the output of _get_content()."""
        return set([row["uri"] for row in rows])

    def _set_content_type(self) -> None:
        self.content_type = "Bluesky Post"
