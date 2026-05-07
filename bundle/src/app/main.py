#!/usr/bin/env python3
"""
Simple FastAPI server to display a game dropdown list.
This queries Databricks to get the list of games and displays them in a dropdown.

Usage:
    python standalone_game_dropdown.py

Then open your browser to: http://localhost:8000
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import markdown
import yaml
from utils.steam import SteamHelper
from utils.google_play import GooglePlayHelper
from utils.reddit import RedditHelper
from utils.databricks import DatabricksClient
from utils.report_utils import split_report_contents, str_to_url_encoding
from utils.genie_room import genie_query, start_new_conversation, refresh_genie_token
from schemas import (
    common as common_schemas,
    dashboard as dashboard_schemas,
    genie as genie_schemas,
    google_play as google_play_schemas,
    reddit as reddit_schemas,
    report as report_schemas,
    steam as steam_schemas,
)
from routers import main, report, dashboard, ingestion, reddit, steam, google_play, genie

from databricks.sdk.core import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create terminal debug logger handler
# terminal_handler = logging.StreamHandler()
# terminal_handler.setLevel(logging.DEBUG)
# terminal_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
# logger.addHandler(terminal_handler)

app = FastAPI(
    title="Social Listening Demo",
    description="App that gets user sentiment from selected games and queries Databricks for analytics/AI/etc.",
    version="1.0.0"
)
app.include_router(main.router)
app.include_router(report.router)
app.include_router(dashboard.router)
app.include_router(ingestion.router)
app.include_router(reddit.router)
app.include_router(steam.router)
app.include_router(google_play.router)
app.include_router(genie.router)

# Mount static files directories
assets_path = Path(__file__).parent / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    logger.info(f"Mounted assets directory: {assets_path}")
else:
    logger.warning(f"Assets directory not found: {assets_path}")

styles_path = Path(__file__).parent / "styles"
if styles_path.exists():
    app.mount("/styles", StaticFiles(directory=str(styles_path)), name="styles")
    logger.info(f"Mounted styles directory: {styles_path}")
else:
    logger.warning(f"Styles directory not found: {styles_path}")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎮 Social Listening Demo Server (FastAPI)")
    print("="*60)
    print("\nStarting server...")
    print("🌐 Open your browser to: http://localhost:8000")
    print("📚 API documentation available at: http://localhost:8000/docs")
    print("📋 Alternative docs at: http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")