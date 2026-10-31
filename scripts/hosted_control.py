#!/usr/bin/env python3
"""Private OCI SDK post-step for the enterprise hosted application.

This command deliberately keeps all runtime inputs and provider receipts private.
It never prints secret material, prompts, response bodies, or OCI request IDs.
"""
import argparse
import base64
import json
from pathlib import Path
import re
import sys

from orm import private_json, save

MAX_BUNDLE_BYTES = 128 * 1024
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def _output(state, *names):
    outputs = state.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("ORM state outputs are unavailable")
    for name in names:
        value = outputs.get(name)
        if isinstance(value, dict) and "value" in value:
            return value["value"]
    raise ValueError("Required ORM output is unavailable")


def _target(state, receipt):
    region = receipt.get("region")
    tenancy = receipt.get("tenancy_id", receipt.get("tenancy"))
    compartment = None
    for source in (state, receipt):
        if isinstance(source, dict):
            compartment = source.get("compartment_id", source.get("child_compartment_id"))
            if compartment:
                break
    if not compartment:
        compartment = _output(state, "compartment_id", "child_compartment_id")
    if not isinstance(region, str) or not isinstance(tenancy, str):
        raise ValueError("Private receipt target is incomplete")
    return region, tenancy, compartment


def _clients(config, oci):
    kw = {"timeout": (5, 30), "retry_strategy": oci.retry.NoneRetryStrategy()}
    return (
        oci.generative_ai.GenerativeAiClient(config, **kw),
        oci.artifacts.ArtifactsClient(config, **kw),
        oci.vault.VaultsClient(config, **kw),
        oci.vulnerability_scanning.VulnerabilityScanningClient(config, **kw),
    )


def _response_data(response):
    return getattr(response, "data", response)


def _verify_application(client, app_id, compartment):
    # The current SDK calls this get_hosted_application; retain the IAM spelling
    # for provider/mock versions which expose that operation explicitly.
    getter = getattr(client, "get_hosted_application_iam", None)
    if getter is None:
        getter = client.get_hosted_application
    app = _response_data(getter(app_id))
    if getattr(app, "compartment_id", None) != compartment:
        raise ValueError("Hosted application compartment mismatch")
    return app


def _secret(args, state, receipt, clients):
    import oci
    genai, vault = clients[0], clients[2]
    region, tenancy, compartment = _target(state, receipt)
    app_id = _output(state, "hosted_application_id")
    _verify_application(genai, app_id, compartment)
    secret_id = _output(state, "runtime_secret_id")
    vault_id = _output(state, "vault_id")
    key_id = _output(state, "key_id")
    metadata = _response_data(vault.get_secret(secret_id))
    if (getattr(metadata, "compartment_id", None) != compartment or
            getattr(metadata, "vault_id", None) != vault_id or
            getattr(metadata, "key_id", None) != key_id):
        raise ValueError("Runtime secret ownership or Vault key mismatch")
    bundle = private_json(args.bundle)
    if set(bundle) - {"config_toml", "environment", "ca_pem"}:
        raise ValueError("Runtime bundle contains unsupported fields")
    if not isinstance(bundle.get("config_toml"), str) or not isinstance(bundle.get("environment"), dict):
        raise ValueError("Runtime bundle is invalid")
    if "ca_pem" in bundle and not isinstance(bundle["ca_pem"], str):
        raise ValueError("Runtime bundle is invalid")
    raw = json.dumps(bundle, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError("Runtime bundle exceeds 128 KiB")
    content = base64.b64encode(raw).decode("ascii")
    details = oci.vault.models.UpdateSecretDetails(
        secret_content=oci.vault.models.Base64SecretContentDetails(content=content))
    vault.update_secret(secret_id, details)
    print(json.dumps({"secret": "updated", "bytes": len(raw), "target": region}))
    return 0


def _image(clients, compartment, repository_id, repository_name, tag, expected):
    artifacts = clients[1]
    response = artifacts.list_container_images(
        compartment, repository_id=repository_id, version=tag,
        repository_name=repository_name, limit=50)
    items = list(getattr(_response_data(response), "items", []) or [])
    matches = [item for item in items if getattr(item, "version", None) == tag]
    if len(matches) != 1:
        raise ValueError("Expected exactly one matching container image")
    image = matches[0]
    digest = str(getattr(image, "digest", ""))
    if digest.lower() != expected.lower():
        raise ValueError("Container image digest mismatch")
    if getattr(image, "repository_id", repository_id) != repository_id:
        raise ValueError("Container image repository mismatch")
    if getattr(image, "compartment_id", compartment) != compartment:
        raise ValueError("Container image compartment mismatch")
    return image


def _scan(clients, state, compartment, repository_name, tag, image):
    """Bind a completed scan to the selected tag and current registry digest."""
    if len(clients) < 4 or getattr(image, "time_created", None) is None:
        raise ValueError("Scan client and image creation time are required")
    scanner = clients[3]
    target_id = _output(state, "container_scan_target_id")
    target = _response_data(scanner.get_container_scan_target(target_id))
    if getattr(target, "compartment_id", None) != compartment or target.lifecycle_state != "ACTIVE":
        raise ValueError("Container scan target ownership or state mismatch")
    response = _response_data(scanner.list_container_scan_results(
        compartment, repository=repository_name, image=tag, limit=50))
    reports = list(getattr(response, "items", response) or [])
    matches = [report for report in reports if
               getattr(report, "container_scan_target_id", None) == target_id and
               getattr(report, "repository", None) == repository_name and
               getattr(report, "image", None) == tag and
               getattr(report, "time_started", None) is not None and
               getattr(report, "time_finished", None) is not None and
               report.time_started >= image.time_created]
    if not matches:
        raise ValueError("No completed scan for the current image version")
    latest = max(matches, key=lambda report: report.time_finished)
    detail = _response_data(scanner.get_container_scan_result(latest.id))
    problems = getattr(detail, "problems", None) or []
    if (getattr(detail, "compartment_id", None) != compartment or
            getattr(detail, "container_scan_target_id", None) != target_id or
            getattr(detail, "repository", None) != repository_name or
            getattr(detail, "image", None) != tag or
            getattr(detail, "highest_problem_severity", None) not in {"NONE", "LOW", "MEDIUM", "HIGH"} or
            any(problem.severity == "CRITICAL" for problem in problems)):
        raise ValueError("Scan ownership, severity or completion gate failed")
    # The VSS API identifies images by tag. Recheck its current digest after
    # reading the report; this is separate from the platform scan gate.
    _image(clients, compartment, image.repository_id, repository_name, tag, image.digest)
    return {"highest_severity": detail.highest_problem_severity,
            "problem_count": detail.problem_count, "critical_findings": 0}


def _create(args, state, receipt, clients, config, oci):
    region, tenancy, compartment = _target(state, receipt)
    app_id = _output(state, "hosted_application_id")
    genai = clients[0]
    _verify_application(genai, app_id, compartment)
    destination = Path(args.deployment_receipt)
    if destination.exists():
        raise ValueError("Deployment receipt already exists; use status")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", args.image_tag or ""):
        raise ValueError("Image tag must be a bounded commit-like tag")
    if not _SHA256.fullmatch(args.expected_digest or ""):
        raise ValueError("Expected digest must be 64 hex SHA-256 characters")
    repo_id = _output(state, "container_repository_id")
    repo_name = _output(state, "container_repository_name")
    image = _image(clients, compartment, repo_id, repo_name, args.image_tag,
                   "sha256:" + args.expected_digest)
    scan = _scan(clients, state, compartment, repo_name, args.image_tag, image)
    namespace = (state.get("object_storage_namespace") or receipt.get("object_storage_namespace") or
                 _output(state, "object_storage_namespace", "namespace"))
    # Hosted artifacts carry the image tag separately. Including it in both
    # fields makes the scan lookup use repository:tag:tag.
    container_uri = f"{region}.ocir.io/{namespace}/{repo_name}"
    artifact = oci.generative_ai.models.SingleDockerArtifact(
        container_uri=container_uri, tag=args.image_tag, is_vulnerability_scan_required=True)
    details = oci.generative_ai.models.CreateHostedDeploymentDetails(
        display_name=f"{repo_name.split('/')[-1]}-{args.image_tag}",
        compartment_id=compartment, hosted_application_id=app_id,
        active_artifact=artifact)
    created = _response_data(genai.create_hosted_deployment(details))
    deployment_id = getattr(created, "id", None)
    if not deployment_id:
        raise ValueError("Provider did not return a hosted deployment ID")
    save(destination, {"deployment_id": deployment_id, "hosted_application_id": app_id,
                       "compartment_id": compartment, "region": region,
                       "tenancy_id": tenancy, "artifact_digest": "sha256:" + args.expected_digest,
                       "scan": scan,
                       "image_tag": args.image_tag})
    print(json.dumps({"deployment": "created", "deployment_receipt": "saved_privately",
                      "artifact_digest": "sha256:" + args.expected_digest}))
    return 0


def _load_deployment(args):
    return private_json(args.deployment_receipt)


def _status(args, state, receipt, clients):
    """Read control-plane readiness without rewriting deployment evidence.

    Ready means eligible for a signed canary, never inference or telemetry
    acceptance. A provider 404 is ambiguous and must not trigger recreation.
    """
    import oci
    deployment = _load_deployment(args)
    region, tenancy, compartment = _target(state, receipt)
    app_id = _output(state, "hosted_application_id")
    if deployment.get("hosted_application_id") != app_id:
        raise ValueError("Deployment application mismatch")
    for key, value in (("region", region), ("tenancy_id", tenancy), ("compartment_id", compartment)):
        if key in deployment and deployment[key] != value:
            raise ValueError("Deployment target mismatch")
    report = {"readiness": "not_ready", "runtime_verified": False,
              "evidence_class": "control_plane_only"}
    try:
        app = _verify_application(clients[0], app_id, compartment)
        if getattr(app, "id", None) != app_id:
            raise ValueError("Application identity mismatch")
        item = _response_data(clients[0].get_hosted_deployment(deployment["deployment_id"]))
        if (getattr(item, "id", None) != deployment["deployment_id"] or
                getattr(item, "compartment_id", None) != compartment or
                getattr(item, "hosted_application_id", None) != app_id):
            raise ValueError("Hosted deployment ownership mismatch")
    except oci.exceptions.ServiceError as exc:
        report.update(readiness="unavailable", reason=("not_authorized_or_not_found"
                      if exc.status == 404 else "provider_read_unavailable"), http_status=exc.status)
        print(json.dumps(report))
        return 2
    artifact = getattr(item, "active_artifact", None)
    report.update(application_state=getattr(app, "lifecycle_state", None),
                  state=getattr(item, "lifecycle_state", None),
                  artifact_status=getattr(artifact, "status", None))
    if report["application_state"] != "ACTIVE" or report["state"] != "ACTIVE" or report["artifact_status"] != "ACTIVE":
        report["reason"] = "runtime_not_active"
    else:
        tag = deployment.get("requested_image_tag", deployment.get("image_tag"))
        digest = deployment.get("requested_artifact_digest", deployment.get("artifact_digest"))
        repository = _output(state, "container_repository_name")
        namespace = (state.get("object_storage_namespace") or receipt.get("object_storage_namespace") or
                     _output(state, "object_storage_namespace", "namespace"))
        expected_uri = f"{region}.ocir.io/{namespace}/{repository}"
        if (not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", tag) or
                not isinstance(digest, str) or not digest.startswith("sha256:") or not _SHA256.fullmatch(digest[7:])):
            report["reason"] = "artifact_binding_incomplete"
        elif getattr(artifact, "tag", None) != tag or getattr(artifact, "container_uri", None) != expected_uri:
            report["reason"] = "active_artifact_differs"
        else:
            try:
                _image(clients, compartment, _output(state, "container_repository_id"), repository, tag, digest)
            except (ValueError, oci.exceptions.ServiceError):
                report["reason"] = "artifact_binding_unverified"
            else:
                report.update(readiness="ready_for_canary", reason="active_artifact_binding_verified")
    print(json.dumps(report))
    return 0 if report["readiness"] == "ready_for_canary" else 2


def _update(args, state, receipt, clients, config, oci):
    """Replace only the verified workshop deployment's scanned artifact."""
    deployment = _load_deployment(args)
    region, tenancy, compartment = _target(state, receipt)
    app_id = _output(state, "hosted_application_id")
    _verify_application(clients[0], app_id, compartment)
    response = clients[0].get_hosted_deployment(deployment["deployment_id"])
    current = _response_data(response)
    if (deployment.get("hosted_application_id") != app_id or
            current.hosted_application_id != app_id or current.compartment_id != compartment):
        raise ValueError("Deployment ownership mismatch")
    if current.lifecycle_state != "ACTIVE":
        raise ValueError("Only an active deployment can be updated")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", args.image_tag or "") or not _SHA256.fullmatch(args.expected_digest or ""):
        raise ValueError("Bounded image tag and SHA-256 digest are required")
    repo = _output(state, "container_repository_name")
    image = _image(clients, compartment, _output(state, "container_repository_id"),
                   repo, args.image_tag, "sha256:" + args.expected_digest)
    scan = _scan(clients, state, compartment, repo, args.image_tag, image)
    namespace = (state.get("object_storage_namespace") or receipt.get("object_storage_namespace") or
                 _output(state, "object_storage_namespace", "namespace"))
    artifact = oci.generative_ai.models.SingleDockerArtifact(
        container_uri=f"{region}.ocir.io/{namespace}/{repo}", tag=args.image_tag,
        is_vulnerability_scan_required=True)
    etag = getattr(response, "headers", {}).get("etag")
    if not etag:
        raise ValueError("Deployment concurrency token is required")
    registered = [item for item in (getattr(current, "artifacts", None) or [])
                  if getattr(item, "container_uri", None) == artifact.container_uri and
                  getattr(item, "tag", None) == args.image_tag]
    if not registered:
        clients[0].add_artifact(oci.generative_ai.models.AddArtifactDetails(
            artifact=oci.generative_ai.models.CreateSingleDockerArtifactDetails(
                container_uri=artifact.container_uri, tag=args.image_tag,
                is_vulnerability_scan_required=True)), deployment["deployment_id"], if_match=etag)
        deployment.update(requested_artifact_digest=image.digest, requested_image_tag=args.image_tag,
                          requested_scan=scan, artifact_acceptance="registered_activation_pending")
        save(args.deployment_receipt, deployment)
        print(json.dumps({"artifact": "registration_submitted", "activation": "pending_readback_and_update"}))
        return 0
    if len(registered) != 1 or getattr(registered[0], "status", None) not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("Registered artifact is not ready for activation")
    clients[0].update_hosted_deployment(deployment["deployment_id"],
        oci.generative_ai.models.UpdateHostedDeploymentDetails(active_artifact=artifact), if_match=etag)
    deployment["previous_artifact_digest"] = deployment.get("artifact_digest")
    deployment.update(requested_artifact_digest=image.digest, requested_image_tag=args.image_tag,
                      requested_scan=scan, artifact_acceptance="pending_provider_readback")
    save(args.deployment_receipt, deployment)
    print(json.dumps({"deployment": "update_submitted", "active_artifact": "not_yet_verified"}))
    return 0


def _invoke(args, state, receipt, clients, config, oci):
    import requests
    deployment = _load_deployment(args)
    region, _, compartment = _target(state, receipt)
    app_id = _output(state, "hosted_application_id")
    _verify_application(clients[0], app_id, compartment)
    if deployment.get("hosted_application_id") != app_id:
        raise ValueError("Deployment application mismatch")
    bundle = private_json(args.bundle)
    env = bundle.get("environment")
    token = env.get("WORKSHOP_SERVICE_TOKEN") if isinstance(env, dict) else None
    if not isinstance(token, str) or not token:
        raise ValueError("Bundle must contain WORKSHOP_SERVICE_TOKEN")
    if not isinstance(args.prompt, str) or not args.prompt or len(args.prompt) > 32000:
        raise ValueError("Prompt is required and bounded")
    if not isinstance(args.session, str) or not args.session or len(args.session) > 256:
        raise ValueError("Session is required and bounded")
    realm = oci.regions.REGION_REALMS.get(region, "oc1")
    host_realm = oci.regions.REALMS[realm]
    url = f"https://inference.generativeai.{region}.oci.{host_realm}/20251112/hostedApplicationsIam/{app_id}/actions/invoke/run"
    signer = oci.signer.Signer(config["tenancy"], config["user"], config["fingerprint"],
                               config.get("key_file"), pass_phrase=config.get("pass_phrase"))
    response = requests.post(url, json={"prompt": args.prompt, "session_id": args.session},
                             headers={"X-Workshop-Token": token, "Content-Type": "application/json"},
                             auth=signer, allow_redirects=False, timeout=(5, 90))
    if response.is_redirect or response.is_permanent_redirect:
        raise ValueError("Invoke endpoint redirect refused")
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("Invoke response is not a JSON object")
    save(args.result, result)
    safe = {key: result.get(key) for key in
            ("outcome", "session", "trace", "steps", "inference_mode", "delivery") if key in result}
    safe["result"] = "saved_privately"
    print(json.dumps(safe))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("secret", "create", "update", "status", "invoke"))
    parser.add_argument("--state", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--deployment-receipt", required=True)
    parser.add_argument("--profile", default="DEFAULT")
    parser.add_argument("--bundle")
    parser.add_argument("--image-tag")
    parser.add_argument("--expected-digest")
    parser.add_argument("--prompt")
    parser.add_argument("--session")
    parser.add_argument("--result")
    args = parser.parse_args(argv)
    try:
        state = private_json(args.state)
        receipt = private_json(args.receipt)
        import oci
        config = oci.config.from_file(profile_name=args.profile)
        if config.get("tenancy") != receipt.get("tenancy_id", receipt.get("tenancy")) or config.get("region") != receipt.get("region"):
            raise ValueError("OCI profile target differs from private receipt")
        clients = _clients(config, oci)
        if args.action == "secret":
            if not args.bundle: raise ValueError("--bundle is required")
            return _secret(args, state, receipt, clients)
        if args.action == "create":
            return _create(args, state, receipt, clients, config, oci)
        if args.action == "update":
            return _update(args, state, receipt, clients, config, oci)
        if args.action == "status":
            return _status(args, state, receipt, clients)
        if not args.bundle or not args.result:
            raise ValueError("--bundle and --result are required")
        if args.action == "invoke":
            return _invoke(args, state, receipt, clients, config, oci)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__,
                          "detail": "Inspect private configuration and provider diagnostics; no fallback action taken"}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
