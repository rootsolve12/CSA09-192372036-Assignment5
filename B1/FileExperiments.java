import java.nio.file.*;
import java.io.*;
import java.time.*;
import java.math.*;
import java.util.*;
public class FileExperiments {
 static BusPass pass(int n){return new BusPass("P"+n,String.format(Locale.ROOT,"%09d",n),"Student "+n,n%12+1,"Stop "+n%20,LocalDate.of(2027,3,31),new BigDecimal("4500.00"));}
 static void file(Path p,int n)throws Exception{try(BufferedWriter w=Files.newBufferedWriter(p)){for(int i=1;i<=n;i++){w.write(PassCodec.encode(pass(i)));w.newLine();}}}
 public static void main(String[] args)throws Exception{
  Path dir=Check.generated("B1"),p=dir.resolve("checks.txt");Files.deleteIfExists(p);BusPassStore store=new BusPassStore(p);
  Check.that(store.find("P1").isEmpty(),"Missing file is an empty store");store.add(pass(1));store.add(pass(2));
  Check.that(store.find("P2").orElseThrow().equals(pass(2)),"Add and find exact record");Check.that(store.find("P999").isEmpty(),"Unknown pass ID returns empty");Check.that(store.route(2).size()==1,"List by route selects correct pass");
  try{store.add(pass(1));throw new AssertionError();}catch(IllegalArgumentException expected){System.out.println("PASS: duplicate pass ID rejected");}
  Files.writeString(p,"PARTIAL",StandardOpenOption.APPEND);store.add(pass(3));Check.that(store.find("P3").isPresent(),"Newline isolates incomplete tail before next append");List<String> rejects=new ArrayList<>();store.scan(x->{},(line,e)->rejects.add(line+":"+e));Check.that(rejects.size()==1,"Damaged tail reported and valid following record remains searchable");
  StringBuilder growth=new StringBuilder("records,run,elapsed_ns,found\n");
  for(int n:new int[]{1000,10000,100000}){Path data=dir.resolve("passes-"+n+".txt");file(data,n);BusPassStore s=new BusPassStore(data);s.find("P"+n);
   for(int run=1;run<=3;run++){long start=System.nanoTime();boolean found=s.find("P"+n).isPresent();long elapsed=System.nanoTime()-start;Check.that(found,"Find final pass among "+n+" records");growth.append(n+","+run+","+elapsed+","+found+"\n");}
  }
  Files.writeString(Path.of("B1/results/growth.csv"),growth);System.out.print(growth);
  Path data=dir.resolve("passes-100000.txt");Map<String,BusPass> index=new HashMap<>();long start=System.nanoTime();new BusPassStore(data).scan(x->index.put(x.passId(),x),(n,e)->{});long build=System.nanoTime()-start;start=System.nanoTime();int found=0;for(int i=99981;i<=100000;i++)if(index.get("P"+i)!=null)found++;long lookups=System.nanoTime()-start;Check.that(found==20,"Twenty indexed lookups returned exact IDs");
  Files.writeString(Path.of("B1/results/index.csv"),"records,build_ns,queries,lookup_ns\n100000,"+build+",20,"+lookups+"\n");System.out.println("Index build_ns="+build+" entries="+index.size()+" 20 lookup_ns="+lookups);
 }
}
