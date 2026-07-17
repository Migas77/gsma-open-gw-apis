DOCKER_REGISTRY=ghcr.io/migas77

# help
for arg in "$@"; do
  if [ "$arg" == "--help" ]; then
    echo "Usage: cmd [-d DOCKER_REGISTRY] [--help]"
    exit 0
  fi
done

# get opts
while getopts "d:" opt; do
  case ${opt} in
    d )
        DOCKER_REGISTRY=$OPTARG
      ;;
    \? )
      echo "Invalid option: -$OPTARG" >&2
      echo "Usage: cmd [-d DOCKER_REGISTRY] [--help]"
      exit 1
      ;;
  esac
done

docker build -t $DOCKER_REGISTRY/gateway -f gateway/Dockerfile gateway
docker push $DOCKER_REGISTRY/gateway
docker build -t $DOCKER_REGISTRY/nginx-gateway -f gateway/nginx/Dockerfile.nginx gateway/nginx
docker push $DOCKER_REGISTRY/nginx-gateway

# package and publish the helm chart as an OCI artifact to the same registry
CHART_NAME=$(awk '/^name:/ { print $2; exit }' charts/gateway/Chart.yaml)
CHART_VERSION=$(awk '/^version:/ { print $2; exit }' charts/gateway/Chart.yaml)

helm dependency build charts/gateway
helm package charts/gateway -d /tmp
helm push /tmp/${CHART_NAME}-${CHART_VERSION}.tgz oci://$DOCKER_REGISTRY
rm /tmp/${CHART_NAME}-${CHART_VERSION}.tgz

# how to consume what was just published
printf "\n\n"
echo "Images and chart published to $DOCKER_REGISTRY"
echo ""
echo "Install/upgrade the release with:"
echo "  helm upgrade --install gateway oci://$DOCKER_REGISTRY/$CHART_NAME --version $CHART_VERSION \\"
echo "    --set image.repository=$DOCKER_REGISTRY/gateway \\"
echo "    --set nginx.deployment.image=$DOCKER_REGISTRY/nginx-gateway:latest"


# helm upgrade --install gateway oci://ghcr.io/migas77/gsma-open-gateway --version 0.2.0 \
#     --set image.repository=ghcr.io/migas77/gateway \
#     --set nginx.deployment.image=ghcr.io/migas77/nginx-gateway:latest
