"""Real inference adapters. No fallback from a failed live call to scripted text."""
import json
import re
from dataclasses import replace
from urllib.request import Request, build_opener, HTTPRedirectHandler
from .config import Config, endpoint, secret
from .runtime import ModelReply


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenAIModel:
    def __init__(self, config: Config):
        self.config = config

    def authorization_token(self):
        return secret(self.config.model["api_key_env"])

    def complete(self, messages):
        c = self.config.model
        hosts = c.get("allowed_hosts")
        if not hosts:
            raise RuntimeError("Live model endpoint allowlist is required")
        url = endpoint(c["endpoint"], allowed_hosts=hosts) + "/chat/completions"
        body = {"model": c["model_id"], "messages": messages, "temperature": 0, "max_tokens": c.get("max_output_tokens", 700)}
        if c.get("json_mode"): body["response_format"] = {"type": "json_object"}
        request = Request(url, data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json",
                                   "Authorization": "Bearer " + self.authorization_token()})
        try:
            with build_opener(_NoRedirect).open(request, timeout=45) as response:
                raw = response.read(256000)
            result = json.loads(raw)
            usage = result.get("usage") or {}
            return ModelReply(result["choices"][0]["message"]["content"],
                              result.get("model") or c["model_id"],
                              usage.get("prompt_tokens"), usage.get("completion_tokens"))
        except Exception:
            raise RuntimeError("Live model request failed; inspect approved provider diagnostics") from None


class VertexModel(OpenAIModel):
    """Vertex OpenAI-compatible API; OAuth stays on the bound Google endpoint."""
    def __init__(self, config):
        super().__init__(config)
        c = config.model
        project, region = c.get("project_id", ""), c.get("region", "")
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project) or not re.fullmatch(r"global|[a-z]+-[a-z0-9]+[0-9]", region):
            raise ValueError("Vertex requires an explicit project and region")
        host = "aiplatform.googleapis.com" if region == "global" else region + "-aiplatform.googleapis.com"
        bases = {f"https://{host}/{version}/projects/{project}/locations/{region}/endpoints/openapi" for version in ("v1", "v1beta1")}
        if c.get("endpoint") not in bases or c.get("allowed_hosts") != [host]:
            raise ValueError("Vertex endpoint must match the exact project, region and Google host")
        if c.get("auth_type") not in {"environment", "metadata"}:
            raise ValueError("Vertex requires explicit environment or metadata OAuth")

    def authorization_token(self):
        if self.config.model["auth_type"] == "environment":
            return secret(self.config.model["access_token_env"])
        from urllib.request import ProxyHandler
        request = Request("http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token",
                          headers={"Metadata-Flavor": "Google"})
        try:
            with build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=5) as response:
                if response.headers.get("Metadata-Flavor") != "Google": raise ValueError("Unverified metadata response")
                data = json.loads(response.read(16000))
            token = data.get("access_token")
            if not isinstance(token, str) or not token or len(token) > 12000: raise ValueError("Invalid metadata token")
            return token
        except Exception:
            raise RuntimeError("Google workload OAuth is unavailable; no fallback was attempted") from None


class OCIModel:
    def __init__(self, config: Config):
        import oci
        from langchain_oci import ChatOCIGenAI
        from langchain_oci.common.auth import create_oci_client_kwargs
        c = config.model
        auth = config.oci.get("auth_type", "API_KEY")
        if auth not in {"API_KEY", "INSTANCE_PRINCIPAL", "RESOURCE_PRINCIPAL", "OKE_WORKLOAD_IDENTITY"}:
            raise ValueError("Unsupported OCI auth_type")
        if not c.get("allowed_hosts"):
            raise ValueError("Live model endpoint allowlist is required")
        kwargs = {"auth_type": auth}
        if auth == "API_KEY":
            kwargs["auth_profile"] = config.oci.get("profile", "DEFAULT")
        self.model_id = c["model_id"]
        if auth == "OKE_WORKLOAD_IDENTITY":
            from .auth import oke_signer
            client_args = {"config": {"region": config.oci["region"]}, "signer": oke_signer(),
                           "service_endpoint": endpoint(c["endpoint"], allowed_hosts=c.get("allowed_hosts")),
                           "timeout": (5, 45)}
        else:
            client_args = create_oci_client_kwargs(auth_type=auth,
                service_endpoint=endpoint(c["endpoint"], allowed_hosts=c.get("allowed_hosts")),
                auth_profile=config.oci.get("profile", "DEFAULT"), timeout=(5, 45))
        client_args["retry_strategy"] = oci.retry.NoneRetryStrategy()
        inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(**client_args)
        model_options = {"temperature": 0, "max_tokens": c.get("max_output_tokens", 700)}
        if c.get("json_mode"): model_options["response_format"] = {"type": "JSON_OBJECT"}
        self.client = ChatOCIGenAI(model_id=self.model_id,
            client=inference_client,
            compartment_id=config.oci["compartment_id"], service_endpoint=endpoint(c["endpoint"], allowed_hosts=c.get("allowed_hosts")),
            model_kwargs=model_options, **kwargs)

    def complete(self, messages):
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        kinds = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
        try:
            response = self.client.invoke([kinds[m["role"]](content=m["content"]) for m in messages])
            usage = getattr(response, "usage_metadata", None) or {}
            meta = getattr(response, "response_metadata", None) or {}
            tokens = meta.get("token_usage") or meta.get("usage") or {}
            content = response.content
            if isinstance(content, list):
                # LangChain may represent a final text response as content
                # blocks. Preserve text, never stringify the Python list or
                # expose non-text reasoning blocks as an action.
                content = "".join(block if isinstance(block, str) else block["text"]
                                  for block in content if isinstance(block, str) or
                                  (isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)))
            if not isinstance(content, str): raise ValueError("Non-text model response")
            return ModelReply(content, meta.get("model_name") or self.model_id,
                usage.get("input_tokens", tokens.get("prompt_tokens")),
                usage.get("output_tokens", tokens.get("completion_tokens")))
        except Exception:
            raise RuntimeError("Live OCI model request failed; no fallback was used") from None


class PricedModel:
    def __init__(self, model, pricing): self.model, self.pricing = model, pricing
    def complete(self, messages):
        from .costs import estimate_cost
        reply = self.model.complete(messages)
        return replace(reply, cost_details=estimate_cost(self.pricing, reply.model, reply.input_tokens, reply.output_tokens))


def live_model(config):
    pricing = config.model.get("pricing")
    if pricing is not None:
        from .costs import validate_pricing
        validate_pricing(pricing, config.model["model_id"])
    engines = {"oci": OCIModel, "openai": OpenAIModel, "vertex": VertexModel}
    if config.model.get("kind") not in engines: raise ValueError("Unsupported live model adapter")
    engine = engines[config.model["kind"]](config)
    return PricedModel(engine, pricing) if pricing is not None else engine
