#!/usr/bin/env python3
from pathlib import Path
from zipfile import ZipFile
import subprocess, os, json
p=Path(__file__).resolve().parents[1]
tools=Path(os.environ['ANDROID_BUILD_TOOLS'])
env=dict(os.environ)
profile=json.loads((p/'patch-profile.json').read_text()) if (p/'patch-profile.json').exists() else {'dex_indices': [3,6]}
dex_indices=profile['dex_indices']
changed_dex={f'classes{index}.dex' for index in dex_indices}
with ZipFile(p/'slack-base.apk') as old, ZipFile(p/'patched-apks/base.apk') as new:
 added_dex={n for n in new.namelist() if n.endswith('.dex')} - {n for n in old.namelist() if n.endswith('.dex')}
 expected_extra={profile['discovery_dex']} if profile.get('discovery_dex') else set()
 if profile.get('fold_dex'): expected_extra.add(profile['fold_dex'])
 assert added_dex==expected_extra, f'Unexpected added DEX files: {added_dex}'
 if expected_extra:
  with ZipFile(p/'discovery-extension/discovery.jar') as extension:
   assert new.read(profile['discovery_dex'])==extension.read('classes.dex')
 if profile.get('fold_dex'):
  with ZipFile(p/'fold-native.apk') as native:
   assert new.read(profile['fold_dex'])==native.read('classes.dex')
 for n in old.namelist():
  if (n.endswith('.dex') and n not in changed_dex) or n.startswith('res/'):
   assert old.read(n)==new.read(n), f'Unexpected changed binary entry: {n}'
 assert 'res/xml/automotive_app_desc.xml' in new.namelist()
 for index in dex_indices:
  with ZipFile(p/f'classes{index}-patched.apk') as changed:
   assert new.read(f'classes{index}.dex')==changed.read('classes.dex')
 print(f'PASS: intended DEX files {dex_indices} changed' + (f"; added verified {profile['discovery_dex']}" if expected_extra else '') + '; all original compiled resources preserved.')
manifest=subprocess.check_output([str(tools/'aapt2'),'dump','xmltree',str(p/'patched-apks/base.apk'),'--file','AndroidManifest.xml'],text=True)
for s in ['slack.services.huddles.auto.HuddlesAutoService','androidx.car.app.category.CALLING','com.google.android.gms.car.application','androidx.car.app.minCarApiLevel']:
 assert s in manifest,s
print('PASS: compiled manifest declares existing calling service and car metadata.')
certs=[]
for n in ['base.apk','split_config.arm64_v8a.apk','split_config.xxhdpi.apk']:
 result=subprocess.check_output([str(tools/'apksigner'),'verify','--print-certs',str(p/'patched-apks'/n)],text=True,env=env)
 certs.append(tuple(l.split('certificate SHA-256 digest: ',1)[1] for l in result.splitlines() if 'certificate SHA-256 digest: ' in l))
 assert certs[-1], 'No signing certificate found'
assert len(set(certs))==1
print('PASS: all three APK signatures valid and match.')

# Prove the entire original resource table is semantically unchanged.
old_dump=subprocess.check_output([str(tools/'aapt2'),'dump','resources',str(p/'slack-base.apk')],text=True)
new_dump=subprocess.check_output([str(tools/'aapt2'),'dump','resources',str(p/'patched-apks/base.apk')],text=True)
import re
new_dump=re.sub(r'    resource 0x7f170014 xml/automotive_app_desc\n      \(\) \(file\) res/xml/automotive_app_desc.xml type=XML\n', '', new_dump)
new_dump=new_dump.replace('type xml id=17 entryCount=21','type xml id=17 entryCount=20')
if profile.get('dark_outlines'):
 from add_car_resource import extend_table
 from patch_outline_colors import patch_table
 with ZipFile(p/'slack-base.apk') as original,ZipFile(p/'patched-apks/base.apk') as patched:
  assert patched.read('resources.arsc')==patch_table(extend_table(original.read('resources.arsc'))),'Unexpected resource table change beyond the three outline tokens'
 print('PASS: original resource table preserved except three night outline values and appended car descriptor.')
else:
 assert old_dump==new_dump, 'Unexpected original resource table change'
 print('PASS: original resource table preserved; only car descriptor appended.')

car_xml=subprocess.check_output([str(tools/'aapt2'),'dump','xmltree',str(p/'patched-apks/base.apk'),'--file','res/xml/automotive_app_desc.xml'],text=True)
assert '"notification"' in car_xml and '"template"' in car_xml
print('PASS: car descriptor declares calling templates and messaging notifications.')
