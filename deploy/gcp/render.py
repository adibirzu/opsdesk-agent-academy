#!/usr/bin/env python3
"""Render an authenticated Cloud Run Service manifest; never applies it."""
import argparse
import json
import re
import sys


_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_REGION = re.compile(r"^[a-z]+-[a-z]+[0-9]$")
_SERVICE = re.compile(r"^[a-z][a-z0-9-]{0,48}[a-z0-9]$")
_ACCOUNT = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$")
_IMAGE = re.compile(r"^([a-z0-9-]+-docker\.pkg\.dev)/([a-z][a-z0-9-]{4,28}[a-z0-9])/([a-z][a-z0-9_-]{0,62})/([a-z0-9][a-z0-9._/-]*)@sha256:([a-f0-9]{64})$")


def render_service(*, project, region, service, service_account, image, bundle_secret, bundle_version):
    if not _ID.fullmatch(project) or not _REGION.fullmatch(region) or not _SERVICE.fullmatch(service):
        raise ValueError("Invalid project, region, or service identifier")
    if not _ACCOUNT.fullmatch(service_account) or service_account.rsplit("@", 1)[1].split(".")[0] != project:
        raise ValueError("Service account must belong to the selected project")
    match = _IMAGE.fullmatch(image)
    if not match or match.group(2) != project or not match.group(1).startswith(region + "-"):
        raise ValueError("Image must be an immutable Artifact Registry digest in the selected project and region")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,255}", bundle_secret) or not re.fullmatch(r"[1-9][0-9]*", str(bundle_version)):
        raise ValueError("Secret name and numeric version are required")
    return {
        "apiVersion": "serving.knative.dev/v1", "kind": "Service",
        "metadata": {"name": service, "namespace": project, "labels": {"cloud.googleapis.com/location": region}},
        "spec": {"template": {"metadata": {"annotations": {
            "autoscaling.knative.dev/minScale": "0", "autoscaling.knative.dev/maxScale": "1",
            "run.googleapis.com/execution-environment": "gen2",
        }}, "spec": {"serviceAccountName": service_account, "containerConcurrency": 1,
            "timeoutSeconds": 240, "containers": [{"image": image,
                "command": ["python", "-m", "agent_workshop.gcp_runtime"],
                "ports": [{"name": "http1", "containerPort": 8080}],
                "resources": {"limits": {"cpu": "1", "memory": "512Mi"}},
                "env": [{"name": "WORKSHOP_GCP_BUNDLE_FILE", "value": "/secrets/workshop/bundle.json"}],
                "volumeMounts": [{"name": "runtime-bundle", "mountPath": "/secrets/workshop", "readOnly": True}],
                "startupProbe": {"httpGet": {"path": "/ready", "port": 8080}, "periodSeconds": 10, "timeoutSeconds": 2, "failureThreshold": 12},
            }], "volumes": [{"name": "runtime-bundle", "secret": {"secretName": bundle_secret,
                "items": [{"key": str(bundle_version), "path": "bundle.json", "mode": 292}]}}]}},
            "traffic": [{"percent": 100, "latestRevision": True}]},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--service-account", required=True)
    parser.add_argument("--image", required=True, help="Artifact Registry image pinned by sha256 digest")
    parser.add_argument("--bundle-secret", required=True)
    parser.add_argument("--bundle-version", required=True, help="Numeric Secret Manager version")
    args = parser.parse_args(argv)
    try:
        result = render_service(**vars(args))
    except ValueError as exc:
        parser.error(str(exc))
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
