import java.sql.*;
public final class Db {
 private Db(){}
 public static Connection open()throws SQLException{
  return DriverManager.getConnection(System.getenv().getOrDefault("ASSIGNMENT_DB_URL","jdbc:mysql://127.0.0.1:3307/assignment5?rewriteBatchedStatements=true&useServerPrepStmts=true"),System.getenv().getOrDefault("ASSIGNMENT_DB_USER","assignment5"),System.getenv().getOrDefault("ASSIGNMENT_DB_PASSWORD",""));
 }
}
