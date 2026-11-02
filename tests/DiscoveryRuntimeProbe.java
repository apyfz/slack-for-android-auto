import dalvik.system.DexClassLoader;
import java.lang.reflect.*;

/** Tests real injected coroutine cancellation without account or network access. */
public final class DiscoveryRuntimeProbe {
  public static final class NativeContinuation {
    public String $channelId = "test-channel";
    final Object context;
    NativeContinuation(Object context) { this.context = context; }
    public Object getContext() { return context; }
  }
  static Object inert(Class<?> type) throws Exception {
    Class<?> unsafe = Class.forName("sun.misc.Unsafe");
    for (Field f : unsafe.getDeclaredFields()) {
      if (f.getType() == unsafe && Modifier.isStatic(f.getModifiers())) {
        f.setAccessible(true);
        return unsafe.getMethod("allocateInstance", Class.class).invoke(f.get(null), type);
      }
    }
    throw new AssertionError("No inert fixture allocator");
  }
  static Field field(Class<?> type, String name) throws Exception {
    Field f = type.getDeclaredField(name); f.setAccessible(true); return f;
  }
  public static void main(String[] args) throws Exception {
    ClassLoader loader = new DexClassLoader(args[0], args[1], null, DiscoveryRuntimeProbe.class.getClassLoader());
    Class<?> bridgeClass = loader.loadClass("slack.services.huddles.auto.discovery.SuspendBridge");
    Constructor<?> ctor = bridgeClass.getDeclaredConstructor(); ctor.setAccessible(true);
    Object bridge = ctor.newInstance();
    Field completionField = bridgeClass.getDeclaredField("completion"); completionField.setAccessible(true);
    Object completion = completionField.get(bridge);
    Field jobField = completion.getClass().getDeclaredField("job"); jobField.setAccessible(true);
    Object job = jobField.get(completion);
    Class<?> jobType = loader.loadClass("kotlinx.coroutines.Job");
    if (!(Boolean) jobType.getMethod("isActive").invoke(job)) throw new AssertionError("Read job not active");
    Method cancel = bridgeClass.getDeclaredMethod("cancel"); cancel.setAccessible(true); cancel.invoke(bridge);
    if (!(Boolean) jobType.getMethod("isCancelled").invoke(job)) throw new AssertionError("Read job not cancelled");
    System.out.println("PASS: injected read continuation has a working cancellable native coroutine Job");
    Class<?> guard = loader.loadClass("slack.services.huddles.auto.discovery.JoinGuard");
    Class<?> data = loader.loadClass("slack.services.huddles.auto.discovery.SlackDiscovery");
    Object sentinel = inert(data);
    Field pending = field(guard, "pendingData"), token = field(guard, "token");
    Class<?> jobImpl = loader.loadClass("kotlinx.coroutines.JobImpl");
    Constructor<?> jobCtor = jobImpl.getConstructor(jobType);
    Method cancelJob = jobType.getMethod("cancel", java.util.concurrent.CancellationException.class);
    for (boolean superseded : new boolean[]{false, true}) {
      Object nativeJob = jobCtor.newInstance(new Object[]{null});
      pending.set(null, sentinel); field(guard, "pendingChannel").set(null, "test-channel"); token.setLong(null, 23);
      guard.getMethod("watch", Object.class).invoke(null, new NativeContinuation(nativeJob));
      if (superseded) token.setLong(null, 24);
      cancelJob.invoke(nativeJob, new java.util.concurrent.CancellationException("test completed"));
      if ((pending.get(null) != null) != superseded) throw new AssertionError("Native cleanup cleared wrong selection token");
      guard.getMethod("clear").invoke(null);
    }
    Object dispatchJob = jobCtor.newInstance(new Object[]{null});
    pending.set(null, sentinel); token.setLong(null, 25);
    Method track = guard.getDeclaredMethod("trackDispatcher", Object.class); track.setAccessible(true); track.invoke(null, dispatchJob);
    cancelJob.invoke(dispatchJob, new java.util.concurrent.CancellationException("dispatch failed"));
    if (pending.get(null) != null) throw new AssertionError("Failed dispatch retained a guard");
    System.out.println("PASS: native completion/failure clear only their own guard; newer selections preserved");
  }
}
