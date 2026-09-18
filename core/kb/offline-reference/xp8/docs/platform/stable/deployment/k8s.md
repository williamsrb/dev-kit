<!-- src:https://developer.enonic.com/docs/platform/stable/deployment/k8s generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/deployment/k8s.md

# Kubernetes deployments

This section describes how to run Enonic XP on a Kubernetes cluster.

## Introduction

## XP operator

Running Enonic XP on Kubernetes is a great way to achieve scalability, high availability and ease of management. Kubernetes deployments are generally based on the [XP Docker image](docs/platform/stable/deployment/docker.md).

The recommended way to deploy XP on Kubernetes is to use the XP Operator, which provides a Kubernetes-native way to manage XP instances.

> **Note:** For detailed documentation, see the [XP Operator documentation](https://developer.enonic.com/docs/xp-operator).

Benefits of using the XP Operator include:

- **Lifecycle management** - handles the deployment, scaling, configuration and management of XP instances on the K8S cluster.

- **Custom resources** - working with the operator involves creating custom resources that define the desired state of your XP instance, and the operator will take care of the rest.

- **Ingress integration** - natively integrated with K8S ingresses, making it easy to expose your XP instance to the outside world.
