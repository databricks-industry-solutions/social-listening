# Games Social Listening Demo

[![Unity Catalog](https://img.shields.io/badge/Unity_Catalog-Enabled-00A1C9?style=for-the-badge)](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
[![Serverless](https://img.shields.io/badge/Serverless-Compute-00C851?style=for-the-badge)](https://docs.databricks.com/en/compute/serverless.html)

**AI-powered player feedback analysis from Steam, Google Play, and Reddit using sentiment extraction and natural language insights.**

Maintainers: [Thomas Xu](thomas.xu@databricks.com), [Brendan Byam](brendan.byam@databricks.com)

## 🚀 What is Games Social Listening?

Games Social Listening is an end-to-end platform that transforms player feedback into actionable insights using AI. It:

- **Ingests** reviews and feedback from Steam, Google Play, and Reddit
- **Translates** content to English using AI translation
- **Analyzes** sentiment across 12 gameplay categories using AI
- **Generates** AI-powered reports tailored for different personas (Community Manager, Marketer, Game Designer)
- **Visualizes** insights through interactive dashboards and Genie Space natural language queries

## 📦 Installation

This solution uses [Databricks Asset Bundle](https://docs.databricks.com/en/dev-tools/bundles/index.html) with automated setup via the `Demo_Setup.ipynb` notebook:

### Prerequisites
- A [Databricks workspace](https://docs.databricks.com/aws/en/admin/workspace/) with [Unity Catalog enabled](https://docs.databricks.com/aws/en/data-governance/unity-catalog/enable-workspaces)
    - And ability to create a schema or access to an existing schema
    - Note: if you are on a Free Trial workspace created using a personal email, you may not be able to ingest data from the games platforms due to [limited external network access](https://docs.databricks.com/aws/en/getting-started/free-trial#trial-limits). Contact your Databricks account team for support.
- Add `*.databricksapps.com` as a domain allowed to embed AI/BI Dashboards
    - Settings > Workspace Admin > Security > External Access:
![prereqs_domain](docs/assets/installation_alt_prereqs_domain.png)
    - You can still proceed with demo installation/setup without this step, but the embedded dashboard will not appear in the Databricks App.

- [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/) installed (optional, for manual deployment)
- [Serverless compute](https://docs.databricks.com/aws/en/compute/serverless/) available
    - If you don't see Serverless as an option in the notebook, ensure you have these [Workspace Previews](https://docs.databricks.com/aws/en/admin/workspace-settings/manage-previews) enabled:
        - Serverless Compute for Delta Live Tables
        - Serverless Compute for Workflows and Notebooks
        - (You may see slightly different names, e.g. "Jobs" instead of "Workflows", "Declarative Pipelines" instead of "Delta Live Tables")
    - If you cannot use Serverless and must use classic compute, see the guidance in [`CONFIGURATION.md`](/docs/CONFIGURATION.md#using-classic-compute).

- [SQL Warehouse](https://docs.databricks.com/aws/en/compute/sql-warehouse/) for dashboard and app queries

### Demo Quick Start (Recommended)

1. **Clone the Repository to your Databricks workspace using a [Git Folder](https://docs.databricks.com/aws/en/repos/repos-setup)**
2. **(Optional)** - To enable Steam and Reddit ingestion, see the instructions in [docs/CONFIGURATION.md](docs/CONFIGURATION.md#enable-steam-and-reddit). **This requires API keys (free) for those platforms**.
3. Access the `Demo_Setup.ipynb` notebook and populate the widgets at the top with your desired values.
![installation_quickstart_widgets](docs/assets/installation_quickstart_widgets.png)

    - Create the catalog and schema if they do not already exist.
    - **Note:** The prefix can only contain lowercase letters, numbers, and hyphens, and that hyphens cannot be at the beginning or end.

4. **Select 'Run All'** to execute all cells in the notebook using serverless compute
![installation_quickstart_run_all](docs/assets/installation_quickstart_run_all.png)

    - The notebook will automatically:
        - Deploy all resources (Jobs, Pipeline, Dashboard, App) via a Databricks Asset Bundle
        - Configure with your workspace settings
        - Load sample data and execute sentiment analysis (Pokemon Go from Google Play)
    - Should take 10-15 minutes
    - Note: by default the Demo Setup notebook will ingest a small amount of data from Pokemon Go on the Google Play Store (to have some initial data to play with). If you want this initial ingestion to ingest data for a different game/platform instead, modify the `parameter` values at the bottom of `bundle/resources/Games Social Listening - Job.job.yml`, adding corresponding API keys via `Secrets Helper` if necessary.
5. **Access the deployed app** in your Databricks workspace!
    - Left sidebar > Compute > Apps

### Alternative: Configure DAB Deployment

For production or custom deployments, see [docs/CONFIGURATION.md#dab-deployment](docs/CONFIGURATION.md#dab-deployment) for CLI-based deployment.

Note that if you want to have multiple demo apps in the same Databricks workspace, make sure to update at least the bundle name in `databricks.yml` to prevent subsequent deploys from overwriting each other. If you still encounter errors, try deleting the `.databricks` directory (autogenerated by DAB validation/deployment) and retrying.

## 🏗️ Project Structure

```
cmeg_player_feedback_app/
├── databricks.yml                    # Databricks Asset Bundle configuration
├── Demo_Setup.ipynb                  # Automated installation notebook
├── bundle/
│   ├── resources/                        # DAB resource definitions
│   │   ├── Games Social Listening - Job.job.yml
│   │   ├── Games Social Listening - Pipeline.pipeline.yml
│   │   ├── Games Social Listening - Dashboard.dashboard.yml
│   │   └── Games Social Listening - App.app.yml
│   └── src/
│       ├── Abstracted_Ingestion.ipynb   # Multi-platform ingestion notebook
│       ├── Summary_Report_Generator.ipynb  # AI report generation
│       ├── app/                          # FastAPI web application
│       │   ├── main.py                   # App entry point
│       │   ├── config.yaml               # App configuration
│       │   ├── routers/                  # API endpoints
│       │   ├── utils/                    # Helper functions
│       │   └── templates/                # UI templates
│       ├── pipeline/                     # Spark Declarative Pipeline transformations
│       │   └── transformations/
│       │       ├── 01_ai_translation.py
│       │       ├── 02_ai_sentiment_extraction.py
│       │       ├── 03_parse_sentiment.py
│       │       └── 04_reporting_layer.py
│       ├── ingestion_utils/              # Platform-specific ingestors
│       │   ├── steam_ingestor.py
│       │   ├── google_play_ingestor.py
│       │   └── reddit_ingestor.py
│       └── config/                       # Configuration files
│           └── config.yaml               # Sentiment categories & personas
└── docs/                             # Documentation
    └── CONFIGURATION.md              # Customization & production guide
```

## 🔄 Demo Contents

The demo implements a **6-stage social listening analysis**:

### Stage 1: Ingestion
- **Pulls user generated content/feedback** from Steam, Google Play, or Reddit
- **Sampling**: Max 10K content records per source, sampled to 2K if exceeded

### Stage 2: AI Translation
- **Translates** all content to English using `ai_translate()`
- **Preserves** original text for reference

### Stage 3: Sentiment Extraction
- **Uses Meta Llama 3.3 70B** for AI sentiment analysis
- **Extracts sentiment** across categories and subtopics from user-generated content

### Stage 4: Reporting Layer Data
- **Creates gold tables** optimized for analytics
- **Powers** dashboard, app, and Genie Space

### Stage 5: Summary Report
- **Generates summary reports** of sentiment analysis for 3 personas (Community Manager, Marketer, Game Designer)

### Stage 6: Consolidates Insight and Actions in the App
- Add new games for sentiment analysis
- Review Summary Reports
- Ask natual language questions with genie
- Drill into deeper insights with the dashboard embedded into the app


## 🎯 Deployed Components

| Component | Description |
|-----------|-------------|
| **Spark Declarative Pipeline** | 4-stage transformation: translation → sentiment extraction → parsing → gold tables |
| **Orchestration Job** | Daily/New Game content ingestion + pipeline execution + dashboard refresh + generate summary report for new games |
| **AI/BI Dashboard** | Interactive analytics with filters, visualizations, and drill into sub topic sentiment |
| **Genie Space** | Natural language queries on player feedback data |
| **Summary Report Job** | Update the AI-generated summary reports for all tracked games |
| **Databricks App** | Add games and explore insights |

## ⚙️ Configuration and Customization

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for:
- Customizing the demo for your own needs
- Productionalizing DAB and assets

## 📚 Documentation

>**Documentation Website**:  
https://databricks-industry-solutions.github.io/social-listening/

Documentation files in this repository:
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - Customization, production deployment, and API keys setup
- **[src/app/README.md](src/app/README.md)** - Databricks App structure and configuration
- **[src/pipeline/README.md](src/pipeline/README.md)** - Pipeline development and transformations
- **[src/ingestion_utils/README.md](src/ingestion_utils/README.md)** - Details on ingestion from platforms, sampling, and adding new platforms for ingestion

## 🎮 Supported Platforms

| Platform | Content Type | Identifier Format | API Key Required |
|----------|--------------|-------------------|------------------|
| **Steam** | Game Reviews | Steam App ID (e.g., `730` for CS:GO) | Yes |
| **Google Play** | App Reviews | Package name (e.g., `com.nianticlabs.pokemongo`) | No |
| **Reddit** | Subreddit Posts | Subreddit name (e.g., `gaming`) | Yes |

To enable Steam and Reddit ingestion, see [CONFIGURATION.md](docs/CONFIGURATION.md#enable-steam-and-reddit).

You can also load data from your own bronze table in Unity Catalog, provided it is in the correct format. For more info see [CONFIGURATION.md](docs/CONFIGURATION.md#ingest-from-generic-table).

**Want to add a new platform?** The ingestion system uses an abstract `DataIngestor` class that makes it easy to add new sources (YouTube, TikTok, etc.). See [src/ingestion_utils/README.md](src/ingestion_utils/README.md) for a step-by-step guide. 

## Demo Teardown

To destroy all demo resources, uncomment the last few cells of the `Demo_Setup.ipynb` and run each to:
- Destroy resources managed by DAB
- Destroy Genie Space via API
- Destroy secret scope via SDK

## 🛠️ Troubleshooting

### Hyphens in Catalog names

Unity Catalog catalog names can contain hyphens (`-`), but this will cause the `Demo Setup` notebook to fail because the catalog name is used in unquoted SQL such as `GRANT ... ON CATALOG <name>`.

**Fix:** Rename the catalog to remove hyphens, for example by changing hyphens to underscores (`my-catalog` → `my_catalog`). The easiest way is via the **Catalog Explorer UI** (Catalog > select the catalog > kebab menu ⋮ > Rename). Then update the `catalog` widget value in `Demo_Setup.ipynb` to match exactly and re-run.

### Errors during the bundle deploy step

If a deploy was interrupted, partially failed, or you manually deleted resources (especially the **App**) via the UI, the bundle's deployment state can become inconsistent. Symptoms include errors like *"an app with the same name already exists"* or errors mentioning a **service principal**. Because Databricks Apps have unique, immutable names and an auto-created service principal — and because the bundle's authoritative Terraform state lives **remotely in the workspace** (not in the local `.databricks` cache) — changing the prefix or deleting the local cache does **not** fix this. You need to remove the orphaned resources and wipe the remote bundle state, then redeploy.

> **Note:** The bundle's remote state lives at `/Workspace/Users/<your-user>/.bundle/games_social_listening/`. Deleting *only* the local `.databricks` folder does not clear it. For more on prefixes and resource naming, see [CONFIGURATION.md#resource-naming-and-prefixes](docs/CONFIGURATION.md#resource-naming-and-prefixes).

**Reset steps:**

1. **Delete the App(s)** and **wait until they fully disappear** before redeploying. This is the only resource that hard-blocks a redeploy (unique name + service principal teardown has a lag).
2. **(Optional, for cleanliness)** Delete leftover jobs, pipelines, dashboards, and Genie spaces. These don't block a redeploy but otherwise become orphan duplicates.
3. **Wipe the remote bundle state** by deleting the `games_social_listening` folder under `/Workspace/Users/<your-user>/.bundle/` (the dot-folder is hidden by default in the Workspace UI — enable "show hidden files", and delete only the `games_social_listening` subfolder, not the whole `.bundle` parent).
4. **(Optional)** Delete the local `.databricks` folder(s) to clear the local cache.
5. **Re-run `Demo_Setup.ipynb`** with a single consistent prefix and a hyphen-free catalog name (that already exists).

#### Sample code — notebook (Python SDK)

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
import time

w = WorkspaceClient()
APP_MATCH  = "social-listening"        # app names use hyphens
NAME_MATCH = "social listening"        # jobs/pipelines/dashboards
BUNDLE_NAME = "games_social_listening"

# 1. Delete app(s) and WAIT for full teardown (the only hard blocker)
for a in [a for a in w.apps.list() if APP_MATCH in (a.name or "").lower()]:
    print("Deleting app:", a.name)
    w.apps.delete(name=a.name)
    while True:
        try:
            w.apps.get(name=a.name); time.sleep(10)
        except NotFound:
            print("  fully deleted:", a.name); break

# 2. (Optional) delete leftover jobs and pipelines
for j in [j for j in w.jobs.list() if j.settings and NAME_MATCH in (j.settings.name or "").lower()]:
    w.jobs.delete(job_id=j.job_id); print("Deleted job:", j.settings.name)
for p in [p for p in w.pipelines.list_pipelines() if NAME_MATCH in (p.name or "").lower()]:
    w.pipelines.delete(pipeline_id=p.pipeline_id); print("Deleted pipeline:", p.name)
# (Dashboards: trash in the UI, or via the Lakeview API. Genie spaces: delete in the UI.)

# 3. Wipe the remote bundle state (the actual "start fresh" step)
user = w.current_user.me().user_name
state_path = f"/Users/{user}/.bundle/{BUNDLE_NAME}"   # Workspace API path omits /Workspace prefix
try:
    w.workspace.delete(state_path, recursive=True)
    print("Wiped bundle state at", state_path)
except NotFound:
    print("No bundle state found at", state_path)

# 4. Re-run Demo_Setup.ipynb with a consistent prefix + hyphen-free catalog.
```

#### Sample code — Databricks CLI

```bash
# 1. Delete app(s) — repeat until NONE remain before redeploying
databricks apps list | grep -i social-listening
databricks apps delete <app-name>
databricks apps list | grep -i social-listening      # confirm gone (teardown has a lag)

# 2. (Optional) delete leftover jobs / pipelines / dashboards
databricks jobs list | grep -i "social listening"
databricks jobs delete <job-id>
databricks pipelines list-pipelines | grep -i "social listening"
databricks pipelines delete <pipeline-id>
databricks lakeview trash <dashboard-id>

# 3. Wipe the remote bundle state (the actual "start fresh" step)
databricks workspace delete /Users/<your-user>@<domain>/.bundle/games_social_listening --recursive

# 4. Clear the local cache, then redeploy with a consistent prefix + hyphen-free catalog
rm -rf .databricks bundle/.databricks src/app/.databricks
```

After the reset, re-running `Demo_Setup.ipynb` (or `databricks bundle deploy`) will create everything fresh.

## ⚠️ Disclaimer

Please note the code in this project is provided for your exploration only, and is not formally supported by Databricks with Service Level Agreements (SLAs). It is provided AS-IS and we do not make any guarantees of any kind. Please do not submit a support ticket relating to any issues arising from the use of this project.

## 📄 License

This project is licensed under the Databricks License. See [licenses.md](licenses.md) for more info.
