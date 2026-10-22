#!/usr/bin/env python3
"""Enable the shipped Slack 26.10.20.0 car service; original DEX stays untouched."""
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]/'slack-patched'
p=root/'AndroidManifest.xml'
ns='http://schemas.android.com/apk/res/android'
ET.register_namespace('android',ns)
a=lambda x:'{'+ns+'}'+x
tree=ET.parse(p); manifest=tree.getroot(); app=manifest.find('application')
assert manifest.get('package')=='com.Slack'
service_name='slack.services.huddles.auto.HuddlesAutoService'
assert not any(s.get(a('name'))==service_name for s in app.findall('service')), 'Already patched'
service=ET.SubElement(app,'service',{a('name'):service_name,a('exported'):'true'})
f=ET.SubElement(service,'intent-filter')
ET.SubElement(f,'action',{a('name'):'androidx.car.app.CarAppService'})
ET.SubElement(f,'category',{a('name'):'androidx.car.app.category.CALLING'})
ET.SubElement(app,'meta-data',{a('name'):'com.google.android.gms.car.application',a('resource'):'@xml/automotive_app_desc'})
ET.SubElement(app,'meta-data',{a('name'):'androidx.car.app.minCarApiLevel',a('value'):'1'})
(root/'res/xml/automotive_app_desc.xml').write_text('<?xml version="1.0" encoding="utf-8"?>\n<automotiveApp><uses name="template"/></automotiveApp>\n')
ET.indent(tree)
tree.write(p,encoding='utf-8',xml_declaration=True)
print('Declared existing Slack car service and descriptor; no bytecode changes.')
