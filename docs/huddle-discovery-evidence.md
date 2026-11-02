# Huddle discovery implementation and verification

Target: Slack 26.10.40.0 / 90016333. Starting merged APK SHA-256 `224c49a40f32256be2c41f662f6a1dd214bee4a481bcc12635c5f9ab00c4fd20`.

Current installed discovery test APK SHA-256 `8ed693e379f593370db1d102859579cdbf9c2ecb77e8a6e475ef3aa46e57a21e`.

## Native data and template boundaries

- REA `ev_e4173111878906d3c3c22422ce3c2744888c99100371541f2846dd95f12f767a`: native repository paginates `FlannelApi.getHuddleList(100, marker)`. Its convenience refresh swallows errors, so extension reads the native Single through retained `kotlin.math.MathKt.await` with a cancellable Job.
- `ev_a86bca72288415889c3abb103f9c894b5f9d0d54c48f5c6b987204e2256f5b0f`: stock live-huddle membership filter; extension resolves the same conversation data and requires `MultipartyChannel.isMember()`.
- `ev_a3bd2813c1f9add2314e3d55da85bbbe8b71d23a8fc3df267c22346177cbcbbf`: `Huddle.isActive()` plus nonempty active members is required.
- `ev_283d3fd28ee033e236ee4369196a3c3779833b6201618ab8ad8d16293ec432bd`: persisted active account supplies current workspace independently of foreground Activity. The foreground active-team detector is unsuitable because it becomes null on Android Auto/Settings.
- `ev_893aa3d1b2996db315e8d0260cfbd8e816fbed54259406b68394b21dbc5fed08`: R8 narrowed `Screen.onGetTemplate` to MessageTemplate. Narrow class3 call-site hooks return the generic Template only for the new screen; stock call screens keep their original method.
- `ev_c323fc85f000f743be1e1d44119f648a898f3297b178516a0ecb37329d4edfcf`: retained native car model defaults and serializable fields. Builders pruned by R8 are replaced with reflective construction of the original models; click delegates use the original Binder implementation.
- `ev_cac61a78d1b0edf321be0f643b87538039884e5181a968803c12aad534acd711`, `ev_631925d4457e24787f0e05c1e421fbdac999854a45c79371209a6110bc3367ba`: existing join flow and Telecom-mode loss of expected call identity.
- `ev_c9d5a856864d22ecbff773b81075e31bdabe67c26b495e7f48a491e45e96dfec`: first retry Config long is maxRetries; Auto selection uses zero, ordinary requests retain two.

## Verification completed

- Installed on real Fold 8 (SM-F971B), Slack account data retained; installed APK hash equals saved Downloads deliverable.
- Actual native Android Auto ListTemplate rendered, including error/retry and a real eligible huddle row with participant count. Fold Telecom state had no active call during discovery.
- Fresh complete source build succeeded. Its classes3/classes6/classes9 bytes exactly match the installed merged test APK. Added classes9 equals compiled extension; original manifest, resources, native libraries and all other DEX bytes match starting merged APK.
- Full build verification passed original resource-table comparison, appended car descriptor, matching valid signatures and intended DEX checks.
- `DiscoveryPolicyProbe` passes membership, ended/missing/replaced call, workspace mismatch, failed refresh and disposed-screen cases.
- `ReflectProbe` reproduces the old failure on inherited channel-name interface methods and passes the corrected lookup.
- On-device `DiscoveryRuntimeProbe` exercises the real injected coroutine Job and exact-token native/dispatcher cleanup without account or network access.
- On-device `CallTitleProbe` and `NotificationSummaryProbe` pass against final APK. Both mute-patch regression cases pass.
- Native Android model serialization was verified through the actual car host. The standalone `DiscoveryAbiProbe` cannot construct Android Binder objects under bare dalvikvm because framework natives are not registered; that harness failure is not a passing standalone ABI test.

## Remaining runtime boundaries

The user must choose a test huddle for a real Auto-initiated join. No discovery row was clicked during development. Verify visible title cleanup, permissions, join failure, mute/hang-up after a list join, workspace switching/reconnect, locked/knock-only huddles and physical car behavior.

The shipped server contract has no expected-call-ID precondition. Client checks reject known stale states but cannot exclude a huddle ending between GET and POST. The ten-second unbound-service guard cleanup prevents an abandoned selection from indefinitely changing later phone joins; a service-start delay beyond that deadline remains a timing limitation. No atomic guarantee is claimed.

Read-only review found four lifecycle issues; code now pushes the stock screen before starting the join, binds native/dispatcher cleanup to the exact selection token, uses persisted active-account identity, and cancels native coroutine reads on timeout/interruption. No new material blocker was found in focused re-review; owner-initiated join remains the next gate.
