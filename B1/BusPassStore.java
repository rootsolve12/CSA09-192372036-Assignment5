import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.io.*;
import java.util.*;
import java.util.function.*;
public class BusPassStore {
 private final Path file;
 public BusPassStore(Path file){this.file=file;}
 public void scan(Consumer<BusPass> valid,BiConsumer<Long,String> rejected)throws IOException {
  if(!Files.exists(file))return;
  try(BufferedReader r=Files.newBufferedReader(file,StandardCharsets.UTF_8)){
   String line;long n=0;while((line=r.readLine())!=null){n++;BusPass pass;
    try{pass=PassCodec.decode(line);}catch(IllegalArgumentException e){rejected.accept(n,e.getMessage());continue;}
    valid.accept(pass);
   }
  }
 }
 public Optional<BusPass> find(String id)throws IOException{
  if(id==null)throw new IllegalArgumentException("Null ID");if(!Files.exists(file))return Optional.empty();
  try(BufferedReader r=Files.newBufferedReader(file,StandardCharsets.UTF_8)){
   String line;while((line=r.readLine())!=null){BusPass p;try{p=PassCodec.decode(line);}catch(IllegalArgumentException e){continue;}if(p.passId().equals(id))return Optional.of(p);}
  }return Optional.empty();
 }
 public List<BusPass> route(int route)throws IOException {List<BusPass> out=new ArrayList<>();scan(p->{if(p.route()==route)out.add(p);},(n,e)->{});return out;}
 // Single-writer append protocol; a shared database is used for concurrent counters in B4.
 public synchronized void add(BusPass pass)throws IOException{
  if(find(pass.passId()).isPresent())throw new IllegalArgumentException("Duplicate pass ID");
  boolean needsNewline=false;
  if(Files.exists(file)&&Files.size(file)>0)try(RandomAccessFile r=new RandomAccessFile(file.toFile(),"r")){r.seek(r.length()-1);needsNewline=r.read()!='\n';}
  try(FileOutputStream stream=new FileOutputStream(file.toFile(),true);BufferedWriter w=new BufferedWriter(new OutputStreamWriter(stream,StandardCharsets.UTF_8))){
   if(needsNewline)w.newLine();w.write(PassCodec.encode(pass));w.newLine();w.flush();stream.getFD().sync();
  }
 }
}
