from pyspark import pipelines as dp
from utilities.utils import build_prompt, build_sentiment_schema
from pyspark.sql.functions import col, expr, lit, concat
import yaml

config_file_path = "../../config/config.yaml"
with open(config_file_path, 'r') as config_file:
  CONFIG_DATA = yaml.safe_load(config_file)

CATEGORIES = CONFIG_DATA["sentiment_categories"]
ENDPOINT_NAME = CONFIG_DATA["llm"]["endpoint_name"]

@dp.table(
    comment="Extract sentiment and topics from game user generated content"
)
def feedback_content_ai_extraction():
    ai_prompt = build_prompt(CATEGORIES)
    output_schema = build_sentiment_schema(CATEGORIES)
    df = spark.readStream.option("skipChangeCommits", "true").table("feedback_content_translated")
    df = df.withColumn(
        "content_topic",
        expr(
            f"ai_query('{ENDPOINT_NAME}', concat({repr(ai_prompt)}, content_text), '{output_schema}')"
        )
    )
    return df