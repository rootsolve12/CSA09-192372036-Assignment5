import java.io.*;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
public class HostelDemo {
 static class Resident implements Serializable {
  private static final long serialVersionUID=2L;
  String name,register;String phone;
  transient char[] password;
  transient Connection connection;
  Resident(String name,String register,Connection c){this.name=name;this.register=register;password="demo-secret-not-for-storage".toCharArray();connection=c;}
 }
 static class Room implements Serializable {private static final long serialVersionUID=1L;String number;List<Resident> residents=new ArrayList<>();Room(String n){number=n;}}
 static class Hostel implements Serializable {private static final long serialVersionUID=1L;List<Room> rooms=new ArrayList<>();}
 public static void main(String[] args)throws Exception{
  Path file=Path.of(args[1]);
  if(args[0].equals("write"))try(Connection c=Db.open()){
   Hostel hostel=new Hostel();Room a=new Room("A101"),b=new Room("B102");Resident r=new Resident("B Hitesh Roy","192372036",c);a.residents.add(r);b.residents.add(r);hostel.rooms.add(a);hostel.rooms.add(b);
   try(ObjectOutputStream out=new ObjectOutputStream(Files.newOutputStream(file))){out.writeObject(hostel);}System.out.println("Saved graph bytes="+Files.size(file)+" rooms=2 sharedResidents=1");
  }else try(ObjectInputStream in=new ObjectInputStream(Files.newInputStream(file))){
   in.setObjectInputFilter(ObjectInputFilter.Config.createFilter("maxdepth=20;maxrefs=10000;maxbytes=1000000;HostelDemo$*;java.base/*;!*"));
   Hostel h=(Hostel)in.readObject();Resident r=h.rooms.get(0).residents.get(0);
   if(r.password!=null||r.connection!=null||r!=h.rooms.get(1).residents.get(0))throw new AssertionError("Transient fields or graph identity");
   System.out.println("PASS: transient password and connection are null; shared resident identity preserved");if(r.phone!=null)throw new AssertionError("Old file should default phone to null");System.out.println("PASS: added phone defaults to null with stable serialVersionUID");
  }
 }
}
