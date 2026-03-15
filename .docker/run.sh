#! /bin/bash

# name of image
IMAGE=lab-website-renderer:latest

# name of running container
CONTAINER=lab-website-renderer

# choose platform flag
PLATFORM=""

# default vars
DOCKER_RUN="docker run"
WORKING_DIR=$(pwd)
ENV_ARGS=""
ENV_FILE=".docker/.env"

# load optional env vars from file if present
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "${ENV_FILE}"
    set +a
fi

# pass through optional api keys from host environment
if [[ -n "${GOOGLE_SCHOLAR_API_KEY}" ]]; then
    ENV_ARGS="${ENV_ARGS} --env GOOGLE_SCHOLAR_API_KEY"
fi

# fix windows faux linux shells/tools
if [[ $OSTYPE == msys* ]] || [[ $OSTYPE == cygwin* ]]; then
    DOCKER_RUN="winpty docker run"
    WORKING_DIR=$(cmd //c cd)
fi

# remove stale container with same name to avoid startup conflicts
docker rm --force ${CONTAINER} > /dev/null 2>&1 || true

# build docker image
docker build ${PLATFORM} \
    --tag ${IMAGE} \
    --file ./.docker/Dockerfile . && \

# run built docker image
${DOCKER_RUN} ${PLATFORM} \
    --name ${CONTAINER} \
    --init \
    --rm \
    --interactive \
    --tty \
    --publish 4000:4000 \
    --publish 35729:35729 \
    --volume "${WORKING_DIR}:/usr/src/app" \
    ${ENV_ARGS} \
    ${IMAGE} "$@"
