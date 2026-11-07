from pathlib import Path
import subprocess,sys,os,datetime,json
R=Path(__file__).resolve().parents[1];os.chdir(R)
TASKS={'A1':['RecordLayouts'],'A2':['LineCounter'],'A3':['StudentDao'],'A4':['SerializationChecks'],'A5':['WalletTransactions'],'B1':['PassStore','FileExperiments','BufferExperiments'],'B2':['AdversarialInputs'],'B3':['InsertExperiments'],'B4':['Migration','MigrationScale']}
selected=sys.argv[1:] or list(TASKS)
(R/'generated/tmp').mkdir(parents=True,exist_ok=True)
java=['java','-Xms128m','-Xmx512m','-Djava.io.tmpdir='+str(R/'generated/tmp'),'-cp','build/common'+os.pathsep+'deps/mysql-connector-j.jar']
for task in selected:
 folder=R/task/'results';folder.mkdir(exist_ok=True)
 with (folder/'execution.txt').open('w') as total:
  for main in TASKS[task]:
   print('RUN',task,main,flush=True)
   with (folder/(main+'.txt')).open('w') as log:
    p=subprocess.run(java+[main],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
   output=(folder/(main+'.txt')).read_text();total.write('$ java '+main+'\n'+output+'\n');total.flush()
   if p.returncode:raise RuntimeError(task+'/'+main+' failed, see '+str(folder/(main+'.txt')))
 checks=[line for line in (folder/'execution.txt').read_text().splitlines() if line.startswith(('PASS:','MEASURE','AFTER FAILURE','COLUMN','DATABASE','DRIVER','TABLE','TRANSACTIONS','REJECT','VERSION','Text record','Transaction','Independent','Migration'))]
 (folder/'checks.txt').write_text('\n'.join(checks)+'\n')
 env={'task':task,'java':subprocess.run(['java','-version'],capture_output=True,text=True).stderr,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'origin':'workspace','jdbc':'MySQL Connector/J 9.5.0; dedicated assignment5 database','heap':'128 MiB initial, 512 MiB max','run_command':'python tools/run.py '+task}
 (folder/'environment.json').write_text(json.dumps(env,indent=2)+'\n');print('DONE',task,flush=True)
