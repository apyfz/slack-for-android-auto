#!/usr/bin/env python3
"""Build a version-pinned Slack Auto patch from user-supplied APKs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA256 = '111955c2933b2d800c162c3340a89e95ef34b7566b8926128c35eb3b0125bd7c'
PROFILES = {
    BASE_SHA256: ('26.10.20.0', '90016283', (3, 6), 3),
    '9dd7d8b33e839650dcf6378a1f772f00b89af7430785a00ca2d4a55a8668b41a':
        ('26.10.40.0', '90016333', (3, 5, 6), 5),
}
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
    parser.add_argument('--huddle-discovery', action='store_true', help='Enable current-workspace discovery (26.10.40.0 only)')
    parser.add_argument('--fold-layout', action='store_true', help='Enable native sidebar/conversation split on large windows (26.10.40.0 only)')
    parser.add_argument('--android-jar', type=Path, help='Android SDK android.jar for discovery compilation')
    parser.add_argument('--kotlin-stdlib', type=Path, help='Local Kotlin stdlib JAR for discovery compilation')
    args = parser.parse_args()
    if not os.environ.get('APK_KEYSTORE_PASSWORD'):
        parser.error('Set APK_KEYSTORE_PASSWORD (never stored in this repository)')
    for path in (args.base, args.arm64, args.density, args.keystore):
        if not path.is_file(): parser.error(f'Missing input: {path}')
    profile = PROFILES.get(hashlib.sha256(args.base.read_bytes()).hexdigest())
    if profile is None:
        parser.error('Unsupported base APK: use a documented, version-pinned Slack APK')
    version, version_code, dex_indices, service_dex = profile
    if args.huddle_discovery or args.fold_layout:
        if version != '26.10.40.0': parser.error('UI extensions support only 26.10.40.0')
        for path in (args.android_jar, args.kotlin_stdlib):
            if path is None or not path.is_file(): parser.error('UI extensions require --android-jar and --kotlin-stdlib')
    if args.fold_layout:
        dex_indices = (2, *dex_indices)
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
        if f"name='com.Slack' versionCode='{version_code}'" not in badging:
            parser.error(f'Wrong package/version: {path}')
    work.mkdir(parents=True)
    (work/'patch-profile.json').write_text(json.dumps({
        'version': version, 'dex_indices': dex_indices, 'service_dex': service_dex,
    }))
    (work/'tools').mkdir()
    for name in ('enable_slack_auto.py', 'add_car_resource.py', 'patch_mute_sync.py', 'patch_notifications.py', 'patch_call_titles.py', 'patch_huddle_discovery.py', 'patch_fold_layout.py', 'patch_fold_surfaces.py', 'patch_outline_colors.py', 'verify_patch.py'):
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
        for index in dex_indices:
            with ZipFile(work/f'classes{index}-wrapper.apk', 'w') as wrapper:
                for name in ('AndroidManifest.xml', 'resources.arsc'):
                    wrapper.writestr(name, source.read(name))
                wrapper.writestr('classes.dex', source.read(f'classes{index}.dex'))
            run('apktool', 'd', '-r', f'classes{index}-wrapper.apk', '-o', f'classes{index}-wrapper')
    service = work/f'classes{service_dex}-wrapper/smali/slack/services/huddles/auto/HuddlesAutoService.smali'
    source = service.read_text()
    assert 'ContributesMultibinding' not in source
    assert source.count('# instance fields') == 1
    service.write_text(source.replace('# instance fields', ANNOTATION+'# instance fields', 1))
    run(sys.executable, 'tools/patch_mute_sync.py', work/'classes6-wrapper/smali/slack/services/huddles/core/impl/meetingsession/ChimeMeetingSessionImpl.smali')
    run(sys.executable, 'tools/patch_notifications.py', work)
    if version == '26.10.40.0':
        run(sys.executable, 'tools/patch_call_titles.py', work/'classes6-wrapper/smali')
    if args.huddle_discovery:
        run(sys.executable, 'tools/patch_huddle_discovery.py', work)
    if args.fold_layout:
        run(sys.executable, 'tools/patch_fold_surfaces.py', work)
        run(sys.executable, 'tools/patch_fold_layout.py', work/'classes2-wrapper/smali')
        # DEX2 is already at 65,536 method references. Relocate only the five
        # patched native UI classes, retaining their exact names and bodies.
        from patch_fold_layout import FILES as fold_files
        native = work/'fold-native-wrapper'
        native.mkdir()
        for name in ('AndroidManifest.xml', 'resources.arsc', 'apktool.yml'):
            shutil.copy2(work/'classes2-wrapper'/name, native/name)
        for relative in fold_files:
            target=native/'smali'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(work/'classes2-wrapper/smali'/relative, target)
        run('apktool', 'b', native, '-o', work/'fold-native.apk')
    if args.huddle_discovery or args.fold_layout:
        run(sys.executable, ROOT/'tools/build_discovery_extension.py', '--work', work/'discovery-extension',
            '--android-jar', args.android_jar.resolve(), '--build-tools', sdk,
            '--kotlin-stdlib', args.kotlin_stdlib.resolve())
    for index in dex_indices:
        run('apktool', 'b', f'classes{index}-wrapper', '-o', f'classes{index}-patched.apk')
    run(sys.executable, 'tools/add_car_resource.py')
    replacements = {}
    for index in dex_indices:
        with ZipFile(work/f'classes{index}-patched.apk') as wrapper:
            replacements[f'classes{index}.dex'] = wrapper.read('classes.dex')
    extra_dex = None
    fold_dex = None
    if args.huddle_discovery or args.fold_layout:
        with ZipFile(args.base) as source:
            import re
            indices = [int(m[1] or 1) for name in source.namelist() if (m := re.fullmatch(r'classes(\d*)\.dex', name))]
        extra_dex = f'classes{max(indices) + 1}.dex'
        with ZipFile(work/'discovery-extension/discovery.jar') as extension:
            replacements[extra_dex] = extension.read('classes.dex')
        metadata = json.loads((work/'patch-profile.json').read_text())
        metadata['discovery_dex'] = extra_dex
        if args.fold_layout:
            fold_dex = f'classes{max(indices) + 2}.dex'
            with ZipFile(work/'fold-native.apk') as native:
                replacements[fold_dex] = native.read('classes.dex')
            metadata['fold_dex'] = fold_dex
            metadata['dark_outlines'] = True
            from patch_outline_colors import patch_table
            with ZipFile(out/'base-resource-safe.apk') as resource_source:
                replacements['resources.arsc'] = patch_table(resource_source.read('resources.arsc'))
        (work/'patch-profile.json').write_text(json.dumps(metadata))
    unsigned = out/'base-final-unsigned.apk'
    with ZipFile(out/'base-resource-safe.apk') as source, ZipFile(unsigned, 'w') as dest:
        for info in source.infolist():
            dest.writestr(info, replacements.get(info.filename, source.read(info.filename)))
        if extra_dex:
            dest.writestr(extra_dex, replacements[extra_dex])
        if fold_dex:
            dest.writestr(fold_dex, replacements[fold_dex])
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
