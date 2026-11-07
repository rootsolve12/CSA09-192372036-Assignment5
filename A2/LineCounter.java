import java.io.*;
import java.nio.file.*;
public class LineCounter {
 public record Result(long lines,long readCalls){}
 public static Result count(Path file,boolean buffered)throws IOException{
  long count=0,calls=0;int last=-1;
  try(InputStream in=new FileInputStream(file.toFile())){
   if(buffered){byte[] b=new byte[65536];int n;while(true){n=in.read(b);calls++;if(n<0)break;for(int i=0;i<n;i++)if(b[i]=='\n')count++;last=b[n-1]&255;}}
   else {int ch;while(true){ch=in.read();calls++;if(ch<0)break;if(ch=='\n')count++;last=ch;}}
  }
  if(last>=0&&last!='\n')count++;return new Result(count,calls);
 }
 public static void main(String[] args)throws Exception {
  long bytes=50000000L;System.out.println("50 decimal MB: single-byte read calls="+(bytes+1)+"; 64KiB block calls="+((bytes+65535)/65536+1));
  Path p=Check.generated("A2").resolve("lines.txt");for(String s:new String[]{"","a\n","a\nb","a\r\nb\n"}){Files.writeString(p,s);Result a=count(p,false),b=count(p,true);Check.that(a.lines==b.lines,"Both counters agree for "+s.length()+" bytes, lines="+a.lines);}
 }
}
