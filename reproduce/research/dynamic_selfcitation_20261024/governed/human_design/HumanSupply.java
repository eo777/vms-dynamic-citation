package de.voynich.text.sourcechooser;
import de.voynich.text.*;
import java.util.*;

/** Experimental visible sources. No paragraph archive or suggestion dictionary.
 * The page condition carries the preceding line while writing a page's first
 * line. The spread condition permits the preceding page throughout. */
public class HumanSupply {
    public static String policy=System.getProperty("bridge.visible", "native");
    public static boolean enabled(){return !policy.equals("native");}
    public static List<GlyphGroup> choose(List<List<GlyphGroup>> lines,List<GlyphGroup> actual,boolean initial){
        int current=Bridge.lineIndex, start=0, previous=0;
        for(int i=0;i<current;i++) if(Bridge.specOn(i)&&Bridge.specPageFinal(i)){previous=start;start=i+1;}
        int lo=policy.equals("spread")?previous:start;
        // lineArrays omits the fixed seed line: its index j is text line j+1.
        if(current==start && policy.equals("page"))lo=Math.max(1,start-1);
        List<List<GlyphGroup>> offered=new ArrayList<>();
        for(int j=0;j<lines.size();j++) if(j+1>=lo&&!lines.get(j).isEmpty())offered.add(lines.get(j));
        if(!actual.isEmpty())offered.add(actual);
        if(offered.isEmpty())offered.add(lines.get(lines.size()-1));
        int pageStartToken=Bridge.written-actual.size();
        for(int j=0;j<lines.size();j++) if(j+1>=start&&!lines.get(j).isEmpty()){pageStartToken=lines.get(j).get(0).bridgePosition;break;}
        StringBuilder row=new StringBuilder("@S\t"+Bridge.written+"\t"+(initial?1:0)+"\t"+pageStartToken+"\t0");
        for(List<GlyphGroup> line:offered){
            row.append("\t").append(line.get(0).bridgePosition).append("|1|0|");
            for(int j=0;j<line.size();j++){if(j>0)row.append(' ');row.append(line.get(j).glyphGroup);}
        }
        String[] bits=Bridge.exchange(row.toString()).split("\\t");
        if(!bits[0].equals("W"))throw new IllegalStateException("Visible chooser requires W response");
        List<GlyphGroup> out=new ArrayList<>();
        GlyphGroup a=new GlyphGroup(bits[1],GlyphGroup.GENERATE_TYPE.REPLACE);a.bridgePosition=Integer.parseInt(bits[3]);
        GlyphGroup b=new GlyphGroup(bits[2],GlyphGroup.GENERATE_TYPE.REPLACE);b.bridgePosition=-1;
        out.add(a);out.add(b);ChooserHelper.removeInitialGallow(out);
        Bridge.lastMode="VISIBLE_"+policy;return out;
    }
}
