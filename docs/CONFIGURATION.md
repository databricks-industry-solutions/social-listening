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
- [Genie Space](#genie-space)

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

To run data ingestion on a regular schedule or at specific times instead of being manually triggered via the app UI, you can follow these steps:

1. In Databricks, clone the job that was created by the bundle.
1. Modify the schedules/triggers as desired.
1. Add job parameters to match the ingestion schedule you want.
1. Read the job parameters in the task notebooks.

#### Steam Example
For example, for Steam you could add a job parameter called `steam_num_past_days`.
In `Abstracted Ingestion`, you could add this code snippet to read the widget value and then pass it as the `over_past_days` value of the SteamIngestor::ingest() call:
```python
dbutils.widgets.text("steam_over_past_days", "", "Steam Over Past Days")
steam_over_past_days = dbutils.widgets.get("steam_over_past_days")
if steam_over_past_days != "":
  # Note: can do a more rigorous check for float-conversion via try-except 
  steam_over_past_days = float(steam_over_past_days)
else:
  steam_over_past_days = None
```

Then, add the same snippet in `Summary_Report_Generator` as well as the following additional snippet to compute the `start_date` of the persona reports:
```python
    from datetime import datetime, timedelta
    if steam_over_past_days:
        start_date = datetime.now() - timedelta(days=steam_over_past_days)
        start_date = start_date.strftime("%Y-%m-%d")
```

Note that you should keep the default value of the widget empty if you don't want the app's original job from the bundle to be affected.

Additionally, note the app will always display the most recent report for each persona (regardless of which job triggered the Summary Report generation task).

### Remove Sampling (Optional)

By default, the demo limits ingestion to the equivalent of 2,000 reviews per game for performance and cost optimization. For production use cases requiring full data coverage, you may want to remove or adjust this sampling.

For more information on sampling strategy and configuration, see the [Ingestion Sampling Documentation](../bundle/src/ingestion_utils/README.md#sampling-strategy).

---

## Customization

Customize the demo for your use case, industry, and more.

### Enable Steam and Reddit

To enable ingestion from Steam and Reddit, you'll need to provide API keys to authenticate API calls. Under the hood, these will be stored securely as [Databricks Secrets](https://docs.databricks.com/aws/en/security/secrets/).

#### 0. Obtain Keys
- Steam:
  - Follow the instructions to obtain a free Web API key [here](https://steamcommunity.com/dev). You will need a [Steam account](https://store.steampowered.com/join).
- Reddit:
  - Sign up to create a free Developer account [here](https://developers.reddit.com/).
  - This will get you these required keys: `client_id`, `client_secret`, `user_agent`.
  - **Update**: Reddit began aggressively locking down access to their API late 2025, so this method no longer works.
    - If you already have the above keys from before, then they should continue to work and you can proceed. 
    - If you do not already have the above keys, the community consensus is that it is effectively impossible to attain them. Reach out to your Databricks team for support with alternative options.

#### 1. Add Your Keys
- Option 1: In-App Settings
  - Simply launch the app and provide your keys on the Settings > Credentials page.

- Option 2: [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/)

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

- Option 3: [Databricks Notebook](https://docs.databricks.com/aws/en/notebooks/)

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

The solution uses Databricks Foundation Model APIs for AI-powered sentiment extraction and report generation. You can customize the LLM endpoint and parameters in `bundle/src/config/config.yaml`.

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

Defined in `bundle/src/config/config.yaml`:

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

Edit `bundle/src/config/config.yaml` to add, remove, or modify categories based on your specific needs.

You should also [update the Genie Space](#genie-space) accordingly afterwards.

Note that if you want to change the categories in the future after already ingesting some data, the Declarative Pipeline will require a full refresh. (Ingested data in the `bronze` table would not need to change. Changing personas or persona prompts only affects the Summary Report generation, so the Declarative Pipeline is unaffected.)

### Report Personas

AI-generated reports are customized for different personas/stakeholders.

#### Default Personas

Defined in `bundle/src/config/config.yaml`:

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

Add or modify personas in `bundle/src/config/config.yaml` to match your organization's roles. Each persona should include:
- `display_text`: The human-readable name shown in the UI
- `prompt`: The system prompt that defines how the AI generates reports for this persona

You will also need to add matching display names in `bundle/src/app/config.yaml`.

### Genie Space

If you modified the sentiment categories or want to make other updates to the Genie space, you can update the Genie Space instructions by following these steps:

If Genie Space already created:
1. Navigate to your Genie Space in Databricks (e.g. via bottom-left link in the deployed app)
2. Click **Edit** → **General Instructions**
3. Ensure the sentiment category list matches your `config.yaml`

If Genie Space not yet created:
1. Update the contents of `bundle/src/genie_space/genie_instructions.txt`
2. Re-run `Demo_Setup.ipynb`

---

## App Configuration and Customization

Please see the [bundle/src/app/README.md](../bundle/src/app/README.md) for detailed configuration and customization options for the application.

---

## Additional Resources

- [Databricks Asset Bundles Documentation](https://docs.databricks.com/en/dev-tools/bundles/index.html)
- [Databricks CLI Reference](https://docs.databricks.com/en/dev-tools/cli/index.html)
- [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Spark Declarative Pipelines](https://docs.databricks.com/en/delta-live-tables/index.html)
- [Databricks Apps](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)

