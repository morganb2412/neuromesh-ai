# Google Cloud deployment runbook

This runbook is prepared for the existing `moesautomationweekly` project. **Applying it creates billable resources.** Review [costs.md](costs.md) and obtain the project's cost approval first. The current build has only inspected the project and run a read-only Terraform plan.

## Preflight

Use an authenticated Google Cloud CLI account with the required project, IAM, Cloud SQL, Artifact Registry, Secret Manager, Cloud Build, and Cloud Run permissions. Existing Cloud Run services and the existing SQL instance are outside this Terraform state. The required APIs are already enabled in the project. Verify the current account, project, and Terraform plan before applying.

```bash
gcloud auth list
gcloud config set project moesautomationweekly
cd infrastructure/terraform
terraform init
terraform validate
terraform plan -var project_id=moesautomationweekly -var deploy_app=false
```

Stage one should show 14 additions and zero changes or deletions from an empty state. The SQL instance is deletion protected. Store Terraform state privately; it contains generated database and operator secrets. Before repeated team use, migrate state to a private encrypted backend with limited access.

## Stage one: durable infrastructure

After cost approval and a project budget alert are in place:

```bash
terraform apply -var project_id=moesautomationweekly -var deploy_app=false
```

This creates a dedicated database, repository, service account, Secret Manager entries, and narrow IAM grants. It does not start Cloud Run or enable ADK/TTS.

## Stage two: image and service

From the repository root, use the repository URI from Terraform output. Build the multi-stage Dockerfile with Cloud Build and push an immutable image tag:

```bash
IMAGE=us-central1-docker.pkg.dev/moesautomationweekly/neuromesh/observatory:0.2.0
gcloud builds submit --project moesautomationweekly --config cloudbuild.yaml --substitutions _IMAGE=$IMAGE .
cd infrastructure/terraform
terraform plan -var project_id=moesautomationweekly -var deploy_app=true -var image=$IMAGE
terraform apply -var project_id=moesautomationweekly -var deploy_app=true -var image=$IMAGE
terraform output -raw app_url
```

Cloud Run is public so visitors can explore indexed records and submit bounded local investigations. Model calls, source synchronization, and Cloud speech require the operator token. Retrieve that token in a private terminal using `terraform output -raw operator_token` and enter it in the app settings. The token is held in browser memory for that tab. Do not put it in URLs, Git, screenshots, or shared logs.

The initial Cloud SQL database is empty except for the labeled visual demonstration layer. In the app settings, run the bounded four-source sync as operator, then verify the source counts, evidence links, Research records, and Analytics fingerprint. Repeated syncs upsert records by stable source ID.

## Optional paid model and voice

After a separate provider usage review, set `enable_adk=true`, `model_id=gemini-3.5-flash-lite`, and `model_location=global` in a Terraform plan. The model identifier and endpoint were checked against current Google documentation; verify availability again before applying. The runtime service account receives `roles/aiplatform.user` only when ADK is enabled. Cloud TTS may be enabled with `enable_cloud_tts=true`. Both are disabled by default and are restricted to operator requests with persistent daily usage reservations.

The browser microphone path uses browser speech recognition; Cloud TTS supplies generated playback audio and jaw amplitude. Verify the voice path on the deployed URL in a supported browser before describing it as production validated.

## Operational checks

Check `/api/health`, `/api/status`, `/api/analytics`, and `/api/clusters`. Review Cloud Run revisions, Cloud SQL health, Cloud Logging errors, and daily billed usage. The app is limited to one Cloud Run instance but Cloud SQL runs continuously. Budget alerts are notifications, not hard service caps. Keep the operator token private; rotate its Secret Manager version if disclosed.
