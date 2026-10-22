#!/usr/bin/env python3
"""Build a version-pinned Slack Auto patch from user-supplied APKs."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA256 = '111955c2933b2d800c162c3340a89e95ef34b7566b8926128c35eb3b0125bd7c'
ANNOTATION = '''.annotation runtime Lcom/squareup/anvil/annotations/ContributesMultibinding;
    boundType = Landroid/app/Service;
    scope = Lslack/di/AuthenticatedScope;
.end annotation

'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--arm64', required=True, type=Path)
    parser.add_argument('--density', required=True, type=Path, help='Matching xxhdpi or xxxhdpi split')
    parser.add_argument('--build-tools', required=True, type=Path, help='Android SDK build-tools directory')
    parser.add_argument('--keystore', required=True, type=Path)
    parser.add_argument('--alias', required=True)
    parser.add_argument('--work', type=Path, default=ROOT / 'build')
    args = parser.parse_args()
    if not os.environ.get('APK_KEYSTORE_PASSWORD'):
        parser.error('Set APK_KEYSTORE_PASSWORD (never stored in this repository)')
    for path in (args.base, args.arm64, args.density, args.keystore):
        if not path.is_file(): parser.error(f'Missing input: {path}')
    if hashlib.sha256(args.base.read_bytes()).hexdigest() != BASE_SHA256:
        parser.error('Unsupported base APK: expected Slack 26.10.20.0 with the documented SHA-256')
    work = args.work.resolve()
    if work.exists(): parser.error('Work directory already exists; use a new --work directory')
    for binary in ('apktool', 'java'):
        if not shutil.which(binary): parser.error(f'{binary} must be on PATH')
    sdk = args.build_tools.resolve()
    for binary in ('apksigner', 'zipalign', 'aapt2'):
        if not (sdk / binary).is_file(): parser.error(f'Missing build tool: {binary}')
    # Every input split must belong to the same package/version.
    for path in (args.base, args.arm64, args.density):
        badging = subprocess.check_output([str(sdk/'aapt2'), 'dump', 'badging', str(path)], text=True)
        if "name='com.Slack' versionCode='90016283'" not in badging:
            parser.error(f'Wrong package/version: {path}')
    work.mkdir(parents=True)
    (work/'tools').mkdir()
    for name in ('enable_slack_auto.py', 'add_car_resource.py', 'patch_mute_sync.py', 'verify_patch.py'):
        shutil.copy2(ROOT/'tools'/name, work/'tools'/name)
    shutil.copy2(args.base, work/'slack-base.apk')
    out = work/'patched-apks'
    out.mkdir()
    def run(*cmd):
        subprocess.run([str(c) for c in cmd], cwd=work, check=True)
    run('apktool', 'd', '-s', 'slack-base.apk', '-o', 'slack-patched')
    run(sys.executable, 'tools/enable_slack_auto.py')
    run('apktool', 'b', 'slack-patched', '-o', out/'base-unsigned.apk')
    with ZipFile(args.base) as source:
        for index in (3, 6):
            with ZipFile(work/f'classes{index}-wrapper.apk', 'w') as wrapper:
                for name in ('AndroidManifest.xml', 'resources.arsc'):
                    wrapper.writestr(name, source.read(name))
                wrapper.writestr('classes.dex', source.read(f'classes{index}.dex'))
            run('apktool', 'd', '-r', f'classes{index}-wrapper.apk', '-o', f'classes{index}-wrapper')
    service = work/'classes3-wrapper/smali/slack/services/huddles/auto/HuddlesAutoService.smali'
    source = service.read_text()
    assert 'ContributesMultibinding' not in source
    assert source.count('# instance fields') == 1
    service.write_text(source.replace('# instance fields', ANNOTATION+'# instance fields', 1))
    run(sys.executable, 'tools/patch_mute_sync.py', work/'classes6-wrapper/smali/slack/services/huddles/core/impl/meetingsession/ChimeMeetingSessionImpl.smali')
    for index in (3, 6):
        run('apktool', 'b', f'classes{index}-wrapper', '-o', f'classes{index}-patched.apk')
    run(sys.executable, 'tools/add_car_resource.py')
    replacements = {}
    for index in (3, 6):
        with ZipFile(work/f'classes{index}-patched.apk') as wrapper:
            replacements[f'classes{index}.dex'] = wrapper.read('classes.dex')
    unsigned = out/'base-final-unsigned.apk'
    with ZipFile(out/'base-resource-safe.apk') as source, ZipFile(unsigned, 'w') as dest:
        for info in source.infolist():
            dest.writestr(info, replacements.get(info.filename, source.read(info.filename)))
    run(sdk/'zipalign', '-P', '16', '-f', '4', unsigned, out/'base.apk')
    # Normalize split filenames for the verification script; the density itself is unchanged.
    shutil.copy2(args.arm64, out/'split_config.arm64_v8a.apk')
    shutil.copy2(args.density, out/'split_config.xxhdpi.apk')
    for name in ('base.apk', 'split_config.arm64_v8a.apk', 'split_config.xxhdpi.apk'):
        run(sdk/'apksigner', 'sign', '--ks', args.keystore.resolve(), '--ks-key-alias', args.alias,
            '--ks-pass', 'env:APK_KEYSTORE_PASSWORD', out/name)
    env = dict(os.environ, ANDROID_BUILD_TOOLS=str(sdk))
    subprocess.run([sys.executable, str(work/'tools/verify_patch.py')], env=env, check=True)
    print(f'Verified APK set: {out}')

if __name__ == '__main__':
    main()
