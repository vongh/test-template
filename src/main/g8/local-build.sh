#!/usr/bin/env bash
set -e

# Read the config
source ./PROJECT_CONFIG

# Build the application. Copy dependency jars
#mvn clean dependency:copy-dependencies

docker build -f DockerfileLocal -t $COMPONENT_NAME .
echo "Built image $COMPONENT_NAME:latest"