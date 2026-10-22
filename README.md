# Slack for Android Auto

Experimental, unofficial patches that expose Slack huddles through Android Auto’s native call controls. Mute and hang-up are handled by Slack’s existing Telecom integration, with an additional patch to synchronize microphone state when it changes on the phone.

This repository contains patch scripts only. Supply your own Slack APKs. Slack binaries, decompiled sources, account data, and signing keys are not distributed here. This project is not affiliated with Slack or Google.

## What works

- A real Slack huddle appears in Android Auto’s native call dashboard.
- Native mute and hang-up control the huddle.
- Phone-side mute changes and the initial microphone state synchronize with Auto. The initial implementation was tested in an emulator and confirmed by the tester.
- With **Taskbar widgets → Show quick controls for apps** enabled, opening the music app keeps its artwork visible while compact mute and hang-up controls occupy the bottom bar.
- In the emulator, bottom-bar mute callbacks reached Slack with the phone locked and its display off; bottom-bar hang-up ended the real huddle.

The normal dashboard still replaces the media tile with the active call tile. This patch does not change Android Auto’s layout rules. It does not add a custom channel browser or chat interface.

## Compatibility and limitations

The patch is pinned to **Slack 26.10.20.0**, version code **90016283**, ARM64. The base APK must have SHA-256:

```text
111955c2933b2d800c162c3340a89e95ef34b7566b8926128c35eb3b0125bd7c
```

This Slack release requires **Android 12L / API 32 or later**. It cannot run directly on an Android 11 head unit; the tested approach runs Slack on the phone and projects Android Auto to the head unit.

Tested with an Android 15/API 35 emulator and Android Auto 17.9.664044. The modified app was also installed and signed into on an OPPO PKJ110/API 37 with Android Auto 17.8.663874, but physical-car operation and two-party audio remain unverified. Slack’s separately bundled car launcher screen has not been fully validated.

**Google sign-in may fail after re-signing.** Google’s Android OAuth clients identify apps by their package and signing certificate. Use Slack’s **Sign in with email** flow with the same email address and its emailed confirmation code, where your workspace permits it. The emulator and phone were signed in successfully; managed workspaces may impose other requirements.

The modified APK has your own signing certificate. It cannot update the official Slack installation in place: uninstalling official Slack removes local app data and requires signing in again. Keep the same private signing key for future modified builds. Official Play Store updates cannot update this differently signed installation. Every new Slack version requires a fresh compatibility review; do not bypass the version guards.

## Build from your own APKs

Requirements:

- Python 3 and Java 21 (tested)
- Apktool **3.0.3** on `PATH`
- Android SDK build-tools **36.0.0** (tested)
- The supported base APK, its matching ARM64 split, and an xxhdpi or xxxhdpi density split
- Your own signing keystore; keep it outside this repository

For an installed copy, `adb -s PHONE_SERIAL shell pm path com.Slack` lists its APK paths. Pull each required file with `adb pull`. All inputs must belong to the same supported version.

Create a signing key if needed; `keytool` prompts for its password:

```sh
keytool -genkeypair -keystore "$HOME/slack-auto.jks" -alias slack-auto \
  -keyalg RSA -keysize 2048 -validity 10000
```

Set `JAVA_HOME` and `PATH` for your Java installation. Set `APK_KEYSTORE_PASSWORD` in your local shell without saving it in source control, then run:

```sh
python3 tools/build.py \
  --base /path/to/base.apk \
  --arm64 /path/to/split_config.arm64_v8a.apk \
  --density /path/to/split_config.xxxhdpi.apk \
  --build-tools "$ANDROID_HOME/build-tools/36.0.0" \
  --keystore "$HOME/slack-auto.jks" \
  --alias slack-auto
```

The default output directory is `build/patched-apks/`. A build requires a new work directory; use `--work build-next` for a subsequent run. Failed builds leave their files for inspection.

The output density file is normalized to the filename `split_config.xxhdpi.apk`, even when its contents are the supplied xxxhdpi split. Its internal split identity and density are preserved. Install all three output files together:

```sh
adb -s PHONE_SERIAL install-multiple --no-incremental \
  build/patched-apks/base.apk \
  build/patched-apks/split_config.arm64_v8a.apk \
  build/patched-apks/split_config.xxhdpi.apk
```

This command does not uninstall an existing official app automatically. For future builds signed with the same key, add `-r` to update the modified installation.

### OPPO split-installer workaround

The tested OPPO intercepted the split installation and opened only the base APK, reporting **Missing split for com.Slack**. Merging the complete set into one APK resolved this. Use [APKEditor 1.4.9](https://github.com/REAndroid/APKEditor/releases/tag/V1.4.9), obtained separately:

```sh
mkdir -p build/merge-input
cp build/patched-apks/base.apk build/merge-input/
cp build/patched-apks/split_config.arm64_v8a.apk build/merge-input/
cp build/patched-apks/split_config.xxhdpi.apk build/merge-input/
java -jar /path/to/APKEditor-1.4.9.jar m \
  -i build/merge-input -o build/Slack-Auto-unsigned.apk \
  -validate-modules -clean-meta
"$ANDROID_HOME/build-tools/36.0.0/zipalign" -P 16 -f 4 \
  build/Slack-Auto-unsigned.apk build/Slack-Auto.apk
"$ANDROID_HOME/build-tools/36.0.0/apksigner" sign \
  --ks "$HOME/slack-auto.jks" --ks-key-alias slack-auto \
  --ks-pass env:APK_KEYSTORE_PASSWORD build/Slack-Auto.apk
"$ANDROID_HOME/build-tools/36.0.0/apksigner" verify build/Slack-Auto.apk
adb -s PHONE_SERIAL install --no-incremental build/Slack-Auto.apk
```

Merging rewrites the resource container. The split-build resource checks run before this optional step. In the tested merged build, all DEX and native library bytes were also checked against the inputs, and the app launched and signed in successfully.

## Configure Android Auto

1. Sign into modified Slack. Accept microphone and Nearby devices/Bluetooth permissions when prompted.
2. Enable Android Auto developer mode by repeatedly tapping its version entry, then enable **Developer settings → Unknown sources** so Auto can discover the locally signed calling app. This is Android Auto’s setting, separate from Android’s APK-installation permission.
3. Enable **Taskbar widgets → Show quick controls for apps**.
4. Reconnect Android Auto. Start a huddle in a conversation you are authorized to use for testing.
5. Open the music app to use compact call controls in the taskbar. Returning to the dashboard shows the larger call tile.

`headunit-1080p.ini` is the tested Desktop Head Unit configuration: **1920×1080, 248 dpi**. At 160 dpi, this Auto build chose a left taskbar even with quick controls enabled; 248 dpi retained the bottom bar. Screen resolution and UI density are separate settings. The physical car negotiates its own display configuration.

## How the patch works

1. Declare Slack’s existing `HuddlesAutoService` as an exported Android Auto `CALLING` service and add the automotive descriptor.
2. Restore its runtime dependency-injection annotation in `classes3.dex`.
3. In `classes6.dex`, publish actual Chime microphone state to Android’s `AudioManager` after local mute requests and audio-session startup. Skip failed requests and redundant writes to avoid feedback loops.
4. Append the descriptor to the original compiled resource table rather than keeping Apktool’s rebuilt resource table. This preserves existing split-resource references.

`verify_patch.py` checks matching APK signatures, car manifest declarations, unchanged original compiled resources, unchanged DEX files outside the two intended containers, and an unchanged resource-table dump apart from the added descriptor. The mute patch additionally checks hashes of the original methods before modifying them.

These checks establish patch integrity, not complete runtime correctness on every phone or car. No credentials, workspace identifiers, screenshots, or runtime logs are needed to build the patch.

## References

- [Android Auto calling apps](https://developer.android.com/training/cars/communication/calling)
- [Desktop Head Unit testing](https://developer.android.com/training/cars/testing/dhu)
- [Google client authentication and signing certificates](https://developers.google.com/android/guides/client-auth)
- [Slack sign-in methods](https://slack.com/help/articles/212681477-Sign-in-to-Slack)
