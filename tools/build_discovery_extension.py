#!/usr/bin/env python3
"""Compile the car extension without distributing Slack or AndroidX binaries."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STUBS = {
    'androidx/car/app/CarContext.java': '''package androidx.car.app;
public class CarContext extends android.content.ContextWrapper {
 public CarContext(android.content.Context context) { super(context); }
}''',
    'androidx/car/app/Screen.java': '''package androidx.car.app;
public abstract class Screen {
 public Screen(CarContext context) {}
 public abstract androidx.car.app.model.MessageTemplate onGetTemplate();
}''',
    'androidx/car/app/model/Template.java': 'package androidx.car.app.model; public interface Template {}',
    'androidx/car/app/model/MessageTemplate.java': 'package androidx.car.app.model; public class MessageTemplate implements Template {}',
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--android-jar', type=Path, required=True)
    parser.add_argument('--build-tools', type=Path, required=True)
    parser.add_argument('--kotlin-stdlib', type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    stubs = args.work / 'compile-only-stubs'
    for rel, content in STUBS.items():
        path = stubs / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    classes = args.work / 'classes'; classes.mkdir(exist_ok=True)
    java = Path(os.environ['JAVA_HOME']) / 'bin/javac'
    sources = list((ROOT / 'extension/src').rglob('*.java')) + list(stubs.rglob('*.java'))
    subprocess.run([str(java), '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-Xlint:-options',
                    '-cp', os.pathsep.join(map(str, (args.android_jar, args.kotlin_stdlib))),
                    '-d', str(classes), *map(str, sources)], check=True)
    extension_classes = list((classes / 'slack').rglob('*.class'))
    assert extension_classes, 'No extension classes compiled'
    subprocess.run([str(args.build_tools / 'd8'), '--min-api', '29', '--lib', str(args.android_jar),
                    '--classpath', str(classes), '--classpath', str(args.kotlin_stdlib),
                    '--output', str(args.work / 'discovery.jar'), *map(str, extension_classes)], check=True)
    print('Compiled extension; compile-only AndroidX stubs excluded from DEX')

if __name__ == '__main__':
    main()
