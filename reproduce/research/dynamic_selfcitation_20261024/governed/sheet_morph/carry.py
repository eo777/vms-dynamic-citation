"""Sensitivity: keep the last line available through the first new-page line.

The strict sheet tests release that carry after the first written token. This
variant permits the same short startup carry as the earlier page experiments.
Also uses equivalent binary page lookup for a faster isolated Java runtime.
"""
from pathlib import Path
import subprocess
import run as runner

BUILD=runner.build_runtime


def build(folder):
    classes,mapping=BUILD(folder)
    path=Path(folder)/'build/source/de/voynich/text/sourcechooser/SheetSupply.java';s=path.read_text()
    old='static int page(int line){int p=0;while(p+1<pages.size()&&pages.get(p+1)[0]<=line)p++;return p;}'
    new='static int page(int line){int lo=0,hi=pages.size();while(lo+1<hi){int mid=(lo+hi)/2;if(pages.get(mid)[0]<=line)lo=mid;else hi=mid;}return lo;}'
    assert s.count(old)==1;s=s.replace(old,new)
    old='        if(!actual.isEmpty())offered.add(actual);'
    assert s.count(old)==1
    s=s.replace(old,'        if(offered.isEmpty()&&current==start)offered.add(lines.get(lines.size()-1));\n'+old)
    path.write_text(s)
    ecj=runner.e.ROOT/'solve/botanical_enrichment/echo7/copying_trace_20261014/generator/ecj.jar'
    proc=subprocess.run(['java','-jar',str(ecj),'-1.8','-encoding','UTF-8','-nowarn','-d',classes]+[str(p) for p in (Path(folder)/'build/source').rglob('*.java')],capture_output=True,text=True)
    assert proc.returncode==0,proc.stdout+proc.stderr
    return classes,mapping


if __name__=='__main__':
    runner.CONDITIONS={
        'sheet_carry_ops':runner.config(ops=True,repel=True),
        'face_carry_ops':runner.config('face',ops=True,repel=True),
        'sheet_carry_edit':runner.config(repel=True,edit=.35),
    }
    runner.build_runtime=build
    runner.__file__=__file__
    runner.main()
