package slack.patches.fold;

import android.app.Activity;
import android.content.Context;
import android.content.ContextWrapper;
import android.graphics.Rect;
import android.os.Build;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import java.lang.reflect.*;
import java.util.*;

/** Reuses the native home/channel fragments; no account, message or call behavior. */
public final class FoldLayout {
  static final String TAG = "SlackFoldLayout";
  static Field field(Object target, String name) throws Exception {
    for (Class<?> c=target.getClass(); c!=null; c=c.getSuperclass()) {
      try { Field f=c.getDeclaredField(name); f.setAccessible(true); return f; }
      catch (NoSuchFieldException ignored) { }
    }
    throw new NoSuchFieldException(name);
  }
  static Object get(Object object,String name) throws Exception { return field(object,name).get(object); }
  static void set(Object object,String name,Object value) throws Exception { field(object,name).set(object,value); }
  static Object call(Object object,String name,Class<?>[] types,Object... args) throws Exception {
    for (Class<?> c=object.getClass();c!=null;c=c.getSuperclass()) {
      try { Method m=c.getDeclaredMethod(name,types);m.setAccessible(true);return m.invoke(object,args); }
      catch (NoSuchMethodException ignored) { }
    }
    throw new NoSuchMethodException(name);
  }
  static Activity activity(Context context) {
    while (context instanceof ContextWrapper) {
      if (context instanceof Activity) return (Activity)context;
      Context next=((ContextWrapper)context).getBaseContext();
      if (next==context) break;
      context=next;
    }
    return context instanceof Activity ? (Activity)context : null;
  }
  static float[] dimensions(Activity activity) {
    float density=activity.getResources().getDisplayMetrics().density;
    Rect bounds=Build.VERSION.SDK_INT>=30 ? activity.getWindowManager().getCurrentWindowMetrics().getBounds()
        : new Rect(0,0,activity.getResources().getDisplayMetrics().widthPixels,activity.getResources().getDisplayMetrics().heightPixels);
    float width=bounds.width();
    try { Object pager=get(activity,"viewPager");if (pager instanceof View && ((View)pager).getWidth()>0)width=((View)pager).getWidth(); }
    catch (Exception ignored) { }
    return new float[]{width/density,bounds.height()/density};
  }
  public static float pageWidth(Activity activity,int page) {
    float[] size=dimensions(activity);
    return FoldLayoutPolicy.fraction(size[0],size[1],page);
  }
  public static void attach(View pager) {
    final int[] previous={-1,-1};
    pager.addOnLayoutChangeListener((view,l,t,r,b,ol,ot,or,ob) -> {
      Activity activity=activity(view.getContext());
      if (activity==null) return;
      float[] size=dimensions(activity);
      int split=FoldLayoutPolicy.split(size[0],size[1])?1:0;
      if (previous[0]==view.getWidth() && previous[1]==split) return;
      previous[0]=view.getWidth();previous[1]=split;
      view.post(() -> refresh(view));
    });
  }
  static void refresh(View view) {
    Activity activity=activity(view.getContext());
    if (activity==null || !(view instanceof ViewGroup)) return;
    try {
      Object adapter=get(view,"mAdapter");
      if (adapter==null) return;
      call(view,"completeScroll",new Class<?>[]{boolean.class},false);
      set(view,"mPopulatePending",false);
      List<?> items=new ArrayList<>((List<?>)get(view,"mItems"));
      if (items.isEmpty()) return;
      // R8 removed the native pager's constant-zero page margin field.
      float margin=0f;
      TreeMap<Integer,Object> ordered=new TreeMap<>();
      for(Object item:items)ordered.put(((Number)get(item,"position")).intValue(),item);
      float offset=0;int nextPosition=0;
      Object first=null,last=null;
      for (Object item:ordered.values()) {
        int position=((Number)get(item,"position")).intValue();
        while(nextPosition<position) {
          offset+=((Number)call(adapter,"getPageWidth",new Class<?>[]{int.class},nextPosition++)).floatValue()+margin;
        }
        float width=((Number)call(adapter,"getPageWidth",new Class<?>[]{int.class},position)).floatValue();
        set(item,"widthFactor",width);set(item,"offset",offset);
        offset+=width+margin;
        nextPosition=position+1;
        if (first==null)first=item;last=item;
      }
      int count=((Number)call(adapter,"getCount",new Class<?>[0])).intValue();
      set(view,"mFirstOffset",((Number)get(first,"position")).intValue()==0?((Number)get(first,"offset")).floatValue():-Float.MAX_VALUE);
      set(view,"mLastOffset",((Number)get(last,"position")).intValue()==count-1?((Number)get(last,"offset")).floatValue()+((Number)get(last,"widthFactor")).floatValue()-1f:Float.MAX_VALUE);
      ViewGroup pager=(ViewGroup)view;
      for(int i=0;i<pager.getChildCount();i++) {
        View child=pager.getChildAt(i);Object lp=child.getLayoutParams();
        if ((Boolean)get(lp,"isDecor"))continue;
        set(lp,"widthFactor",0f);set(lp,"needsMeasure",true);
      }
      call(view,"populate",new Class<?>[0]);
      view.requestLayout();
      view.post(() -> {
        try {
          int current=((Number)get(view,"mCurItem")).intValue();
          call(view,"scrollToItem",new Class<?>[]{int.class,int.class,boolean.class,boolean.class},current,0,false,false);
          onPageSelected(activity);
        } catch(Exception e) { Log.w(TAG,"Unable to align resized panes",e); }
      });
      float[] size=dimensions(activity);
      Log.i(TAG,"Native pane geometry: widthDp="+Math.round(size[0])+", split="+FoldLayoutPolicy.split(size[0],size[1]));
    } catch(Exception e) { Log.w(TAG,"Unable to update native pane widths",e); }
  }
  public static void onPageSelected(Activity activity) {
    try {
      Object pager=get(activity,"viewPager");
      int current=((Number)get(pager,"mCurItem")).intValue();
      Object home=call(activity,"getNavHomeFragment",new Class<?>[0]);
      if(home==null)return;
      float[] size=dimensions(activity);
      boolean visible=FoldLayoutPolicy.split(size[0],size[1]) && current!=0;
      FoldRail.layout(activity,FoldLayoutPolicy.split(size[0],size[1]));
      if(visible && current==1 && pager instanceof View) ((View)pager).post(() -> {
        try {call(pager,"scrollToItem",new Class<?>[]{int.class,int.class,boolean.class,boolean.class},2,0,false,false);}
        catch(Exception e){Log.w(TAG,"Unable to align home navigation panes",e);}
      });
      int importance=visible || current==1 ? View.IMPORTANT_FOR_ACCESSIBILITY_AUTO : View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS;
      set(home,"importantForAccessibility",importance);
      call(home,"updateImportantForAccessibility",new Class<?>[]{Integer.class},(Object)null);
      View shroud=activity.findViewById(0x7f0a0796);
      if(shroud!=null) {
        shroud.setVisibility(visible?View.GONE:View.VISIBLE);
      }
    } catch(Exception e) { Log.w(TAG,"Unable to update sidebar accessibility",e); }
  }
}
