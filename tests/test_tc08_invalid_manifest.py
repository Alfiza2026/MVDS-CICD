"""TC08 - Deploy with an invalid Kubernetes manifest."""

import yaml
import os
import tempfile


def test_invalid_manifest_fails_validation():
    invalid_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-deployment
  namespace: mvds
spec:
  replicas: one
  selector:
    matchLabels:
      app: broken
  template:
    metadata:
      labels:
        app: broken
    spec:
      containers:
      - name: broken
        image:
        ports:
        - containerPort: not-a-number
"""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp.write(invalid_yaml)
    tmp.close()

    with open(tmp.name) as f:
        docs = list(yaml.safe_load_all(f))

    os.unlink(tmp.name)

    spec = docs[0]["spec"]
    container = spec["template"]["spec"]["containers"][0]

    assert not isinstance(spec["replicas"], int)
    assert container["image"] is None
    assert not isinstance(container["ports"][0]["containerPort"], int)