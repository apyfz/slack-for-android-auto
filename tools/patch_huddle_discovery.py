#!/usr/bin/env python3
"""Enable the current-workspace discovery screen in exact Slack 26.10.40 code."""
import hashlib
from pathlib import Path
import re
import sys

HOOK = 'Lslack/services/huddles/auto/discovery/DiscoveryScreen;'
HASHES = {
    (3, 'androidx/car/app/AppManager$$ExternalSyntheticLambda2.smali'): 'f4c049ad8465eea3e9b661563b94aad2ad7a59c3ace7f8bad62fe1e9d5388b2d',
    (3, 'androidx/car/app/CarAppBinder.smali'): '62d3e5ff04f4915282584462e8b14e674a6c5a330f234fcedacea00203903028',
    (3, 'androidx/car/app/ScreenManager.smali'): '96e83f888d0ffe172fd376c24a486b6bc28c9a2f88d208293e6ca9b90e0ce2c0',
    (6, 'slack/services/calls/api/ConsolidatedRoomsApiImpl.smali'): '81e648d780cc060e80dce281648f88290b25eb92737012afcfa79bf606c75c14',
    (6, 'slack/services/calls/repository/CallsRepositoryImpl.smali'): '7ed827540b0470db06fbf58824427461edd7813a70a9607cc4d2ccc21f4f5459',
    (6, 'slack/services/huddles/service/impl/telecom/HuddleBaseConnection$joinHuddle$2.smali'): 'a9c190a287f9bdcb6b91e3bb5c61ec9feaf46567328096e274751e682adb984b',
}

def patch(work):
    sources = {}
    for (dex, rel), digest in HASHES.items():
        path = work / f'classes{dex}-wrapper/smali' / rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f'Unsupported discovery hook: {rel}'
        sources[path] = path.read_text()
    for path, original in list(sources.items()):
        text = original
        if path.name == 'AppManager$$ExternalSyntheticLambda2.smali':
            pattern = r'invoke-virtual \{([^}]+)\}, Landroidx/car/app/Screen;->onGetTemplate\(\)Landroidx/car/app/model/MessageTemplate;'
            text, count = re.subn(pattern, lambda m: f'invoke-static {{{m[1]}}}, {HOOK}->templateFor(Landroidx/car/app/Screen;)Landroidx/car/app/model/Template;', text)
            assert count == 2
        elif path.name == 'CarAppBinder.smali':
            pattern = r'invoke-virtual \{([^}]+)\}, Lslack/services/huddles/auto/HuddlesAutoSession;->makeActiveHuddleScreen\(Landroid/content/Intent;\)Lslack/services/huddles/auto/screens/HuddleAutoScreen;'
            text, count = re.subn(pattern, lambda m: f'invoke-static {{{m[1]}}}, {HOOK}->createScreen(Ljava/lang/Object;Landroid/content/Intent;)Landroidx/car/app/Screen;', text)
            assert count == 2
            text, count = re.subn(r'(ScreenManager;->push\()Lslack/services/huddles/auto/screens/HuddleAutoScreen;', r'\1Landroidx/car/app/Screen;', text)
            assert count == 2
        elif path.name == 'ScreenManager.smali':
            assert text.count('Lslack/services/huddles/auto/screens/HuddleAutoScreen;') == 4
            text = text.replace('Lslack/services/huddles/auto/screens/HuddleAutoScreen;', 'Landroidx/car/app/Screen;')
        elif path.name == 'CallsRepositoryImpl.smali':
            method = re.search(r'^\.method public final joinHuddle\(Ljava/lang/String;Ljava/lang/String;ZLslack/telemetry/tracing/TraceContext;Ljava/lang/String;Lkotlin/coroutines/jvm/internal/ContinuationImpl;\)Ljava/lang/Object;\n.*?^\.end method', text, re.M | re.S)
            assert method and hashlib.sha256(method[0].encode()).hexdigest() == 'c584f5ffe4b86fd83e8400db68bbcae3041478889d2f5fc78d20dbd7199100ea'
            assert method[0].count('    const-wide/16 v11, 0x2') == 1
            patched = method[0].replace('    const-wide/16 v11, 0x2', '    invoke-static/range {p1 .. p1}, Lslack/services/huddles/auto/discovery/JoinGuard;->retryCount(Ljava/lang/String;)J\n    move-result-wide v11', 1)
            text = text.replace(method[0], patched, 1)
        elif path.name == 'HuddleBaseConnection$joinHuddle$2.smali':
            marker = '    :pswitch_2\n    sget-object v15, Lkotlin/Unit;->INSTANCE:Lkotlin/Unit;'
            assert text.count(marker) == 1
            text = text.replace(marker, '    :pswitch_2\n    invoke-static {v10}, Lslack/services/huddles/auto/discovery/JoinGuard;->watch(Ljava/lang/Object;)V\n\n    sget-object v15, Lkotlin/Unit;->INSTANCE:Lkotlin/Unit;', 1)
        else:
            line = '    invoke-static/range {v3 .. v14}, Lslack/api/methods/rooms/RoomsApi;->join$default('
            assert text.count(line) == 1
            text = text.replace(line, '    invoke-static {v4}, Lslack/services/huddles/auto/discovery/JoinGuard;->beforeJoin(Ljava/lang/String;)V\n\n' + line, 1)
        sources[path] = text
    for path, text in sources.items(): path.write_text(text)
    print('Patched launcher, generic screen push, native templates and guarded room dispatch')

if __name__ == '__main__':
    assert len(sys.argv) == 2, 'Usage: patch_huddle_discovery.py BUILD_WORK'
    patch(Path(sys.argv[1]))
