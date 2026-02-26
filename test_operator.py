import pytest
from unittest.mock import patch, MagicMock
import kopf

import custom_operator

@patch('custom_operator.client.AppsV1Api')
def test_create_deployment(mock_apps_v1):
    mock_api_instance = mock_apps_v1.return_value
    deployment_name = "pr-142-app"
    image = "orim2002/my-app"
    tag = "v2.1"
    namespace = "preview-pr-142"
    custom_operator.create_deployment(deployment_name, image, tag, namespace)
    mock_api_instance.create_namespaced_deployment.assert_called_once()
    args, kwargs = mock_api_instance.create_namespaced_deployment.call_args
    assert kwargs['namespace'] == "preview-pr-142"
    created_deployment = kwargs['body']
    assert created_deployment.metadata.name == "pr-142-app"
    container = created_deployment.spec.template.spec.containers[0]
    assert container.image == "orim2002/my-app:v2.1"
    assert container.liveness_probe is not None
    assert container.readiness_probe.http_get.path == "/"

@patch('custom_operator.client.CoreV1Api')
def test_create_service(mock_core_v1):
    mock_api_instance = mock_core_v1.return_value
    custom_operator.create_service("pr-142-svc", "pr-142-app", "preview-pr-142")
    mock_api_instance.create_namespaced_service.assert_called_once()
    _, kwargs = mock_api_instance.create_namespaced_service.call_args
    created_service = kwargs['body']
    assert created_service.metadata.name == "pr-142-svc"
    assert created_service.spec.selector["app"] == "pr-142-app"
    assert created_service.spec.ports[0].port == 80

@patch('custom_operator.client.NetworkingV1Api')
def test_create_ingress(mock_networking_v1):
    mock_api_instance = mock_networking_v1.return_value
    custom_operator.create_ingress("pr-142-ingress", "pr-142.preview.orimatest.com", "pr-142-svc", "preview-pr-142")
    mock_api_instance.create_namespaced_ingress.assert_called_once()
    _, kwargs = mock_api_instance.create_namespaced_ingress.call_args
    assert kwargs['namespace'] == "preview-pr-142"
    ingress = kwargs['body']
    assert ingress.metadata.name == "pr-142-ingress"
    assert ingress.metadata.annotations["cert-manager.io/cluster-issuer"] == "selfsigned-issuer"
    assert ingress.spec.ingress_class_name == "nginx"
    assert ingress.spec.tls[0].hosts[0] == "pr-142.preview.orimatest.com"
    assert ingress.spec.rules[0].host == "pr-142.preview.orimatest.com"
    assert ingress.spec.rules[0].http.paths[0].backend.service.name == "pr-142-svc"

@patch('custom_operator.client.CoreV1Api')
@patch('custom_operator.create_ingress')
@patch('custom_operator.create_service')
@patch('custom_operator.create_deployment')
def test_create_fn_success(mock_create_deployment, mock_create_service, mock_create_ingress, mock_core_v1):
    spec = {'pr_number': 142, 'branch_name': 'feature-x', 'image': 'orim2002/my-app', 'image_tag': 'v2.1'}
    result = custom_operator.create_fn(spec=spec, name='test', namespace='preview-envs', logger=MagicMock())
    mock_create_deployment.assert_called_once_with("pr-142-app", "orim2002/my-app", "v2.1", "preview-pr-142")
    mock_create_service.assert_called_once_with("pr-142-svc", "pr-142-app", "preview-pr-142")
    mock_create_ingress.assert_called_once_with("pr-142-ingress", "pr-142.preview.orimatest.com", "pr-142-svc", "preview-pr-142")
    assert result['status'] == 'Environment Created'
    assert result['url'] == 'https://pr-142.preview.orimatest.com'
    assert result['namespace'] == 'preview-pr-142'

def test_create_fn_missing_fields():
    spec = {'pr_number': 142, 'branch_name': 'feature-x'}  # missing image and image_tag
    with pytest.raises(kopf.PermanentError):
        custom_operator.create_fn(spec=spec, name='test', namespace='preview-envs', logger=MagicMock())

@patch('custom_operator.client.AppsV1Api')
def test_update_fn(mock_apps_v1):
    mock_api_instance = mock_apps_v1.return_value
    spec = {'pr_number': 142, 'image': 'orim2002/my-app', 'image_tag': 'v2.2'}
    custom_operator.update_fn(spec=spec, name='test', namespace='preview-envs', logger=MagicMock())
    mock_api_instance.patch_namespaced_deployment.assert_called_once()
    _, kwargs = mock_api_instance.patch_namespaced_deployment.call_args
    assert kwargs['name'] == "pr-142-app"
    assert kwargs['namespace'] == "preview-pr-142"
    assert kwargs['body']['spec']['template']['spec']['containers'][0]['image'] == "orim2002/my-app:v2.2"

def test_update_fn_missing_fields():
    spec = {'pr_number': 142}  # missing image and image_tag
    with pytest.raises(kopf.PermanentError):
        custom_operator.update_fn(spec=spec, name='test', namespace='preview-envs', logger=MagicMock())

@patch('custom_operator.client.CoreV1Api')
def test_delete_fn_decrements_gauge(mock_core_v1):
    spec = {'pr_number': 142}
    before = custom_operator.ACTIVE_ENVIRONMENTS._value.get()
    custom_operator.delete_fn(spec=spec, name='test', namespace='preview-envs', logger=MagicMock())
    after = custom_operator.ACTIVE_ENVIRONMENTS._value.get()
    assert after == before - 1
    mock_core_v1.return_value.delete_namespace.assert_called_once_with("preview-pr-142")
