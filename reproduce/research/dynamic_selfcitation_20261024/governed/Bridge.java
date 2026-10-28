package de.voynich.text;
import java.io.*;
import java.util.*;

/** Synchronous hooks for the governed generator: proposal acceptance (@P, with the slot of the word being written),
 *  source choice (@S, see sourcechooser.GovernedChooser) and the accepted-token journal (@A).
 *  -Dbridge.enabled=true switches the hooks on; -Dbridge.innovator=true hands Timm's paragraph-initial step to the
 *  governor (the morpher is then called with isParagraphInitial=false); -Dbridge.admitlr=true admits l and r as word
 *  starts in the curve-line grammar. */
public class Bridge {
    public static boolean enabled=Boolean.parseBoolean(System.getProperty("bridge.enabled","false"));
    public static boolean innovator=Boolean.parseBoolean(System.getProperty("bridge.innovator","false"));
    public static boolean admitLR=Boolean.parseBoolean(System.getProperty("bridge.admitlr","false"));
    public static boolean overflow=Boolean.parseBoolean(System.getProperty("bridge.overflow","false"));
    /** -Dbridge.operations=true: the morpher is run once per operation and the governor chooses among the results (@O) */
    public static boolean operations=Boolean.parseBoolean(System.getProperty("bridge.operations","false"));
    public static int forcedMethod=-1;
    /** -Dbridge.partnerorder=true: combine is tried in both orders and the governor picks the result (?C query) */
    public static boolean partnerOrder=Boolean.parseBoolean(System.getProperty("bridge.partnerorder","false"));
    public static int chooseOrder(String a,String b) {
        System.out.println("?C\t"+a+"\t"+b);System.out.flush();
        try { String reply=input.readLine(); if(reply==null)throw new IOException("Bridge closed"); return Integer.parseInt(reply.split("\\t")[1]); }
        catch(IOException e){throw new RuntimeException(e);}
    }
    /** -Dbridge.pagespec=FILE: per text line (the seed line is line 0) the manuscript's geometry: characters, 1 if the
     *  line ends a paragraph, 1 if it ends a page; lines beyond the file keep Timm's own page and paragraph rules. */
    public static int[][] pageSpec=loadSpec(System.getProperty("bridge.pagespec"));
    public static int lineIndex=0;
    static int[][] loadSpec(String file) {
        if(file==null)return null;
        try {
            List<int[]> rows=new ArrayList<>();
            for(String ln:java.nio.file.Files.readAllLines(java.nio.file.Paths.get(file))){
                if(ln.isEmpty()||ln.startsWith("#"))continue;
                String[] f=ln.split("\t");rows.add(new int[]{Integer.parseInt(f[0]),Integer.parseInt(f[1]),Integer.parseInt(f[2])});
            }
            return rows.toArray(new int[0][]);
        } catch(IOException e){throw new RuntimeException(e);}
    }
    public static boolean specOn(int i){return pageSpec!=null&&i<pageSpec.length;}
    public static int specChars(int i){return pageSpec[i][0];}
    public static boolean specParFinal(int i){return pageSpec[i][1]==1;}
    public static boolean specPageFinal(int i){return pageSpec[i][2]==1;}
    /** the generator's validity class (set at start); ?F word -> !F count of legal one-glyph neighbours (governor --mode freedom) */
    public static de.voynich.text.canfollow.I_CanFollow canFollow;
    static final String[] EVA={"a","c","d","e","f","h","i","k","l","m","n","o","p","q","r","s","t","y"};
    static HashMap<String,Integer> freedomCache=new HashMap<>();
    static int legalNeighbour(String v,String w,HashSet<String> seen) {
        if(v.isEmpty()||v.equals(w)||!seen.add(v)||canFollow==null)return 0;
        GlyphGroup g=new GlyphGroup(v,GlyphGroup.GENERATE_TYPE.REPLACE);
        return (canFollow.isValid(g)&&canFollow.hasValidStartGlyph(g))?1:0;
    }
    public static int freedom(String w) {
        Integer c=freedomCache.get(w);if(c!=null)return c;
        HashSet<String> seen=new HashSet<>();int n=0;
        for(int i=0;i<=w.length();i++)for(String g:EVA)n+=legalNeighbour(w.substring(0,i)+g+w.substring(i),w,seen);
        for(int i=0;i<w.length();i++){n+=legalNeighbour(w.substring(0,i)+w.substring(i+1),w,seen);for(String g:EVA)n+=legalNeighbour(w.substring(0,i)+g+w.substring(i+1),w,seen);}
        freedomCache.put(w,n);return n;
    }
    static BufferedReader input=new BufferedReader(new InputStreamReader(System.in));
    public static int written=0;
    /** the chooser mode (LOCALY, PARAGRAPH_INITIAL, SUGGESTION, RANDOM) of the source of the current proposal; journal only */
    public static String lastMode="";
    static int nextId=0;
    static IdentityHashMap<GlyphGroup,Integer> proposals=new IdentityHashMap<>();

    public static String exchange(String row) {
        System.out.println(row);System.out.flush();
        try {
            String reply=input.readLine();
            while(reply!=null&&reply.startsWith("?F\t")){System.out.println("!F\t"+freedom(reply.substring(3)));System.out.flush();reply=input.readLine();}
            if(reply==null)throw new IOException("Bridge closed");
            return reply;
        }catch(IOException e){throw new RuntimeException(e);}
    }
    public static void seed(GlyphGroup g,String previous) {
        if(!enabled)return;
        g.bridgePosition=written++;g.bridgePrevious=previous;
    }
    public static List<GlyphGroup> propose(List<GlyphGroup> source,List<GlyphGroup> raw,GlyphGroup previous,
                                           boolean paragraphInitial,boolean lineInitial,int linesInPage,int available,int maxLength) {
        if(!enabled)return raw;
        proposals.clear();List<GlyphGroup> result=new ArrayList<>();
        GlyphGroup origin=source.get(0);
        int id=nextId++;
        StringBuilder row=new StringBuilder("@P\t"+id+"\t"+written+"\t"+origin.bridgePosition+"\t"+
            origin.bridgePrevious+"\t"+(previous==null?"":previous.glyphGroup)+"\t"+origin.glyphGroup+
            "\tS:"+(paragraphInitial?1:0)+":"+(lineInitial?1:0)+":"+linesInPage+":"+available+":"+maxLength+":"+lastMode);
        for(GlyphGroup g:raw)row.append("\t").append(g.glyphGroup).append(":").append(g.generateType.name());
        String reply=exchange(row.toString());
        if(reply.isEmpty())return result;
        for(String w:reply.split("\\t")) {
            String[] bits=w.split(":");
            GlyphGroup g=new GlyphGroup(bits[0],GlyphGroup.GENERATE_TYPE.valueOf(bits[1]));
            proposals.put(g,id*100+Integer.parseInt(bits[2]));result.add(g);
        }
        return result;
    }
    public static List<GlyphGroup> morphAll(de.voynich.text.morph.I_GroupMorpher morpher,List<GlyphGroup> source,GlyphGroup previous,
                                            boolean paragraphInitial,boolean lineInitial) {
        List<List<GlyphGroup>> options=new ArrayList<>();
        for(int m=0;m<3;m++){forcedMethod=m;options.add(morpher.morphGroup(source,previous,paragraphInitial,lineInitial));}
        forcedMethod=-1;
        StringBuilder row=new StringBuilder("@O\t"+written+"\t"+source.get(0).glyphGroup+"\t"+(previous==null?"":previous.glyphGroup));
        for(List<GlyphGroup> opt:options){row.append("\t");for(int i=0;i<opt.size();i++){if(i>0)row.append('|');row.append(opt.get(i).glyphGroup).append(':').append(opt.get(i).generateType.name());}}
        int k=Integer.parseInt(exchange(row.toString()).trim());
        return options.get(Math.max(0,Math.min(options.size()-1,k)));
    }
    public static void trimmed(GlyphGroup old,GlyphGroup shorter) {
        if(enabled && proposals.containsKey(old))proposals.put(shorter,proposals.get(old));
    }
    public static void accept(GlyphGroup g,GlyphGroup previous) {
        if(!enabled)return;
        Integer id=proposals.get(g);
        System.out.println("@A\t"+written+"\t"+(id==null?-1:id)+"\t"+g.glyphGroup+"\t"+g.generateType.name());
        g.bridgePosition=written++;g.bridgePrevious=previous==null?"":previous.glyphGroup;
    }
}
