# Google Cloud deployment runbook

This runbook describes the live deployment in the existing `moesautomationweekly` project. **Repeating or changing it can create billable resources.** Review [costs.md](costs.md) before changing capacity. The initial deployment was approved and completed on 2026-11-14 local time.

## Preflight

Use an authenticated Google Cloud CLI account with the required project, IAM, Cloud SQL, Artifact Registry, Secret Manager, Cloud Build, and Cloud Run permissions. Existing Cloud Run services and the existing SQL instance are outside this Terraform state. The required APIs are already enabled in the project. Verify the current account, project, and Terraform plan before applying.

```bash
gcloud auth list
gcloud config set project moesautomationweekly
export TF_VAR_ncbi_contact_email="$(git config user.email)"
cd infrastructure/terraform
terraform init
terraform validate
terraform plan -var project_id=moesautomationweekly -var deploy_app=true -var image=us-central1-docker.pkg.dev/moesautomationweekly/neuromesh/observatory@sha256:b24c5e2ab85a11a92f4b01b62335f3cef9d7b22fe22651ca97dc60d6d299bba4 -var enable_adk=true -var model_id=gemini-3.5-flash-lite -var model_location=global -var enable_cloud_tts=true
```

An empty state originally showed 14 additions and zero changes or deletions. The live state now includes an additional repository-scoped Cloud Build writer grant. Release 0.3.1 used a saved plan with **0 additions, 1 in-place Cloud Run image change, and 0 deletions**. The SQL instance is deletion protected and explicitly uses Cloud SQL Enterprise edition, required for `db-f1-micro` on PostgreSQL 16. Store Terraform state privately; it contains generated database and operator secrets as well as the NCBI contact email. The local state and backup files are ignored by Git and restricted to the owner. Before repeated team use, migrate state to a private encrypted backend with limited access.

## Stage one: durable infrastructure

The initial deployment ran this once, after cost approval and a project budget alert were in place. Do not rerun it against the live state with `deploy_app=false`, because that would plan to remove Cloud Run:

```bash
terraform apply -var project_id=moesautomationweekly -var deploy_app=false
```

This creates a dedicated database, repository, service account, Secret Manager entries, and narrow IAM grants. It does not start Cloud Run or enable ADK/TTS.

## Stage two: image and service

From the repository root, use the repository URI from Terraform output. Build the multi-stage Dockerfile with Cloud Build, then use the pushed digest for Terraform deployment:

```bash
IMAGE=us-central1-docker.pkg.dev/moesautomationweekly/neuromesh/observatory:0.3.1
gcloud builds submit --project moesautomationweekly --config cloudbuild.yaml --substitutions=_IMAGE=$IMAGE .
cd infrastructure/terraform
terraform plan -var project_id=moesautomationweekly -var deploy_app=true -var image=IMAGE_DIGEST_URI -var enable_adk=true -var model_id=gemini-3.5-flash-lite -var model_location=global -var enable_cloud_tts=true
terraform apply -var project_id=moesautomationweekly -var deploy_app=true -var image=IMAGE_DIGEST_URI -var enable_adk=true -var model_id=gemini-3.5-flash-lite -var model_location=global -var enable_cloud_tts=true
terraform output -raw app_url
```

Replace `IMAGE_DIGEST_URI` with the full Artifact Registry path ending in `@sha256:...` from the successful build output.

Cloud Run is publicly reachable through `invoker_iam_disabled=true`, Google's supported approach when domain-restricted sharing blocks an `allUsers` IAM grant. Visitors can explore indexed records, but all POST routes that investigate, synchronize sources, or synthesize speech require Admin authorization. The UI offers an **Admin** sign-in button and keeps the token in browser memory for that tab. Copy it privately with `terraform output -raw operator_token | pbcopy` and paste it into the Admin form. Indexed Admin questions do not call a model unless the separate Gemini switch is on. Do not put the token in URLs, Git, chats, screenshots, or shared logs.

On 2026-11-16, operator tokens displayed in a conversation were rotated through Terraform. The previous versions were destroyed, and Cloud Run pins the current version. The configuration creates a new version before destroying the old one and updates Cloud Run when the version changes. A public cited answer and operator-only authorization passed after rotation. Never paste the token into a chat; copy it directly to the clipboard from a private terminal when needed.

The initial Cloud SQL database contained the labeled visual demonstration layer. The 0.3.0 application hides those rows from research views and analytics. `scripts/sync_cloud_scholarly.py --limit 5` successfully synchronized OpenAlex, arXiv, and PubMed into the existing database. The script reads the Terraform operator token privately and never prints it. The NCBI contact email is passed through a sensitive Terraform variable from local Git configuration, never committed to Git. The [live Observatory](https://neuromesh-observatory-wwtovkiwnq-uc.a.run.app/) reported 47 public records, 15 normalized scholarly works, 171 visible entities, and 159 evidenced relationships after the sync. Repeated syncs upsert records by stable source ID.

## Optional paid model and voice

The current deployment sets `enable_adk=true`, `model_id=gemini-3.5-flash-lite`, `model_location=global`, and `enable_cloud_tts=true`. The model identifier and endpoint were checked against current Google documentation; verify availability again before changing them. The runtime service account has `roles/aiplatform.user`, and the selected voice is `en-US-Standard-J`, a lower-cost male Standard voice. Both provider endpoints are restricted to operator requests with persistent daily usage reservations. A bounded deployed test passed for both providers, including audio-reactive browser playback and interruption.

The browser microphone path uses browser speech recognition; Cloud TTS supplies generated playback audio and jaw amplitude. The app retries a premature recognition disconnect twice and reports the browser's error code and device guidance. Browser speech recognition may still fail if Chrome cannot access a working input device or its recognition service. Verify the voice path on the deployed URL with a physical microphone before describing it as production validated.

## Operational checks

Check `/api/health`, `/api/status`, `/api/analytics`, and `/api/clusters`. Review Cloud Run revisions, Cloud SQL health, Cloud Logging errors, and daily billed usage. The app is limited to one Cloud Run instance but Cloud SQL runs continuously. Budget alerts are notifications, not hard service caps. Keep the operator token private; rotate its Secret Manager version if disclosed.
