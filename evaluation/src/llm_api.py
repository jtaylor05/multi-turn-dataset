import io
import json
from random import random
import time
import openai
from google.genai.types import GenerateContentConfig, Content, Part
from google import genai as google
from anthropic import Anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request as AnthropicBatchRequest
import os
import requests
import uuid

class LLMAPI:

    def __init__(self, key: str = "", model : str = None):
        self.key = key
        self.model = model

    def request(self, prompt, system: str = "", model: str = None, conv_id: str = None) -> tuple:
        # always return as (conv_id, output)
        return ("", "")

    def add_to_history(self, conv_id, prompt, response):
        pass

    def submit_batch(self, requests: list[dict], system: str, model: str = None) -> str:
        # Each request is {"conv_id": str, "prompt": str, "history": list}
        # Returns a batch_id string
        return "<batch_id>"

    def poll_batch(self, batch_id: str) -> tuple[str, list[dict] | None]:
        # Returns (status, results_or_None)
        # status: "pending" | "complete" | "failed"
        # results: list of {"conv_id": str, "output": str} on complete, None otherwise
        return ("pending", None)

class MockAPI(LLMAPI):
    """
    A mock LLMAPI implementation for testing purposes.
    """
    BATCH_COUNTER = 0
    
    def __init__(self, key: str = "", model : str = None, chance_of_error: float = 0.05, chance_of_delay: float = 0.05, chance_of_failure: float = 0.05):
        super().__init__(key, model)
        self.requests = {}
        
        self.coe = chance_of_error
        self.cod = chance_of_delay
        self.cof = chance_of_failure
    
    def request(self, prompt, system: str = "", model: str = None, conv_id: str = None) -> tuple:
        # Simulate a response by echoing the prompt
        return (conv_id if conv_id else "mock_conv_id", f"Mock response to: {prompt}")

    def add_to_history(self, conv_id, prompt, response):
        # No-op for mock
        pass

    def submit_batch(self, requests: list[dict], system: str, model: str = None) -> str:
        # Return a mock batch ID
        
        self.BATCH_COUNTER += 1
        new_id = f"mock_batch_id_{self.BATCH_COUNTER}"
        self.requests[new_id] = requests
        return new_id

    def poll_batch(self, batch_id: str) -> tuple[str, list[dict] | None]:
        # Simulate a completed batch with mock results
        if not batch_id in self.requests:
            print("No requests found for batch_id:", batch_id)
            return ("failed", None)
        
        results = []
        for req in self.requests[batch_id]:
            seed = random()
            if seed < self.coe:
                results.append({"conv_id": req["conv_id"], "output": None, "error": "Simulated error"})
            elif seed < self.coe + self.cod:
                return ("pending", None)  # Simulate a delay
            elif seed < self.coe + self.cod + self.cof:
                return ("failed", None)  # Simulate a failure
            else:
                results.append({"conv_id": req["conv_id"], "output": f"Mock output for: {req['prompt']:.20}"})
        return ("complete", results)

# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIAPI(LLMAPI):
    """
    Batch flow: upload JSONL file → create batch → poll status → download output file.
    The Alibaba (Qwen) API is OpenAI-compatible and uses the exact same pattern,
    so AlibabaAPI inherits this implementation unchanged.
    """

    def __init__(self, key: str = "", model : str = None):
        super().__init__(key, model)
        if "OPENAI_API_KEY" in os.environ:
            self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        else:
            self.client = openai.OpenAI(api_key=self.key)

    def request(self, prompt, system: str = "", model: str = None, conv_id: str = None) -> tuple:
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")
        if conv_id:
            response = self.client.responses.create(
                model=used_model,
                instructions=system,
                input=prompt,
                previous_response_id=conv_id
            )
        else:
            response = self.client.responses.create(
                model=used_model,
                instructions=system,
                input=prompt
            )
        if conv_id:
            return (conv_id, response.output_text)
        return (response.id, response.output_text)

    def submit_batch(self, requests: list[dict], system: str, model: str = None) -> str:
        """
        Build a JSONL file in memory, upload it, then create a batch job.
        Each request dict must have keys: "conv_id", "prompt", "history".
        history is a list of {"role": ..., "content": ...} messages (may be empty).
        Returns the batch_id.
        """
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")
        lines = []
        for req in requests:
            history = req.get("history", [])
            messages = history + [{"role": "user", "content": req["prompt"]}]
            line = {
                "custom_id": req["conv_id"],
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": used_model,
                    "messages": [{"role": "system", "content": system}] + messages
                }
            }
            lines.append(json.dumps(line))

        jsonl_bytes = "\n".join(lines).encode("utf-8")
        file_obj = io.BytesIO(jsonl_bytes)
        file_obj.name = "batch_input.jsonl"

        uploaded = self.client.files.create(file=file_obj, purpose="batch")
        batch = self.client.batches.create(
            input_file_id=uploaded.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        return batch.id

    def poll_batch(self, batch_id: str) -> tuple[str, list[dict] | None]:
        batch = self.client.batches.retrieve(batch_id)
        status = batch.status  # validating | in_progress | completed | failed | expired | cancelled

        if status == "completed":
            raw = self.client.files.content(batch.output_file_id).text
            results = []
            for line in raw.strip().splitlines():
                entry = json.loads(line)
                conv_id = entry["custom_id"]
                # Individual requests can succeed or fail within a completed batch
                if entry.get("error"):
                    results.append({"conv_id": conv_id, "output": None, "error": entry["error"]})
                else:
                    text = entry["response"]["body"]["choices"][0]["message"]["content"]
                    results.append({"conv_id": conv_id, "output": text})
            return ("complete", results)

        if status in ("failed", "expired", "cancelled"):
            return ("failed", None)

        return ("pending", None)


# ---------------------------------------------------------------------------
# Alibaba / Qwen  (OpenAI-compatible batch endpoint)
# ---------------------------------------------------------------------------

class AlibabaAPI(OpenAIAPI):
    """
    Qwen models on DashScope expose an OpenAI-compatible batch API at the same
    base_url used for chat completions. The submit/poll logic is identical to
    OpenAIAPI — only the client endpoint differs.
    """

    def __init__(self, key: str = "", model : str = None,
                 base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"):
        super().__init__(key, model)
        api_key = os.environ.get("DASHSCOPE_API_KEY", self.key)
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)


# ---------------------------------------------------------------------------
# Google / Gemini
# ---------------------------------------------------------------------------

class GoogleAPI(LLMAPI):
    """
    Batch flow: client.batches.create(model, src=inline_requests) →
    poll job.state == "JOB_STATE_SUCCEEDED" → iterate job.inline_responses.
    System instructions are passed per-request inside the config field.
    """

    # Terminal states for polling
    _DONE_STATES = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}

    def __init__(self, key: str = "", model : str = None):
        super().__init__(key, model)
        api_key = os.environ.get("GEMINI_API_KEY", self.key)
        self.client = google.Client(api_key=api_key)
        self.chats = {}

    def request(self, prompt, system: str = "", model: str = None, conv_id: str = None) -> tuple:
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")
        
        convo = list(self.chats.get(conv_id, [])) if conv_id else []
        convo.append(Content(role="user", parts=[Part.from_text(text=prompt)]))

        response = self.client.models.generate_content(
            model=used_model,
            contents=convo,
            config=GenerateContentConfig(system_instruction=system)
        )

        convo.append(Content(role="model", parts=[Part.from_text(text=response.text)]))

        if not conv_id:
            # Gemini sync responses don't carry a stable conversation ID; use a
            # UUID so callers always get a resumable handle back.
            import uuid
            new_id = str(uuid.uuid4())
            self.chats[new_id] = convo
            return (new_id, response.text)

        self.chats[conv_id] = convo
        return (conv_id, response.text)

    def add_to_history(self, conv_id, prompt, response):
        convo = [
            Content(role="user", parts=[Part.from_text(text=prompt)]),
            Content(role="model", parts=[Part.from_text(text=response)])
        ]
        self.chats[conv_id] = convo

    def submit_batch(self, requests: list[dict], system: str, model: str) -> str:
        """
        Builds inline GenerateContentRequest dicts and submits them as a batch.
        Each request dict must have keys: "conv_id", "prompt", "history".
        history entries should be {"role": "user"|"model", "content": str}.
        Returns the batch job name (used as batch_id for polling).
        """
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")
        inline_requests = []
        for req in requests:
            contents = []
            for msg in req.get("history", []):
                role = "model" if msg["role"] == "assistant" else msg["role"]
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            contents.append({"role": "user", "parts": [{"text": req["prompt"]}]})

            inline_requests.append({
                "contents": contents,
                "config": {
                    "system_instruction": system
                },
                # Stash conv_id so we can reassemble results later.
                # Gemini uses a top-level "key" field for this purpose.
                "key": req["conv_id"]
            })

        job = self.client.batches.create(
            model=used_model,
            src=inline_requests
        )
        return job.name  # e.g. "batches/abc123"

    def poll_batch(self, batch_id: str) -> tuple[str, list[dict] | None]:
        job = self.client.batches.get(name=batch_id)
        state = job.state.name if hasattr(job.state, "name") else str(job.state)

        if state == "JOB_STATE_SUCCEEDED":
            results = []
            for resp in job.inline_responses:
                conv_id = resp.key
                # resp.response is a GenerateContentResponse
                try:
                    text = resp.response.text
                    results.append({"conv_id": conv_id, "output": text})
                except Exception as e:
                    results.append({"conv_id": conv_id, "output": None, "error": str(e)})
            return ("complete", results)

        if state in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"):
            return ("failed", None)

        return ("pending", None)


# ---------------------------------------------------------------------------
# Anthropic / Claude
# ---------------------------------------------------------------------------

class AnthropicAPI(LLMAPI):
    """
    Batch flow: client.messages.batches.create(requests=[...]) →
    poll processing_status == "ended" → stream results via client.messages.batches.results().
    """

    def __init__(self, key: str = "", model : str = None):
        super().__init__(key, model)
        api_key = os.environ.get("ANTHROPIC_API_KEY", self.key)
        self.client = Anthropic(api_key=api_key)
        self.chats = {}

    def request(self, prompt, system: str = "", model: str = None, conv_id: str = None) -> tuple:
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")
        
        convo = list(self.chats.get(conv_id, [])) if conv_id else []
        convo.append({"role": "user", "content": prompt})

        response = self.client.messages.create(
            model=used_model,
            max_tokens=8096,
            system=system,
            messages=convo
        )

        output = response.content[0].text
        convo.append({"role": "assistant", "content": output})

        if not conv_id:
            self.chats[response.id] = convo
            return (response.id, output)

        self.chats[conv_id] = convo
        return (conv_id, output)

    def add_to_history(self, conv_id, prompt, response):
        self.chats[conv_id] = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]

    def submit_batch(self, requests: list[dict], system: str, model: str = None) -> str:
        """
        Submits a Message Batch. Each request dict must have:
        "conv_id", "prompt", and optionally "history" (list of role/content dicts).
        Returns the batch ID string.
        """
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")
        batch_requests = []
        for req in requests:
            history = list(req.get("history", []))
            messages = history + [{"role": "user", "content": req["prompt"]}]

            batch_requests.append(
                AnthropicBatchRequest(
                    custom_id=req["conv_id"],
                    params=MessageCreateParamsNonStreaming(
                        model=used_model,
                        max_tokens=8096,
                        system=system,
                        messages=messages
                    )
                )
            )

        batch = self.client.messages.batches.create(requests=batch_requests)
        return batch.id

    def poll_batch(self, batch_id: str) -> tuple[str, list[dict] | None]:
        batch = self.client.messages.batches.retrieve(batch_id)

        if batch.processing_status == "ended":
            results = []
            for result in self.client.messages.batches.results(batch_id):
                conv_id = result.custom_id
                if result.result.type == "succeeded":
                    text = result.result.message.content[0].text
                    results.append({"conv_id": conv_id, "output": text})
                elif result.result.type == "errored":
                    results.append({"conv_id": conv_id, "output": None,
                                    "error": str(result.result.error)})
                elif result.result.type == "expired":
                    results.append({"conv_id": conv_id, "output": None, "error": "expired"})
            return ("complete", results)

        # processing_status is "in_progress" or "canceling"
        return ("pending", None)


# ---------------------------------------------------------------------------
# Ollama (local) API
# ---------------------------------------------------------------------------


class OllamaAPI(LLMAPI):
    """
    Ollama API wrapper mirroring the AnthropicAPI structure. Uses a local
    Ollama HTTP server (default http://localhost:11434) `/api/chat` endpoint.

    Note: Ollama has no native batch/async job API the way Anthropic does.
    `submit_batch` registers requests locally, and `poll_batch` runs them
    synchronously on first poll, then reports "complete" from then on -
    there is no real "in_progress" state to observe.
    """

    def __init__(self, key: str = "", model: str = None, base_url: str = "http://localhost:11434", timeout = 60):
        super().__init__(key, model)
        self.base_url = os.environ.get("OLLAMA_BASE_URL", base_url.rstrip('/'))
        self.session = requests.Session()
        self.chats = {}
        self._batches = {}
        self.timeout = timeout

    def request(self, prompt, system: str = "", model: str = None, conv_id: str = None) -> tuple:
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")

        convo = list(self.chats.get(conv_id, [])) if conv_id else []
        convo.append({"role": "user", "content": prompt})

        messages = ([{"role": "system", "content": system}] if system else []) + convo

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": used_model,
            "messages": messages,
            "stream": True,
        }

        resp = self.session.post(url, json=payload, timeout=self.timeout, stream=True)
        resp.raise_for_status()

        output_parts = []
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            content = chunk.get("message", {}).get("content")
            if content:
                output_parts.append(content)
            if chunk.get("done"):
                break

        output = "".join(output_parts)

        convo.append({"role": "assistant", "content": output})

        if not conv_id:
            conv_id = f"ollama_conv_{uuid.uuid4().hex}"

        self.chats[conv_id] = convo
        return (conv_id, output)

    def add_to_history(self, conv_id, prompt, response):
        self.chats[conv_id] = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]

    def submit_batch(self, requests: list[dict], system: str, model: str = None) -> str:
        """
        Registers a batch for local synchronous processing. Each request
        dict must have "conv_id", "prompt", and optionally "history"
        (list of role/content dicts).
        Returns a locally-generated batch ID string.
        """
        used_model = model if model is not None else self.model
        if used_model is None:
            raise ValueError("Model cannot be none")

        batch_id = f"ollama_batch_{uuid.uuid4().hex}"
        self._batches[batch_id] = {
            "requests": list(requests),
            "status": "pending",
            "results": None,
            "system": system,
            "model": used_model,
        }
        return batch_id

    def poll_batch(self, batch_id: str) -> tuple[str, list[dict] | None]:
        if batch_id not in self._batches:
            return ("failed", None)

        batch_entry = self._batches[batch_id]
        if batch_entry["status"] == "complete":
            return ("complete", batch_entry["results"])

        results = []
        for req in batch_entry["requests"]:
            conv_id = req["conv_id"]
            if "history" in req:
                # Explicit history provided (possibly empty) - seed/reset it.
                # An empty list intentionally starts conv_id with no prior context.
                self.chats[conv_id] = list(req["history"])
            # else: leave self.chats[conv_id] as-is, so any history already
            # tracked for this conv_id (e.g. from a prior request() call)
            # carries forward into this batch.

            try:
                _, output = self.request(
                    req["prompt"],
                    system=batch_entry["system"],
                    model=batch_entry["model"],
                    conv_id=conv_id,
                )
                results.append({"conv_id": conv_id, "output": output})
            except Exception as e:
                results.append({"conv_id": conv_id, "output": None, "error": str(e)})

        batch_entry["status"] = "complete"
        batch_entry["results"] = results
        return ("complete", results)