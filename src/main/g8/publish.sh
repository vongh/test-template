#!/usr/bin/env bash
set -e
source ./PROJECT_CONFIG
$(aws ecr get-login --region ap-southeast-2)
REV=$(git rev-parse --short HEAD)

docker tag $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:latest $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:$REV

if [ ! -z "$GO_PIPELINE_COUNTER" ]
then
    echo "Tagging revision $REV as version $GO_PIPELINE_COUNTER"
    docker tag $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:$REV $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:$GO_PIPELINE_COUNTER
    docker push $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:$GO_PIPELINE_COUNTER
fi

docker push $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:$REV
docker push $AWS_ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$COMPONENT_NAME:latest