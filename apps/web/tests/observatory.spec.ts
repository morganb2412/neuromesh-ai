import { expect, test } from '@playwright/test';

test('observatory renders and receives grounded investigation events', async ({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Intelligence, in motion/})).toBeVisible();
  await expect(page.locator('.dataset-badge')).toContainText(/DEMONSTRATION DATA|PUBLIC RECORDS/);
  await expect(page.locator('.graph-stage canvas')).toBeVisible();
  await expect(page.locator('.holo-canvas canvas')).toBeVisible();
  await page.getByRole('button',{name:'AI agent research'}).click();
  await expect(page.locator('.message.assistant')).toHaveCount(2);
  await expect(page.locator('.investigation-state')).toContainText(/cited records/);
});

test('research and analytics show indexed measurements', async ({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Research',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Research.'})).toBeVisible();
  await expect(page.locator('.record-grid .workspace-card').first()).toBeVisible();
  await page.getByRole('button',{name:'Locate in graph'}).first().click();
  await expect(page.locator('.entity-inspector')).toBeVisible();
  await page.getByRole('button',{name:'Analytics',exact:true}).click();
  await expect(page.getByText('TF-IDF / PUBLIC RECORD TITLES')).toBeVisible();
  await expect(page.getByText('Dataset SHA-256:')).toBeVisible();
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
  const title=await page.evaluate(async()=>{const graph=await (await fetch('/api/graph')).json();return graph.nodes.find((n:any)=>!n.demo&&n.source_record_id)?.label});
  expect(title).toBeTruthy();
  await page.evaluate(value=>(window as any).__fakeTranscript=`Find evidence about ${value}`,title);
  await page.getByRole('button',{name:'Talk to NeuroMesh'}).click();
  await expect(page.locator('.message.user')).toContainText(title);
  await expect(page.getByTitle('Toggle voice mode')).toContainText('Voice on');
  await expect.poll(()=>page.evaluate(()=>(window as any).__spokenText||''),{timeout:15000}).not.toBe('');
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
  await page.getByRole('button',{name:'Talk to NeuroMesh'}).click();
  await expect(page.locator('.message.assistant').last()).toContainText('could not find a working microphone');
  await expect(page.locator('.investigation-state')).toContainText('audio-capture');
});
