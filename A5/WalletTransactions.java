import java.sql.*;
import java.math.*;
public class WalletTransactions {
 static void reset()throws SQLException{try(Connection c=Db.open();Statement s=c.createStatement()){s.executeUpdate("UPDATE wallet SET balance=CASE id WHEN 1 THEN 1000.00 ELSE 100.00 END");}}
 static String balances()throws SQLException{try(Connection c=Db.open();Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT balance FROM wallet ORDER BY id")){r.next();BigDecimal a=r.getBigDecimal(1);r.next();BigDecimal b=r.getBigDecimal(1);return a+","+b+" total="+a.add(b);}}
 static void transfer(boolean transaction,boolean fail)throws SQLException{
  try(Connection c=Db.open()){
   c.setAutoCommit(!transaction);
   try {
    if(transaction)try(PreparedStatement p=c.prepareStatement("SELECT id FROM wallet WHERE id IN (1,2) ORDER BY id FOR UPDATE");ResultSet r=p.executeQuery()){while(r.next())r.getInt(1);}
    try(PreparedStatement p=c.prepareStatement("UPDATE wallet SET balance=balance-? WHERE id=? AND balance>=?")){p.setBigDecimal(1,new BigDecimal("500.00"));p.setInt(2,1);p.setBigDecimal(3,new BigDecimal("500.00"));if(p.executeUpdate()!=1)throw new SQLException("Insufficient balance");}
    if(fail)throw new SQLException("Injected failure after debit");
    try(PreparedStatement p=c.prepareStatement("UPDATE wallet SET balance=balance+? WHERE id=?")){p.setBigDecimal(1,new BigDecimal("500.00"));p.setInt(2,2);if(p.executeUpdate()!=1)throw new SQLException("Missing target");}
    if(transaction)c.commit();
   }catch(SQLException e){if(transaction)try{c.rollback();}catch(SQLException rollback){e.addSuppressed(rollback);}throw e;}
  }
 }
 public static void main(String[] args)throws Exception{
  reset();try{transfer(true,true);}catch(SQLException e){System.out.println(e.getMessage());}System.out.println("Transaction failure: "+balances());Check.that(balances().equals("1000.00,100.00 total=1100.00"),"Failure rolls back debit");
  transfer(true,false);System.out.println("Transaction success: "+balances());Check.that(balances().equals("500.00,600.00 total=1100.00"),"Successful transfer preserves money");
  reset();try{transfer(false,true);}catch(SQLException e){}System.out.println("Independent auto-commit failure: "+balances());Check.that(balances().equals("500.00,100.00 total=600.00"),"Unsafe alternative loses 500 between commits");reset();
 }
}
