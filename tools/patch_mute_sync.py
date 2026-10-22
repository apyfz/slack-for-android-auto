#!/usr/bin/env python3
"""Patch only Slack 26.10.20.0's decoded classes6 ChimeMeetingSessionImpl.
Usage: python3 patch_mute_sync.py path/to/ChimeMeetingSessionImpl.smali
No APK/signing/emulator operations. Fails closed if either original method differs.
"""
import hashlib
import pathlib
import re
import sys

C = 'Lslack/services/huddles/core/impl/meetingsession/ChimeMeetingSessionImpl;'
EXPECTED = {
    'setMute': 'e5c75231cf23ef090171428c49073b89f7f1204432c460cede9dc3694bd3a7b3',
    'onAudioSessionStarted': '092b76d8e863e687f54166f86d8ae4f29c01f29cae13f6e259072ef2edbe68ec',
}
HELPER = r'''
# Huddle Auto: publish actual Chime microphone state to Android Telecom.
# p1 is expected mute (0/1), or -1 to publish initial/reconnected actual state.
.method private syncHuddleMute(I)V
    .locals 4

    :try_start_sync
    iget-boolean v0, p0, CLASS->isTelecom:Z
    if-eqz v0, :sync_done

    sget-object v0, Lcom/amazonaws/services/chime/sdk/meetings/internal/audio/DefaultAudioClientController;->audioClientState:Lcom/amazonaws/services/chime/sdk/meetings/internal/audio/AudioClientState;
    sget-object v1, Lcom/amazonaws/services/chime/sdk/meetings/internal/audio/AudioClientState;->STARTED:Lcom/amazonaws/services/chime/sdk/meetings/internal/audio/AudioClientState;
    if-ne v0, v1, :sync_done

    iget-object v0, p0, CLASS->chimeAudioVideo:Lcom/amazonaws/services/chime/sdk/meetings/audiovideo/AudioVideoFacade;
    if-eqz v0, :sync_done
    check-cast v0, Landroidx/paging/LegacyPageFetcher;
    iget-object v0, v0, Landroidx/paging/LegacyPageFetcher;->source:Ljava/lang/Object;
    if-eqz v0, :sync_done
    check-cast v0, Lcom/slack/data/slog/SlogInfo$Builder;
    iget-object v0, v0, Lcom/slack/data/slog/SlogInfo$Builder;->is_synthetic:Ljava/lang/Object;
    if-eqz v0, :sync_done
    check-cast v0, Lcom/amazonaws/services/chime/sdk/meetings/internal/audio/DefaultAudioClientController;
    iget-object v0, v0, Lcom/amazonaws/services/chime/sdk/meetings/internal/audio/DefaultAudioClientController;->audioClient:Lcom/xodee/client/audio/audioclient/AudioClient;
    if-eqz v0, :sync_done
    invoke-virtual {v0}, Lcom/xodee/client/audio/audioclient/AudioClient;->getMicMute()Z
    move-result v1

    # A failed native mute request must not be reported as applied.
    if-ltz p1, :sync_actual
    if-ne v1, p1, :sync_done
    :sync_actual
    iget-object v0, p0, CLASS->context:Landroid/content/Context;
    if-eqz v0, :sync_done
    const-string v2, "audio"
    invoke-virtual {v0, v2}, Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;
    move-result-object v0
    if-eqz v0, :sync_done
    check-cast v0, Landroid/media/AudioManager;
    invoke-virtual {v0}, Landroid/media/AudioManager;->isMicrophoneMute()Z
    move-result v2
    if-eq v1, v2, :sync_done

    invoke-virtual {v0, v1}, Landroid/media/AudioManager;->setMicrophoneMute(Z)V
    const-string v0, "HuddleAutoSync"
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    const-string v3, "Published actual Chime mute="
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2, v1}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_sync
    .catch Ljava/lang/RuntimeException; {:try_start_sync .. :try_end_sync} :sync_error
    :sync_done
    return-void

    # Integration failure must not terminate a huddle.
    :sync_error
    move-exception v0
    const-string v1, "HuddleAutoSync"
    const-string v2, "Unable to publish microphone state"
    invoke-static {v1, v2, v0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    return-void
.end method
'''.replace('CLASS', C)

def patch(text):
    assert 'syncHuddleMute' not in text, 'Already patched'
    assert f'.class public final {C}' in text
    originals = {}
    for name, digest in EXPECTED.items():
        matches = re.findall(r'^\.method public final ' + name + r'\(Z\)V\n.*?^\.end method', text, re.M | re.S)
        assert len(matches) == 1, f'Expected unique {name}'
        body = matches[0]
        assert hashlib.sha256(body.encode()).hexdigest() == digest, f'Unsupported original {name}'
        originals[name] = body
    mute = originals['setMute']
    assert mute.count('.locals 2') == 1
    # R8 reuses p0 for AudioClient. Preserve original session in new v2.
    mute = mute.replace('.locals 2', '.locals 3\n\n    move-object v2, p0', 1)
    call = '    invoke-virtual {p0, p1}, Lcom/xodee/client/audio/audioclient/AudioClient;->setMicMute(Z)I'
    assert mute.count(call) == 2
    mute = mute.replace(call, call + f'\n\n    invoke-direct {{v2, p1}}, {C}->syncHuddleMute(I)V')
    start = originals['onAudioSessionStarted']
    assert start.count('    return-void') == 1
    # v0 is dead at normal return. p0 still refers to the session on this path.
    start = start.replace('    return-void', f'    const/4 v0, -0x1\n    invoke-direct {{p0, v0}}, {C}->syncHuddleMute(I)V\n\n    return-void', 1)
    result = text.replace(originals['setMute'], mute, 1).replace(originals['onAudioSessionStarted'], start, 1) + HELPER
    assert result.count('->syncHuddleMute(I)V') == 3
    assert result.count('.method private syncHuddleMute(I)V') == 1
    assert result.count('->setMicrophoneMute(Z)V') == text.count('->setMicrophoneMute(Z)V') + 1
    return result

if __name__ == '__main__':
    assert len(sys.argv) == 2, __doc__
    path = pathlib.Path(sys.argv[1])
    assert path.name == 'ChimeMeetingSessionImpl.smali'
    original = path.read_text()
    result = patch(original)
    path.write_text(result)
    print('Patched ChimeMeetingSessionImpl: two native mute hooks and initial/reconnect sync')
