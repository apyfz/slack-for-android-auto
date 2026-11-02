import android.os.Bundle;
import dalvik.system.DexClassLoader;
import java.lang.reflect.*;
import java.util.*;

/** Runs against real Slack DEX on Android; no messages or notifications are sent. */
public final class NotificationSummaryProbe {
  static void check(boolean ok, String detail) { if (!ok) throw new AssertionError(detail); }
  // Inert identity fixtures for fields the copy operation only carries through;
  // these objects are never called and no PendingIntent is ever sent.
  static Object inert(Class<?> type) throws Exception {
    Class<?> unsafe = Class.forName("sun.misc.Unsafe");
    for (Field f : unsafe.getDeclaredFields()) {
      if (f.getType() == unsafe && Modifier.isStatic(f.getModifiers())) {
        f.setAccessible(true);
        return unsafe.getMethod("allocateInstance", Class.class).invoke(f.get(null), type);
      }
    }
    throw new AssertionError("No allocator for inert fixture");
  }
  public static void main(String[] args) throws Exception {
    ClassLoader loader = new DexClassLoader(args[0], args[1], null, NotificationSummaryProbe.class.getClassLoader());
    Class<?> action = loader.loadClass("androidx.core.app.NotificationCompat$Action");
    Class<?> icon = loader.loadClass("androidx.core.graphics.drawable.IconCompat");
    Class<?> remote = loader.loadClass("androidx.core.app.RemoteInput");
    Class<?> pending = Class.forName("android.app.PendingIntent");
    Class<?> model = loader.loadClass("slack.libraries.notifications.push.model.Notification");
    Constructor<?> ctor = action.getConstructor(icon, CharSequence.class, pending, Bundle.class,
      Array.newInstance(remote, 0).getClass(), boolean.class, int.class, boolean.class);
    Bundle extras = new Bundle(); extras.putString("sentinel", "preserve");
    Object remoteInputs = Array.newInstance(remote, 0);
    Object resourceIcon = icon.getMethod("createWithResource", android.content.res.Resources.class, String.class, int.class)
      .invoke(null, null, "com.Slack", 0x7f080001);
    Object intent = inert(pending);
    Object reply = ctor.newInstance(resourceIcon, "reply", intent, extras, remoteInputs, true, 1, false);
    Object read = ctor.newInstance(null, "read", null, extras, null, false, 2, false);
    Object other = ctor.newInstance(null, "other", null, extras, null, true, 4, true);
    ArrayList<Object> input = new ArrayList<>(Arrays.asList(reply, read, other));
    Constructor<?> modelCtor = null;
    for (Constructor<?> c : model.getConstructors()) if (c.getParameterTypes().length == 17) modelCtor = c;
    check(modelCtor != null, "Missing direct model constructor");
    Class<?>[] types = modelCtor.getParameterTypes();
    Object metadata = inert(types[12]), publicVersion = inert(types[11]);
    Object style = inert(loader.loadClass("slack.libraries.notifications.push.model.Style$Messaging"));
    Object notification = modelCtor.newInstance("child-id", "test-group", false, 2, "test-channel", "workspace",
      "title", "body", intent, null, input, publicVersion, metadata, style, null, null, null);
    Method copy = null;
    for (Method m : model.getDeclaredMethods()) if (m.getName().equals("copy$default")) copy = m;
    check(copy != null, "Missing summary copy method");
    Object summaryNotification = copy.invoke(null, notification, "summary-id", null, null, 81914);
    check(model.getField("isGroupSummary").getBoolean(summaryNotification), "Summary copy flag not set");
    check(model.getField("actions").get(notification) == input, "Summary hook mutated the child list");
    List<?> hooked = (List<?>) model.getField("actions").get(summaryNotification);
    check(hooked != input, "Summary copy still shares Auto actions with child");
    check(((Number) action.getField("mSemanticAction").get(hooked.get(0))).intValue() == 0, "Summary copy still Auto eligible");
    Object childCopy = copy.invoke(null, notification, "unused", null, null, 131071);
    check(model.getField("actions").get(childCopy) == input, "Non-summary copy changed actions");
    check(model.getField("style").get(summaryNotification) == style, "Summary style changed");
    check(model.getField("metadata").get(summaryNotification) == metadata, "Summary metadata changed");
    Method helper = model.getDeclaredMethod("autoSummaryActions", boolean.class, List.class);
    helper.setAccessible(true);
    check(helper.invoke(null, false, input) == input, "Child list must stay identical");
    List<?> summary = (List<?>) helper.invoke(null, true, input);
    check(summary != input && summary.size() == 3, "Summary must clone the list");
    check(summary.get(2) == other, "Unrelated action must stay identical");
    for (int i = 0; i < 2; i++) {
      Object src = input.get(i), dst = summary.get(i);
      check(src != dst, "Summary must not mutate the child's shared Action");
      check(((Number) action.getField("mSemanticAction").get(dst)).intValue() == 0, "Summary must not project as a message");
      check(action.getField("mShowsUserInterface").getBoolean(dst), "Summary should keep phone UI behavior");
      check(((Number) action.getField("mSemanticAction").get(src)).intValue() == i + 1, "Child semantic action changed");
      check(!action.getField("mShowsUserInterface").getBoolean(src), "Child Auto action changed");
      for (String field : new String[]{"mIcon", "title", "actionIntent", "mExtras", "mRemoteInputs", "mAllowGeneratedReplies", "icon"}) {
        Object a = action.getField(field).get(src), b = action.getField(field).get(dst);
        check(a == b || Objects.equals(a,b), "Changed payload: " + field);
      }
    }
    check("preserve".equals(extras.getString("sentinel")), "Action extras mutated");
    check(((List<?>) helper.invoke(null, true, new ArrayList<>())).isEmpty(), "Empty summary failed");
    System.out.println("PASS: child metadata and payloads preserved; summary actions cloned; unrelated actions unchanged");
  }
}
