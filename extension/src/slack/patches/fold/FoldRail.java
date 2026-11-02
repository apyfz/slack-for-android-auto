package slack.patches.fold;

import android.app.Activity;
import android.graphics.*;
import android.graphics.drawable.Drawable;
import android.util.Log;
import android.view.*;
import java.lang.reflect.*;
import java.util.*;

/** Adapts the existing Material navigation items, retaining their events and badges. */
public final class FoldRail {
  static Object constant(String type,String name) throws Exception {return Class.forName(type).getField(name).get(null);}
  static Object invoke(String type,String name,Object... args) throws Exception {
    for(Method m:Class.forName(type).getMethods()) if(m.getName().equals(name)&&m.getParameterCount()==args.length)return m.invoke(null,args);
    throw new NoSuchMethodException(type+"."+name);
  }
  static Object consume(Object composer,Object local) throws Exception {
    return FoldLayout.call(composer,"consume",new Class<?>[]{Class.forName("androidx.compose.runtime.ProvidableCompositionLocal")},local);
  }
  static boolean enabled(Object composer) {
    try {
      String locals="androidx.compose.ui.platform.AndroidCompositionLocals_androidKt";
      consume(composer,constant(locals,"LocalConfiguration"));
      View view=(View)consume(composer,constant(locals,"LocalView"));
      for(View candidate=view;candidate!=null;) {
        if(candidate.getId()==0x7f0a031d) {
          Activity activity=FoldLayout.activity(view.getContext());
          if(activity==null)return false;
          float[] size=FoldLayout.dimensions(activity);
          return FoldLayoutPolicy.split(size[0],size[1]);
        }
        ViewParent parent=candidate.getParent();candidate=parent instanceof View?(View)parent:null;
      }
    }catch(Exception e){Log.w(FoldLayout.TAG,"Unable to resolve navigation rail window",e);}
    return false;
  }
  public static long railColor(long original,Object composer) {
    return enabled(composer)?0xff11131600000000L:original;
  }
  public static Object measure(Object arrangement,Object alignment,Object composer,int flags) {
    try {
      if(enabled(composer)) return invoke("androidx.compose.foundation.layout.ColumnKt","columnMeasurePolicy",
          constant("androidx.compose.foundation.layout.OffsetKt","Top"),constant("androidx.compose.ui.Alignment$Companion","CenterHorizontally"),composer,0);
      return invoke("androidx.compose.foundation.layout.RowKt","rowMeasurePolicy",arrangement,alignment,composer,flags);
    }catch(Exception e){throw new IllegalStateException("Native navigation measure policy",e);}
  }
  public static Object scope(Object original,Object composer) {
    if(!enabled(composer))return original;
    try {
      Class<?> scope=Class.forName("androidx.compose.foundation.layout.RowScope");
      return Proxy.newProxyInstance(scope.getClassLoader(),new Class<?>[]{scope},(proxy,method,args)->{
        if(method.getName().equals("weight")) {
          Object modifier=args[1];
          modifier=invoke("androidx.compose.foundation.layout.SizeKt","fillMaxWidth",modifier,1f);
          return invoke("androidx.compose.foundation.layout.SizeKt","height-3ABfNKs",modifier,80f);
        }
        if(method.getName().equals("align"))return args[0];
        return method.invoke(original,args);
      });
    }catch(Exception e){Log.w(FoldLayout.TAG,"Unable to adapt navigation item scope",e);return original;}
  }
  static final int SNAPSHOT_TAG=0x7f0ffffe;
  static class Snapshot {
    final View bar,content;final Object barParams,contentParams;final Drawable foreground;
    final int[] padding;
    final Map<String,Object> barFields=new HashMap<>(),contentFields=new HashMap<>();
    Snapshot(View root,View bar,View content)throws Exception {
      this.bar=bar;this.content=content;barParams=bar.getLayoutParams();contentParams=content.getLayoutParams();foreground=root.getForeground();padding=new int[]{bar.getPaddingLeft(),bar.getPaddingTop(),bar.getPaddingRight(),bar.getPaddingBottom()};
      for(String name:new String[]{"width","height","topToTop","bottomToBottom","bottomToTop","startToStart","endToEnd"}) {
        barFields.put(name,FoldLayout.get(barParams,name));contentFields.put(name,FoldLayout.get(contentParams,name));
      }
      contentFields.put("topMargin",((ViewGroup.MarginLayoutParams)contentParams).topMargin);
      contentFields.put("startMargin",((ViewGroup.MarginLayoutParams)contentParams).getMarginStart());
    }
    void restore(View root)throws Exception {
      for(Map.Entry<String,Object> e:barFields.entrySet())FoldLayout.set(barParams,e.getKey(),e.getValue());
      for(Map.Entry<String,Object> e:contentFields.entrySet())if(!e.getKey().equals("startMargin")&&!e.getKey().equals("topMargin"))FoldLayout.set(contentParams,e.getKey(),e.getValue());
      ((ViewGroup.MarginLayoutParams)contentParams).setMarginStart((Integer)contentFields.get("startMargin"));
      ((ViewGroup.MarginLayoutParams)contentParams).topMargin=(Integer)contentFields.get("topMargin");
      bar.setLayoutParams((ViewGroup.LayoutParams)barParams);content.setLayoutParams((ViewGroup.LayoutParams)contentParams);root.setForeground(foreground);bar.setPadding(padding[0],padding[1],padding[2],padding[3]);
    }
  }
  static final int STATUS_TAG=0x7f0ffffd;
  static class StatusArea {
    final Drawable foreground;
    StatusArea(View view){foreground=view.getForeground();}
  }
  static void statusSpace(View view,int top,boolean wide) {
    if(view==null)return;
    StatusArea state=(StatusArea)view.getTag(STATUS_TAG);
    if(!wide){if(state!=null){view.setForeground(state.foreground);view.setTag(STATUS_TAG,null);}return;}
    if(state==null){state=new StatusArea(view);view.setTag(STATUS_TAG,state);}
    final Drawable original=state.foreground;
    final Paint background=new Paint();background.setColor(view.getId()==0x7f0a0791?0xff17191d:0xff1a1d21);
    view.setForeground(new Drawable(){
      public void draw(Canvas canvas){if(original!=null){original.setBounds(getBounds());original.draw(canvas);}Rect b=getBounds();canvas.drawRect(b.left,b.top,b.right,b.top+top,background);}
      public void setAlpha(int alpha){background.setAlpha(alpha);}public void setColorFilter(ColorFilter filter){background.setColorFilter(filter);}public int getOpacity(){return PixelFormat.TRANSLUCENT;}
    });
  }
  static void layout(Activity activity,boolean wide)throws Exception {
    View root=activity.findViewById(0x7f0a0795),bar=activity.findViewById(0x7f0a031d),content=activity.findViewById(0x7f0a0791);
    if(root==null||bar==null||content==null)return;
    Snapshot state=(Snapshot)root.getTag(SNAPSHOT_TAG);
    if(!wide){statusSpace(content,0,false);statusSpace(activity.findViewById(0x7f0a0794),0,false);if(state!=null){state.restore(root);root.setTag(SNAPSHOT_TAG,null);}return;}
    if(state==null){state=new Snapshot(root,bar,content);root.setTag(SNAPSHOT_TAG,state);}
    int rail=Math.round(80*root.getResources().getDisplayMetrics().density);
    int top=root.getRootWindowInsets()==null?0:(android.os.Build.VERSION.SDK_INT>=30?root.getRootWindowInsets().getInsets(WindowInsets.Type.statusBars()).top:root.getRootWindowInsets().getSystemWindowInsetTop());
    bar.setPadding(bar.getPaddingLeft(),top,bar.getPaddingRight(),bar.getPaddingBottom());
    ((ViewGroup.MarginLayoutParams)state.contentParams).topMargin=(Integer)state.contentFields.get("topMargin");
    statusSpace(content,top,true);
    statusSpace(activity.findViewById(0x7f0a0794),top,true);
    FoldLayout.set(state.barParams,"width",rail);FoldLayout.set(state.barParams,"height",0);
    FoldLayout.set(state.barParams,"topToTop",0);FoldLayout.set(state.barParams,"bottomToBottom",0);
    FoldLayout.set(state.barParams,"startToStart",0);FoldLayout.set(state.barParams,"endToEnd",-1);
    FoldLayout.set(state.contentParams,"bottomToTop",-1);FoldLayout.set(state.contentParams,"bottomToBottom",0);
    ((ViewGroup.MarginLayoutParams)state.contentParams).setMarginStart(rail);
    bar.setLayoutParams((ViewGroup.LayoutParams)state.barParams);content.setLayoutParams((ViewGroup.LayoutParams)state.contentParams);
    root.setBackgroundColor(0xff17191d);bar.setBackgroundColor(0xff111316);
    FoldSurfaces.attach(activity,root);
    final Drawable previous=state.foreground;
    final Paint paint=new Paint();paint.setColor(root.getContext().getColor(0x7f06010d));
    final float stroke=1f;
    root.setForeground(new Drawable(){
      public void draw(Canvas canvas){if(previous!=null){previous.setBounds(getBounds());previous.draw(canvas);}Rect b=getBounds();canvas.drawRect(rail-stroke,b.top,rail,b.bottom,paint);canvas.drawRect(b.right-stroke,b.top,b.right,b.bottom,paint);}
      public void setAlpha(int alpha){paint.setAlpha(alpha);}public void setColorFilter(ColorFilter filter){paint.setColorFilter(filter);}public int getOpacity(){return PixelFormat.TRANSLUCENT;}
    });
  }
}
