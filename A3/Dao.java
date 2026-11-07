import java.sql.*;
import java.util.*;
public interface Dao<T,K>{
 void insert(T object)throws SQLException;
 Optional<T> findById(K key)throws SQLException;
 List<T> findAll()throws SQLException;
 void update(T object)throws SQLException;
 boolean delete(K key)throws SQLException;
}
