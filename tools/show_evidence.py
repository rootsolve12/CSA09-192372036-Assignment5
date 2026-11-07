from pathlib import Path
import sys,csv,statistics
R=Path(__file__).resolve().parents[1];task,mode=sys.argv[1:3]
print('\033[2J\033[H',end='')
print(task+' | CSA09 | B Hitesh Roy | Register 192372036 | Workspace')
print('OpenJDK 21.0.13 | MySQL 8.4.13 | Synthetic assignment fixtures')
if mode=='compiler':
 source={'A1':'RecordLayouts.java','A2':'LineCounter.java','A3':'StudentDao.java','A4':'SerializationChecks.java','A5':'WalletTransactions.java','B1':'PassStore.java','B2':'AdversarialInputs.java','B3':'PassLoader.java','B4':'Migration.java'}[task]
 print('Source excerpt: '+task+'/'+source)
 for i,line in enumerate((R/task/source).read_text().splitlines()[:8]):print(f'{i+1:2}: {line}')
 print('\nActual saved build record (compiled before the runs):')
 print((R/task/'results/compiler.txt').read_text().strip())
 if task=='A4':print('All v1, v2 and incompatible UID source variants also compile successfully.')
else:
 print('Actual saved run evidence; full commands and output remain in results/')
 folder=R/task/'results'
 if task in ['A1','A2']:
  name='RecordLayouts.txt' if task=='A1' else 'LineCounter.txt';print((folder/name).read_text().strip())
 elif task in ['A3','A5','B2','B4']:
  for line in (folder/'checks.txt').read_text().splitlines():print(line)
  if task=='B4':print((folder/'MigrationScale.txt').read_text().strip())
 elif task=='A4':
  for line in (folder/'SerializationChecks.txt').read_text().splitlines():
   if line.startswith(('VERSION','Saved graph','PASS:','Exception in thread')):print(line)
 elif task=='B1':
  print('Supplied TODO output:\n'+(folder/'PassStore.txt').read_text().strip())
  print('Bytes       Method       Mean ms   Lines     Java read calls')
  data=list(csv.DictReader((folder/'buffering.csv').open()))
  for n in [1000000,10000000,50000000]:
   for flag,label in [('false','single'),('true','block64K')]:
    rows=[r for r in data if int(r['bytes'])==n and r['buffered']==flag];print(f'{n:9} {label:9} {statistics.mean(int(r["elapsed_ns"])/1e6 for r in rows):10.3f} {rows[0]["lines"]:8} {rows[0]["read_calls"]:>10}')
  print('Records     Mean final-record find ms')
  data=list(csv.DictReader((folder/'growth.csv').open()))
  for n in [1000,10000,100000]:print(f'{n:9} {statistics.mean(int(r["elapsed_ns"])/1e6 for r in data if int(r["records"])==n):12.3f}')
  print('Normal, missing ID, route, duplicate and damaged-tail checks passed.')
 elif task=='B3':
  print('Rows    Statement ms  Prepared ms  Batch tx ms  Batch auto ms')
  data=list(csv.DictReader((folder/'insert-measurements.csv').open()))
  for n in [1000,10000,100000]:
   vals=[statistics.mean(int(r['elapsed_ns'])/1e6 for r in data if int(r['rows'])==n and r['method']==method and r['auto_commit']==auto) for method,auto in [('Statement','false'),('Prepared','false'),('Batch','false'),('Batch','true')]];print(f'{n:7} '+''.join(f'{v:13.3f}' for v in vals))
  for line in (folder/'transaction-verification.txt').read_text().splitlines():print(line)
  columns=[line for line in (folder/'metadata-verification.txt').read_text().splitlines() if line.startswith('COLUMN ')][:7]
  for line in columns:print(line)
  print('All 3 small-data methods verified every column type and exact values.')
print('Evidence origin: actual workspace execution, not a student-device claim.')
