"""Behavioral regressions for independent fork-sync review findings; hosted CI only."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent


class InstallerIsolationTest(unittest.TestCase):
    def test_inherited_destinations_cannot_escape_fixture_homes(self):
        for script in ('test-install-hermes-destination.sh', 'test-install-continue-after-failure.sh'):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                victim = root / 'existing-installation'
                plugin = victim / 'hermes/plugins/agency-agents-router'
                plugin.mkdir(parents=True)
                (plugin / 'plugin.yaml').write_text('name: agency-agents-router\n')
                (plugin / 'personal.txt').write_text('preserve personal installation\n')
                (victim / 'hermes/config.yaml').write_text('personal: preserve\n')
                env = dict(os.environ, HOME=str(root / 'test-home'),
                           HERMES_HOME=str(victim / 'hermes'), HERMES_PLUGIN_DIR=str(plugin),
                           GEMINI_AGENTS_DIR=str(victim / 'gemini'),
                           QWEN_AGENTS_DIR=str(victim / 'qwen'), CURSOR_RULES_DIR=str(victim / 'cursor'))
                def snapshot():
                    return {str(p.relative_to(victim)): p.read_bytes() for p in victim.rglob('*') if p.is_file()}
                before = snapshot()
                result = subprocess.run(['bash', str(SCRIPTS / script)], env=env,
                                        capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(snapshot(), before)


class FrontmatterAndFenceTest(unittest.TestCase):
    def test_comment_lines_are_not_scalar_continuations(self):
        cases = [
            ("'Build APIs'\n  # metadata comment", 'Build APIs'),
            ('Build APIs\n  # metadata comment\n  with care', 'Build APIs with care'),
            ("'Build\n  # literal content\n  APIs'\n  # metadata comment", 'Build # literal content APIs'),
            ('"Build\n  # literal content\n  APIs"\n  # metadata comment', 'Build # literal content APIs'),
            ("'It''s APIs'\n  # metadata comment", "It's APIs"),
            ('"Say \\"hello\\""\n  # metadata comment', 'Say "hello"'),
        ]
        for value, expected in cases:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                fixture = Path(tmp) / 'agent.md'
                fixture.write_text('---\ndescription: ' + value + '\ncolor: blue\n---\n')
                result = subprocess.run(['bash', '-c', 'source "$1"; get_field description "$2"',
                                         'regression', str(SCRIPTS / 'lib.sh'), str(fixture)],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)

    def test_inline_backtick_span_is_not_a_fence_opener(self):
        shell = '''source "$1"
if fence_open_p '```inline code```'; then exit 1; fi
if fence_open_p '   ```language`invalid'; then exit 2; fi
fence_open_p '  ```python' || exit 3
[[ "${BASH_REMATCH[2]}" == '```' ]] || exit 4
fence_open_p '~~~language`allowed' || exit 5
'''
        result = subprocess.run(['bash', '-c', shell, 'regression', str(SCRIPTS / 'lib.sh')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
