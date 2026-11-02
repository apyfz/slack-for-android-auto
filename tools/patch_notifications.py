#!/usr/bin/env python3
"""Add car action metadata to Slack's existing notification handlers."""
import hashlib
from pathlib import Path
import sys

HANDLER = 'Lslack/services/notifications/push/impl/handlers/mentions/MentionNotificationHandlerImpl;'
BUILDER = 'Landroidx/core/app/NotificationCompat$Action$Builder;'
MODEL = 'Lslack/libraries/notifications/push/model/Notification;'
ACTION = 'Landroidx/core/app/NotificationCompat$Action;'
SUPPORTED = {
    ('90caee9e7d0b75a65003e3e6fe26d20d6aa860a8f52c7d4c18c1e9db69d0d685',
     'a3fff3a2f8f7fe5a6bae338f89c020fc51da6ab282b80006763aecb5caab2bbf'): False,
    ('38940d0e4af223c50952d73e505d146722587edfd7d787684029a39c61d5d401',
     '4552ce62b5e83421e8a3d59da6ea49b143c896387827be5274393bdb8a3ea70b'): True,
}

def summary_model(source):
    # Slack clones the first child's MessagingStyle and actions into a second
    # notification with a distinct summary ID. Keep phone actions usable while
    # preventing that copy from becoming a second Auto conversation. Never
    # mutate an Action: the child and summary originally share those objects.
    anchor = f'    iget-object v14, v0, {MODEL}->actions:Ljava/util/List;'
    assert source.count(anchor) == 1, 'Unsupported summary action copy'
    source = source.replace(anchor, anchor + f'''

    invoke-static {{v6, v14}}, {MODEL}->autoSummaryActions(ZLjava/util/List;)Ljava/util/List;
    move-result-object v14''', 1)
    source += f'''
.method private static autoSummaryActions(ZLjava/util/List;)Ljava/util/List;
    .locals 13
    if-eqz p0, :auto_original
    new-instance v9, Ljava/util/ArrayList;
    invoke-direct {{v9}}, Ljava/util/ArrayList;-><init>()V
    invoke-interface {{p1}}, Ljava/util/List;->iterator()Ljava/util/Iterator;
    move-result-object v10
    :auto_loop
    invoke-interface {{v10}}, Ljava/util/Iterator;->hasNext()Z
    move-result v12
    if-eqz v12, :auto_done
    invoke-interface {{v10}}, Ljava/util/Iterator;->next()Ljava/lang/Object;
    move-result-object v11
    check-cast v11, {ACTION}
    iget-boolean v12, v11, {ACTION}->mShowsUserInterface:Z
    if-nez v12, :auto_add_original
    iget-byte v12, v11, {ACTION}->mSemanticAction:B
    const/4 v7, 0x1
    if-eq v12, v7, :auto_clone
    const/4 v7, 0x2
    if-ne v12, v7, :auto_add_original
    :auto_clone
    new-instance v0, {ACTION}
    iget-object v1, v11, {ACTION}->mIcon:Landroidx/core/graphics/drawable/IconCompat;
    iget-object v2, v11, {ACTION}->title:Ljava/lang/CharSequence;
    iget-object v3, v11, {ACTION}->actionIntent:Landroid/app/PendingIntent;
    iget-object v4, v11, {ACTION}->mExtras:Landroid/os/Bundle;
    iget-object v5, v11, {ACTION}->mRemoteInputs:[Landroidx/core/app/RemoteInput;
    iget-boolean v6, v11, {ACTION}->mAllowGeneratedReplies:Z
    const/4 v7, 0x0
    const/4 v8, 0x1
    invoke-direct/range {{v0 .. v8}}, {ACTION}-><init>(Landroidx/core/graphics/drawable/IconCompat;Ljava/lang/CharSequence;Landroid/app/PendingIntent;Landroid/os/Bundle;[Landroidx/core/app/RemoteInput;ZIZ)V
    invoke-virtual {{v9, v0}}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z
    goto :auto_loop
    :auto_add_original
    invoke-virtual {{v9, v11}}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z
    goto :auto_loop
    :auto_done
    return-object v9
    :auto_original
    return-object p1
.end method
'''
    return source

def patch(root):
    builder = root/'classes3-wrapper/smali/androidx/core/app/NotificationCompat$Action$Builder.smali'
    handler = root/'classes6-wrapper/smali/slack/services/notifications/push/impl/handlers/mentions/MentionNotificationHandlerImpl.smali'
    original_builder = builder.read_text()
    original_handler = handler.read_text()
    identity = tuple(hashlib.sha256(s.encode()).hexdigest() for s in (original_builder, original_handler))
    assert identity in SUPPORTED, 'Unsupported action builder/notification handler pair'
    model_result = None
    if SUPPORTED[identity]:
        model = root/'classes3-wrapper/smali/slack/libraries/notifications/push/model/Notification.smali'
        action = root/'classes3-wrapper/smali/androidx/core/app/NotificationCompat$Action.smali'
        model_source = model.read_text()
        assert hashlib.sha256(model_source.encode()).hexdigest() == 'a7392ca7421df9067c4740e977d0d14109fe29c905ac15c04932b6c6e46959c5', 'Unsupported summary model'
        assert hashlib.sha256(action.read_bytes()).hexdigest() == 'c406ae7b19a82c9300a554b33831cbec07ce5948e278283b3becd47257c5a459', 'Unsupported Action constructor'
        model_result = summary_model(model_source)
    # R8 finalized this field because stock Slack never calls its setter. Restore
    # mutability only; retain the original default for every other action.
    field = '.field public final mShowsUserInterface:Z'
    assert original_builder.count(field) == 1
    result_builder = original_builder.replace(field, '.field public mShowsUserInterface:Z', 1)
    read = f'    iput-byte v3, v2, {BUILDER}->mSemanticAction:B'
    assert original_handler.count(read) == 1
    result = original_handler.replace(read, read+f'\n\n    invoke-static {{v2}}, {HANDLER}->configureAutoRead({BUILDER})V', 1)
    # Stock Slack only builds the read action for channel/thread categories.
    # DMs can use UNKNOWN, so include direct-message channel IDs explicitly.
    gate = '    if-ne v2, v3, :cond_27'
    assert result.count(gate) == 1
    result = result.replace(gate, '''    if-eq v2, v3, :cond_28

    invoke-interface/range {p2 .. p2}, Lslack/libraries/notifications/push/model/MessageNotification;->getChannelId()Ljava/lang/String;
    move-result-object v2
    if-eqz v2, :cond_27
    const-string v3, "D"
    invoke-virtual {v2, v3}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v2
    if-eqz v2, :cond_27''', 1)
    for register in ('v10', 'v9', 'v5'):
        call = f'    invoke-virtual {{v3, {register}}}, {BUILDER}->addRemoteInput(Landroidx/core/app/RemoteInput;)V'
        assert result.count(call) == 1
        result = result.replace(call, call+f'\n\n    invoke-static {{v3}}, {HANDLER}->configureAutoReply({BUILDER})V', 1)
    for name, semantic in [('Read', 2), ('Reply', 1)]:
        result += f'''
# Android Auto consumes existing service PendingIntents; no new message transport.
.method private static configureAuto{name}({BUILDER})V
    .locals 1
    const/4 v0, 0x{semantic}
    iput-byte v0, p0, {BUILDER}->mSemanticAction:B
    const/4 v0, 0x0
    iput-boolean v0, p0, {BUILDER}->mShowsUserInterface:Z
    return-void
.end method
'''
    builder.write_text(result_builder)
    handler.write_text(result)
    if model_result is not None:
        model.write_text(model_result)
        print('Patched summary copies: preserve child Auto actions and phone summary actions')
    print('Patched notification metadata: existing read action and three reply branches')

if __name__ == '__main__':
    assert len(sys.argv) == 2, 'Usage: patch_notifications.py WORK_DIRECTORY'
    patch(Path(sys.argv[1]))
