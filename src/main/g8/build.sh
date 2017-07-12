#!/usr/bin/env bash
set -e

# Read the config
source ./PROJECT_CONFIG

# Build the application. Copy dependency jars
#mvn clean dependency:copy-dependencies

$(aws ecr get-login --region $AWS_REGION)
docker build -t $COMPONENT_NAME .
docker tag $COMPONENT_NAME:latest $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:latest
echo "Built image $COMPONENT_NAME:latest"