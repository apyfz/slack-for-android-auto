package slack.patches.fold;

import android.app.Activity;
import android.graphics.drawable.*;
import android.util.Log;
import android.view.*;

/** Only structural composer shells; child pills, cards and controls retain their shapes. */
public final class FoldSurfaces {
  static final int WATCH_TAG=0x7f0ffffb,BACKGROUND_TAG=0x7f0ffffa,HEADER_TAG=0x7f0ffff9;
  static void square(Drawable background) {
    if(background instanceof GradientDrawable){((GradientDrawable)background).setCornerRadii(null);((GradientDrawable)background).setCornerRadius(0f);}
    if(background instanceof LayerDrawable){LayerDrawable layers=(LayerDrawable)background;for(int i=0;i<layers.getNumberOfLayers();i++)square(layers.getDrawable(i));}
    else if(background instanceof InsetDrawable)square(((InsetDrawable)background).getDrawable());
    else if(background instanceof StateListDrawable){StateListDrawable states=(StateListDrawable)background;for(int i=0;i<states.getStateCount();i++)square(states.getStateDrawable(i));}
  }
  static void shadeSidebar(View view) {
    if(view==null||view.getClass().getName().contains("Compose"))return;
    Drawable background=view.getBackground();
    boolean base=background instanceof ColorDrawable&&((ColorDrawable)background).getColor()==0xff1a1d21;
    if(background instanceof ColorStateListDrawable){android.content.res.ColorStateList colors=((ColorStateListDrawable)background).getColorStateList();base=colors!=null&&!colors.isStateful()&&colors.getDefaultColor()==0xff1a1d21;}
    if(base)view.setBackgroundColor(0xff17191d);
    if(view instanceof ViewGroup)for(int i=0;i<((ViewGroup)view).getChildCount();i++)shadeSidebar(((ViewGroup)view).getChildAt(i));
  }
  static void alignHeader(Activity activity) {
    View toolbar=activity.findViewById(0x7f0a0cfa);
    if(toolbar==null||toolbar.getHeight()==0)return;
    float[] size=FoldLayout.dimensions(activity);
    boolean wide=FoldLayoutPolicy.split(size[0],size[1]);
    int[] original=(int[])toolbar.getTag(HEADER_TAG);
    if(!wide){if(original!=null){ViewGroup.LayoutParams lp=toolbar.getLayoutParams();lp.height=original[0];toolbar.setLayoutParams(lp);toolbar.setPadding(original[2],original[3],original[4],original[5]);toolbar.setTag(HEADER_TAG,null);}return;}
    if(original==null){original=new int[]{toolbar.getLayoutParams().height,toolbar.getHeight(),toolbar.getPaddingLeft(),toolbar.getPaddingTop(),toolbar.getPaddingRight(),toolbar.getPaddingBottom()};toolbar.setTag(HEADER_TAG,original);}
    // Native sidebar header is 60dp, while the conversation toolbar is 56dp.
    // Include the final physical pixel occupied by the sidebar's hairline.
    int inset=Math.round(4*toolbar.getResources().getDisplayMetrics().density)+1;
    int height=original[1]+inset;
    if(toolbar.getPaddingTop()!=original[3]+inset)toolbar.setPadding(original[2],original[3]+inset,original[4],original[5]);
    ViewGroup.LayoutParams lp=toolbar.getLayoutParams();
    if(lp.height!=height){lp.height=height;toolbar.setLayoutParams(lp);}
  }
  static void update(Activity activity) {
    alignHeader(activity);
    View home=activity.findViewById(0x7f0a0795);
    if(home!=null){
      shadeSidebar(home.findViewById(0x7f0a0964));
      if(home instanceof ViewGroup)((ViewGroup)home).setClipChildren(true);
      View content=home.findViewById(0x7f0a0791);
      if(content instanceof ViewGroup)((ViewGroup)content).setClipChildren(true);
    }
    for(int id:new int[]{0x7f0a00ce,0x7f0a00cf}) {
      View view=activity.findViewById(id);if(view==null)continue;
      Drawable background=view.getBackground();
      if(background!=null&&view.getTag(BACKGROUND_TAG)!=background){
        Drawable.ConstantState state=background.getConstantState();
        Drawable copy=(state==null?background:state.newDrawable(view.getResources())).mutate();square(copy);
        view.setTag(BACKGROUND_TAG,copy);view.setBackground(copy);
        Log.i("SlackFoldLayout","Squared composer shell: "+view.getResources().getResourceEntryName(id)+" "+copy.getClass().getSimpleName());
      }
      if(view.getClipToOutline())view.setOutlineProvider(ViewOutlineProvider.BOUNDS);
    }
  }
  static void attach(Activity activity,View root) {
    if(root.getTag(WATCH_TAG)==null){root.setTag(WATCH_TAG,Boolean.TRUE);root.getViewTreeObserver().addOnGlobalLayoutListener(()->update(activity));}
    update(activity);
  }
}
