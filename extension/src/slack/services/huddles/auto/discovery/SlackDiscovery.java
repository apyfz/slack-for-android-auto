package slack.services.huddles.auto.discovery;

import java.util.*;

/** Uses only the current authenticated Slack component and its native data APIs. */
final class SlackDiscovery {
  static final class Entry {
    final String channel, call, title;
    final int participants;
    Entry(String channel, String call, String title, int participants) {
      this.channel = channel; this.call = call; this.title = title; this.participants = participants;
    }
  }
  final Object component, repo, facade, loggedIn, accountManager, registry;
  final String workspace;
  SlackDiscovery(Object session) throws Exception {
    Object factory = Reflect.field(session, "huddleAutoScreenFactory");
    Object switching = Reflect.field(factory, "this$0");
    component = Reflect.field(switching, "mergedMainAuthenticatedComponentImpl");
    Object unauthenticated = Reflect.field(switching, "mergedMainUnauthenticatedComponentImpl");
    accountManager = Reflect.call(Reflect.field(unauthenticated, "accountManagerDbImplProvider"), "get");
    registry = Reflect.call(Reflect.field(component, "provideScopedDisposableRegistryProvider"), "get");
    Object shard = Reflect.field(component, "mergedMainAuthenticatedComponentImplShard2");
    repo = Reflect.call(Reflect.field(shard, "huddleRepositoryImplProvider"), "get");
    facade = Reflect.call(component, "conversationRepositoryFacade");
    loggedIn = Reflect.field(Reflect.field(component, "loggedInUserProvider"), "instance");
    workspace = (String) Reflect.call(Reflect.field(loggedIn, "team"), "getId");
  }
  String currentWorkspace() throws Exception {
    if (!String.valueOf(Reflect.field(registry, "state")).equals("ACTIVE_OPEN"))
      throw new java.io.IOException("Slack workspace session closed");
    Object current = Reflect.call(accountManager, "getActiveAccount");
    return current == null ? "" : (String) Reflect.field(current, "teamId");
  }
  Object first(Object flow) throws Exception {
    SuspendBridge bridge = new SuspendBridge();
    try { return bridge.await(Reflect.call(Reflect.type("kotlinx.coroutines.flow.StateFlowKt"), "first", flow, bridge)); }
    finally { bridge.cancel(); }
  }
  Object conversation(String channel) throws Exception {
    return first(Reflect.call(Reflect.type("slack.conversations.ConversationRepositoryFacade"),
        "getSyncedConversationById$default", facade, channel));
  }
  boolean member(Object channel) throws Exception {
    Class<?> multiparty = Reflect.type("slack.model.MultipartyChannel");
    return channel != null && multiparty.isInstance(channel) && (Boolean) Reflect.call(channel, "isMember");
  }
  Object toHuddle(Object item) throws Exception {
    return Reflect.call(Reflect.type("androidx.core.graphics.PathParser"), "toHuddle", item);
  }
  Object response(String method, Object... args) throws Exception {
    Object api = Reflect.field(repo, "flannelApi");
    Object single = Reflect.call(api, method, args);
    SuspendBridge bridge = new SuspendBridge();
    try { return bridge.await(Reflect.call(Reflect.type("kotlin.math.MathKt"), "await", single, bridge)); }
    finally { bridge.cancel(); }
  }
  static String clean(String value) {
    return value == null ? "" : value.replace("\ufffc", "").replace("\ufffd", "").trim();
  }
  Entry entry(Object huddle, Object channel) throws Exception {
    List<?> members = (List<?>) Reflect.field(huddle, "activeMembers");
    boolean active = (Boolean) Reflect.call(huddle, "isActive");
    if (!DiscoveryPolicy.visible(member(channel), active, members.size())) return null;
    String title = clean((String) Reflect.call(channel, "getDisplayName"));
    if (title.isEmpty()) title = clean((String) Reflect.call(channel, "getName"));
    if (title.isEmpty()) return null;
    return new Entry((String) Reflect.field(huddle, "channelId"), (String) Reflect.field(huddle, "callId"), title, members.size());
  }
  List<Entry> load() throws Exception {
    if (!workspace.equals(currentWorkspace())) throw new java.io.IOException("Workspace changed");
    List<Object> huddles = new ArrayList<>();
    Set<String> markers = new HashSet<>();
    String marker = null;
    do {
      if (Thread.currentThread().isInterrupted()) throw new InterruptedException();
      Object response = response("getHuddleList", 100, marker);
      for (Object item : (List<?>) Reflect.field(response, "huddles")) huddles.add(toHuddle(item));
      marker = (String) Reflect.field(response, "nextMarker");
      if (marker != null && !markers.add(marker)) throw new java.io.IOException("Repeated discovery page");
    } while (marker != null);
    List<Entry> result = new ArrayList<>();
    Set<String> seen = new HashSet<>();
    for (Object huddle : huddles) {
      if (Thread.currentThread().isInterrupted()) throw new InterruptedException();
      String id = (String) Reflect.field(huddle, "channelId");
      if (!(Boolean) Reflect.call(huddle, "isActive") || ((List<?>) Reflect.field(huddle, "activeMembers")).isEmpty()) continue;
      Entry entry = entry(huddle, conversation(id));
      if (entry != null && seen.add(id)) result.add(entry);
    }
    if (!workspace.equals(currentWorkspace())) throw new java.io.IOException("Workspace changed");
    result.sort((a, b) -> a.title.compareToIgnoreCase(b.title));
    return result;
  }
  Object revalidate(Entry selected, boolean screenCurrent) throws Exception {
    Object response = response("getHuddleInfo", Collections.singleton(selected.channel));
    for (Object item : (List<?>) Reflect.field(response, "huddles")) {
      Object huddle = toHuddle(item);
      if (!selected.channel.equals(Reflect.field(huddle, "channelId"))) continue;
      Object channel = conversation(selected.channel);
      int participants = ((List<?>) Reflect.field(huddle, "activeMembers")).size();
      if (DiscoveryPolicy.canJoin(workspace, currentWorkspace(), selected.call,
          (String) Reflect.field(huddle, "callId"), true, member(channel),
          (Boolean) Reflect.call(huddle, "isActive"), participants, screenCurrent)) return huddle;
    }
    throw new java.io.IOException("This huddle is no longer available");
  }
}
