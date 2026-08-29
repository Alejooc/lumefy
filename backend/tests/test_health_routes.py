import unittest

from app.core.config import settings
from app.main import app


class HealthRouteTests(unittest.TestCase):
    def test_health_routes_are_available_internally_and_through_api_proxy(self):
        paths = {route.path for route in app.routes if hasattr(route, "path")}

        self.assertIn("/healthz", paths)
        self.assertIn("/readyz", paths)
        self.assertIn(f"{settings.API_V1_STR}/healthz", paths)
        self.assertIn(f"{settings.API_V1_STR}/readyz", paths)


if __name__ == "__main__":
    unittest.main()
