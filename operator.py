import kopf
import logging
from kubernetes import client, config

try:
    config.load_kube_config()
except config.ConfigException:
    config.load_incluster_config()

@kopf.on.create('devops.orima.com', 'v1', 'previewenvironments')
def create_fn(spec, name, namespace, logger, **kwargs):
    pr_number = spec.get('pr_number')
    image_tag = spec.get('image_tag')

    apps_v1 = client.AppsV1Api()
    deployment_name = f"pr-{pr_number}-app"
    service_name = f"pr-{pr_number}-svc"

    container = client.V1Container(
        name="app",
        image=f"nginx:{image_tag}",
        ports=[client.V1ContainerPort(container_port=80)]
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
        logger.error(f"Failed to create deployment: {e}")
        raise e
    
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
        logger.error(f"Failed to create service: {e}")
        raise e
    
    return {'status': 'Environment Created', 'deployment': deployment_name, 'service': service_name}
