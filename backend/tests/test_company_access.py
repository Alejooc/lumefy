import unittest
from inspect import signature

from app.api.v1.endpoints.companies import read_current_company, update_current_company
from app.core import auth
from app.core.permissions import PermissionChecker


class CompanyAccessTests(unittest.TestCase):
    def test_all_tenant_users_can_load_their_company_context(self):
        dependency = signature(read_current_company).parameters["current_user"].default.dependency
        self.assertIs(dependency, auth.get_current_user)

    def test_only_company_administrators_can_update_company_data(self):
        dependency = signature(update_current_company).parameters["current_user"].default.dependency
        self.assertIsInstance(dependency, PermissionChecker)
        self.assertEqual(dependency.required_permission, "manage_company")


if __name__ == "__main__":
    unittest.main()
