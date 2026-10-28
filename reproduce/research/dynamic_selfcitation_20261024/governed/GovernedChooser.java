package de.voynich.text.sourcechooser;
import de.voynich.text.*;
import java.util.*;

/** Source-choice hook. Timm's own draw (line, pos) is computed first and passed as the default; the window
 *  is exactly the set of lines his draw could have produced, with the multiplicity of each line, so that the
 *  governor can reproduce his selection distribution when its temperature is zero. */
public class GovernedChooser {
    public static class Pick { public int line, pos; public List<GlyphGroup> far; public String partner; }

    public static Pick pick(List<List<GlyphGroup>> lines, List<GlyphGroup> actual, int linesInPage, boolean isLineInitial, int defLine, int defPos) {
        if(!Bridge.enabled)return null;
        int size=lines.size();
        int draws=Math.max(1, Math.max(2, linesInPage)-2);
        LinkedHashMap<Integer,Integer> mult=new LinkedHashMap<>();
        for(int k=0;k<draws;k++){int l=size-(1+k); if(l<0)l=size-1; mult.merge(l,1,Integer::sum);}
        StringBuilder row=new StringBuilder("@S\t"+Bridge.written+"\t"+(isLineInitial?1:0)+"\t"+defLine+"\t"+defPos);
        for(Map.Entry<Integer,Integer> e:mult.entrySet()) {
            List<GlyphGroup> sl=lines.get(e.getKey());
            row.append("\t").append(e.getKey()).append("|").append(e.getValue()).append("|").append(ChooserHelper.calcLinePosition(actual, sl)).append("|");
            for(int i=0;i<sl.size();i++){if(i>0)row.append(' ');row.append(sl.get(i).glyphGroup);}
        }
        String reply=Bridge.exchange(row.toString());
        if(reply.isEmpty())return null;
        String[] bits=reply.split("\\t");
        Pick p=new Pick();
        if(bits[0].equals("I")){p.line=Integer.parseInt(bits[1]);p.pos=Integer.parseInt(bits[2]);if(bits.length>3)p.partner=bits[3];return p;}
        GlyphGroup g=new GlyphGroup(bits[1],GlyphGroup.GENERATE_TYPE.REPLACE);g.bridgePosition=Integer.parseInt(bits[3]);
        GlyphGroup n=new GlyphGroup(bits[2],GlyphGroup.GENERATE_TYPE.REPLACE);n.bridgePosition=Integer.parseInt(bits[3])+1;
        p.far=new ArrayList<>();p.far.add(g);p.far.add(n);
        return p;
    }
}
