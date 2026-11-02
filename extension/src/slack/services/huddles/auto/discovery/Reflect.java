package slack.services.huddles.auto.discovery;

import java.lang.reflect.*;

/** Exact-version access to Slack and the R8-reduced Car App ABI. */
final class Reflect {
  static Class<?> type(String name) throws Exception { return Class.forName(name); }
  static Object field(Object object, String name) throws Exception {
    return findField(object instanceof Class ? (Class<?>) object : object.getClass(), name)
        .get(object instanceof Class ? null : object);
  }
  static Field findField(Class<?> type, String name) throws Exception {
    for (Class<?> c = type; c != null; c = c.getSuperclass()) {
      try { Field f = c.getDeclaredField(name); f.setAccessible(true); return f; }
      catch (NoSuchFieldException ignored) { }
    }
    throw new NoSuchFieldException(type.getName() + "." + name);
  }
  static void set(Object object, String name, Object value) throws Exception {
    findField(object.getClass(), name).set(object, value);
  }
  static boolean accepts(Class<?> type, Object value) {
    if (value == null) return !type.isPrimitive();
    if (!type.isPrimitive()) return type.isInstance(value);
    return (type == boolean.class && value instanceof Boolean)
        || (type == int.class && value instanceof Integer)
        || (type == byte.class && value instanceof Byte)
        || (type == long.class && value instanceof Long);
  }
  static boolean accepts(Class<?>[] types, Object[] args) {
    if (types.length != args.length) return false;
    for (int i = 0; i < types.length; i++) if (!accepts(types[i], args[i])) return false;
    return true;
  }
  static Object call(Object object, String name, Object... args) throws Exception {
    Class<?> type = object instanceof Class ? (Class<?>) object : object.getClass();
    Method match = null;
    for (Class<?> c = type; c != null; c = c.getSuperclass()) {
      for (Method m : c.getDeclaredMethods()) {
        if (m.getName().equals(name) && accepts(m.getParameterTypes(), args)) {
          if (match != null && !match.getReturnType().isAssignableFrom(m.getReturnType())) continue;
          match = m;
        }
      }
      if (match != null) break;
    }
    if (match == null) {
      for (Method m : type.getMethods()) {
        if (m.getName().equals(name) && accepts(m.getParameterTypes(), args)) {
          match = m;
          if (!m.isBridge()) break;
        }
      }
    }
    if (match == null) throw new NoSuchMethodException(type.getName() + "." + name);
    match.setAccessible(true);
    try { return match.invoke(object instanceof Class ? null : object, args); }
    catch (InvocationTargetException e) {
      Throwable cause = e.getCause();
      if (cause instanceof Exception) throw (Exception) cause;
      throw e;
    }
  }
  static Object make(String name, Object... args) throws Exception {
    for (Constructor<?> c : type(name).getDeclaredConstructors()) {
      if (accepts(c.getParameterTypes(), args)) {
        c.setAccessible(true); return c.newInstance(args);
      }
    }
    throw new NoSuchMethodException(name + ".<init>");
  }
}
