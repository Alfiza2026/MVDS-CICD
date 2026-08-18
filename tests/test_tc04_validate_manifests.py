"""TC04 - Validate Kubernetes manifests before deployment."""

import yaml
import os

K8S_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "k8s"))


def test_manifests_are_valid_yaml():
    for component in ["provider", "consumer"]:
        path = os.path.join(K8S_DIR, component, "deployment.yaml")
        with open(path) as f:
            docs = list(yaml.safe_load_all(f))

        assert len(docs) == 2
        assert docs[0]["kind"] == "Deployment"
        assert docs[1]["kind"] == "Service"
