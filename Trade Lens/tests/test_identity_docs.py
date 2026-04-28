import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRADE_LENS = ROOT / "Trade Lens"


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
            TRADE_LENS / "SKILL.md",
            TRADE_LENS / "AGENTS.md",
            TRADE_LENS / "README.md",
        ]

        for path in docs:
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn("agent workflow", text, path.name)
            self.assertIn("not shell cli commands", text, path.name)
            self.assertNotIn("## commands", text, path.name)
            self.assertNotIn("## command system", text, path.name)
            self.assertNotIn("## command router", text, path.name)


if __name__ == "__main__":
    unittest.main()
