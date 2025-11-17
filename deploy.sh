#!/bin/bash

set -e

########################################
# CONFIGURATION
########################################
APP_NAME="voice-todo-backend"
RESOURCE_GROUP="test-rg"
ENV_NAME="test-env"
ACR_NAME="demoacr123"                           # ACR name only
REGISTRY="${ACR_NAME}.azurecr.io"               # Full registry URL

IMAGE_NAME="shram_demo"
IMAGE_TAG="v1"
IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

########################################
# LOGIN
########################################
echo "🔵 Logging into Azure..."
az login --only-show-errors

echo "🔵 Logging into Azure Container Registry locally..."
az acr login --name $ACR_NAME


########################################
# DOCKER BUILDX CREATE (only first time)
########################################
if ! docker buildx inspect builder > /dev/null 2>&1; then
    echo "🛠 Creating Docker buildx builder..."
    docker buildx create --use --name builder
fi


########################################
# BUILD + PUSH (linux/amd64 REQUIRED)
########################################
echo "🔵 Building image for linux/amd64..."
docker buildx build \
  --platform linux/amd64 \
  -t $IMAGE \
  --push .


########################################
# DEPLOY / UPDATE CONTAINER APP
########################################
echo "🔵 Checking if Container App exists..."
EXISTS=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "name" -o tsv 2>/dev/null || echo "")

if [ -z "$EXISTS" ]; then
    echo "🟡 Creating new Container App with system-managed identity..."

    az containerapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $ENV_NAME \
        --image $IMAGE \
        --target-port 8000 \
        --ingress external \
        --registry-server $REGISTRY \
        --system-assigned

else
    echo "🟢 Updating existing Container App with latest image..."
    az containerapp update \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $IMAGE \
        --registry-server $REGISTRY
fi


########################################
# ASSIGN MANAGED IDENTITY PERMISSION
########################################
echo "🔵 Fetching Managed Identity principal ID..."
MI_PRINCIPAL_ID=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query identity.principalId -o tsv)

SUB_ID=$(az account show --query id -o tsv)

echo "🔵 Assigning AcrPull role to Container App identity..."
az role assignment create \
  --assignee $MI_PRINCIPAL_ID \
  --scope "/subscriptions/$SUB_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME" \
  --role AcrPull \
  --only-show-errors || echo "Role already exists, skipping."


########################################
# FETCH PUBLIC URL
########################################
echo "🔵 Fetching Container App FQDN..."
FQDN=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

echo ""
echo "🟢 Deployment Complete!"
echo "🌍 Public URL:"
echo "https://$FQDN"
