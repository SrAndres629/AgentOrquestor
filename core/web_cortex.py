import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from core.event_bus import bus
from core.telemetry import telemetry


class WebCortex:
    """
    External research engine for AgentOrquestor.
    - Async, concurrency-limited
    - Persists results into .cortex/ sharded by task_id
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        max_concurrency: Optional[int] = None,
        cortex_base_path: str = ".cortex",
        strict_api_key: Optional[bool] = None,
    ):
        if api_key is None:
            # Support both conventional env var and user's local naming.
            api_key = (
                os.getenv("TAVILY_API_KEY", "").strip()
                or os.getenv("tavily", "").strip()
                or os.getenv("TAVILY", "").strip()
            )
        self.api_key = api_key.strip() if api_key else ""
        self.client = client or httpx.AsyncClient(timeout=30.0)
        self.cortex_base_path = cortex_base_path

        if max_concurrency is None:
            env = os.getenv("WEB_CORTEX_MAX_CONCURRENCY", "").strip()
            try:
                max_concurrency = int(env) if env else 3
            except ValueError:
                max_concurrency = 3
        self._sem = asyncio.Semaphore(max(1, int(max_concurrency)))

        if strict_api_key is None:
            strict_env = os.getenv("WEB_CORTEX_STRICT", "").strip()
            strict_api_key = strict_env == "1"
        self.strict_api_key = bool(strict_api_key)

    def _task_dir(self, task_id: str) -> str:
        safe_task = task_id or "global"
        safe_task = "".join(ch for ch in safe_task if ch.isalnum() or ch in ("-", "_", ":"))[:64] or "global"
        path = os.path.join(self.cortex_base_path, "snapshots", safe_task)
        os.makedirs(path, exist_ok=True)
        return path

    async def research(self, query: str, task_id: str = "global") -> Dict[str, Any]:
        telemetry.emit_event("WEB_RESEARCH_STARTED", {"query": query, "task_id": task_id})

        if not self.api_key:
            msg = "Missing TAVILY_API_KEY"
            telemetry.emit_event("WEB_RESEARCH_MISS", {"query": query, "task_id": task_id, "error": msg})
            bus.publish("WEB_RESEARCH_MISS", {"query": query, "error": msg}, sender="WebCortex")
            if self.strict_api_key:
                raise RuntimeError(msg)
            return {"query": query, "content": [], "sources": 0, "error": msg}

        async with self._sem:
            results = await self._tavily_search(query)

        payload = {"query": query, "content": results, "sources": len(results)}
        self._persist_web_context(task_id=task_id, payload=payload)

        bus.publish(
            "WEB_RESEARCH_COMPLETED",
            {"query": query, "sources": len(results)},
            sender="WebCortex"
        )
        telemetry.emit_event("WEB_RESEARCH_COMPLETED", {"query": query, "task_id": task_id, "sources": len(results)})
        return payload

    async def _tavily_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Tavily Search API.
        Docs: https://docs.tavily.com/documentation/api-reference/endpoint/search
        """
        url = os.getenv("TAVILY_SEARCH_URL", "").strip() or "https://api.tavily.com/search"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        max_results_env = os.getenv("WEB_CORTEX_MAX_RESULTS", "").strip()
        try:
            max_results = int(max_results_env) if max_results_env else 5
        except ValueError:
            max_results = 5

        body = {
            "query": query,
            "search_depth": os.getenv("WEB_CORTEX_SEARCH_DEPTH", "").strip() or "basic",
            "max_results": max(1, max_results),
            "include_answer": False,
            "include_images": False,
            "include_raw_content": os.getenv("WEB_CORTEX_RAW_CONTENT", "").strip() or "markdown",
        }

        r = await self.client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json() if isinstance(r.json(), dict) else {}
        raw_results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(raw_results, list):
            return []

        cleaned: List[Dict[str, Any]] = []
        for item in raw_results[: max(1, max_results)]:
            if not isinstance(item, dict):
                continue
            cleaned.append(
                {
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "content": item.get("content") or item.get("raw_content"),
                    "score": item.get("score"),
                }
            )
        return cleaned

    def _persist_web_context(self, task_id: str, payload: Dict[str, Any]) -> None:
        try:
            path = os.path.join(self._task_dir(task_id), "web_context.jsonl")
            record = {"ts": time.time(), **payload}
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # Never break core flow on persistence issues.
            pass


web_cortex = WebCortex()
