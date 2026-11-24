import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {spawnSync} from 'node:child_process';
import {get_lightning_status, sanitizeStatus, SOCKET_PATH} from '../scripts/lightning_status.mjs';
const PIN='026634a7f5dd7f3f70d69760e99bb5a4ffecada96ed0b514c88738c97df92c5860';
const valid={status:'verified-read-only',network:'bitcoin',nodePublicKey:PIN,balanceScope:'credential-bound-not-other-apps',connectionBalanceMsat:0,connectionBalanceSats:0,paymentsEnabled:false,invoiceCreationEnabled:false};
function transport({body=JSON.stringify(valid),status=200,type='application/json',error,aborted=false}={}) {
  let calls=0,options;
  return {get calls(){return calls;},get options(){return options;},request(opts,callback){
    calls++;options=opts;const req=new EventEmitter();req.destroy=()=>{};
    req.end=()=>queueMicrotask(()=>{
      if(error){req.emit('error',error);return;}
      const response=new EventEmitter();response.statusCode=status;response.headers={'content-type':type};response.resume=()=>{};
      callback(response);if(aborted){response.emit('aborted');return;}response.emit('data',Buffer.from(body));response.emit('end');
    });return req;
  }};
}
test('only local status GET, one request, no secret output',async()=>{
 const t=transport({body:JSON.stringify({...valid,secret:'DO_NOT_PRINT',transactions:['private']})});
 const result=await get_lightning_status({expectedNodePublicKey:PIN,requestImpl:t.request});
 assert.equal(t.calls,1);assert.deepEqual(t.options,{socketPath:SOCKET_PATH,path:'/v1/status',method:'GET',agent:false});assert.deepEqual(result,valid);assert(!JSON.stringify(result).includes('DO_NOT_PRINT'));
});
test('no identity pin means no transport',async()=>{
 const t=transport();await assert.rejects(get_lightning_status({requestImpl:t.request}),/INVALID_PUBLIC_IDENTITY_PIN/);assert.equal(t.calls,0);
});
test('identity, network, balance scope and disabled operations enforced',()=>{
 for(const bad of [{nodePublicKey:'03'+'a'.repeat(64)},{network:'testnet'},{balanceScope:'main-wallet'},{paymentsEnabled:true},{invoiceCreationEnabled:true}])assert.throws(()=>sanitizeStatus({...valid,...bad},PIN));
});
test('bounded numeric balance including msat precision; never claims spendable',()=>{
 assert.equal(sanitizeStatus({...valid,connectionBalanceMsat:1001,connectionBalanceSats:1.001},PIN).connectionBalanceSats,1.001);
 for(const amount of [-1,1.5,Number.MAX_SAFE_INTEGER+1,NaN,'0',false])assert.throws(()=>sanitizeStatus({...valid,connectionBalanceMsat:amount},PIN));
 assert.throws(()=>sanitizeStatus({...valid,connectionBalanceMsat:1000,connectionBalanceSats:2},PIN));
});
test('HTTP failures and redirects never retried or followed',async()=>{
 for(const status of [301,404,429,503]){const t=transport({status,body:'SECRET_FAILURE'});await assert.rejects(get_lightning_status({expectedNodePublicKey:PIN,requestImpl:t.request}),e=>!e.message.includes('SECRET_FAILURE'));assert.equal(t.calls,1);}
});
test('oversized, malformed and wrong-type responses fail closed',async()=>{
 for(const t of [transport({body:'x'.repeat(8193)}),transport({body:'PRIVATE_NOT_JSON'}),transport({type:'text/html'})])await assert.rejects(get_lightning_status({expectedNodePublicKey:PIN,requestImpl:t.request}));
});
test('transport errors and aborted responses are sanitized',async()=>{
 for(const t of [transport({error:Object.assign(Error('PRIVATE_RAW_ERROR'),{code:'EACCES'})}),transport({aborted:true})])await assert.rejects(get_lightning_status({expectedNodePublicKey:PIN,requestImpl:t.request}),e=>!e.message.includes('PRIVATE_RAW_ERROR'));
});
test('CLI rejects payment, invoice, URI and arbitrary socket options before connection',()=>{
 for(const args of [['pay_invoice','PRIVATE_INVOICE'],['create_invoice','1'],['--socket','/private'],['--nwc-uri','PRIVATE_URI']]){
  const result=spawnSync(process.execPath,['scripts/lightning_status.mjs',...args],{encoding:'utf8'});assert.equal(result.status,2);assert.deepEqual(JSON.parse(result.stdout),{status:'unavailable',code:'INVALID_ARGUMENTS',automaticRetry:false});assert.equal(result.stderr,'');
 }
});
test('absolute deadline destroys request; no retry',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});let calls=0,destroyed=false;
 const requestImpl=()=>{calls++;const req=new EventEmitter();req.end=()=>{};req.destroy=()=>{destroyed=true;};return req;};
 const promise=get_lightning_status({expectedNodePublicKey:PIN,requestImpl});const rejected=assert.rejects(promise,/BROKER_TIMEOUT/);t.mock.timers.tick(15000);await rejected;assert.equal(calls,1);assert.equal(destroyed,true);
});
test('real Unix HTTP transport interoperates with broker-shaped JSON',async t=>{
 const http=await import('node:http');const fs=await import('node:fs/promises');const os=await import('node:os');const path=await import('node:path');
 const directory=await fs.mkdtemp(path.join(os.tmpdir(),'skill-status-'));const socket=path.join(directory,'status.sock');let requests=0;
 const server=http.createServer((request,response)=>{requests++;assert.equal(request.url,'/v1/status');response.writeHead(200,{'Content-Type':'application/json','Connection':'close'});response.end(JSON.stringify(valid));});
 await new Promise(resolve=>server.listen(socket,resolve));t.after(async()=>{await new Promise(resolve=>server.close(resolve));await fs.rm(directory,{recursive:true,force:true});});
 const result=await get_lightning_status({expectedNodePublicKey:PIN,requestImpl:(options,callback)=>{assert.equal(options.socketPath,SOCKET_PATH);return http.request({...options,socketPath:socket},callback);}});
 assert.deepEqual(result,valid);assert.equal(requests,1);
});
