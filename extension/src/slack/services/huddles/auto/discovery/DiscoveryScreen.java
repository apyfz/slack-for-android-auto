package slack.services.huddles.auto.discovery;

import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import androidx.car.app.CarContext;
import androidx.car.app.Screen;
import androidx.car.app.model.MessageTemplate;
import androidx.car.app.model.Template;
import java.lang.reflect.Proxy;
import java.util.*;
import java.util.concurrent.*;

/** Native current-workspace huddle list alongside Slack's original call screen. */
public final class DiscoveryScreen extends Screen {
  static final String TAG = "HuddleDiscovery";
  static final String MODEL = "androidx.car.app.model.";
  static final int PAGE_SIZE = 3;
  final Object session;
  final Handler main = new Handler(Looper.getMainLooper());
  final ExecutorService worker = Executors.newSingleThreadExecutor();
  SlackDiscovery data;
  List<SlackDiscovery.Entry> entries = Collections.emptyList();
  Future<?> pending;
  volatile int generation;
  boolean visible, destroyed, loading = true, busy;
  String error;
  int page;
  final Runnable tick = new Runnable() {
    public void run() {
      if (visible && !destroyed) {
        if (!busy) refresh(false);
        main.postDelayed(this, 15000);
      }
    }
  };

  public static Screen createScreen(Object session, Intent intent) {
    try {
      if (intent != null && intent.getStringExtra("EXTRA_CHANNEL_ID") != null)
        return (Screen) Reflect.call(session, "makeActiveHuddleScreen", intent);
      CarContext context = (CarContext) Reflect.field(session, "mCarContext");
      return new DiscoveryScreen(context, session);
    } catch (Exception e) {
      Log.e(TAG, "Unable to create discovery screen", e);
      try { return (Screen) Reflect.call(session, "makeActiveHuddleScreen", new Intent()); }
      catch (Exception failure) { throw new IllegalStateException("Slack car screen unavailable", failure); }
    }
  }

  public static Template templateFor(Screen screen) {
    if (screen instanceof DiscoveryScreen) return ((DiscoveryScreen) screen).listTemplate();
    return screen.onGetTemplate();
  }

  public DiscoveryScreen(CarContext context, Object session) throws Exception {
    super(context);
    this.session = session;
    data = new SlackDiscovery(session);
    Class<?> observer = Reflect.type("androidx.lifecycle.LifecycleEventObserver");
    Object proxy = Proxy.newProxyInstance(observer.getClassLoader(), new Class<?>[]{observer}, (p, m, a) -> {
      if (m.getName().equals("onStateChanged")) lifecycle(String.valueOf(a[1]));
      else if (m.getName().equals("hashCode")) return System.identityHashCode(p);
      else if (m.getName().equals("equals")) return p == a[0];
      else if (m.getName().equals("toString")) return "Huddle discovery lifecycle";
      return null;
    });
    Reflect.call(Reflect.call(this, "getLifecycle"), "addObserver", proxy);
  }

  void lifecycle(String event) {
    if (event.equals("ON_START")) {
      visible = true;
      refresh(true);
      main.removeCallbacks(tick); main.postDelayed(tick, 15000);
    } else if (event.equals("ON_STOP") || event.equals("ON_DESTROY")) {
      visible = false; generation++; busy = false;
      if (pending != null) pending.cancel(true);
      main.removeCallbacks(tick);
      if (event.equals("ON_DESTROY")) { destroyed = true; worker.shutdownNow(); }
    }
  }

  void refresh(boolean showLoading) {
    if (destroyed || !visible || busy) return;
    busy = true; error = null;
    if (showLoading) loading = true;
    int request = ++generation;
    invalidateHost();
    pending = worker.submit(() -> {
      try {
        List<SlackDiscovery.Entry> result = data.load();
        main.post(() -> {
          if (!current(request)) return;
          entries = result; page = Math.min(page, Math.max(0, (entries.size() - 1) / PAGE_SIZE));
          loading = false; busy = false; error = null;
          Log.i(TAG, "Loaded eligible live huddles: " + result.size());
          invalidateHost();
        });
      } catch (Exception e) {
        Log.w(TAG, "Discovery refresh failed", e);
        main.post(() -> {
          if (!current(request)) return;
          entries = Collections.emptyList(); loading = false; busy = false;
          error = "Couldn't load huddles. Tap Refresh to try again.";
          invalidateHost();
        });
      }
    });
  }

  boolean current(int request) { return !destroyed && visible && request == generation; }

  void select(SlackDiscovery.Entry selected) {
    if (busy || loading || !visible || destroyed) return;
    busy = true; loading = true; error = null;
    int request = ++generation;
    invalidateHost();
    pending = worker.submit(() -> {
      try {
        Object fresh = data.revalidate(selected, current(request));
        main.post(() -> {
          if (!current(request)) return;
          try {
            // The lower join boundary also checks this exact call ID before dispatch.
            Reflect.call(data.repo, "addOrUpdateHuddle", fresh);
            Screen active = (Screen) Reflect.call(session, "makeActiveHuddleScreen", new Intent());
            push(active);
            JoinGuard.arm(data, selected);
            Object presenter = Reflect.field(active, "presenter");
            Object scope = Reflect.field(presenter, "findTracer");
            Object join = Reflect.make("slack.services.find.recents.impl.RecentsManagerImpl$1$3",
                presenter, selected.channel, null, (byte) 19);
            Object job = Reflect.call(Reflect.type("kotlinx.coroutines.AwaitKt"), "launch$default", scope, null, null, join, 3);
            JoinGuard.trackDispatcher(job);
          } catch (Exception e) {
            Log.w(TAG, "Unable to open selected huddle", e);
            error = "Couldn't join this huddle. Tap Refresh to try again.";
          }
          loading = false; busy = false; invalidateHost();
        });
      } catch (Exception e) {
        Log.w(TAG, "Selected huddle unavailable", e);
        main.post(() -> {
          if (!current(request)) return;
          entries = Collections.emptyList(); loading = false; busy = false;
          error = "This huddle is no longer available. Tap Refresh.";
          invalidateHost();
        });
      }
    });
  }

  void push(Screen screen) throws Exception {
    Object context = Reflect.field(this, "mCarContext");
    Object manager = Reflect.call(context, "getCarService", Reflect.type("androidx.car.app.ScreenManager"));
    Reflect.call(manager, "push", screen);
  }
  void currentHuddle() {
    try { push((Screen) Reflect.call(session, "makeActiveHuddleScreen", new Intent())); }
    catch (Exception e) { Log.w(TAG, "Unable to open current huddle", e); }
  }

  void invalidateHost() {
    if (!visible || destroyed) return;
    try {
      Object context = Reflect.field(this, "mCarContext");
      Object manager = Reflect.call(context, "getCarService", Reflect.type("androidx.car.app.AppManager"));
      Object dispatcher = Reflect.field(manager, "mHostDispatcher");
      Object callback = Reflect.make("androidx.camera.camera2.adapter.ZslControlImpl$$ExternalSyntheticLambda1", (byte) 26);
      Object remote = Reflect.make("androidx.car.app.CarAppBinder$$ExternalSyntheticLambda4", dispatcher, "app", "invalidate", callback);
      Reflect.call(Reflect.type("androidx.car.app.utils.RemoteUtils"), "dispatchCallToHost", "invalidate", remote);
    } catch (Exception e) { Log.w(TAG, "Unable to refresh car template", e); }
  }

  static Object text(String text) throws Exception {
    return Reflect.call(Reflect.type(MODEL + "CarText"), "create", text);
  }
  static Object click(Runnable action) throws Exception {
    Class<?> listener = Reflect.type(MODEL + "OnClickListener");
    Object proxy = Proxy.newProxyInstance(listener.getClassLoader(), new Class<?>[]{listener}, (p, m, a) -> {
      if (m.getName().equals("onClick")) action.run();
      else if (m.getName().equals("hashCode")) return System.identityHashCode(p);
      else if (m.getName().equals("equals")) return p == a[0];
      else if (m.getName().equals("toString")) return "Huddle action";
      return null;
    });
    return Reflect.call(Reflect.type(MODEL + "OnClickDelegateImpl"), "create", proxy);
  }
  static Object row(String title, String subtitle, Runnable action) throws Exception {
    Object row = Reflect.make(MODEL + "Row");
    Reflect.set(row, "mTitle", text(title));
    if (subtitle != null) Reflect.set(row, "mTexts", Collections.singletonList(text(subtitle)));
    Reflect.set(row, "mOnClickDelegate", click(action));
    return row;
  }
  Template listTemplate() {
    try {
      Object template = Reflect.make(MODEL + "ListTemplate");
      Reflect.set(template, "mTitle", text("Huddles"));
      Reflect.set(template, "mHeaderAction", Reflect.field(Reflect.type(MODEL + "Action"), "APP_ICON"));
      Reflect.set(template, "mIsLoading", loading);
      Object refresh = Reflect.make(MODEL + "Action$Builder");
      Reflect.set(refresh, "mTitle", text("Refresh"));
      Reflect.set(refresh, "mOnClickDelegate", click(() -> refresh(true)));
      Object strip = Reflect.make(MODEL + "ActionStrip");
      Reflect.set(strip, "mActions", Collections.singletonList(Reflect.call(refresh, "build")));
      Reflect.set(template, "mActionStrip", strip);
      if (!loading) {
        Object list = Reflect.make(MODEL + "ItemList");
        List<Object> rows = new ArrayList<>();
        rows.add(row("Current huddle", "View call status and controls", this::currentHuddle));
        if (error != null) rows.add(row("Couldn't load huddles", error, () -> refresh(true)));
        else if (entries.isEmpty()) rows.add(row("No active huddles", "Tap Refresh to check again", () -> refresh(true)));
        else {
          if (page > 0) rows.add(row("Previous huddles", null, () -> { page--; invalidateHost(); }));
          int end = Math.min(entries.size(), (page + 1) * PAGE_SIZE);
          for (int i = page * PAGE_SIZE; i < end; i++) {
            SlackDiscovery.Entry entry = entries.get(i);
            rows.add(row(entry.title, entry.participants + (entry.participants == 1 ? " participant · Join" : " participants · Join"), () -> select(entry)));
          }
          if (end < entries.size()) rows.add(row("More huddles", null, () -> { page++; invalidateHost(); }));
        }
        Reflect.set(list, "mItems", rows);
        Reflect.set(template, "mSingleList", list);
      }
      return (Template) template;
    } catch (Exception e) {
      Log.e(TAG, "Unable to render huddle list", e);
      return onGetTemplate();
    }
  }
  @Override public MessageTemplate onGetTemplate() {
    try {
      Object builder = Reflect.make(MODEL + "MessageTemplate$Builder", "Huddles are temporarily unavailable.");
      return (MessageTemplate) Reflect.call(builder, "build");
    } catch (Exception e) { throw new IllegalStateException("Unable to render huddle error", e); }
  }
}
