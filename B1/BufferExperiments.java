import java.nio.file.*;
import java.io.*;
import java.util.*;
public class BufferExperiments {
 public static void main(String[] args)throws Exception{
  Path dir=Check.generated("B1");byte[] line=("a".repeat(99)+"\n").getBytes(java.nio.charset.StandardCharsets.US_ASCII);StringBuilder csv=new StringBuilder("bytes,buffered,run,elapsed_ns,lines,read_calls\n");
  for(int bytes:new int[]{1000000,10000000,50000000}){
   Path p=dir.resolve("log-"+bytes+".txt");try(OutputStream out=new BufferedOutputStream(Files.newOutputStream(p))){for(int i=0;i<bytes/100;i++)out.write(line);}
   LineCounter.count(p,true); // Warm cache once, then alternate measured methods.
   for(int run=1;run<=3;run++)for(boolean buffered:new boolean[]{false,true}){
    long start=System.nanoTime();LineCounter.Result r=LineCounter.count(p,buffered);long elapsed=System.nanoTime()-start;
    Check.that(r.lines()==bytes/100,"Exact line count "+bytes+" bytes buffered="+buffered);csv.append(bytes+","+buffered+","+run+","+elapsed+","+r.lines()+","+r.readCalls()+"\n");System.out.println("MEASURE bytes="+bytes+" buffered="+buffered+" run="+run+" ms="+elapsed/1e6+" calls="+r.readCalls());
   }
  }
  Files.writeString(Path.of("B1/results/buffering.csv"),csv);
 }
}
