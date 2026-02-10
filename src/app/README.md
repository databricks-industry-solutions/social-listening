# Games Social Listening App

This is the **Databricks App** that provides the interactive UI for the Games Social Listening platform. The app is automatically deployed via Databricks Asset Bundle and runs on Databricks App hosting.

## 📂 Application Structure

```
src/app/
├── main.py                       # FastAPI application entry point
├── config.yaml                   # App configuration (UI, navigation, data sources)
├── dependencies.py               # Shared dependencies (DataLoader, config)
├── requirements.txt              # Python dependencies
│
├── routers/                      # API endpoint routers
│   ├── __init__.py
│   ├── main.py                   # Home page router
│   ├── dashboard.py              # Dashboard page router
│   ├── genie.py                  # Genie Space integration router
│   ├── google_play.py            # Google Play ingestion router
│   ├── reddit.py                 # Reddit ingestion router
│   ├── steam.py                  # Steam ingestion router
│   ├── report.py                 # AI report generation router
│   └── ingestion.py              # Generic ingestion router
│
├── schemas/                      # Pydantic data models
│   ├── __init__.py
│   ├── common.py                 # Shared response models
│   ├── dashboard.py              # Dashboard-specific models
│   ├── genie.py                  # Genie Space models
│   ├── google_play.py            # Google Play models
│   ├── reddit.py                 # Reddit models
│   ├── steam.py                  # Steam models
│   └── report.py                 # Report generation models
│
├── utils/                        # Helper utilities
│   ├── __init__.py
│   ├── data.py                   # DataLoader for Databricks queries
│   ├── databricks.py             # Databricks SDK helpers
│   ├── genie_room.py             # Genie Space API client
│   ├── google_play.py            # Google Play scraping logic
│   ├── reddit.py                 # Reddit API client
│   ├── steam.py                  # Steam API client
│   ├── rendering.py              # UI rendering helpers
│   ├── report_utils.py           # Report generation logic
│   └── token_minter.py           # Databricks token management
│
├── templates/                    # HTML templates
│   └── index.html                # Main app template
│
├── styles/                       # CSS stylesheets
│   ├── main.css                  # Main app styles
│   ├── sidebar.css               # Sidebar navigation styles
│   ├── theme.css                 # Active theme
│   ├── theme_example_default.css # Example: Default theme
│   └── theme_example_rmg.css     # Example: RMG branded theme
│
└── assets/                       # Static assets (images, icons)
    ├── databricks/               # Databricks icons (57 SVG files)
    ├── genie/                    # Genie Space UI assets
    ├── google_play/              # Google Play icon
    ├── reddit/                   # Reddit logo
    └── steam/                    # Steam icon
```

## ⚙️ Configuration

The app uses `src/app/config.yaml` for configuration; view that file for more information.

## 🎨 Styling

### Theme System

The app uses CSS variables for theming. Customize by editing `styles/theme.css`:

### Pre-built Themes

- **Default Theme** (`theme_example_default.css`): Simple blue theme
- **RMG Theme** (`theme_example_rmg.css`): Alternate Real Money Gaming (RMG) color scheme

To use a pre-built theme, copy it to `theme.css`:

```bash
cp styles/theme_example_rmg.css styles/theme.css
```

### Custom Styling

Key CSS files:
- **`main.css`**: Global app styles (typography, buttons, forms)
- **`sidebar.css`**: Navigation sidebar styles
- **`theme.css`**: Active theme variables (modify this for your brand)

## 🧩 Core Components

### DataLoader (`utils/data.py`)

Manages Databricks SQL Warehouse connections and queries.

### Databricks Client (`utils/databricks.py`)

Wrapper for Databricks SDK operations.

### Genie Room Client (`utils/genie_room.py`)

Interface for Genie Space natural language queries.

### Platform Ingestors (`utils/*.py`)

- **`steam.py`**: Steam reviews API client
- **`google_play.py`**: Google Play reviews scraper (google-play-scraper)
- **`reddit.py`**: Reddit PRAW client for subreddit posts

## 📚 Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Configuration Guide](../../docs/CONFIGURATION.md)
