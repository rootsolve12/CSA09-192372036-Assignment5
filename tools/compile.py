from pathlib import Path
import subprocess,json,datetime
R=Path(__file__).resolve().parents[1];dest=R/'build/common';dest.mkdir(parents=True,exist_ok=True)
compiler=['java','-m','jdk.compiler/com.sun.tools.javac.Main','-g']
sources=list((R/'tools/support').glob('*.java'))+[p for part in ['A1','A2','A3','A4','A5','B1','B2','B3','B4'] for p in (R/part).glob('*.java')]
p=subprocess.run(compiler+['-d',str(dest)]+list(map(str,sources)),capture_output=True,text=True)
if p.returncode:raise RuntimeError(p.stderr)
for task in ['A1','A2','A3','A4','A5','B1','B2','B3','B4']:
 q=R/task;(q/'results').mkdir(exist_ok=True);(q/'screenshots').mkdir(exist_ok=True)
 (q/'results/compiler.txt').write_text('Compiler: '+' '.join(compiler)+'\nTask sources: '+', '.join(str(p.relative_to(R)) for p in sources if p.parent.name==task)+'\nAll shared dependencies compiled into build/common\nExit=0\n')
for version in ['v1','v2','incompatible']:
 target=R/'build/A4'/version;target.mkdir(parents=True,exist_ok=True)
 p=subprocess.run(compiler+['-cp',str(dest),'-d',str(target),str(R/'A4'/version/'HostelDemo.java')],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
print('Compiled all nine task groups and all three serialization versions')
(R/'build/environment.json').write_text(json.dumps({'java':subprocess.run(['java','-version'],capture_output=True,text=True).stderr,'origin':'workspace','utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2))
