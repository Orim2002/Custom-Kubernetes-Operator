import kopf
import logging
import time
from kubernetes import client, config
from prometheus_client import Counter, Gauge, Histogram

preview_envs_created = Counter(
    'preview_environments_created_total',
    'Total number of preview environments successfully created'
)

preview_envs_active = Gauge(
    'preview_environments_active',
    'Number of currently active preview environments'
)

preview_env_errors = Counter(
    'preview_environment_errors_total',
    'Total number of errors during preview environment resource creation',
    ['resource']
)

preview_env_duration = Histogram(
    'preview_environment_creation_duration_seconds',
    'End-to-end time to provision a complete preview environment',
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

logger = logging.getLogger(__name__)

try:
    config.load_kube_config()
except config.ConfigException:
    try: 
        config.load_incluster_config()
    except config.ConfigException:
        logger.warning("Kubernetes config could not be loaded. This is expected during CI/tests.")


def create_deployment(deployment_name, image, tag, namespace):
    apps_v1 = client.AppsV1Api()
    resources = client.V1ResourceRequirements(
        requests={"cpu": "100m", "memory": "128Mi"},
        limits={"cpu": "250m", "memory": "256Mi"},
    )

    health_probe = client.V1Probe(
        http_get=client.V1HTTPGetAction(path="/", port=80),
        initial_delay_seconds=2,
        period_seconds=5,
        timeout_seconds=2,
        failure_threshold=3
    )

    container = client.V1Container(
        name="app",
        image=f"{image}:{tag}",
        ports=[client.V1ContainerPort(container_port=80)],
        resources=resources,
        liveness_probe=health_probe,
        readiness_probe=health_probe
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
        spec=client.V1PodSpec(containers=[container])
    )

    deployment_spec = client.V1DeploymentSpec(
        replicas=1,
        selector=client.V1LabelSelector(match_labels={"app":deployment_name}),
        template=template
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=deployment_spec
    )

    kopf.adopt(deployment)

    try:
        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        logger.info(f"Successfully created Deployment: {deployment_name}")
    except client.exceptions.ApiException as e:
        preview_env_errors.labels(resource='deployment').inc()
        logger.error(f"Failed to create deployment: {e}")
        raise e
    
def create_service(service_name, deployment_name, namespace):
    core_v1 = client.CoreV1Api()
    
    service_spec = client.V1ServiceSpec(
        selector={"app": deployment_name},
        ports=[client.V1ServicePort(port=80, target_port=80)],
        type="ClusterIP"
    )
    
    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=service_name),
        spec=service_spec
    )
    
    kopf.adopt(service)

    try:
        core_v1.create_namespaced_service(namespace=namespace, body=service)
        logger.info(f"Successfully created Serivce: {service_name}")
    except client.exceptions.ApiException as e:
        preview_env_errors.labels(resource='service').inc()
        logger.error(f"Failed to create service: {e}")
        raise e

def create_ingress(ingress_name, ingress_host, service_name, namespace):
    networking_v1 = client.NetworkingV1Api()
    networking_v1 = client.NetworkingV1Api()
    ingress_spec = client.V1IngressSpec(
        rules=[
            client.V1IngressRule(
                host=ingress_host,
                http=client.V1HTTPIngressRuleValue(
                    paths=[
                        client.V1HTTPIngressPath(
                            path="/",
                            path_type="Prefix",
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    name=service_name,
                                    port=client.V1ServiceBackendPort(number=80)
                                )
                            )
                        )
                    ]
                )
            )
        ]
    )
    ingress = client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(name=ingress_name),
        spec=ingress_spec
    )
    kopf.adopt(ingress)
    try:
        networking_v1.create_namespaced_ingress(namespace=namespace, body=ingress)
        logger.info(f"Successfully created Ingress: {ingress_name} for {ingress_host}")
    except client.exceptions.ApiException as e:
        preview_env_errors.labels(resource='ingress').inc()
        logger.error(f"Failed to create ingress: {e}")
        raise e

@kopf.on.create('devops.orima.com', 'v1', 'previewenvironments')
def create_fn(spec, name, namespace, logger, **kwargs):
    pr_number = spec.get('pr_number')
    branch_name = spec.get('branch_name')
    image = spec.get("image")
    tag = spec.get('image_tag')

    deployment_name = f"pr-{pr_number}-app"
    service_name = f"pr-{pr_number}-svc"
    ingress_name = f"pr-{pr_number}-ingress"
    ingress_host = f"pr-{pr_number}.preview.orima.com"

    start = time.time()
    create_deployment(deployment_name, image, tag, namespace)
    create_service(service_name, deployment_name, namespace)
    create_ingress(ingress_name, ingress_host, service_name, namespace)
    preview_env_duration.observe(time.time() - start)
    preview_envs_created.inc()
    preview_envs_active.inc()

    return {
        'status': 'Environment Created',
        'deployment': deployment_name,
        'service': service_name,
        'ingress': ingress_name,
        'url': f"http://{ingress_host}"
    }


@kopf.on.delete('devops.orima.com', 'v1', 'previewenvironments')
def delete_fn(spec, name, namespace, logger, **kwargs):
    pr_number = spec.get('pr_number')
    logger.info(f"Preview environment for PR {pr_number} deleted")
    preview_envs_active.dec()
