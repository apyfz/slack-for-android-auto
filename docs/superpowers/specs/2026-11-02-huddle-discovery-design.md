# Android Auto huddle discovery

Approved in chat: current Slack workspace, active huddles the signed-in user can join, native list, channel names and participant counts, refresh/loading/empty/error states, fresh eligibility check before joining. Preserve native call controls and never join automatically.

Use Slack 26.10.40.0's existing authenticated HuddleRepositoryImpl and conversation membership model. Keep credentials inside Slack. Reuse the existing Auto join path after a deliberate row tap. Do not enumerate private channels outside the signed-in user's membership. Reject known stale, missing, ended or replaced huddles before joining.

Backend limitation found during implementation: native `rooms.join` accepts channel ID, without an expected-call-ID precondition. Fresh selection checks and a second cache/call-ID check immediately before API dispatch prevent known stale joins, but cannot atomically exclude a huddle ending between the final client check and server processing. Disable Slack's application-level join retries for a guarded Auto selection, preserve normal phone-call retries, and document this residual race.

Use a native Android Auto ListTemplate and lifecycle-bound work. The implementation must account for R8's narrowed Screen.onGetTemplate return type and merged builders without replacing the working native Telecom integration. Keep the existing active-call screen reachable. Current workspace changes must invalidate pending results and row selections.

Validation: pin exact original artifact and method hashes; test filtering/stale selection and Unicode titles; build/sign with existing certificate; verify only intended DEX members changed and resources are preserved; install in place on Fold 8 and inspect the actual car screen. Only the user chooses a real huddle to join. Empty discovery is not proof of complete discovery coverage; verify a known active eligible huddle when available.
