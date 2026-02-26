# Custom Kubernetes Operator

A Python-based Kubernetes operator built with [kopf](https://kopf.readthedocs.io/) that manages the full lifecycle of dynamic preview environments. It watches for `PreviewEnvironment` custom resources and automatically provisions or tears down isolated Kubernetes environments per Pull Request.

---

## How It Works

When a `PreviewEnvironment` CR is applied to the cluster, the operator:

1. Creates a dedicated namespace `preview-pr-{N}` (full isolation per PR)
2. Deploys the application as a Kubernetes `Deployment` with liveness/readiness probes and resource limits
3. Creates a `ClusterIP Service` to route internal traffic
4. Creates an NGINX `Ingress` with TLS via cert-manager → live at `https://pr-{N}.preview.orimatest.com`

When the CR is deleted, the operator deletes the entire namespace — cascading all resources automatically.

---

## Files

| File | Description |
|------|-------------|
| `custom_operator.py` | Main operator logic — all kopf event handlers |
| `metrics.py` | Prometheus metrics definitions and HTTP server |
| `test_operator.py` | Unit tests (pytest + unittest.mock) |
| `Dockerfile` | Container image definition |
| `requirements.txt` | Python dependencies |

---

## Operator Handlers

| Handler | Trigger | What it does |
|---------|---------|--------------|
| `startup_fn` | Operator start | Starts Prometheus metrics HTTP server on port 8000 |
| `create_fn` | CR created | Creates namespace, deployment, service, ingress |
| `update_fn` | CR spec changed | Patches deployment with new image tag (rolling update) |
| `delete_fn` | CR deleted | Deletes the PR namespace, cascading all resources |
| `resume_fn` | Operator restart | Re-syncs in-memory gauge state without recreating resources |
| `ttl_check_fn` | Every 60s (timer) | Auto-deletes CR if `ttl_seconds` has elapsed since creation |

---

## Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `preview_environments_created_total` | Counter | `branch_name` | Total successful creates |
| `preview_environments_failed_total` | Counter | `step` | Failures by step (deployment/service/ingress/update) |
| `preview_environments_active` | Gauge | — | Currently live environments |
| `preview_environments_reconcile_total` | Counter | `pr_number` | Reconciliation events per PR |
| `preview_environment_creation_duration_seconds` | Histogram | — | End-to-end provisioning time |
| `preview_environments_expired_total` | Counter | — | Environments auto-deleted by TTL |

---

## Running Locally

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run (requires a valid kubeconfig)
kopf run custom_operator.py --all-namespaces
```

## Running Tests

```bash
pytest test_operator.py -v
```

---

## Building the Docker Image

```bash
docker build -t youruser/custom-operator:latest .
docker push youruser/custom-operator:latest
```

---

## Example Custom Resource

```yaml
apiVersion: devops.orima.com/v1
kind: PreviewEnvironment
metadata:
  name: pr-42-env
  namespace: preview-environments
spec:
  pr_number: 42
  branch_name: "feature/my-feature"
  image: "youruser/my-app"
  image_tag: "a3f9c2d"
  ttl_seconds: 3600  # optional: auto-delete after 1 hour
```

---

## Key Design Decisions

**Namespace isolation** — Each PR gets its own namespace (`preview-pr-{N}`). This prevents resource name collisions between PRs and makes cleanup trivial: deleting one namespace cascades all resources inside it, with no need for owner references.

**TTL auto-cleanup** — The `ttl_seconds` field allows environments to self-destruct after a set time, preventing abandoned environments from running indefinitely and wasting cloud resources.

**Fallback on update** — If `update_fn` gets a 404 (deployment was manually deleted), it falls back to a full create rather than failing permanently.

---

## Dependencies

- [kopf](https://github.com/nolar/kopf) — Kubernetes operator framework for Python
- [kubernetes](https://github.com/kubernetes-client/python) — Official Kubernetes Python client
- [prometheus-client](https://github.com/prometheus/client_python) — Prometheus metrics
