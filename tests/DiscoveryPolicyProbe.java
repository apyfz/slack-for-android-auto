import slack.services.huddles.auto.discovery.DiscoveryPolicy;

public final class DiscoveryPolicyProbe {
  static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
  public static void main(String[] args) {
    check(DiscoveryPolicy.visible(true, true, 2), "Live member channel missing");
    check(!DiscoveryPolicy.visible(false, true, 2), "Nonmember channel exposed");
    check(!DiscoveryPolicy.visible(true, false, 2), "Ended huddle exposed");
    check(!DiscoveryPolicy.visible(true, true, 0), "Empty huddle exposed");
    check(DiscoveryPolicy.canJoin("T1", "T1", "R1", "R1", true, true, true, 2, true), "Valid selection rejected");
    check(!DiscoveryPolicy.canJoin("T1", "T2", "R1", "R1", true, true, true, 2, true), "Workspace switch ignored");
    check(!DiscoveryPolicy.canJoin("T1", "T1", "R1", "R2", true, true, true, 2, true), "Replaced huddle accepted");
    check(!DiscoveryPolicy.canJoin("T1", "T1", "R1", null, true, true, true, 2, true), "Missing huddle accepted");
    check(!DiscoveryPolicy.canJoin("T1", "T1", "R1", "R1", false, true, true, 2, true), "Failed refresh accepted");
    check(!DiscoveryPolicy.canJoin("T1", "T1", "R1", "R1", true, false, true, 2, true), "Lost membership accepted");
    check(!DiscoveryPolicy.canJoin("T1", "T1", "R1", "R1", true, true, false, 2, true), "Ended huddle accepted");
    check(!DiscoveryPolicy.canJoin("T1", "T1", "R1", "R1", true, true, true, 0, true), "No participants accepted");
    check(!DiscoveryPolicy.canJoin("T1", "T1", "R1", "R1", true, true, true, 2, false), "Disposed screen accepted");
    System.out.println("PASS: membership, ended/missing/replaced huddles, workspace switch, failed refresh and disposal guards");
  }
}
