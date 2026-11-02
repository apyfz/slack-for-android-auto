import slack.patches.fold.FoldLayoutPolicy;

public final class FoldLayoutPolicyProbe {
  static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
  public static void main(String[] args) {
    check(FoldLayoutPolicy.split(932,704), "Unfolded landscape must split");
    check(FoldLayoutPolicy.split(704,932), "Unfolded portrait must split");
    check(!FoldLayoutPolicy.split(475,751), "Cover must remain compact");
    check(!FoldLayoutPolicy.split(751,475), "Landscape cover must remain compact");
    check(!FoldLayoutPolicy.split(600,704), "Narrow app window must remain compact");
    for (float width : new float[]{680,704,932,1200}) {
      float sidebar = FoldLayoutPolicy.fraction(width,704,1);
      float content = FoldLayoutPolicy.fraction(width,704,2);
      check(Math.abs(sidebar+content-1f)<0.00001f, "Visible panes must fill exactly one viewport");
      check(sidebar*width>=339.99f && sidebar*width<=400.01f, "Sidebar width out of bounds");
    }
    check(FoldLayoutPolicy.fraction(475,751,1)==1f, "Compact sidebar width changed");
    check(FoldLayoutPolicy.fraction(475,751,2)==1f, "Compact channel width changed");
    System.out.println("PASS: both unfolded orientations, cover, narrow windows and exact two-pane geometry");
  }
}
