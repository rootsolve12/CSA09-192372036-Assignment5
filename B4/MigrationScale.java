import java.nio.file.*;
public class MigrationScale {
 public static void main(String[] args)throws Exception{
  InsertExperiments.clear();long start=System.nanoTime();Migration.Report r=Migration.migrate(Path.of("generated/B1/passes-100000.txt"),Path.of("B4/results/scale-rejected.csv"));long elapsed=System.nanoTime()-start;
  Check.that(r.imported()==100000&&r.rejected()==0&&InsertExperiments.count()==100000,"Streaming migration imports 100000 full seven-field records in one transaction");
  Files.writeString(Path.of("B4/results/migration-scale.csv"),"records,rejected,elapsed_ns\n100000,0,"+elapsed+"\n");System.out.println("Migration scale rows=100000 rejected=0 ms="+elapsed/1e6);
 }
}
