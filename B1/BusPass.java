import java.math.*;
import java.time.*;
public record BusPass(String passId,String register,String name,int route,String stop,LocalDate validUntil,BigDecimal amount){
 public BusPass {
  if(passId==null||passId.length()>32||!passId.matches("P[0-9]+"))throw new IllegalArgumentException("Invalid pass ID");
  if(register==null||!register.matches("[0-9]{9}"))throw new IllegalArgumentException("Invalid register number");
  if(name==null||name.isBlank()||name.length()>80||stop==null||stop.isBlank()||stop.length()>80)throw new IllegalArgumentException("Invalid name or stop");
  if(name.indexOf('\n')>=0||name.indexOf('\r')>=0||stop.indexOf('\n')>=0||stop.indexOf('\r')>=0)throw new IllegalArgumentException("Multiline text is not supported");
  if(route<=0||validUntil==null||amount==null||amount.signum()<0||amount.compareTo(new BigDecimal("9999999999.99"))>0)throw new IllegalArgumentException("Invalid route date or amount");
  try{amount=amount.setScale(2,RoundingMode.UNNECESSARY);}catch(ArithmeticException e){throw new IllegalArgumentException("Amount needs at most two decimal places",e);}
 }
}
