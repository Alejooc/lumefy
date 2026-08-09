import unittest

from app.core.middleware import RequestObservabilityMiddleware


async def successful_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 204, "headers": []})
    await send({"type": "http.response.body", "body": b""})


class RequestObservabilityTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, request_id: bytes | None):
        headers = [] if request_id is None else [(b"x-request-id", request_id)]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/resource",
            "headers": headers,
            "state": {},
        }
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await RequestObservabilityMiddleware(successful_app)(scope, receive, send)
        response_headers = dict(messages[0]["headers"])
        return scope, response_headers[b"x-request-id"].decode("ascii")

    async def test_preserves_safe_client_request_id(self):
        scope, response_request_id = await self.invoke(b"checkout-123")

        self.assertEqual(response_request_id, "checkout-123")
        self.assertEqual(scope["state"]["request_id"], "checkout-123")

    async def test_replaces_log_injection_request_id(self):
        scope, response_request_id = await self.invoke(b"bad\nforged-log")

        self.assertRegex(response_request_id, r"^[0-9a-f]{32}$")
        self.assertEqual(scope["state"]["request_id"], response_request_id)


if __name__ == "__main__":
    unittest.main()
