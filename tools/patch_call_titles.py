#!/usr/bin/env python3
"""Clean rich-text placeholders only at Slack's Telecom call-title boundary.

Supports the exact 26.10.40.0 title collectors; rejects unknown input code.
"""
import hashlib
from pathlib import Path
import sys

COLLECTORS = {
    'slack/services/lists/fields/ListsFileManagerImpl$1$3.smali':
        'e63e85f2cc17391bc2f2c05ce1e983843ba423aebdd3e32f0982a7a3c9ff11e9',
    'slack/services/huddles/service/impl/telecom/HuddleIncomingConnection$onShowIncomingCallUi$2$1.smali':
        '5c2865e05bdd01977d87ea535a189c2dcce33664984660b49e6702a8dcda27ed',
}
HELPER = r'''.class public final Lslack/services/huddles/auto/AutoCallTitle;
.super Ljava/lang/Object;

.method public static clean(Ljava/lang/String;)Ljava/lang/String;
    .locals 2
    if-eqz p0, :done
    const-string v0, "\ufffc"
    const-string v1, ""
    invoke-virtual {p0, v0, v1}, Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;
    move-result-object p0
    const-string v0, "\ufffd"
    invoke-virtual {p0, v0, v1}, Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;
    move-result-object p0
    invoke-virtual {p0}, Ljava/lang/String;->trim()Ljava/lang/String;
    move-result-object p0
    :done
    return-object p0
.end method
'''

def patch(root):
    helper = root / 'slack/services/huddles/auto/AutoCallTitle.smali'
    assert not helper.exists(), 'Call-title cleanup already present'
    updates = []
    for rel, digest in COLLECTORS.items():
        path = root / rel
        original = path.read_text()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f'Unsupported title collector: {rel}'
        lines = original.splitlines(keepends=True)
        matches = [i for i, line in enumerate(lines) if 'Landroid/telecom/Connection;->setCallerDisplayName(' in line]
        assert len(matches) == 1, f'Expected one title setter: {rel}'
        lines.insert(matches[0], '    invoke-static {p1}, Lslack/services/huddles/auto/AutoCallTitle;->clean(Ljava/lang/String;)Ljava/lang/String;\n    move-result-object p1\n\n')
        updates.append((path, ''.join(lines)))
    for path, text in updates:
        path.write_text(text)
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(HELPER)
    print('Patched incoming/outgoing Telecom title collectors')

if __name__ == '__main__':
    assert len(sys.argv) == 2, 'Usage: patch_call_titles.py path/to/classes6-wrapper/smali'
    patch(Path(sys.argv[1]))
