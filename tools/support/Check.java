import java.nio.file.*;
public final class Check {
 public static void that(boolean condition,String message){if(!condition)throw new AssertionError(message);System.out.println("PASS: "+message);}
 public static Path generated(String task)throws Exception{Path p=Path.of("generated",task);Files.createDirectories(p);return p;}
}
