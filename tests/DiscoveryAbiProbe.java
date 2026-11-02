import dalvik.system.DexClassLoader;
import java.lang.reflect.*;
import java.util.*;

/** Exercises the shipped AndroidX model/serialization ABI with no account/network access. */
public final class DiscoveryAbiProbe {
  static Object call(Class<?> c, String name, Class<?>[] types, Object... args) throws Exception {
    Method m = c.getDeclaredMethod(name, types); m.setAccessible(true); return m.invoke(null, args);
  }
  public static void main(String[] args) throws Exception {
    ClassLoader loader = new DexClassLoader(args[0], args[1], null, DiscoveryAbiProbe.class.getClassLoader());
    Class<?> screen = loader.loadClass("slack.services.huddles.auto.discovery.DiscoveryScreen");
    Class<?> reflect = loader.loadClass("slack.services.huddles.auto.discovery.Reflect");
    Method make = reflect.getDeclaredMethod("make", String.class, Object[].class); make.setAccessible(true);
    Method set = reflect.getDeclaredMethod("set", Object.class, String.class, Object.class); set.setAccessible(true);
    Object row = call(screen, "row", new Class<?>[]{String.class, String.class, Runnable.class}, "#design", "2 participants · Join", (Runnable) () -> {});
    Object list = make.invoke(null, "androidx.car.app.model.ItemList", new Object[0]);
    set.invoke(null, list, "mItems", Collections.singletonList(row));
    Object template = make.invoke(null, "androidx.car.app.model.ListTemplate", new Object[0]);
    Object title = call(screen, "text", new Class<?>[]{String.class}, "Huddles");
    set.invoke(null, template, "mTitle", title);
    set.invoke(null, template, "mSingleList", list);
    Class<?> bundleable = loader.loadClass("androidx.car.app.serialization.Bundleable");
    Object bundle = bundleable.getMethod("create", Object.class).invoke(null, template);
    Object restored = bundleable.getMethod("get").invoke(bundle);
    if (!template.equals(restored)) throw new AssertionError("List template serialization changed content");
    System.out.println("PASS: native list/row/click delegate and AndroidX template serialization");
  }
}
