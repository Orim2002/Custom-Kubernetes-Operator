# Kubernetes Dynamic Preview Environment Operator

A Custom Kubernetes Operator built with Python and Kopf that automates the provisioning and teardown of ephemeral preview environments for pull requests. 

## Overview
In fast-paced engineering teams, developers need isolated environments to test their PRs before merging. Creating these manually is a bottleneck, and leaving them running indefinitely causes massive cloud waste.

This Operator solves both problems by extending the Kubernetes API with a `PreviewEnvironment` Custom Resource Definition (CRD). It actively listens to cluster events and dynamically provisions a dedicated `Deployment` and `Service` for every new PR. Once the PR is closed and the Custom Resource is deleted, Kubernetes Garbage Collection automatically destroys the underlying infrastructure, enabling true **FinOps** and zero-waste environments.

## Key Features
* **Custom Kubernetes Controller:** Built entirely in Python using the `kopf` framework.
* **Idempotent Reconciliation:** Ensures the actual state of the cluster matches the desired state seamlessly.
* **Automated Cleanup:** Leverages Kubernetes OwnerReferences (`kopf.adopt`) for guaranteed garbage collection of orphaned resources.
* **Least Privilege RBAC:** Runs securely inside the cluster with scoped permissions using dedicated ServiceAccounts and ClusterRoles.

## Tech Stack
* **Language:** Python 3.12
* **Infrastructure:** Kubernetes, Docker
* **Libraries:** `kopf` (Kubernetes Operator Pythonic Framework), `kubernetes-client`

## Quick Start (Local Development)

### 1. Prerequisites
* [Docker](https://docs.docker.com/get-docker/)
* [kind](https://kind.sigs.k8s.io/) (Kubernetes IN Docker)
* `kubectl`

### 2. Cluster Setup
Create a local cluster:
```bash
kind create cluster --name operator-dev
```

### 3. Build and load the operator
Build the Docker image and load it directly into the `kind` cluster:
```bash
docker build -t custom-operator:v1 .
kind load docker-image custom-operator:v1 --name operator-dev
```

### 4. Deploy the operator
Apply the CRD and the Operator manifests (RBAC + Deployment):
```bash
kubectl apply -f crd.yaml
kubectl apply -f operator-deploy.yaml
```
Verify the Operator is running:
```bash
kubectl get pods -l app=custom-operator
```

### 5. Create all the CR objects
Create all the CR objects based on `cr.yaml`
```bash
kubectl apply -f cr.yaml
kubectl get pods,svc
```

## Architecture

### 1. Event
CI/CD pipeline creates a `PreviewEnvironment` object in the cluster when a PR is opened.

### 2. Watch
The Custom Operator detects the `create` event via the Kubernetes API.

### 3. Reconcile
The Operator dynamically generates a `Deployment` and a `ClusterIP Service`, injecting OwnerReferences.

### 4. Destroy
When PR is merged/closed, the CI pipeline deletes the `PreviewEnvironment` object, triggering native Kubernetes cascade deletion.