package slack.services.huddles.auto.discovery;

import android.os.SystemClock;
import java.util.List;
import java.util.concurrent.CancellationException;

/** One explicit Auto selection; native phone-initiated calls remain unchanged. */
public final class JoinGuard {
  static SlackDiscovery pendingData;
  static String pendingChannel, pendingCall;
  static long selectedAt;
  static long token;
  static Object watchedJob;
  static Object dispatcherJob;
  static synchronized void arm(SlackDiscovery data, SlackDiscovery.Entry entry) {
    pendingData = data; pendingChannel = entry.channel; pendingCall = entry.call;
    selectedAt = SystemClock.elapsedRealtime();
    token++; watchedJob = null; dispatcherJob = null;
    long selectedToken = token;
    new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
      synchronized (JoinGuard.class) {
        if (token != selectedToken || pendingData == null || watchedJob != null) return;
        if (dispatcherJob != null) {
          try { Reflect.call(dispatcherJob, "cancel", new CancellationException("Huddle startup timed out")); }
          catch (Exception ignored) { }
        }
        clear();
      }
    }, 10000);
  }
  public static synchronized void clear() {
    pendingData = null; pendingChannel = null; pendingCall = null; selectedAt = 0; watchedJob = null; dispatcherJob = null;
  }
  public static synchronized long retryCount(String channel) {
    return pendingData != null && channel.equals(pendingChannel) ? 0L : 2L;
  }
  static synchronized void trackDispatcher(Object job) throws Exception {
    if (pendingData == null) return;
    long selectedToken = token;
    dispatcherJob = job;
    kotlin.jvm.functions.Function1<Throwable, kotlin.Unit> finished = cause -> {
      if (cause != null) synchronized (JoinGuard.class) { if (token == selectedToken) clear(); }
      return kotlin.Unit.INSTANCE;
    };
    Reflect.call(job, "invokeOnCompletion", finished);
  }
  public static synchronized void watch(Object continuation) {
    if (pendingData == null) return;
    try {
      Object channel = Reflect.field(continuation, "$channelId");
      if (!pendingChannel.equals(channel)) return;
      Object context = Reflect.call(continuation, "getContext");
      Object key = Reflect.field(Reflect.type("kotlinx.coroutines.Job$Key"), "$$INSTANCE");
      Object job = Reflect.call(context, "get", key);
      if (job == null || job == watchedJob) return;
      long selectedToken = token;
      watchedJob = job;
      kotlin.jvm.functions.Function1<Throwable, kotlin.Unit> finished = cause -> {
        synchronized (JoinGuard.class) { if (token == selectedToken) clear(); }
        return kotlin.Unit.INSTANCE;
      };
      Reflect.call(job, "invokeOnCompletion", finished);
    } catch (Exception e) {
      // A selected Auto request must not continue if cleanup cannot be installed.
      throw new CancellationException("Unable to track selected huddle startup");
    }
  }
  public static synchronized void beforeJoin(String channel) {
    if (pendingData == null || !channel.equals(pendingChannel)) return;
    try {
      Object huddle = Reflect.call(Reflect.field(pendingData.repo, "huddleLocalCache"), "getHuddle", channel);
      boolean active = huddle != null && (Boolean) Reflect.call(huddle, "isActive");
      String call = huddle == null ? null : (String) Reflect.field(huddle, "callId");
      int count = huddle == null ? 0 : ((List<?>) Reflect.field(huddle, "activeMembers")).size();
      boolean recent = SystemClock.elapsedRealtime() - selectedAt <= 10000;
      if (!DiscoveryPolicy.canJoin(pendingData.workspace, pendingData.currentWorkspace(), pendingCall,
          call, recent, true, active, count, true)) throw new CancellationException("Selected huddle ended or changed");
    } catch (CancellationException e) { throw e; }
    catch (Exception e) { throw new CancellationException("Unable to verify selected huddle"); }
    finally { clear(); }
  }
}
