// Only stdin JSON enters this fixed reference-codec process. No shell or model code.
import {encode,decode} from '@toon-format/toon';
let raw=''; for await(const chunk of process.stdin) raw+=chunk;
try {
 const {op,values}=JSON.parse(raw);
 const result=values.map(value=>op==='decode'?decode(value,{strict:true}):{text:encode(value),decoded:decode(encode(value),{strict:true})});
 process.stdout.write(JSON.stringify(result));
} catch {process.stderr.write('TOON codec rejected input');process.exitCode=1;}
