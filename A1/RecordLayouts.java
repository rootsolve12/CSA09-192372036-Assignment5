import java.io.*;
import java.math.*;
import java.time.*;
import java.nio.file.*;
public class RecordLayouts {
 static void write(DataOutputStream out,BusPass p)throws IOException{
  out.writeInt(1);out.writeUTF(p.passId());out.writeUTF(p.register());out.writeUTF(p.name());out.writeInt(p.route());out.writeUTF(p.stop());out.writeLong(p.validUntil().toEpochDay());out.writeLong(p.amount().movePointRight(2).longValueExact());
 }
 static BusPass read(DataInputStream in)throws IOException{
  if(in.readInt()!=1)throw new IOException("Unknown version");return new BusPass(in.readUTF(),in.readUTF(),in.readUTF(),in.readInt(),in.readUTF(),LocalDate.ofEpochDay(in.readLong()),BigDecimal.valueOf(in.readLong(),2));
 }
 public static void main(String[] args)throws Exception{
  BusPass p=new BusPass("P1001","192372036","Roy | Hitesh \\ A",12,"Main Gate",LocalDate.of(2027,3,31),new BigDecimal("4500.00"));
  String line=PassCodec.encode(p);System.out.println("Text record: "+line);Check.that(p.equals(PassCodec.decode(line)),"Escaped delimiter and backslash round trip");
  Path f=Check.generated("A1").resolve("pass.bin");try(DataOutputStream out=new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(f)))){write(out,p);}
  try(DataInputStream in=new DataInputStream(new BufferedInputStream(Files.newInputStream(f)))){Check.that(p.equals(read(in)),"Binary DataOutputStream layout round trip");}
  System.out.println("Text UTF8 bytes="+(line+"\n").getBytes(java.nio.charset.StandardCharsets.UTF_8).length+" binary bytes="+Files.size(f));
 }
}
