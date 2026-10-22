#!/usr/bin/env python3
from pathlib import Path
from zipfile import ZipFile
import subprocess, os
p=Path(__file__).resolve().parents[1]
tools=Path(os.environ['ANDROID_BUILD_TOOLS'])
env=dict(os.environ)
with ZipFile(p/'slack-base.apk') as old, ZipFile(p/'patched-apks/base.apk') as new:
 for n in old.namelist():
  if (n.endswith('.dex') and n not in ('classes3.dex','classes6.dex')) or n.startswith('res/'):
   assert old.read(n)==new.read(n), f'Unexpected changed binary entry: {n}'
 assert 'res/xml/automotive_app_desc.xml' in new.namelist()
 for index in (3,6):
  with ZipFile(p/f'classes{index}-patched.apk') as changed:
   assert new.read(f'classes{index}.dex')==changed.read('classes.dex')
 print('PASS: only the two intended DEX files changed; all original compiled resources preserved.')
manifest=subprocess.check_output([str(tools/'aapt2'),'dump','xmltree',str(p/'patched-apks/base.apk'),'--file','AndroidManifest.xml'],text=True)
for s in ['slack.services.huddles.auto.HuddlesAutoService','androidx.car.app.category.CALLING','com.google.android.gms.car.application','androidx.car.app.minCarApiLevel']:
 assert s in manifest,s
print('PASS: compiled manifest declares existing calling service and car metadata.')
certs=[]
for n in ['base.apk','split_config.arm64_v8a.apk','split_config.xxhdpi.apk']:
 result=subprocess.check_output([str(tools/'apksigner'),'verify','--print-certs',str(p/'patched-apks'/n)],text=True,env=env)
 certs.append(next(l for l in result.splitlines() if l.startswith('Signer #1 certificate SHA-256 digest:')))
assert len(set(certs))==1
print('PASS: all three APK signatures valid and match.')

# Prove the entire original resource table is semantically unchanged.
old_dump=subprocess.check_output([str(tools/'aapt2'),'dump','resources',str(p/'slack-base.apk')],text=True)
new_dump=subprocess.check_output([str(tools/'aapt2'),'dump','resources',str(p/'patched-apks/base.apk')],text=True)
import re
new_dump=re.sub(r'    resource 0x7f170014 xml/automotive_app_desc\n      \(\) \(file\) res/xml/automotive_app_desc.xml type=XML\n', '', new_dump)
new_dump=new_dump.replace('type xml id=17 entryCount=21','type xml id=17 entryCount=20')
assert old_dump==new_dump, 'Unexpected original resource table change'
print('PASS: original resource table preserved; only car descriptor appended.')
