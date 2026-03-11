import json
import os
import tempfile
import unittest

import httpx


class TestWebCortex(unittest.IsolatedAsyncioTestCase):
    async def test_research_persists_and_emits(self):
        from core.web_cortex import WebCortex

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content.decode("utf-8"))
            self.assertIn("query", body)
            self.assertEqual(body["max_results"], 2)
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"url": "https://example.com/a", "title": "A", "content": "alpha", "score": 0.9},
                        {"url": "https://example.com/b", "title": "B", "content": "beta", "score": 0.8},
                    ]
                },
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, timeout=5.0) as client:
            with tempfile.TemporaryDirectory() as tmp:
                os.environ["WEB_CORTEX_MAX_RESULTS"] = "2"
                wc = WebCortex(api_key="test", client=client, cortex_base_path=tmp, strict_api_key=True)
                res = await wc.research("hello", task_id="t1")

                self.assertEqual(res["query"], "hello")
                self.assertEqual(res["sources"], 2)
                self.assertEqual(len(res["content"]), 2)

                p = os.path.join(tmp, "snapshots", "t1", "web_context.jsonl")
                self.assertTrue(os.path.exists(p))
                with open(p, "r", encoding="utf-8") as f:
                    line = f.readline().strip()
                obj = json.loads(line)
                self.assertEqual(obj["query"], "hello")
                self.assertEqual(obj["sources"], 2)

