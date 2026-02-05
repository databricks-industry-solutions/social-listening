# Content Ingestion

This directory contains platform-specific ingestors for fetching player reviews and feedback.

## Structure

```
ingestion_utils/
├── data_ingestor.py          # Abstract base class
├── steam_ingestor.py          # Steam reviews
├── google_play_ingestor.py    # Google Play reviews
└── reddit_ingestor.py         # Reddit posts
```

## Architecture

All ingestors inherit from `DataIngestor` and return a standardized schema:

```python
{
  "content_id": "string",        # Unique identifier
  "content_type": "string",      # Platform type (e.g., "Steam Review")
  "game_name": "string",         # Game display name
  "content_text": "string",     # Review/post text
  "timestamp": "timestamp",      # Content creation time
  "author_id": "string",         # Author identifier
  "content_metadata": "string"  # Platform-specific metadata (JSON)
}
```

## Sampling Strategy

To ensure manageable data volumes and reasonable processing times, the ingestion system implements automatic sampling:

### Default Sampling Rules

- **Maximum fetch limit**: 10,000 reviews or equivalent per source
- **Sample size**: If more than 10,000 reviews or equivalent are available, data is randomly sampled down to 2,000 reviews
- **Sampling method**: Uniform random sampling to ensure representative distribution across time periods and ratings


### Adjusting Sample Size

To modify sampling behavior, either edit the classes in this directory or simply call their methods with different parameters.

**Note**: Larger sample sizes will increase processing time and costs for AI translation and sentiment extraction.

## Adding a New Platform

To add a new platform (e.g., YouTube comments):

1. **Create ingestor class** (`youtube_ingestor.py`):
   ```python
   from ingestion_utils.data_ingestor import DataIngestor
   from pyspark.sql import DataFrame, SparkSession
   
   class YouTubeIngestor(DataIngestor):
       ....
   ```

2. **Add to `Abstracted_Ingestion.ipynb`**:
   ```python
   from ingestion_utils import YouTubeIngestor
   
   # In the ingestion logic cell:
   elif CONTENT_TYPE == "YouTube Comment":
       youtube_ingestor = YouTubeIngestor(spark)
       output_df = youtube_ingestor.ingest(video_id=SOURCE_CONTENT_ID, game_name=GAME_NAME)
   ```

3. **Add API keys** (if required) to `src/config/config.yaml`, `resources/Games Social Listening - App.app.yml`, and within app code
