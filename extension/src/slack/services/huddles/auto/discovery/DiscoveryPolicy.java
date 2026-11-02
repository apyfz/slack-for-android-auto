package slack.services.huddles.auto.discovery;

public final class DiscoveryPolicy {
  public static boolean visible(boolean member, boolean active, int participants) {
    return member && active && participants > 0;
  }
  public static boolean canJoin(String workspace, String currentWorkspace, String selectedCall,
      String freshCall, boolean refreshed, boolean member, boolean active, int participants,
      boolean screenCurrent) {
    return screenCurrent && refreshed && workspace != null && workspace.equals(currentWorkspace)
        && selectedCall != null && !selectedCall.isEmpty() && selectedCall.equals(freshCall)
        && visible(member, active, participants);
  }
}
