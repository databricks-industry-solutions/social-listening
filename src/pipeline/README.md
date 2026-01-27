# Games Social Listening Pipeline

This directory contains the **Spark Declarative Pipeline** that processes player feedback through AI-powered sentiment extraction and analysis.

## 🔄 Pipeline Overview

The pipeline implements a **4-stage transformation** process that converts raw reviews into structured sentiment data:

```
Bronze (Raw Content)
    ↓ 01_ai_translation.py
Silver (Translated Content)
    ↓ 02_ai_sentiment_extraction.py
Silver (AI-Extracted JSON)
    ↓ 03_parse_sentiment.py
Silver (Parsed Sentiment)
    ↓ 04_reporting_layer.py
Gold (Denormalized Analytics Tables)
```

## 📂 Directory Structure

```
src/pipeline/
├── README.md                          # This file
├── transformations/                   # Pipeline transformation logic
│   ├── 01_ai_translation.py           # Stage 1: AI translation to English
│   ├── 02_ai_sentiment_extraction.py  # Stage 2: LLM sentiment extraction
│   ├── 03_parse_sentiment.py          # Stage 3: Parse JSON to structured columns
│   └── 04_reporting_layer.py          # Stage 4: Create gold analytics tables
├── utilities/
│   └── utils.py                       # Shared utility functions
└── explorations/
    └── sample_exploration.py          # Ad-hoc data exploration notebooks
```

---

## 📚 Additional Resources

- [Spark Declarative Pipelines Documentation](https://docs.databricks.com/en/delta-live-tables/index.html)
- [Databricks AI Functions](https://docs.databricks.com/en/large-language-models/ai-functions.html)
- [Foundation Model APIs](https://docs.databricks.com/en/machine-learning/foundation-models/index.html)
- [Configuration Guide](../../docs/CONFIGURATION.md)
