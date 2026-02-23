import pytest
from unittest.mock import patch, MagicMock

import custom_operator

@patch('custom_operator.client.AppsV1Api')
@patch('custom_operator.kopf.adopt')
def test_create_deployment(mock_adopt, mock_apps_v1):
    mock_api_instance = mock_apps_v1.return_value
    deployment_name = "pr-142-app"
    image = "orim2002/my-app"
    tag = "v2.1"
    namespace = "preview-envs"
    custom_operator.create_deployment(deployment_name, image, tag, namespace)
    mock_api_instance.create_namespaced_deployment.assert_called_once()
    args, kwargs = mock_api_instance.create_namespaced_deployment.call_args
    assert kwargs['namespace'] == "preview-envs"
    created_deployment = kwargs['body']
    assert created_deployment.metadata.name == "pr-142-app"
    container = created_deployment.spec.template.spec.containers[0]
    assert container.image == "orim2002/my-app:v2.1"
    assert container.liveness_probe is not None
    assert container.readiness_probe.http_get.path == "/"
    mock_adopt.assert_called_once_with(created_deployment)

@patch('custom_operator.client.CoreV1Api')
@patch('custom_operator.kopf.adopt')
def test_create_service(mock_adopt, mock_core_v1):
    mock_api_instance = mock_core_v1.return_value
    custom_operator.create_service("pr-142-svc", "pr-142-app", "preview-envs")
    mock_api_instance.create_namespaced_service.assert_called_once()
    _, kwargs = mock_api_instance.create_namespaced_service.call_args
    created_service = kwargs['body']
    assert created_service.metadata.name == "pr-142-svc"
    assert created_service.spec.selector["app"] == "pr-142-app"
    assert created_service.spec.ports[0].port == 80