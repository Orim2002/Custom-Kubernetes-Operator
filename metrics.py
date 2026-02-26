from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging

logger = logging.getLogger(__name__)

# How many full preview environments were created successfully
ENVIRONMENTS_CREATED = Counter(
    "preview_environments_created_total",
    "Total preview environments successfully created",
    ["branch_name"]
)

# How many failed (broken down by which step failed)
ENVIRONMENTS_FAILED = Counter(
    "preview_environments_failed_total",
    "Total preview environment creation failures",
    ["step"]  # "deployment", "service", or "ingress"
)

# How many are currently alive
ACTIVE_ENVIRONMENTS = Gauge(
    "preview_environments_active",
    "Currently active preview environments"
)

# Tracks how many times each PR has triggered reconciliation
RECONCILE_COUNT = Counter(
    "preview_environments_reconcile_total",
    "Total reconciliation events per PR",
    ["pr_number"]
)

# How long the full create_fn takes end to end
CREATION_DURATION = Histogram(
    "preview_environment_creation_duration_seconds",
    "Time to fully provision a preview environment",
    buckets=[1, 2, 5, 10, 20, 30, 60, float("inf")]
)

# Pre-initialize labels so metrics exist from startup even before any events occur
ENVIRONMENTS_CREATED.labels(branch_name="unknown")
ENVIRONMENTS_FAILED.labels(step="deployment")
ENVIRONMENTS_FAILED.labels(step="service")
ENVIRONMENTS_FAILED.labels(step="ingress")
ENVIRONMENTS_FAILED.labels(step="update")
RECONCILE_COUNT.labels(pr_number="unknown")

def start_metrics_server(port: int = 8000):
    start_http_server(port)
    logger.info(f"Metrics server started on :{port}")