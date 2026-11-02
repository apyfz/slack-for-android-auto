#!/usr/bin/env python3
"""Square structural sidebar/composer corners, retaining native cards and pills."""
import hashlib
from pathlib import Path
import sys

def patch(root):
    edits=[(2,'slack/services/navigationview/api/home/NavPullDownMessageKt.smali','fbdbee3fa884dfbdc0ffe94b607c98134607cfce475557155ef04067e1efa8e0','    sget v5, Lslack/kit/usertheme/SKDimen;->cornerRadius75:F','    const/4 v5, 0x0'),
           (5,'slack/services/composer/widgets/v2/ComposerUiExtKt.smali','7a8e32dbf8d02796f5ae1c15dd99e468beb16bf449d0acb0fc5e836a3ecaab62','    sget v0, Lslack/kit/usertheme/SKDimen;->cornerRadius100:F','    const/4 v0, 0x0')]
    sources=[]
    for dex,rel,digest,old,new in edits:
        p=root/f'classes{dex}-wrapper/smali'/rel
        assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,f'Unsupported structural UI class: {rel}'
        text=p.read_text();assert text.count(old)==1
        text=text.replace(old,new)
        if dex==2:
            old_branch='    if-eqz v9, :cond_4'
            assert text.count(old_branch)==1
            text=text.replace(old_branch,'    const-wide v12, 0xff17191d00000000L\n    goto :cond_4')
        sources.append((p,text))
    p=root/'classes2-wrapper/smali/slack/kit/usertheme/SKColorSetKt.smali'
    assert hashlib.sha256(p.read_bytes()).hexdigest()=='b103d30738f03addbd36177b27dbb4c2a8ffa3e5ebcb3b54fa2d1ed1da2f05b0'
    text=p.read_text()
    for old,new in [('0xff797c81L','0xff42454aL'),('0x80797c81L','0x8042454aL'),('0x4d797c81','0x4d42454a')]:
        assert text.count(old)==1
        text=text.replace(old,new)
    sources.append((p,text))
    for p,text in sources:p.write_text(text)
    print('Squared sidebar panel and shared composer shape/border radius; cards and pills unchanged')
if __name__=='__main__':patch(Path(sys.argv[1]))
