import java.sql.*;
import java.nio.file.*;
import java.util.*;
public class AdversarialInputs {
 static boolean login(String id,String password,boolean prepared)throws SQLException{
  try(Connection c=Db.open()){
   if(prepared)try(PreparedStatement s=c.prepareStatement("SELECT id FROM users WHERE id=? AND pwd=?")){s.setString(1,id);s.setString(2,password);try(ResultSet r=s.executeQuery()){return r.next();}}
   else {String sql="SELECT * FROM users WHERE id='"+id+"' AND pwd='"+password+"'";try(Statement s=c.createStatement();ResultSet r=s.executeQuery(sql)){return r.next();}}
  }
 }
 public static void main(String[] args)throws Exception {
  Check.that(login("student","demo-only-password",true),"Valid local fixture login");Check.that(!login("student","wrong",false)&&!login("student","wrong",true),"Ordinary wrong password rejected");
  String injected="' OR '1'='1' -- ";boolean unsafe=login(injected,"wrong",false),safe=login(injected,"wrong",true);System.out.println("Local-only injected ID="+injected+" unsafe="+unsafe+" prepared="+safe);Check.that(unsafe&&!safe,"Unsafe concatenation bypassed; parameterized query rejects same input");
  Path p=Path.of("B2/inputs/damaged-passes.txt");List<String> rejected=new ArrayList<>();List<BusPass> valid=new ArrayList<>();new BusPassStore(p).scan(valid::add,(n,e)->rejected.add("line="+n+" "+e));for(String s:rejected)System.out.println("REJECT "+s);
  Check.that(valid.size()==2&&rejected.size()==3,"Wrong field count, nonnumeric amount and blank line rejected; two valid records retained");Check.that(new BusPassStore(p).find("P1003").isPresent(),"Damaged rows do not stop later valid lookup");
 }
}
