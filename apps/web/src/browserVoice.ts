/** Browser voices do not expose gender, so prefer known masculine English voice names. */
export function selectMasculineVoice<T extends {name:string;lang:string}>(voices:T[]):T|undefined{
  const preferences:[string,string][]=[
    ['eddy','en-us'],['reed','en-us'],['alex','en-us'],['microsoft guy','en-us'],
    ['microsoft david','en-us'],['microsoft mark','en-us'],['google us english male','en-us'],
    ['daniel','en-gb'],['google uk english male','en-gb'],['fred','en-us'],
    ['ralph','en-us'],['albert','en-us'],['grandpa','en-us'],
  ];
  for(const [name,language] of preferences){const voice=voices.find(v=>v.lang.toLowerCase().startsWith(language)&&v.name.toLowerCase().startsWith(name));if(voice)return voice}
  return voices.find(v=>v.lang.toLowerCase().startsWith('en')&&/\bmale\b/i.test(v.name));
}
