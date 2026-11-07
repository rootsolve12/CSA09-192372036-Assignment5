import java.nio.charset.StandardCharsets;
import java.time.*;
import java.math.*;
import java.util.*;
import java.util.zip.CRC32;
public final class PassCodec {
 static String escape(String s){return s.replace("\\","\\\\").replace("|","\\|");}
 public static String payload(BusPass p){return String.join("|",escape(p.passId()),escape(p.register()),escape(p.name()),""+p.route(),escape(p.stop()),p.validUntil().toString(),p.amount().toPlainString());}
 public static String checksum(String s){CRC32 c=new CRC32();c.update(s.getBytes(StandardCharsets.UTF_8));return String.format(Locale.ROOT,"%08x",c.getValue());}
 public static String encode(BusPass p){String s=payload(p);return s+"|"+checksum(s);}
 public static BusPass decode(String line){
  int end=line.lastIndexOf('|');if(end<0)throw new IllegalArgumentException("Missing checksum");String body=line.substring(0,end);
  if(!checksum(body).equals(line.substring(end+1)))throw new IllegalArgumentException("Checksum mismatch");
  List<String> fields=new ArrayList<>();StringBuilder b=new StringBuilder();boolean quoted=false;
  for(char ch:body.toCharArray()){
   if(quoted){if(ch!='\\'&&ch!='|')throw new IllegalArgumentException("Invalid escape");b.append(ch);quoted=false;}
   else if(ch=='\\')quoted=true;else if(ch=='|'){fields.add(b.toString());b.setLength(0);}else b.append(ch);
  }
  if(quoted)throw new IllegalArgumentException("Incomplete escape");fields.add(b.toString());if(fields.size()!=7)throw new IllegalArgumentException("Expected seven fields");
  try{return new BusPass(fields.get(0),fields.get(1),fields.get(2),Integer.parseInt(fields.get(3)),fields.get(4),LocalDate.parse(fields.get(5)),new BigDecimal(fields.get(6)));}
  catch(RuntimeException e){throw new IllegalArgumentException("Invalid field: "+e.getMessage(),e);}
 }
}
