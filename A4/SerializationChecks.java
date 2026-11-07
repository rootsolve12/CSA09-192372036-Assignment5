import java.nio.file.*;
import java.util.*;
public class SerializationChecks {
 static int run(String version,String mode,Path file)throws Exception{
  String cp=Path.of("build/A4",version)+java.io.File.pathSeparator+"build/common"+java.io.File.pathSeparator+"deps/mysql-connector-j.jar";List<String> command=List.of("java","-Djava.io.tmpdir="+Path.of("generated/tmp").toAbsolutePath(),"-cp",cp,"HostelDemo",mode,file.toString());Process p=new ProcessBuilder(command).redirectErrorStream(true).start();String result=new String(p.getInputStream().readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);int exit=p.waitFor();System.out.println("VERSION "+version+" MODE "+mode+" EXIT "+exit);System.out.print(result);if(version.equals("incompatible"))Check.that(result.contains("InvalidClassException"),"Changed UID produces InvalidClassException");return exit;
 }
 public static void main(String[] args)throws Exception{
  Path f=Check.generated("A4").resolve("hostel-v1.ser");Check.that(run("v1","write",f)==0,"Version 1 graph saved");Check.that(run("v1","read",f)==0,"Version 1 graph restored");Check.that(run("v2","read",f)==0,"Old graph read with added phone and stable UID");Check.that(run("incompatible","read",f)!=0,"Incompatible UID rejected");
 }
}
