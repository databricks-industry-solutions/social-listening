# Configuration & Long Term Use

This guide covers **customizing** the Games Social Listening demo and **productionalizing** it for daily use.

## Table of Contents

**Moving to Long Term Usage**
- [DAB Deployment](#dab-deployment)
- [Enable Job Scheduling](#enable-job-scheduling)
- [Remove Sampling (Optional)](#remove-sampling-optional)

**Customization**
- [Enable Steam and Reddit](#enable-steam-and-reddit)
- [Ingest from Generic Table](#ingest-from-generic-table)
- [Add New Platforms](#add-new-platforms)
- [LLM Endpoint Configuration](#llm-endpoint-configuration)
- [Sentiment Categories](#sentiment-categories)
- [Report Personas](#report-personas)

**App Configuration**
- [App Configuration and Customization](#app-configuration-and-customization)

---

## Moving to Long Term Usage

### DAB Deployment

For production, deploy Databricks Asset Bundles (DAB) via Databricks CLI instead of `Demo_Setup.ipynb`. The main bundle configuration file is `databricks.yml`.

Specifically, you'll need to hardcode bundle variables for each environment to deploy. Edit `databricks.yml` to hardcode values instead of passing via CLI:

```yaml
targets:
  prod:
    workspace:
      host: https://your-workspace.cloud.databricks.com
      root_path: /Workspace/Shared/.bundle/${bundle.name}/${bundle.target}
    variables:
      catalog: prod_social_listening        # Your production catalog
      schema: player_feedback                # Your production schema
      warehouse_id: abc123def456              # Your SQL Warehouse ID
      prefix: prod                            # Resource naming prefix
```

**Before**: Variables passed via `databricks bundle deploy --var="catalog=my_catalog"` in `Demo_Setup.ipynb`

**After**: Variables hardcoded in `databricks.yml`

#### Deployment Steps

```bash
# 1. Clone repository
git clone <repository-url>
cd social-listening

# 2. Validate bundle
databricks bundle validate --target prod

# 3. Deploy
databricks bundle deploy --target prod

# 4. Run job to populate data
databricks bundle run Games_Social_Listening_Job --target prod
```

#### Destroying Resources

```bash
# Remove all deployed resources
databricks bundle destroy --target prod
```

**Note**: Currently, not all configurations for the demo can be configured via DAB. Follow the `Demo_Setup.ipynb` to:
- Create the Genie Space via API
- Provide permissions to the App Service Principal to the catalog, job, and Genie Space
- Update the app configurations (`src/app/config.yaml`) with the deployed resources from DAB (Job ID, Genie Space ID, Dashboard URL, etc.)

### Enable Job Scheduling

The Social Listening jobs can be configured to bring in new reviews on a regular cadence. Both the main job and the weekly summary report job have parameters to specify if the `update_type` is a `NEW_GAME` or `REFRESH`.

In `resources/Games Social Listening - Job.job.yml`, set `pause_status: UNPAUSED`:

```yaml
resources:
  jobs:
    Games_Social_Listening_Job:
      name: ${var.prefix}_Games_Social_Listening
      tasks:
        # ... tasks ...
      schedule:
        quartz_cron_expression: "0 0 8 * * ?"  # Daily at 8 AM ET
        timezone_id: "America/New_York"
        pause_status: UNPAUSED  # Change from PAUSED
```

The weekly summary report job is already configured with a schedule to update AI-generated reports weekly, but this can be updated if necessary. Simply update the `pause_status` from `PAUSED` to `UNPAUSED`.

### Remove Sampling (Optional)

By default, the demo limits ingestion to the equivalent of 2,000 reviews per game for performance and cost optimization. For production use cases requiring full data coverage, you may want to remove or adjust this sampling.

For more information on sampling strategy and configuration, see the [Ingestion Sampling Documentation](../src/ingestion_utils/README.md#sampling-strategy).

---

## Customization

Customize the demo for your use case, industry, and more.

### Enable Steam and Reddit

To enable ingestion from Steam and Reddit, you'll need to provide API keys to authenticate API calls.

#### 0. Obtain Keys
- Steam: Follow the instructions to obtain a free Web API key [here](https://steamcommunity.com/dev). You will need a Steam account.
- Reddit: Sign up to create a free Developer account [here](https://developers.reddit.com/).
  - This will get you these required keys: `client_id`, `client_secret`, `user_agent`.

#### 1. Add Secrets
- Option 1: [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/)

  ```bash
  # Create Steam secret
  databricks secrets put-secret social_listening_app steam_api_key --string-value "YOUR_ACTUAL_STEAM_KEY"
  
  # Create Reddit secrets
  databricks secrets put-secret social_listening_app reddit_client_id --string-value "YOUR_ACTUAL_CLIENT_ID"
  databricks secrets put-secret social_listening_app reddit_client_secret --string-value "YOUR_ACTUAL_CLIENT_SECRET"
  databricks secrets put-secret social_listening_app reddit_user_agent --string-value "social_listening:v1.0 (by /u/yourusername)"

  # Verify Secrets Creation
  databricks secrets list-secrets social_listening_app
  ```

- Option 2: [Databricks Notebook](https://docs.databricks.com/aws/en/notebooks/)

  - Use the `Secrets_Helper.ipynb` notebook provided in this repository.

#### 2. Update Secrets in DAB Configuration

Uncomment the references to the secrets you added above in the App DAB resource (`resources/Games Social Listening - App.app.yml`). For secrets you didn't add values for, leave those lines commented:

```yaml
resources:
  apps:
    social_listening_app:
      name: ${var.prefix}_social_listening_app
      resources:
        - name: reddit_client_id
          secret:
            scope: social_listening_app
            key: reddit_client_id
        - name: reddit_client_secret
          secret:
            scope: social_listening_app
            key: reddit_client_secret
        - name: reddit_user_agent
          secret:
            scope: social_listening_app
            key: reddit_user_agent
        - name: steam_api_key
          secret:
            scope: social_listening_app
            key: steam_api_key
```

#### 3. Re-deploy the App
Simply re-run the `Demo_Setup.ipynb` notebook from top to bottom. When going to the app page in Databricks, you should see the newly added secrets under "App Resources":

![app_resources_page](assets/app_resources.png)

### Ingest from Generic Table

You may ingest data from a generic table you've already created in Unity Catalog. 

1. Create your table
    - It can be located anywhere in Unity Catalog.
    - It can include multiple `game_name` values and `content_type` values (see below). 
    - It must include the following columns:
      - `content_id`
        - Type: string
        - E.g. "123", "abc-def", etc.  
      - `content_type`
        - Type: string
        - E.g. "Steam Review", "Reddit Comment"  
      - `game_name`
        - Type: string
        - E.g. "Call of Duty"
      - `content_text`
        - Type: string
        - E.g. a game review, social media comment, etc.
      - `timestamp`
        - Type: timestamp
        - E.g. 2026-02-02T20:34:55.126+00:00
      - `author_id`
        - Type: string
        - E.g. "abc-123", "john_smith_98"
      - `content_metadata`
        - Type: string
        - Can be empty, a JSON string, or any other value you would like. This column is unused in the pipeline, and is used as a catch-all for relevant metadata associated with each piece of content.
        - E.g. "{"upvotes": 123, "tags": ["action", "adventure"]}"

1. Change the App configuration file
    - Starting from the root of this repo, navigate to `src/app/config.yaml`.
    - Add `generic_table` to the `ui/main/add_game_sources` section.

1. Re-run the `Demo_Setup` notebook.

1. Re-open the App, and you should now see the "Generic Table" option on the "Add Game" page.
    - Follow the on-screen instructions to add your bronze table.
    - Your bronze table will remain unchanged, and rows will be added to the auto-generated bronze/silver/gold tables from the Lakeflow Job and Pipeline.
    - You may append to the same bronze table and re-add it multiple times (there is built-in de-duplication).


### Add New Platforms

Existing supported platforms:

| Platform | Content Type | Identifier Format | API Key Required |
|----------|--------------|-------------------|------------------|
| **Steam** | Game Reviews | Steam App ID (e.g., `730` for CS:GO) | Yes |
| **Google Play** | App Reviews | Package name (e.g., `com.nianticlabs.pokemongo`) | No |
| **Reddit** | Subreddit Posts | Subreddit name (e.g., `gaming`) | Yes |

**Want to add a new platform?** The ingestion system uses an abstract `DataIngestor` class that makes it easy to add new sources (YouTube, TikTok, etc.). See [src/ingestion_utils/README.md](../src/ingestion_utils/README.md) for a step-by-step guide.

### LLM Endpoint Configuration

The solution uses Databricks Foundation Model APIs for AI-powered sentiment extraction and report generation. You can customize the LLM endpoint and parameters in `src/config/config.yaml`.

#### Default Configuration

```yaml
llm:
  endpoint_name: "databricks-meta-llama-3-3-70b-instruct"
  parameters:
    max_tokens: 1000
    temperature: 0.20
```

#### Customizing the LLM

**Endpoint Name**: Change to any Databricks Foundation Model endpoint or your own provisioned model.

**Parameters**:
- `max_tokens`: Maximum number of tokens in the response (default: 1000)
- `temperature`: Controls randomness in responses (0.0 = deterministic, 1.0 = creative, default: 0.20)

#### Example: Using a Different Model

```yaml
llm:
  endpoint_name: "databricks-meta-llama-3-1-405b-instruct"
  parameters:
    max_tokens: 1500
    temperature: 0.15
```

**Note**: After changing the LLM configuration, restart the pipeline jobs and app to apply the changes.

### Sentiment Categories

Sentiment categories define the topics extracted from the content.

#### Default Categories

Defined in `src/config/config.yaml`:

```yaml
sentiment_categories:
  - 'gameplay_mechanics'           # Core gameplay features
  - 'matchmaking_game_balance'     # Fairness, matchmaking
  - 'game_performance'             # FPS, lag, crashes
  - 'replayability'                # Long-term engagement
  - 'character'                    # Character design, abilities
  - 'monetization'                 # IAP, pricing, pay-to-win
  - 'bugs_glitches_techissues'     # Technical issues
  - 'graphics_audio'               # Visuals and sound
  - 'suggestion_feedback'          # Feature requests
  - 'account_issues'               # Login, account problems
  - 'cheating_hacking'             # Cheating, exploits
  - 'toxicity'                     # Community toxicity
  - 'player_retention'             # Retention, churn
  - 'onboarding'                   # New player experience
```

#### Customizing Categories

Edit `src/config/config.yaml` to add, remove, or modify categories based on your specific needs.

#### Updating Genie Space

If you modify categories, update the Genie Space instructions to reflect the new categories:

1. Navigate to your Genie Space in Databricks
2. Click **Edit** → **General Instructions**
3. Update the category list to match your `config.yaml`

### Report Personas

AI-generated reports are customized for different personas/stakeholders.

#### Default Personas

Defined in `src/config/config.yaml`:

```yaml
personas:
  community_manager:
    display_text: 'Community Manager'
    prompt: 'You are an expert community manager assistant...'

  marketer:
    display_text: 'Marketer'
    prompt: 'Write a concise, human-readable summary for a marketer...'

  game_designer:
    display_text: 'Game Designer'
    prompt: 'Write a concise, human-readable summary for a game designer...'
```

#### Customizing Personas

Add or modify personas in `src/config/config.yaml` to match your organization's roles. Each persona should include:
- `display_text`: The human-readable name shown in the UI
- `prompt`: The system prompt that defines how the AI generates reports for this persona

You will also need to add matching display names in `src/app/config.yaml`.

---

## App Configuration and Customization

Please see the [src/app/README.md](../src/app/README.md) for detailed configuration and customization options for the application.

---

## Additional Resources

- [Databricks Asset Bundles Documentation](https://docs.databricks.com/en/dev-tools/bundles/index.html)
- [Databricks CLI Reference](https://docs.databricks.com/en/dev-tools/cli/index.html)
- [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Spark Declarative Pipelines](https://docs.databricks.com/en/delta-live-tables/index.html)
- [Databricks Apps](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)

