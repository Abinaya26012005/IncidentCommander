const assert=require('node:assert/strict'),ui=require('../web/context-ui.js');
assert.match(ui.card(null),/No context measurements/);assert.match(ui.card({status:'investigating'}),/aria-busy="true"/);
for(const strategy of ['JSON','TOON','HYBRID']) for(const status of ['PASS','FAIL']) for(const budget of ['PASS','EXCEEDED','NOT CONFIGURED']) {
 const row={purpose:'RCA',selected_strategy:strategy,original_tokens:1234567,optimized_tokens:1000000,token_reduction:19,integrity_status:status,budget:{status:budget},strategy_reasons:['Long reason '.repeat(100)+'<script>'],integrity_details:{trace_ids:{required:0,preserved:0,status:'N/A'}},candidate_results:['JSON','TOON','HYBRID'].map(s=>({strategy:s,tokens:123,bytes:456,integrity_status:status})),fallback_triggered:true,fallback_reason:'Rejected <unsafe>',delivery:'PREPARED — NOT SENT'};
 for(const app of ['payflow','converselab']) {const i={application_id:app,context_optimization:[{purpose:'INCIDENT_MEMORY',selected_strategy:'JSON',original_tokens:10,optimized_tokens:10,retrieved_incidents:0,runbooks:1},row]};const card=ui.card(i),details=ui.details(i);assert.match(card,/1,234,567/);assert.ok(details.includes(strategy+' ✓'));assert.match(details,/N\/A/);assert.ok(!details.includes('<script>'));assert.match(details,/Incident memory/);assert.match(details,/JSON fallback|Rejected &lt;unsafe&gt;/);}
}
assert.match(ui.card({context_optimization:[{purpose:'RCA',status:'ERROR',fallback_reason:'Unavailable'}]}),/role="alert"/);
console.log('Context UI states passed');
