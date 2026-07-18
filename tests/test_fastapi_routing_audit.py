import unittest

from core.app import app


class FastApiRoutingAuditTest(unittest.TestCase):
    def test_legacy_task_routes_are_not_registered(self) -> None:
        routes = {getattr(route, "path", None) for route in app.routes if hasattr(route, "path")}
        self.assertNotIn("/tasks/legacy", routes)
        self.assertNotIn("/tasks/legacy/status", routes)
        self.assertNotIn("/tasks/legacy/{task_id}", routes)

    def test_duplicate_method_path_pairs_are_not_registered(self) -> None:
        seen = set()
        duplicates = []
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None) or set()
            if not path or not methods:
                continue
            for method in methods:
                pair = (method, path)
                if pair in seen:
                    duplicates.append(pair)
                else:
                    seen.add(pair)

        self.assertEqual([], duplicates)


if __name__ == "__main__":
    unittest.main()
