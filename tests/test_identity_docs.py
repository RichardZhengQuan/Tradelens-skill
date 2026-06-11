import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IdentityDocsTest(unittest.TestCase):
    def test_root_skill_describes_markdown_skill_not_current_native_app(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("local markdown-first trading analysis skill", text)
        self.assertIn("not a native macos app", text)
        self.assertIn("no swiftui ui", text)
        self.assertIn("no xcode project", text)
        self.assertNotIn("use swift and swiftui", text)
        self.assertNotIn("current xcode project", text)
        self.assertNotIn("tradelens/tradelens.xcodeproj", text)

    def test_docs_mark_slash_workflows_as_agent_workflows_not_cli(self):
        docs = [
            ROOT / "SKILL.md",
            ROOT / "AGENTS.md",
            ROOT / "README.md",
        ]

        for path in docs:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("agent workflow", text, path.name)
            self.assertIn("not shell cli commands", text, path.name)
            self.assertNotIn("## commands", text, path.name)
            self.assertNotIn("## command system", text, path.name)
            self.assertNotIn("## command router", text, path.name)

    def test_report_contract_is_persistent_source_of_truth(self):
        text = (ROOT / "docs" / "report_contract.md").read_text(encoding="utf-8")

        self.assertIn("source of truth", text.lower())
        self.assertIn("## **Term-Aware Trade Judgment**", text)
        self.assertIn("## Why", text)
        self.assertIn("NO CLEAR EDGE", text)
        self.assertIn("Section order", text)

    def test_skill_routes_commands_to_specific_docs(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("docs/report_contract.md", text)
        self.assertIn("docs/provider_rules.md", text)
        self.assertIn("docs/assets_rules.md", text)
        self.assertIn("For small commands, do not load full analysis docs.", text)

    def test_provider_safety_is_internal_not_repeated_boilerplate(self):
        docs = [
            ROOT / "SKILL.md",
            ROOT / "AGENTS.md",
            ROOT / "docs" / "provider_rules.md",
            ROOT / "docs" / "safety_rules.md",
        ]

        for path in docs:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("do not repeat routine safety boilerplate", text, path.name)
            self.assertIn("normal successful provider", text, path.name)

    def test_trade_checks_require_assets_history_and_local_market_fallback(self):
        docs = [
            ROOT / "SKILL.md",
            ROOT / "AGENTS.md",
            ROOT / "docs" / "analysis_rules.md",
            ROOT / "docs" / "provider_rules.md",
            ROOT / "README.md",
        ]

        for path in docs:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("trade check", text, path.name)
            self.assertIn("assets.md", text, path.name)
            self.assertIn("trade.md", text, path.name)
            self.assertIn("market_data.md", text, path.name)
            self.assertIn("realtime/latest", text, path.name)

    def test_asset_checks_are_api_first_when_providers_are_configured(self):
        docs = [
            ROOT / "SKILL.md",
            ROOT / "AGENTS.md",
            ROOT / "README.md",
            ROOT / "docs" / "assets_rules.md",
            ROOT / "docs" / "provider_rules.md",
        ]

        for path in docs:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("asset checks", text, path.name)
            self.assertIn("read-only", text, path.name)
            self.assertIn("account", text, path.name)
            self.assertIn("positions", text, path.name)
            self.assertIn("assets.md", text, path.name)

    def test_asset_checks_must_not_mix_provider_quotes_with_local_assets(self):
        docs = [
            ROOT / "SKILL.md",
            ROOT / "AGENTS.md",
            ROOT / "README.md",
            ROOT / "docs" / "assets_rules.md",
            ROOT / "docs" / "provider_rules.md",
        ]

        for path in docs:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("mix", text, path.name)
            self.assertIn("local", text, path.name)
            self.assertIn("quote", text, path.name)
            self.assertIn("asset", text, path.name)


if __name__ == "__main__":
    unittest.main()
