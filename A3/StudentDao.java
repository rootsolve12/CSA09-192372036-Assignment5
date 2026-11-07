import java.sql.*;
import java.util.*;
public class StudentDao implements Dao<Student,String>{
 private Student row(ResultSet r)throws SQLException{return new Student(r.getString("reg_no"),r.getString("name"),r.getString("email"));}
 public void insert(Student x)throws SQLException{try(Connection c=Db.open();PreparedStatement p=c.prepareStatement("INSERT INTO student(reg_no,name,email) VALUES(?,?,?)")){p.setString(1,x.register());p.setString(2,x.name());p.setString(3,x.email());p.executeUpdate();}}
 public Optional<Student> findById(String key)throws SQLException{try(Connection c=Db.open();PreparedStatement p=c.prepareStatement("SELECT reg_no,name,email FROM student WHERE reg_no=?")){p.setString(1,key);try(ResultSet r=p.executeQuery()){return r.next()?Optional.of(row(r)):Optional.empty();}}}
 public List<Student> findAll()throws SQLException{try(Connection c=Db.open();PreparedStatement p=c.prepareStatement("SELECT reg_no,name,email FROM student ORDER BY reg_no");ResultSet r=p.executeQuery()){List<Student> result=new ArrayList<>();while(r.next())result.add(row(r));return result;}}
 public void update(Student x)throws SQLException{try(Connection c=Db.open();PreparedStatement p=c.prepareStatement("UPDATE student SET name=?,email=? WHERE reg_no=?")){p.setString(1,x.name());p.setString(2,x.email());p.setString(3,x.register());if(p.executeUpdate()!=1)throw new SQLException("Student not found");}}
 public boolean delete(String key)throws SQLException{try(Connection c=Db.open();PreparedStatement p=c.prepareStatement("DELETE FROM student WHERE reg_no=?")){p.setString(1,key);return p.executeUpdate()==1;}}
 public static void main(String[] args)throws Exception{
  StudentDao dao=new StudentDao();dao.delete("192372036");Student s=new Student("192372036","B Hitesh Roy","student@example.invalid");dao.insert(s);Check.that(dao.findById(s.register()).orElseThrow().equals(s),"Generic DAO insert and find");dao.update(new Student(s.register(),s.name(),"updated@example.invalid"));Check.that(dao.findAll().stream().anyMatch(x->x.email().equals("updated@example.invalid")),"Generic DAO update and findAll");Check.that(dao.delete(s.register())&&dao.findById(s.register()).isEmpty(),"Generic DAO delete and missing ID");
 }
}
