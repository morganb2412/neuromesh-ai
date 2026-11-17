import { expect, test, type Page } from '@playwright/test';

const adminToken=process.env.NEUROMESH_TEST_ADMIN_TOKEN;
async function signIn(page:Page){
  test.skip(!adminToken,'requires a configured test operator token');
  await page.route('**/api/speech',route=>route.fulfill({status:503,body:'Browser speech test'}));
  await page.getByRole('button',{name:'Admin',exact:true}).click();
  await page.getByLabel('OPERATOR TOKEN').fill(adminToken!);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('button',{name:'Admin active'})).toBeVisible();
}

test('public visitors can browse but cannot ask the assistant',async({page})=>{
  await page.goto('/');
  await expect(page.locator('.guest-access')).toContainText('read only');
  await expect(page.getByRole('textbox',{name:'Research question'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Talk to NeuroMesh'})).toHaveCount(0);
  const response=await page.request.post('/api/investigate',{data:{question:'Find continual learning research'}});
  expect(response.status()).toBe(403);
});

test('invalid admin sign-in leaves the public view read only',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Admin',exact:true}).click();
  await page.getByLabel('OPERATOR TOKEN').fill('invalid-token');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Token not accepted');
  await expect(page.locator('.guest-access')).toContainText('read only');
  await expect(page.getByRole('textbox',{name:'Research question'})).toHaveCount(0);
});

test('unavailable API shows no fabricated graph or counts', async ({page})=>{
  await page.route('**/api/graph',route=>route.abort());
  await page.route('**/api/status',route=>route.abort());
  await page.goto('/');
  await expect(page.locator('.system-pill')).toContainText('API OFFLINE');
  await expect(page.locator('.dataset-badge')).toContainText('API OFFLINE');
  await expect(page.locator('.graph-status')).toContainText('NO INDEXED GRAPH');
  await expect(page.locator('.metric-value')).toContainText('0');
  await expect(page.locator('.holo-canvas canvas')).toBeVisible();
});

test('observatory renders and receives grounded investigation events', async ({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Intelligence, in motion/})).toBeVisible();
  await expect(page.locator('.dataset-badge')).toContainText(/DEMONSTRATION DATA|PUBLIC RECORDS/);
  await expect(page.locator('.graph-stage canvas')).toBeVisible();
  await expect(page.locator('.holo-canvas canvas')).toBeVisible();
  await signIn(page);
  await page.getByRole('button',{name:'AI agent research'}).click();
  await expect(page.locator('.message.assistant')).toHaveCount(2);
  await expect(page.locator('.investigation-state')).toContainText(/cited records/);
});

test('research and analytics show indexed measurements', async ({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Research',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Research.',exact:true})).toBeVisible();
  await expect(page.locator('.record-grid .workspace-card').first()).toBeVisible();
  await page.getByRole('button',{name:'Locate in graph'}).first().click();
  await expect(page.locator('.entity-inspector')).toBeVisible();
  await page.getByRole('button',{name:'Analytics',exact:true}).click();
  await expect(page.getByText('TF-IDF / PUBLIC RECORD TITLES')).toBeVisible();
  await expect(page.getByText('Dataset SHA-256:')).toBeVisible();
});

test('admin panel exposes source controls and explicit agent mode', async ({page})=>{
  await page.goto('/');
  await signIn(page);
  await page.getByRole('button',{name:'Admin active'}).click();
  const sources=page.getByRole('combobox',{name:'Public source'});
  await expect(sources.locator('option')).toHaveCount(6);
  await sources.selectOption('pubmed');
  await expect(page.getByRole('button',{name:'Sync pubmed'})).toBeEnabled();
  await expect(page.getByRole('checkbox',{name:'Use Gemini agent for questions'})).not.toBeChecked();
  await page.getByRole('button',{name:'Sign out'}).click();
  await expect(page.locator('.guest-access')).toContainText('read only');
  await expect(page.locator('.message')).toHaveCount(0);
  await page.getByRole('button',{name:'Experiments',exact:true}).click();
  await expect(page.getByText('Use Admin sign-in')).toBeVisible();
});

test('first microphone turn automatically enables spoken reply', async ({page})=>{
  await page.addInitScript(()=>{
    const state=window as any;
    class FakeRecognition{
      onresult: ((event:any)=>void)|null=null; onerror:null=null; onend:(()=>void)|null=null;
      start(){setTimeout(()=>{this.onresult?.({results:[[ {transcript:state.__fakeTranscript} ]]});this.onend?.()},100)}
      stop(){}
    }
    Object.defineProperty(window,'SpeechRecognition',{value:FakeRecognition,configurable:true});
    Object.defineProperty(window,'webkitSpeechRecognition',{value:FakeRecognition,configurable:true});
    Object.defineProperty(window,'speechSynthesis',{value:{cancel(){},speak(utterance:any){state.__spokenText=utterance.text;utterance.onstart?.();setTimeout(()=>utterance.onend?.(),1500)}},configurable:true});
  });
  await page.goto('/');
  await signIn(page);
  const title=await page.evaluate(async()=>{const graph=await (await fetch('/api/graph')).json();return graph.nodes.find((n:any)=>!n.demo&&n.source_record_id)?.label});
  expect(title).toBeTruthy();
  await page.evaluate(value=>(window as any).__fakeTranscript=`Find evidence about ${value}`,title);
  await page.getByRole('button',{name:'Talk to NeuroMesh'}).click();
  await expect(page.locator('.message.user')).toContainText(title);
  await expect(page.getByTitle('Toggle voice mode')).toContainText('Voice on');
  await expect.poll(()=>page.evaluate(()=>(window as any).__spokenText||''),{timeout:15000}).not.toBe('');
});

test('browser speech chooses the available masculine voice', async ({page})=>{
  await page.addInitScript(()=>{
    const state=window as any;
    Object.defineProperty(window,'SpeechSynthesisUtterance',{value:class{voice:any=null;onstart:any;onend:any;onerror:any;onboundary:any;text:string;constructor(text:string){this.text=text}},configurable:true});
    Object.defineProperty(window,'speechSynthesis',{value:{cancel(){},getVoices(){return [{name:'Samantha',lang:'en-US'},{name:'Eddy (English (United States))',lang:'en-US'}]},speak(utterance:any){state.__voiceName=utterance.voice?.name;utterance.onstart?.();setTimeout(()=>utterance.onend?.(),100)}},configurable:true});
  });
  await page.goto('/');
  await signIn(page);
  await page.getByTitle('Toggle voice mode').click();
  await page.getByTitle('Unmute assistant').click();
  await page.getByRole('button',{name:'AI agent research'}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__voiceName)).toBe('Eddy (English (United States))');
});

test('the 3D jaw reacts to a spoken word boundary and stops on interruption', async ({page})=>{
  await page.addInitScript(()=>{
    const state=window as any;
    const original=window.matchMedia.bind(window);
    window.matchMedia=(query:string)=>query.includes('prefers-reduced-motion')
      ? {matches:true,media:query,addEventListener(){},removeEventListener(){}} as any : original(query);
    Object.defineProperty(window,'SpeechSynthesisUtterance',{value:class{voice:any=null;onstart:any;onend:any;onerror:any;onboundary:any;text:string;constructor(text:string){this.text=text}},configurable:true});
    Object.defineProperty(window,'speechSynthesis',{value:{cancel(){},getVoices(){return [{name:'Eddy (English (United States))',lang:'en-US'}]},speak(utterance:any){state.__utterance=utterance;utterance.onstart?.()}},configurable:true});
  });
  await page.goto('/');
  await signIn(page);
  await page.getByTitle('Toggle voice mode').click();
  await page.getByTitle('Unmute assistant').click();
  await page.getByRole('button',{name:'AI agent research'}).click();
  await expect(page.locator('.hologram')).toHaveAttribute('data-state','speaking');
  await page.waitForTimeout(650);
  const canvas=page.locator('.holo-canvas canvas');
  const before=await canvas.screenshot();
  await page.evaluate(()=>(window as any).__utterance.onboundary?.({name:'word',charIndex:0}));
  await page.waitForTimeout(90);
  const speaking=await canvas.screenshot();
  expect(speaking.equals(before)).toBe(false);
  await page.getByTitle('Stop speaking or investigating').click();
  await expect(page.locator('.hologram')).toHaveAttribute('data-state','interrupted');
});

test('microphone reconnects after a premature recognition end', async ({page})=>{
  await page.addInitScript(()=>{
    const state=window as any;
    class FakeRecognition{
      onresult:((event:any)=>void)|null=null;onerror:((event:any)=>void)|null=null;onend:(()=>void)|null=null;
      start(){state.__starts=(state.__starts||0)+1;if(state.__starts===1)setTimeout(()=>this.onend?.(),10);else setTimeout(()=>this.onresult?.({results:[[{transcript:'Find public funding records',isFinal:true}]]}),10)}
      stop(){this.onend?.()}
    }
    Object.defineProperty(window,'SpeechRecognition',{value:FakeRecognition,configurable:true});
    Object.defineProperty(window,'speechSynthesis',{value:{cancel(){},speak(utterance:any){utterance.onstart?.();utterance.onend?.()}},configurable:true});
  });
  await page.goto('/');
  await signIn(page);
  await page.getByRole('button',{name:'Talk to NeuroMesh'}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__starts)).toBe(2);
  await expect(page.locator('.message.user')).toContainText('Find public funding records');
  await expect(page.locator('.message.assistant').last()).not.toContainText('could not hear');
});

test('microphone keeps listening after a no-speech timeout', async ({page})=>{
  await page.addInitScript(()=>{
    const state=window as any;
    class FakeRecognition{
      onresult:((event:any)=>void)|null=null;onerror:((event:any)=>void)|null=null;onend:(()=>void)|null=null;
      start(){state.__starts=(state.__starts||0)+1;if(state.__starts===1)setTimeout(()=>{this.onerror?.({error:'no-speech'});this.onend?.()},10);else setTimeout(()=>this.onresult?.({results:[[{transcript:'Show indexed AI agent research',isFinal:true}]]}),10)}
      stop(){}
    }
    Object.defineProperty(window,'SpeechRecognition',{value:FakeRecognition,configurable:true});
    Object.defineProperty(window,'speechSynthesis',{value:{cancel(){},speak(utterance:any){utterance.onstart?.();utterance.onend?.()}},configurable:true});
  });
  await page.goto('/');
  await signIn(page);
  await page.getByRole('button',{name:'Talk to NeuroMesh'}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__starts)).toBe(2);
  await expect(page.locator('.message.user')).toContainText('Show indexed AI agent research');
});

test('microphone failure reports the actual browser error', async ({page})=>{
  await page.addInitScript(()=>{
    class FakeRecognition{
      onresult:null=null;onerror:((event:any)=>void)|null=null;onend:(()=>void)|null=null;
      start(){setTimeout(()=>{this.onerror?.({error:'audio-capture'});this.onend?.()},10)}
      stop(){}
    }
    Object.defineProperty(window,'SpeechRecognition',{value:FakeRecognition,configurable:true});
  });
  await page.goto('/');
  await signIn(page);
  await page.getByRole('button',{name:'Talk to NeuroMesh'}).click();
  await expect(page.locator('.message.assistant').last()).toContainText('could not find a working microphone');
  await expect(page.locator('.investigation-state')).toContainText('audio-capture');
});
