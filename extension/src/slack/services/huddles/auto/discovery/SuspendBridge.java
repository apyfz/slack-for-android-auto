package slack.services.huddles.auto.discovery;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import kotlin.ResultKt;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.CoroutineContext;
import kotlin.coroutines.intrinsics.CoroutineSingletons;
import kotlin.coroutines.jvm.internal.SuspendLambda;

/** Callback continuation also satisfies R8's narrowed SuspendLambda parameter. */
final class SuspendBridge extends SuspendLambda {
  static final class Completion implements Continuation<Object> {
    final CountDownLatch done = new CountDownLatch(1);
    final Object job;
    final CoroutineContext context;
    volatile Object result;
    Completion() throws Exception {
      job = Reflect.make("kotlinx.coroutines.JobImpl", (Object) null);
      context = (CoroutineContext) job;
    }
    public CoroutineContext getContext() { return context; }
    public void resumeWith(Object value) { result = value; done.countDown(); }
    void cancel() {
      try { Reflect.call(job, "cancel", new java.util.concurrent.CancellationException("Discovery read finished")); }
      catch (Exception ignored) { }
    }
  }
  final Completion completion;
  SuspendBridge() throws Exception { this(new Completion()); }
  private SuspendBridge(Completion completion) { super(0, completion); this.completion = completion; }
  public Object invokeSuspend(Object result) { return result; }
  void cancel() { completion.cancel(); }
  Object await(Object returned) throws Exception {
    try {
      Object value = returned;
      if (returned == CoroutineSingletons.COROUTINE_SUSPENDED) {
        if (!completion.done.await(20, TimeUnit.SECONDS)) throw new java.io.IOException("Slack read timed out");
        value = completion.result;
      }
      ResultKt.throwOnFailure(value);
      return value;
    } finally {
      completion.cancel();
    }
  }
}
