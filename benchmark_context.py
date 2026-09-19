"""Measured fixtures + saved hero evidence. No provider call or live-AI claim."""
import json,time
from pathlib import Path
from ai_reasoning import bounded_input
from context_optimization import ContextOptimizationRequest,optimize
from context_optimization.fixtures import fixtures

def run(output):
    cases=fixtures();root=Path(__file__).parent
    for app in ('PAYFLOW','CONVERSELAB'):
        path=root.parent/('HARDENING-'+app+'-AFTER.json')
        if path.exists():
            inc=json.loads(path.read_text(encoding='utf-8'))
            cases[app.lower()+'_hero']=json.loads(bounded_input(inc['evidence'],{'application_id':inc['application_id'],'incident_id':inc['id'],'services':inc['affected_services'],'allowed_files':['config.json'] if app=='CONVERSELAB' else ['config.json','payment_logic.py']}))
    results=[]
    for name,payload in cases.items():
        app='converselab' if name.startswith('converselab') else 'payflow'
        row=optimize(ContextOptimizationRequest(payload,'RCA',app,'BENCH-'+name)).public();row['fixture']=name;results.append(row)
        print(name,row['selected_strategy'],[(c['strategy'],c['tokens']) for c in row['candidate_results']],row['token_reduction'],row['total_optimization_time_ms'])
    output.write_text(json.dumps({'timestamp':time.time(),'scope':'Synthetic fixtures and previously recorded hero evidence; no live LLM','results':results},indent=2),encoding='utf-8')

if __name__=='__main__':run(Path(__file__).parent.parent/'CONTEXT-BENCHMARKS.json')
