"""Governed build: the pinned upstream generator plus the hooks (source choice, proposal acceptance with slot
information, journal), a runtime switch that hands Timm's paragraph-initial step to the governor, and a runtime
switch that admits l and r as word starts. The original classes in ../build/original stay untouched.
"""
from pathlib import Path
import shutil, subprocess, hashlib, json
HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
ROOT=STUDY.parents[1]
UP=ROOT/'solve/botanical_enrichment/echo7/copying_trace_20261014/generator'

def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

def main():
    out=HERE/'build';src=out/'source'
    manifest=json.loads((UP/'source_manifest.json').read_text())
    for r in manifest['files']:
        assert hashlib.sha256((UP/'upstream'/r['path']).read_bytes()).hexdigest()==r['sha256']
    if src.exists():shutil.rmtree(src)
    shutil.copytree(UP/'upstream/source/src/main/java',src)
    pkg=src/'de/voynich/text'
    shutil.copyfile(HERE/'Bridge.java',pkg/'Bridge.java')
    shutil.copyfile(HERE/'GovernedChooser.java',pkg/'sourcechooser/GovernedChooser.java')
    file=pkg/'GlyphGroup.java';s=file.read_text()
    s=replace(s,'public String glyphGroup;','public String glyphGroup;\n    public int bridgePosition=-1;\n    public String bridgePrevious="";')
    file.write_text(s,encoding='utf-8')
    file=pkg/'sourcechooser/ChooserHelper.java';s=file.read_text()
    s=replace(s,'ret.set(i, new GlyphGroup(newTokens, ret.get(i).generateType));',
        'GlyphGroup prior=ret.get(i);\n                    GlyphGroup next=new GlyphGroup(newTokens,prior.generateType);\n                    next.bridgePosition=prior.bridgePosition;next.bridgePrevious=prior.bridgePrevious;\n                    ret.set(i,next);')
    file.write_text(s,encoding='utf-8')
    file=pkg/'sourcechooser/PageSourceGroupChooser.java';s=file.read_text()
    s=replace(s,'        } else {\n            pos = randomNumberGenerator.rand(sourceLine.size());\n        }\n',
        '        } else {\n            pos = randomNumberGenerator.rand(sourceLine.size());\n        }\n'
        '        GovernedChooser.Pick governed = GovernedChooser.pick(generatedLinesList, actualLineList, linesInPage, isLineInitial, line, pos);\n'
        '        if (governed != null) {\n            if (governed.far != null) { return governed.far; }\n'
        '            line = governed.line; pos = governed.pos; sourceLine = generatedLinesList.get(line);\n        }\n')
    file.write_text(s,encoding='utf-8')
    s=replace(s,'        ChooserHelper.removeInitialGallow(ret);\n','        Bridge.lastMode=mode.name();\n        ChooserHelper.removeInitialGallow(ret);\n')
    s=replace(s,'        } else {\n            ret.add(sourceLine.get(pos));\n        }\n\n        return ret;\n    }\n\n    private List<GlyphGroup> chooseFromParagraphInitialLines(',
        '        } else {\n            ret.add(sourceLine.get(pos));\n        }\n'
        '        if (governed != null && governed.partner != null && ret.size() > 1) { ret.set(1, new GlyphGroup(governed.partner, GlyphGroup.GENERATE_TYPE.REPLACE)); }\n'
        '\n        return ret;\n    }\n\n    private List<GlyphGroup> chooseFromParagraphInitialLines(')
    file.write_text(s,encoding='utf-8')
    file=pkg/'canfollow/CurveLineCanFollow.java';s=file.read_text()
    s=replace(s,'private static final List<String> startGlyphList = Arrays.asList( "qo", "a", "o", "y", "c", "s", "d", "k", "t", "p", "f", "x");',
        'private static final List<String> startGlyphList = de.voynich.text.Bridge.admitLR\n'
        '        ? Arrays.asList( "qo", "a", "o", "y", "c", "s", "d", "k", "t", "p", "f", "x", "l", "r")\n'
        '        : Arrays.asList( "qo", "a", "o", "y", "c", "s", "d", "k", "t", "p", "f", "x");')
    file.write_text(s,encoding='utf-8')
    file=pkg/'SelfCitationTextGenerator.java';s=file.read_text()
    s=replace(s,'wordCount += textArray.length;', 'wordCount += textArray.length;\n            String bridgePrev="";')
    s=replace(s,'            config.statistics.newLine();\n            if (config.statistics.linesInPage == config.pageLength || i == linesToCreate-1) {\n',
        '            config.statistics.newLine();\n'
        '            if (Bridge.specOn(i)) {\n'
        '                if (Bridge.specPageFinal(i) || i == linesToCreate-1) { isParagraphFinal = true; config.statistics.newPage(); }\n'
        '                else if (Bridge.specParFinal(i)) { isParagraphFinal = true; config.statistics.newParagraph(); }\n'
        '            } else if (config.statistics.linesInPage == config.pageLength || i == linesToCreate-1) {\n')
    s=replace(s,'generatedText.add(generateLine(isParagraphInitial, isParagraphFinal, initialLineCount));',
        'Bridge.lineIndex = i; generatedText.add(generateLine(isParagraphInitial, isParagraphFinal, initialLineCount));')
    s=replace(s,'        int maxLineLength = Config.maxLineLength;\n        // for the last line paragraph limit the line length\n        if (isParagraphFinal) {\n',
        '        int maxLineLength = Config.maxLineLength;\n'
        '        if (Bridge.specOn(Bridge.lineIndex)) {\n'
        '            maxLineLength = Math.max(4, Bridge.specChars(Bridge.lineIndex));\n'
        '        } else\n'
        '        // for the last line paragraph limit the line length\n        if (isParagraphFinal) {\n')
    s=replace(s,'config.statistics.remember(glyphGroup);','Bridge.canFollow=config.canFollow;Bridge.seed(glyphGroup,bridgePrev);bridgePrev=group;\n                config.statistics.remember(glyphGroup);')
    file2=pkg/'morph/SlimGroupMorpher.java';s2=file2.read_text()
    s2=replace(s2,'int rand = isParagraphInitial && isLineInitial  ? 0 : randomNumberGenerator.rand(100);',
        'int rand = (isParagraphInitial && isLineInitial && !de.voynich.text.Bridge.innovator) ? 0 : randomNumberGenerator.rand(100);')
    s2=replace(s2,'int rand = (isParagraphInitial && isLineInitial && !de.voynich.text.Bridge.innovator) ? 0 : randomNumberGenerator.rand(100);',
        'int rand = (isParagraphInitial && isLineInitial && !de.voynich.text.Bridge.innovator) ? 0 : randomNumberGenerator.rand(100);\n'
        '        if (de.voynich.text.Bridge.forcedMethod >= 0) rand = de.voynich.text.Bridge.forcedMethod == 0 ? 0 : de.voynich.text.Bridge.forcedMethod == 1 ? addRemoveProbability + 1 : 100;')
    s2=replace(s2,'    GlyphGroup combineGlyphgroups(List<GlyphGroup> sourceGroups) {\n',
        '    GlyphGroup combineGlyphgroups(List<GlyphGroup> sourceGroups) {\n'
        '        if (de.voynich.text.Bridge.partnerOrder && sourceGroups.size() > 1 && !sourceGroups.get(0).glyphGroup.equals(sourceGroups.get(1).glyphGroup)) {\n'
        '            GlyphGroup a = combineGlyphgroups0(sourceGroups);\n'
        '            java.util.List<GlyphGroup> rev = new java.util.ArrayList<>(); rev.add(sourceGroups.get(1)); rev.add(sourceGroups.get(0));\n'
        '            GlyphGroup b = combineGlyphgroups0(rev);\n'
        '            boolean okA = !a.glyphGroup.equals(sourceGroups.get(0).glyphGroup);\n'
        '            boolean okB = !b.glyphGroup.equals(sourceGroups.get(1).glyphGroup) && !b.glyphGroup.equals(sourceGroups.get(0).glyphGroup);\n'
        '            if (okA && okB && !a.glyphGroup.equals(b.glyphGroup)) return de.voynich.text.Bridge.chooseOrder(a.glyphGroup, b.glyphGroup) == 1 ? b : a;\n'
        '            if (okB && !okA) return b;\n'
        '            return a;\n'
        '        }\n'
        '        return combineGlyphgroups0(sourceGroups);\n'
        '    }\n'
        '    GlyphGroup combineGlyphgroups0(List<GlyphGroup> sourceGroups) {\n')
    file2.write_text(s2,encoding='utf-8')
    s=replace(s,'List<GlyphGroup> morphedGroups = config.groupMorpher.morphGroup(sourceGroups, lastGeneratedGroup, isParagraphInitial, isLineInitial);',
        'List<GlyphGroup> morphedGroups = Bridge.operations ? Bridge.morphAll(config.groupMorpher, sourceGroups, lastGeneratedGroup, isParagraphInitial, isLineInitial) : config.groupMorpher.morphGroup(sourceGroups, lastGeneratedGroup, isParagraphInitial, isLineInitial);')
    s=replace(s,'if (morphedGroups.size() > 0) {',
        'morphedGroups=Bridge.propose(sourceGroups,morphedGroups,lastGeneratedGroup,isParagraphInitial,isLineInitial,config.statistics.linesInPage,availablePlaceInLine,maxLineLength);\n                if (morphedGroups.size() > 0) {')
    s=replace(s,'morphedGroup = tryToTrim(morphedGroup, availablePlaceInLine /* availableLength */);',
        'GlyphGroup untrimmed=morphedGroup;\n                                if(!(Bridge.overflow && glyphGroupList.size()>0)) morphedGroup = tryToTrim(morphedGroup, availablePlaceInLine /* availableLength */);\n                                Bridge.trimmed(untrimmed,morphedGroup);')
    s=replace(s,'if (availablePlaceInLine - morphedGroup.length() >= 0) {',
        'if (availablePlaceInLine - morphedGroup.length() >= 0 || (Bridge.overflow && glyphGroupList.size()>0)) {')
    s=replace(s,'glyphGroupList.add(morphedGroup);','Bridge.accept(morphedGroup,lastGeneratedGroup);\n                                glyphGroupList.add(morphedGroup);')
    file.write_text(s,encoding='utf-8')
    classes=out/'classes'
    if classes.exists():shutil.rmtree(classes)
    classes.mkdir(parents=True)
    p=subprocess.run(['java','-jar',str(UP/'ecj.jar'),'-1.8','-encoding','UTF-8','-nowarn','-d',str(classes)]+[str(p) for p in src.rglob('*.java')],capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    (HERE/'build_verification.json').write_text(json.dumps({'upstream_commit':manifest['commit'],
        'source_hashes':{str(p.relative_to(src)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob('*.java')}},indent=2))
    print('Compiled governed build')

if __name__=='__main__':main()
