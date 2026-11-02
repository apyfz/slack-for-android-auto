#!/usr/bin/env python3
"""Version-pinned native Slack home/sidebar and message split for large windows."""
import hashlib
from pathlib import Path
import re
import sys

BASE='slack/features/home/'
FILES={
 BASE.replace('slack/features/home/','slack/features/navigationview/navhome/buttonbar/')+'NavButtonBarUiKt.smali':'d0fa4901ddcc442bbe5860ac7b88c1700e3e37d478810a9b41a329423cf013c3',
 BASE+'v2/HomeUiKt$$ExternalSyntheticLambda9.smali':'610207abf77519319d95fb238fbf1eeefce6d5f16908848a6303f9dd7d5d4ac1',
 BASE+'VintageHomeActivity$setupViewPager$1.smali':'1725a6f596461a616c011a4bcfd8ac787006ba3f846291fafe586467ec8ef76f',
 BASE+'VintageHomeActivity$setupViewPager$2.smali':'5cba9e248f096ecc8126c92b2eebde0cb6cc4edb215e72be3952c39dbda03a52',
 BASE+'widgets/CustomSwipingViewPager.smali':'655bf942ed3a0b0ae60495a3d547d7881ffadeee826583803fdb5deb55fc584b',
}
HELPER='Lslack/patches/fold/FoldLayout;'

def patch(root):
 sources={}
 for rel,digest in FILES.items():
  p=root/rel
  assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,f'Unsupported native fold hook: {rel}'
  sources[p]=p.read_text()
 for p,text in list(sources.items()):
  if p.name=='NavButtonBarUiKt.smali':
   old='    iget-wide v10, p2, Lslack/kit/usertheme/BaseSet;->secondary:J'
   assert text.count(old)==1
   text=text.replace(old,old+'\n    invoke-static {v10, v11, v5}, Lslack/patches/fold/FoldRail;->railColor(JLjava/lang/Object;)J\n    move-result-wide v10')
  elif p.name=='HomeUiKt$$ExternalSyntheticLambda9.smali':
   start=text.index('    :pswitch_14\n');end=text.index('    :pswitch_15\n',start) if '    :pswitch_15\n' in text[start:] else len(text)
   # Switch labels are descending in this R8 class: end at the next case.
   match=re.search(r'(?=^    :pswitch_[0-9a-f]+$)',text[start+len('    :pswitch_14\n'):],re.M)
   if match:end=start+len('    :pswitch_14\n')+match.start()
   block=text[start:end]
   old='invoke-static {v1, v3, v2, v4}, Landroidx/compose/foundation/layout/RowKt;->rowMeasurePolicy(Landroidx/compose/foundation/layout/Arrangement$Horizontal;Landroidx/compose/ui/Alignment$Vertical;Landroidx/compose/runtime/Composer;I)Landroidx/compose/foundation/layout/RowMeasurePolicy;'
   assert block.count(old)==1
   block=block.replace(old,'invoke-static {v1, v3, v2, v4}, Lslack/patches/fold/FoldRail;->measure(Ljava/lang/Object;Ljava/lang/Object;Ljava/lang/Object;I)Ljava/lang/Object;')
   old='    sget-object v0, Landroidx/compose/foundation/layout/RowScopeInstance;->INSTANCE:Landroidx/compose/foundation/layout/RowScopeInstance;'
   assert block.count(old)==1
   block=block.replace(old,old+'\n    invoke-static {v0, v2}, Lslack/patches/fold/FoldRail;->scope(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;\n    move-result-object v0\n    check-cast v0, Landroidx/compose/foundation/layout/RowScope;')
   text=text[:start]+block+text[end:]
  elif p.name.endswith('$1.smali'):
   match=re.search(r'^\.method public final getPageWidth\(I\)F\n.*?^\.end method',text,re.M|re.S)
   assert match and hashlib.sha256(match[0].encode()).hexdigest()=='eb0dc8eef589c06185d1fa845104c9c215bc846c7f6d33cd281f523a8a7dab30'
   old='    :cond_0\n    const/high16 p0, 0x3f800000    # 1.0f'
   new='    :cond_0\n    iget-object v0, p0, Lslack/features/home/VintageHomeActivity$setupViewPager$1;->this$0:Lslack/features/home/VintageHomeActivity;\n    invoke-static {v0, p1}, '+HELPER+'->pageWidth(Landroid/app/Activity;I)F\n    move-result p0'
   assert match[0].count(old)==1
   text=text.replace(match[0],match[0].replace(old,new),1)
  elif p.name.endswith('$2.smali'):
   match=re.search(r'^\.method public final onPageSelected\(I\)V\n.*?^\.end method',text,re.M|re.S)
   assert match and match[0].count('    return-void')==1
   updated=match[0].replace('    return-void','    invoke-static {v6}, '+HELPER+'->onPageSelected(Landroid/app/Activity;)V\n\n    return-void')
   text=text.replace(match[0],updated,1)
  else:
   match=re.search(r'^\.method public constructor <init>\(Landroid/content/Context;Landroid/util/AttributeSet;\)V\n.*?^\.end method',text,re.M|re.S)
   assert match and match[0].count('    return-void')==1
   updated=match[0].replace('    return-void','    invoke-static {p0}, '+HELPER+'->attach(Landroid/view/View;)V\n\n    return-void')
   text=text.replace(match[0],updated,1)
  sources[p]=text
 for p,text in sources.items():p.write_text(text)
 print('Patched native page widths, resize listener and visible-sidebar accessibility')

if __name__=='__main__':
 assert len(sys.argv)==2,'Usage: patch_fold_layout.py CLASSES2_SMALI'
 patch(Path(sys.argv[1]))
