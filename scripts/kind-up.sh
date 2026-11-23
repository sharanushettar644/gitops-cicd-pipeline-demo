#!/usr/bin/env bash
# Spin up the whole GitOps setup on a local kind cluster:
# kind cluster -> Argo CD -> root app -> staging + prod apps deployed from Git.
set -euo pipefail

CLUSTER=${CLUSTER:-gitops-demo}
ARGOCD_VERSION=${ARGOCD_VERSION:-stable}

for bin in kind kubectl; do
  command -v "$bin" >/dev/null || { echo "Missing $bin - install it first."; exit 1; }
done

if ! kind get clusters | grep -qx "$CLUSTER"; then
  echo ">> Creating kind cluster '$CLUSTER'"
  kind create cluster --name "$CLUSTER" --wait 120s
fi

echo ">> Installing Argo CD ($ARGOCD_VERSION)"
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side --force-conflicts \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=300s

echo ">> Bootstrapping the root application (app of apps)"
kubectl apply -f "$(dirname "$0")/../argocd/root-app.yaml"

PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)
cat <<MSG

Done. Argo CD is syncing staging and prod from Git.

  Argo CD UI : kubectl -n argocd port-forward svc/argocd-server 8443:443
               then open https://localhost:8443  (user: admin, password: ${PASSWORD})
  Staging API: kubectl -n sample-api-staging port-forward svc/sample-api 8080:80
               then curl http://localhost:8080/
MSG
