import java.sql.*;
import java.nio.file.*;
import java.util.*;
public class InsertExperiments {
 static final String INSERT="INSERT INTO bus_pass(pass_id,reg_no,name,route_no,amount) VALUES(?,?,?,?,?)";
 static List<String[]> rows(int n){List<String[]> out=new ArrayList<>();for(int i=1;i<=n;i++)out.add(new String[]{"P"+i,String.format(Locale.ROOT,"%09d",i),"Student "+i,""+(i%12+1),"4500.00"});return out;}
 static void clear()throws SQLException{try(Connection c=Db.open();Statement s=c.createStatement()){s.executeUpdate("DELETE FROM bus_pass");}}
 static int count()throws SQLException{try(Connection c=Db.open();Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT COUNT(*) FROM bus_pass")){r.next();return r.getInt(1);}}
 static void parameters(PreparedStatement p,String[] r)throws SQLException{p.setString(1,r[0]);p.setString(2,r[1]);p.setString(3,r[2]);p.setInt(4,Integer.parseInt(r[3]));double a=Double.parseDouble(r[4]);if(!Double.isFinite(a)||a<0)throw new IllegalArgumentException("Invalid amount");p.setDouble(5,a);}
 static void load(Connection c,List<String[]> rows,String method,boolean auto)throws SQLException{
  c.setAutoCommit(auto);
  try {
   if(method.equals("Statement"))try(Statement s=c.createStatement()){
    // Only deterministic program-generated numeric/text fixtures enter this deliberately literal comparison.
    for(String[] r:rows)s.executeUpdate("INSERT INTO bus_pass(pass_id,reg_no,name,route_no,amount) VALUES('"+r[0]+"','"+r[1]+"','"+r[2]+"',"+r[3]+","+r[4]+")");
   }else try(PreparedStatement p=c.prepareStatement(INSERT)){
    int n=0;for(String[] r:rows){parameters(p,r);if(method.equals("Prepared"))p.executeUpdate();else{p.addBatch();n++;if(n%1000==0){p.executeBatch();p.clearBatch();}}}if(method.equals("Batch"))p.executeBatch();
   }
   if(!auto)c.commit();
  }catch(SQLException|RuntimeException e){if(!auto)try{c.rollback();}catch(SQLException rollback){e.addSuppressed(rollback);}throw e;}
 }
 static void metadata()throws SQLException{
  try(Connection c=Db.open();Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT * FROM bus_pass ORDER BY pass_id")){
   ResultSetMetaData m=r.getMetaData();for(int i=1;i<=m.getColumnCount();i++)System.out.println("COLUMN "+i+" "+m.getColumnName(i)+" "+m.getColumnTypeName(i)+" JDBC="+m.getColumnType(i));
   Check.that(m.getColumnCount()==7,"Seven schema columns visible");int[] types={Types.VARCHAR,Types.CHAR,Types.VARCHAR,Types.INTEGER,Types.VARCHAR,Types.DATE,Types.DECIMAL};String[] names={"pass_id","reg_no","name","route_no","boarding_stop","validity_date","amount"};for(int i=1;i<=7;i++)Check.that(m.getColumnType(i)==types[i-1]&&m.getColumnName(i).equals(names[i-1]),"Metadata type and name "+names[i-1]);
   int n=0;while(r.next()){n++;int id=Integer.parseInt(r.getString("pass_id").substring(1));Check.that(id>=1&&id<=10&&r.getString("reg_no").equals(String.format(Locale.ROOT,"%09d",id))&&r.getString("name").equals("Student "+id)&&r.getInt("route_no")==id%12+1&&r.getBigDecimal("amount").compareTo(new java.math.BigDecimal("4500.00"))==0&&r.getString("boarding_stop").isEmpty()&&r.getDate("validity_date")==null,"Exact selected values row "+id);}Check.that(n==10,"SELECT contains ten records");
  }
 }
 static void failureChecks()throws Exception{
  List<String[]> broken=rows(10000);broken.get(5000)[4]="not-a-number";
  for(boolean auto:new boolean[]{true,false}){clear();try(Connection c=Db.open()){try{load(c,broken,"Batch",auto);throw new AssertionError();}catch(NumberFormatException expected){System.out.println("Injected numeric failure auto="+auto);}}int n=count();System.out.println("AFTER FAILURE auto="+auto+" rows="+n);Check.that(n==(auto?5000:0),"Expected partial versus rolled-back rows");}
  clear();try(Connection c=Db.open()){try{PassLoader.loadAll(c,broken);throw new AssertionError();}catch(NumberFormatException expected){}Check.that(c.getAutoCommit(),"Failed supplied loader restores auto-commit");}Check.that(count()==0,"Invalid amount halfway leaves zero supplied-loader rows");
  List<String[]> duplicate=rows(10000);duplicate.get(5000)[0]="P1";clear();try(Connection c=Db.open()){try{PassLoader.loadAll(c,duplicate);throw new AssertionError();}catch(SQLException expected){System.out.println("Injected duplicate SQL code="+expected.getErrorCode());}}Check.that(count()==0,"SQL batch failure also rolls back every row");
 }
 public static void main(String[] args)throws Exception{
  if(args.length>0&&args[0].equals("failures")){failureChecks();return;}
  for(String method:List.of("Statement","Prepared","Batch")){clear();try(Connection c=Db.open()){load(c,rows(10),method,false);}Check.that(count()==10,method+" inserts ten records");metadata();}
  if(args.length>0&&args[0].equals("small"))return;
  StringBuilder csv=new StringBuilder("rows,method,auto_commit,run,elapsed_ns,stored\n");
  for(int n:new int[]{1000,10000,100000}){
   List<String[]> data=rows(n);
   for(String method:List.of("Statement","Prepared","Batch"))for(int run=1;run<=3;run++){
    clear();long elapsed;try(Connection c=Db.open()){long start=System.nanoTime();load(c,data,method,false);elapsed=System.nanoTime()-start;}int stored=count();Check.that(stored==n,"Measured "+method+" "+n+" rows exact");csv.append(n+","+method+",false,"+run+","+elapsed+","+stored+"\n");System.out.println("MEASURE "+n+" "+method+" tx run="+run+" ms="+elapsed/1e6);
   }
   for(int run=1;run<=3;run++){
    clear();long elapsed;try(Connection c=Db.open()){long start=System.nanoTime();load(c,data,"Batch",true);elapsed=System.nanoTime()-start;}int stored=count();Check.that(stored==n,"Auto-commit batch count "+n);csv.append(n+",Batch,true,"+run+","+elapsed+","+stored+"\n");
   }
   clear();try(Connection c=Db.open()){Check.that(PassLoader.loadAll(c,data)==n,"Supplied PassLoader loads "+n);Check.that(c.getAutoCommit(),"PassLoader restores auto-commit");}Check.that(count()==n,"Supplied loader committed exact count "+n);
  }
  Files.writeString(Path.of("B3/results/insert-measurements.csv"),csv);
  failureChecks();
 }
}
