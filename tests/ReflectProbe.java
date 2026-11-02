package slack.services.huddles.auto.discovery;

public final class ReflectProbe {
  public interface Channel { default String getDisplayName() { return "#design"; } }
  public static final class MemberChannel implements Channel { }
  public static void main(String[] args) throws Exception {
    if (!"#design".equals(Reflect.call(new MemberChannel(), "getDisplayName")))
      throw new AssertionError("Inherited interface channel name unavailable");
    System.out.println("PASS: inherited interface methods resolve through the native channel ABI");
  }
}
