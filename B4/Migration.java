import java.sql.*;
import java.nio.file.*;
import java.io.*;
public class Migration {
 public record Report(int imported,int rejected){}
 static String csv(String s){return "\""+s.replace("\"","\"\"")+"\"";}
 public static Report migrate(Path input,Path report)throws Exception{
  int valid=0,bad=0,pending=0;Path tmp=Files.createTempFile(report.toAbsolutePath().getParent(),"rejects-",".tmp");boolean published=false;
  try(Connection c=Db.open()){
   c.setAutoCommit(false);
   try(BufferedReader reader=Files.newBufferedReader(input);BufferedWriter reject=Files.newBufferedWriter(tmp);PreparedStatement p=c.prepareStatement("INSERT INTO bus_pass(pass_id,reg_no,name,route_no,boarding_stop,validity_date,amount) VALUES(?,?,?,?,?,?,?)")){
    reject.write("line,reason,raw\n");String line;int number=0;
    while((line=reader.readLine())!=null){number++;BusPass pass;
     try{pass=PassCodec.decode(line);if(pass.validUntil().getYear()<1000||pass.validUntil().getYear()>9999)throw new IllegalArgumentException("Date outside MySQL DATE range");}
     catch(IllegalArgumentException e){bad++;reject.write(number+","+csv(e.getMessage())+","+csv(line)+"\n");continue;}
     p.setString(1,pass.passId());p.setString(2,pass.register());p.setString(3,pass.name());p.setInt(4,pass.route());p.setString(5,pass.stop());p.setDate(6,Date.valueOf(pass.validUntil()));p.setBigDecimal(7,pass.amount());p.addBatch();valid++;pending++;
     if(pending==1000){p.executeBatch();p.clearBatch();pending=0;}
    }
    if(pending>0)p.executeBatch();reject.flush();c.commit();
   }catch(Exception e){try{c.rollback();}catch(SQLException rollback){e.addSuppressed(rollback);}throw e;}
   try{Files.move(tmp,report,StandardCopyOption.REPLACE_EXISTING);}catch(IOException e){throw new IOException("Database committed, but rejection report publication failed; do not blindly retry import",e);}published=true;return new Report(valid,bad);
  }finally{if(!published)Files.deleteIfExists(tmp);}
 }
 public static void main(String[] args)throws Exception{
  InsertExperiments.clear();Report r=migrate(Path.of("B2/inputs/damaged-passes.txt"),Path.of("B4/results/rejected.csv"));System.out.println("Migration imported="+r.imported+" rejected="+r.rejected);Check.that(r.imported==2&&r.rejected==3&&InsertExperiments.count()==2,"Migration commits all valid rows and reports every invalid row");
  try(Connection c=Db.open();Statement s=c.createStatement();ResultSet rs=s.executeQuery("SELECT boarding_stop,validity_date FROM bus_pass WHERE pass_id='P1003'")){Check.that(rs.next()&&rs.getString(1).equals("South Gate")&&rs.getDate(2).toString().equals("2027-03-31"),"Migration preserves boarding stop and validity date");}
  try{migrate(Path.of("B2/inputs/damaged-passes.txt"),Path.of("B4/results/rejected-again.csv"));throw new AssertionError();}catch(SQLException expected){System.out.println("Second import duplicate: transaction rejected code="+expected.getErrorCode());}Check.that(InsertExperiments.count()==2,"Failed repeat import leaves existing rows unchanged");
  try(Connection c=Db.open()){
   DatabaseMetaData m=c.getMetaData();System.out.println("DATABASE "+m.getDatabaseProductName()+" "+m.getDatabaseProductVersion());System.out.println("DRIVER "+m.getDriverName()+" "+m.getDriverVersion());System.out.println("TRANSACTIONS supported="+m.supportsTransactions()+" isolation="+c.getTransactionIsolation());try(ResultSet rs=m.getTables(c.getCatalog(),null,"%",new String[]{"TABLE"})){while(rs.next())System.out.println("TABLE "+rs.getString("TABLE_NAME"));}
  }
 }
}
