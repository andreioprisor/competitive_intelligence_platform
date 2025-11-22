import os, requests, time
from typing import List, Dict, Optional, Any

class OpenRouterAdapter:
    """
    Minimal adapter for OpenRouter chat completions with:
      - single model OR ordered list of fallback models
      - simple prioritization (sort by priority dict)
      - BYOK per model via `HTTP-Provider-Authorization`
      - automatic fallback: BYOK -> credits -> next model
    """

    def __init__(
        self,
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: Optional[str] = None,
        referer: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.common_headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if app_title:
            self.common_headers["X-Title"] = app_title
        if referer:
            self.common_headers["HTTP-Referer"] = referer

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        models: Optional[List[str]] = None,
        priorities: Optional[Dict[str, int]] = None,
        byok: Optional[Dict[str, str]] = None,  # {model_id: provider_api_key}
        temperature: float = 0.0,
        max_output_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        retry_on: tuple = (429, 500, 502, 503, 504),
        backoff_secs: float = 0.8,
    ) -> Dict[str, Any]:
        """
        - If `model` is provided, it's used first; `models` (if any) are tried after it.
        - If `priorities` is provided (lower = sooner), the combined list is sorted by it.
        - If `byok` has an entry for a model, try that model with BYOK header; on failure,
          retry same model without BYOK (OpenRouter credits), then move to next model.
        """
        if not model and not models:
            raise ValueError("Provide `model` or `models`.")

        # Build ordered candidate list
        cand = []
        if model:
            cand.append(model)
        if models:
            cand.extend([m for m in models if m not in cand])

        if priorities:
            cand.sort(key=lambda m: priorities.get(m, 1_000_000))  # unknowns last

        url = f"{self.base_url}/chat/completions"
        body_base = {
            "messages": messages,
            "temperature": temperature,
        }
        if max_output_tokens is not None:
            # OpenRouter accepts `max_tokens` like OpenAI; some hosts also accept `max_output_tokens`
            body_base["max_tokens"] = max_output_tokens
        if extra_body:
            body_base.update(extra_body)

        last_error = None
        for m in cand:
            # 1) Try BYOK (if provided for this model)
            if byok and m in byok:
                headers = dict(self.common_headers)
                headers["HTTP-Provider-Authorization"] = f"Bearer {byok[m]}"
                payload = dict(body_base)
                payload["model"] = m
                r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                if r.ok:
                    return r.json()
                last_error = (m, "byok", r.status_code, r.text)
                if r.status_code in retry_on:
                    time.sleep(backoff_secs)  # light backoff before credits fallback

            # 2) Retry SAME model via OpenRouter credits (no BYOK header)
            headers = dict(self.common_headers)
            payload = dict(body_base)
            payload["model"] = m
            r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if r.ok:
                return r.json()
            last_error = (m, "credits", r.status_code, r.text)
            if r.status_code in retry_on:
                time.sleep(backoff_secs)

        # If we get here, all attempts failed
        model_info = " -> ".join(cand)
        raise RuntimeError(
            f"All model attempts failed ({model_info}). "
            f"Last error: model={last_error[0]} path={last_error[1]} "
            f"status={last_error[2]} body={last_error[3][:500]}"
        )
    # convenience method
    def get_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        models: Optional[List[str]] = None,
        priorities: Optional[Dict[str, int]] = None,
        byok: Optional[Dict[str, str]] = None,
        temperature: float = 0.0,
        max_output_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        retry_on: tuple = (429, 500, 502, 503, 504),
        backoff_secs: float = 0.8,
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        response = self.chat(
            messages=messages,
            model=model,
            models=models,
            priorities=priorities,
            byok=byok,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            extra_body=extra_body,
            retry_on=retry_on,
            backoff_secs=backoff_secs,
        )
        return response["choices"][0]["message"]["content"]
