import dalvik.system.DexClassLoader;
import java.lang.reflect.Method;
import java.util.Objects;

/** Runs only the APK's title formatter; never joins a call or sends requests. */
public final class CallTitleProbe {
  public static void main(String[] args) throws Exception {
    ClassLoader loader = new DexClassLoader(args[0], args[1], null, CallTitleProbe.class.getClassLoader());
    Class<?> formatter;
    try { formatter = loader.loadClass("slack.services.huddles.auto.AutoCallTitle"); }
    catch (ClassNotFoundException e) { throw new AssertionError("Call title still has no plain-text cleanup", e); }
    Method clean = formatter.getMethod("clean", String.class);
    String[][] cases = {
      {"\ufffcpracta-test", "practa-test"},
      {"\ufffdpracta-test", "practa-test"},
      {" \ufffc practa-test ", "practa-test"},
      {"#general", "#general"},
      {"设计 — café 🎧", "设计 — café 🎧"},
      {"Ada Lovelace", "Ada Lovelace"},
      {"", ""}, {null, null}
    };
    for (String[] pair : cases) {
      Object actual = clean.invoke(null, pair[0]);
      if (!Objects.equals(pair[1], actual)) throw new AssertionError("Incorrect title cleanup: " + actual);
    }
    System.out.println("PASS: placeholder characters removed; channel names, Unicode and DM names preserved");
  }
}
