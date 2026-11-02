package slack.patches.fold;

public final class FoldLayoutPolicy {
  public static boolean split(float widthDp, float heightDp) { return widthDp >= 680 && heightDp >= 600; }
  public static float fraction(float widthDp, float heightDp, int page) {
    if (!split(widthDp,heightDp) || (page != 1 && page != 2)) return 1f;
    float sidebar = Math.max(340f, Math.min(400f, widthDp * 0.42f)) / widthDp;
    return page == 1 ? sidebar : 1f - sidebar;
  }
}
