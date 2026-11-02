#!/usr/bin/env python3
"""Check the mute patch against local decoded inputs, without shipping Slack code.

Usage: python3 tools/test_patch_mute_sync.py --smali ORIGINAL.smali [--smali OTHER.smali]
"""
import argparse
from pathlib import Path
import re
import unittest

from patch_mute_sync import patch


INPUTS = []


class MutePatchTests(unittest.TestCase):
    def test_supported_inputs_keep_the_actual_audio_controller_chain(self):
        if not INPUTS:
            self.skipTest('Supply local original decoded inputs with --smali')
        for path in INPUTS:
            with self.subTest(path=str(path)):
                original = path.read_text()
                result = patch(original)
                mute = re.search(r'^\.method public final setMute\(Z\)V\n.*?^\.end method', original, re.M | re.S)[0]
                # The helper must read the same controller that Slack itself mutes.
                chain = re.search(r'check-cast p0, (L[^;]+;)\s+.*?iget-object p0, p0, (L[^\n]+)->([^\n]+)', mute, re.S)
                self.assertIsNotNone(chain)
                helper = result[result.index('.method private syncHuddleMute(I)V'):]
                self.assertIn('check-cast v0, '+chain[1], helper)
                self.assertIn('iget-object v0, v0, '+chain[2]+'->'+chain[3], helper)
                self.assertEqual(result.count('->syncHuddleMute(I)V'), 3)
                self.assertIn('move-object v2, p0', result)
                self.assertIn('if-ne v1, p1, :sync_done', helper)
                self.assertIn('if-eq v1, v2, :sync_done', helper)
                with self.assertRaisesRegex(AssertionError, 'Already patched'):
                    patch(result)

    def test_changed_original_method_is_rejected(self):
        if not INPUTS:
            self.skipTest('Supply local original decoded inputs with --smali')
        for path in INPUTS:
            with self.subTest(path=str(path)):
                original = path.read_text()
                changed = original.replace('.method public final setMute(Z)V\n', '.method public final setMute(Z)V\n    # unsupported upstream change\n', 1)
                with self.assertRaisesRegex(AssertionError, 'Unsupported original'):
                    patch(changed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smali', action='append', required=True, type=Path)
    args, rest = parser.parse_known_args()
    INPUTS.extend(args.smali)
    unittest.main(argv=[__file__, *rest])
