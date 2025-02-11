#!/bin/bash

# Configuration
PROJECT_ID="thekey-dev"
REGION="europe-west2"        # London region
ZONE="europe-west2-a"        # London zone
SERVICE_NAME="sarah-testing"
BUCKET_NAME="sarah-testing-db-${PROJECT_ID}"  # Make bucket name unique to project

echo "Deploying Sarah Testing Application to London region..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION} (London)"

# Ensure we're using the correct project
gcloud config set project ${PROJECT_ID}

# Create Cloud Storage bucket if it doesn't exist
echo "Setting up Cloud Storage bucket..."
gsutil mb -l ${REGION} gs://${BUCKET_NAME} || true

# Build and push the container
echo "Building and pushing container..."
gcloud builds submit \
  --tag europe-west2-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/app \
  --region=${REGION}

# Create service account if it doesn't exist
echo "Setting up service account..."
gcloud iam service-accounts create ${SERVICE_NAME}-sa \
  --display-name="Service Account for ${SERVICE_NAME}" || true

# Grant necessary permissions
echo "Configuring IAM permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectCreator"

# Deploy to Cloud Run
echo "Deploying to Cloud Run in London..."
gcloud run deploy ${SERVICE_NAME} \
  --image europe-west2-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/app \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --set-env-vars="BUCKET_NAME=${BUCKET_NAME},DB_PATH=/app/data/sarah_testing.db,CLOUD_RUN_SERVICE=true" \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --min-instances=1 \
  --max-instances=10 \
  --service-account="${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')

echo "✅ Deployment complete!"
echo "🌍 Your application is available at: ${SERVICE_URL}"
echo "📊 Monitor your application at: https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics?project=${PROJECT_ID}" 