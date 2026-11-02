# Android Auto Huddle Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show active joinable huddles in the current Slack workspace on Android Auto.

**Architecture:** Inject a small native car-screen extension into the version-pinned Slack APK. Reuse Slack's authenticated repository and existing join flow; adapt the R8-reduced car-template boundary with narrowly guarded patches.

**Tech Stack:** Java, AndroidX Car App models already in Slack, Kotlin coroutine/flow interoperability, smali, Python patch tooling, Android SDK.

**Spec:** `docs/superpowers/specs/2026-11-02-huddle-discovery-design.md`

## Global Constraints

- Slack 26.10.40.0 / versionCode 90016333 only; source APK hash must match the supported profile.
- Current workspace only; no credentials exported and no automatic join.
- Preserve existing native mute/hang-up and account data.
- Selection must recheck membership and active participants after a fresh read.
- Reject known missing/ended/stale huddles at selection and native API dispatch; disable application-level retries for Auto selections. The native backend lacks atomic join-existing preconditions (see spec).
- No commits, pushes, or OPPO installation included in this task.

## Review Focus

- Huddle ends between rendering and selection: recheck before dispatch and show unavailable.
- Workspace changes during an async request: discard result and selection.
- Discovery refresh fails: clear selection eligibility, show retry, do not treat stale cache as fresh.
- Unknown or private nonmember conversation: omit row.
- Car host destroys screen during a request: cancel work and ignore callbacks.

### Task 1: Pin the extension and template boundaries

**Files:** `tools/patch_huddle_discovery.py`, `tools/build.py`, `docs/huddle-discovery-evidence.md`.

- [x] Record current repository/provider/join descriptors and the R8 car ABI.
- [x] Add fail-closed guards for exact methods and required class inventory.
- [x] Verify an unsupported source is rejected before any mutation.

### Task 2: Implement discovery and guarded selection

**Files:** `extension/src/slack/services/huddles/auto/discovery/DiscoveryScreen.java`, related small adapters, `tests/DiscoveryPolicyProbe.java`.

**Interfaces:** entry factory consumes existing Auto session/authenticated component and returns the discovery screen; adapter reads repository huddles and membership; click handler delegates to existing channel join flow only after refresh and revalidation.

- [x] Write failing policy tests for active participants, membership, ended/missing huddle, workspace mismatch, refresh failure and screen disposal.
- [x] Implement lifecycle-bound authenticated reads, deterministic list ordering and bounded native rows.
- [x] Implement explicit row selection with revalidation and one in-flight join.
- [x] Run tests against compiled extension DEX and verify empty/error/Unicode cases.

### Task 3: Render, package and verify on Fold

**Files:** template adapter/patch, `tools/build.py`, `README.md`.

- [x] Render ListTemplate with loading, empty, error, refresh and live-huddle rows.
- [x] Preserve active huddle screen and native Telecom controls.
- [x] Build with the original signing certificate and inspect exact changed members.
- [x] Run title, notification-summary and mute regressions.
- [x] Install in place and inspect loading/empty/error/list states in DHU.
- [ ] Ask user to select a known active eligible huddle for live join validation; verify actual call state and title.
- [x] Record live verification boundaries and any unresolved join restrictions.
