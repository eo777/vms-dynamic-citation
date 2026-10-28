package de.voynich.text.sourcechooser;
import de.voynich.text.*;
import java.util.*;
import java.nio.file.*;

/** Explicit causal source pages. Table rows: line start, node index, sheet side.
 * Side -1 denotes an unresolved complex foldout: same-side mode uses only the
 * current page there. A preceding line is carried on a page's first line when
 * no written source surface is available. No unseen/future words are offered. */
public class SheetSupply {
    static List<int[]> pages=new ArrayList<>();
    static { try {
        for(String line:Files.readAllLines(Paths.get(System.getProperty("bridge.sheetmap")))) {
            String[] f=line.split("\t");pages.add(new int[]{Integer.parseInt(f[0]),Integer.parseInt(f[1]),Integer.parseInt(f[2])});
        }
    }catch(Exception e){throw new RuntimeException(e);} }
    static int page(int line){int p=0;while(p+1<pages.size()&&pages.get(p+1)[0]<=line)p++;return p;}
    public static List<GlyphGroup> choose(List<List<GlyphGroup>> lines,List<GlyphGroup> actual,boolean initial){
        int current=Bridge.lineIndex, p=page(current), node=pages.get(p)[1], side=pages.get(p)[2], start=pages.get(p)[0];
        String policy=HumanSupply.policy;
        List<List<GlyphGroup>> offered=new ArrayList<>();
        for(int j=0;j<lines.size();j++) {
            int q=page(j+1);boolean allowed=q==p;
            if(policy.equals("sheet"))allowed=pages.get(q)[1]==node;
            if(policy.equals("face"))allowed=q==p||(side>=0&&pages.get(q)[1]==node&&pages.get(q)[2]==side);
            if(allowed&&!lines.get(j).isEmpty())offered.add(lines.get(j));
        }
        if(!actual.isEmpty())offered.add(actual);
        if(offered.isEmpty())offered.add(lines.get(lines.size()-1));
        int pageStartToken=Bridge.written-actual.size();
        for(int j=0;j<lines.size();j++)if(j+1>=start&&!lines.get(j).isEmpty()){pageStartToken=lines.get(j).get(0).bridgePosition;break;}
        StringBuilder row=new StringBuilder("@S\t"+Bridge.written+"\t"+(initial?1:0)+"\t"+pageStartToken+"\t"+node);
        for(List<GlyphGroup> line:offered){row.append("\t").append(line.get(0).bridgePosition).append("|1|0|");
            for(int j=0;j<line.size();j++){if(j>0)row.append(' ');row.append(line.get(j).glyphGroup);}}
        String[] bits=Bridge.exchange(row.toString()).split("\\t");
        if(!bits[0].equals("W"))throw new IllegalStateException("Sheet chooser requires W response");
        List<GlyphGroup> out=new ArrayList<>();
        GlyphGroup a=new GlyphGroup(bits[1],GlyphGroup.GENERATE_TYPE.REPLACE);a.bridgePosition=Integer.parseInt(bits[3]);
        out.add(a);out.add(new GlyphGroup(bits[2],GlyphGroup.GENERATE_TYPE.REPLACE));
        ChooserHelper.removeInitialGallow(out);Bridge.lastMode="VISIBLE_"+policy;return out;
    }
}
