import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const SKILL=process.env.AMAZON_CLV_PRESENTATION_SKILL ?? '/Users/Darsh/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
const PY=process.env.AMAZON_CLV_RUNTIME_PYTHON ?? '/Users/Darsh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')));
const FONT=resolvePresentationFont();
console.log('Selected installed presentation font:',FONT);
const D=JSON.parse(await fs.readFile(path.join(ROOT,'reports/release_data.json'),'utf8'));
const pres=Presentation.create({slideSize:{width:1280,height:720}});
const C={navy:'#142D42',teal:'#087E83',orange:'#E89B3C',muted:'#526878',light:'#E7EFF2',white:'#FFFFFF'};
const money=v=>'$'+Math.round(v).toLocaleString('en-US');
const pct=v=>(v*100).toFixed(1)+'%';
const sources='Data: Berke et al. (2024), Scientific Data 11, 491. https://www.nature.com/articles/s41597-024-03329-6 . Harvard Dataverse v1.0, CC0 1.0. https://doi.org/10.7910/DVN/YGLYDY . Analysis: saved project run amazon-clv-1.0-6efb098a6e, seed 42. All spending figures are recorded customer purchase value, not Amazon net revenue/profit or incremental campaign revenue.';
function txt(s,text,x,y,w,h,size=26,color=C.navy,bold=false){
 const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=text; a.text.style={typeface:FONT,fontSize:size,color,bold}; return a;
}
function slide(title,subtitle=''){
 const s=pres.slides.add();s.background.fill=C.white;
 txt(s,'AMAZON CUSTOMER VALUE  /  HISTORICAL DEMONSTRATION',64,26,1120,25,15,C.teal,true);
 txt(s,title,64,76,1150,110,44,C.navy,true);
 if(subtitle)txt(s,subtitle,64,176,1150,60,25,C.muted);
 txt(s,'Recorded purchase value · 2018 through October 2022',64,675,1030,24,14,C.muted);
 txt(s,String(pres.slides.items.length).padStart(2,'0')+' / 12',1120,675,110,24,14,C.muted);
 s.speakerNotes.text=sources;
 return s;
}
function table(s,values,x=64,y=250,w=1152,h=320,widths=null,size=22){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,...(widths?{columnWidths:widths}:{})});
 t.borders.assign({fill:C.light,width:.7,style:'solid'});
 for(let r=0;r<values.length;r++)for(let col=0;col<values[0].length;col++){
  const cell=t.getCell(r,col);cell.fill=r===0?C.light:C.white;
  cell.text.style={typeface:FONT,fontSize:size,color:C.navy,bold:r===0};
 }
 return t;
}
function chart(s,type,categories,series,position,options={}){
 const c=s.charts.add(type,{position,categories,series:series.map(s=>({...s,values:s.values.map(v=>Number(v.toFixed(8)))})),hasLegend:series.length>1,legend:{position:'bottom',textStyle:{fontSize:18,fill:C.navy}},chartFill:C.white,plotAreaFill:C.white,xAxis:{textStyle:{fontSize:17,fill:C.muted},majorGridlines:null},yAxis:{textStyle:{fontSize:17,fill:C.muted},majorGridlines:{fill:C.light,width:1,style:'solid'}},...options});
 applyPresentationChartFont(c,{fontFamily:FONT});return c;
}
function note(s,text){txt(s,text,64,608,1152,56,23,C.muted);}

let s=slide('Amazon customer value forecasts');
txt(s,'90-day and 180-day spending',64,242,1130,80,52,C.teal,true);
txt(s,'Marketing prioritization within an illustrative contact budget',64,350,1050,86,34);
txt(s,'A reproducible local analysis of real, consented purchase histories',64,474,1000,75,27,C.muted);
txt(s,'October 2026',64,581,700,40,23,C.muted);

s=slide('Dataset and observation contract','Verified original bytes, with an explicit common observation window');
table(s,[['Measure','Retained analysis'],['Accounts',D.audit.valid_customers.toLocaleString('en-US')],['Purchased-item rows',D.audit.valid_rows.toLocaleString('en-US')],['Recorded purchase value',money(D.audit.total_value_cents/100)],['Observation window','January 2018 through October 2022'],['Later-dated rows excluded','113,659, including one 2024 record']],64,250,1152,330,[400,752],25);
note(s,'Harvard Dataverse v1.0, CC0 1.0. MD5 matches the original. Identical rows remain because order IDs are unavailable.');

s=slide('Purchase-value concentration','A minority of accounts explains much of the recorded spending');
chart(s,'line',D.concentration.map(r=>pct(r.customer_fraction)),[{name:'Share of recorded spending',values:D.concentration.map(r=>r.spending_fraction),line:{fill:C.teal,width:3,style:'solid'}},{name:'Equal spending',values:D.concentration.map(r=>r.customer_fraction),line:{fill:'#A6B5C0',width:1.5,style:'dashed'}}],{left:80,top:245,width:1110,height:350},{xAxis:{title:'Accounts, highest spending first',textStyle:{fontSize:16}},yAxis:{numberFormatCode:'0%',min:0,max:1,textStyle:{fontSize:18},majorGridlines:{fill:C.light,width:1}}});
note(s,'Descriptive concentration uses the full retained window. It does not measure the additional value of a prediction model.');

s=slide('Snapshot features and future spending','One account at one historical scoring date is one modeling observation');
table(s,[['Component','Date rule','Meaning'],['Features','Purchase date < scoring date','Only earlier information'],['90-day target','[scoring date, scoring date + 90 days)','Recorded future value'],['180-day target','[scoring date, scoring date + 180 days)','Contains the 90-day window'],['No future purchase','Complete window observed','Zero target remains present'],['Incomplete window','End exceeds October 2022 coverage','Unavailable target, never zero']],64,250,1152,315,[245,470,437],21);
note(s,'Features: recency, observed history, purchase days, spending windows, diversity, category shares, trends, and seasonality.');

s=slide('Label-aware chronological validation','Training examples must finish their entire target window before the cutoff');
table(s,[['Stage','Cutoff','90-day latest label end','180-day latest label end'],['Validation fold 1','2021-01-01','2020-12-30','2020-12-28'],['Validation fold 2','2021-07-01','2021-03-01','2021-05-30'],['Final fitting','2022-01-01','2021-12-30','2021-12-28'],['Final test 1','2022-01-01','Frozen bundle','Frozen bundle'],['Final test 2','2022-05-01','Same frozen bundle','Same frozen bundle']],64,250,1152,315,[270,210,336,336],22);
note(s,'Development scoring dates are in 2019–2020. Final refitting may use mature 2021 labels after choices freeze.');

s=slide('Validation selected different models by horizon','90 days: histogram boosting. 180 days: Ridge with alpha 100');
for(const [idx,h] of [90,180].entries()){
 const all=D.validation_summary.filter(r=>r.horizon===h);
 const best=kind=>all.filter(r=>r.kind===kind).sort((a,b)=>a.mean_rmse-b.mean_rmse)[0];
 const rows=[all.find(r=>r.name==='trailing_90'),all.find(r=>r.name==='trailing_365'),best('ridge'),best('hgb')];
 chart(s,'bar',['Trailing 90d','Trailing 365d','Best Ridge','Best boosting'],[{name:'Mean validation RMSE',values:rows.map(r=>r.mean_rmse),fill:idx?C.orange:C.teal}],{left:64+idx*585,top:246,width:555,height:350},{title:h+'-day validation RMSE',titleTextStyle:{fontSize:25},hasLegend:false,barOptions:{direction:'column',grouping:'clustered'},yAxis:{numberFormatCode:'$#,##0',textStyle:{fontSize:17},majorGridlines:{fill:C.light,width:1}},xAxis:{textStyle:{fontSize:15}}});
}
note(s,'Bounded search and a predeclared 1% RMSE tie rule. The 180-day comparisons include max(raw180, selected90).');

s=slide('Untouched 2022 test performance','The same final models score both dates without refitting');
table(s,[['Scoring date','Days','MAE','RMSE','WAPE','Top 20% capture','Gain vs history']].concat(D.selected_metrics.map(r=>[r.scoring_date,String(r.horizon),money(r.mae),money(r.rmse),pct(r.wape),pct(r.capture_20),r.capture_20_gain_pp.toFixed(2)+' pp'])),64,255,1152,300,[185,80,145,145,145,190,262],23);
note(s,'Ranking gains over trailing-year spending are modest: 0.28–0.99 percentage points. Lower RMSE does not imply large marketing gains.');

s=slide('Calibration exposes amount-forecast limitations','January 2022 deciles, ranked by predicted spending from lowest to highest');
for(const [idx,h] of [90,180].entries()){
 const cal=D.calibration.filter(r=>r.horizon===h&&r.scoring_date==='2022-01-01');
 chart(s,'line',cal.map(r=>String(r.decile)),[{name:'Predicted',values:cal.map(r=>r.predicted_mean),line:{fill:C.teal,width:3},marker:{symbol:'circle',size:5}},{name:'Actual',values:cal.map(r=>r.actual_mean),line:{fill:C.orange,width:3},marker:{symbol:'circle',size:5}}],{left:64+idx*585,top:245,width:555,height:350},{title:h+'-day mean spending by decile',titleTextStyle:{fontSize:24},yAxis:{numberFormatCode:'$#,##0',textStyle:{fontSize:17},majorGridlines:{fill:C.light,width:1}},xAxis:{title:'Predicted-value decile',textStyle:{fontSize:18}}});
}
note(s,'January total forecasts overstate actual spending by 16.6% at 90 days and 25.3% at 180 days. Good rankings can coexist with poor calibration.');

s=slide('Horizon comparison and uncertainty','Normalized errors favor 180 days, while 90 days has better aggregate calibration');
const dates=['2022-01-01','2022-05-01'];
for(const [idx,measure] of ['wape','normalized_rmse'].entries()){
 chart(s,'bar',dates,[90,180].map((h,i)=>({name:h+' days',values:dates.map(d=>D.selected_metrics.find(r=>r.horizon===h&&r.scoring_date===d)[measure]),fill:i?C.orange:C.teal})),{left:64+idx*585,top:245,width:555,height:315},{title:measure==='wape'?'WAPE':'RMSE / mean actual spending',titleTextStyle:{fontSize:24},barOptions:{direction:'column',grouping:'clustered'},yAxis:{numberFormatCode:'0.00',textStyle:{fontSize:18},majorGridlines:{fill:C.light,width:1}}});
}
txt(s,'500 customer-level bootstrap resamples preserve repeated dates per account.',64,571,1152,40,23,C.muted);
txt(s,'Intervals condition on fitted models. Overlapping windows and calendar uncertainty remain.',64,615,1152,40,23,C.muted);

s=slide('Customer-value coverage under a contact budget','January 2022. Illustrative $1,000 budget at $1 per contact, selecting 1,000 accounts');
for(const [idx,h] of [90,180].entries()){
 const m=D.marketing.filter(r=>r.horizon===h&&r.scoring_date==='2022-01-01');
 chart(s,'bar',['Predicted','Historical','Recency','Random'],[{name:'Actual spending covered',values:m.map(r=>r.coverage_fraction),fill:idx?C.orange:C.teal}],{left:64+idx*585,top:245,width:555,height:350},{title:h+'-day coverage',titleTextStyle:{fontSize:26},hasLegend:false,barOptions:{direction:'column',grouping:'clustered'},yAxis:{numberFormatCode:'0%',min:0,max:.6,textStyle:{fontSize:18},majorGridlines:{fill:C.light,width:1}},xAxis:{textStyle:{fontSize:19}}});
}
note(s,'Covered spending is observed value among selected accounts. A campaign’s incremental revenue cannot be estimated from these histories.');

s=slide('Gift-card sensitivity and customer errors','The independent sensitivity changes targets, cohort eligibility, and sometimes selected models');
table(s,[['Date','Days','Primary normalized RMSE','No-gift normalized RMSE','No-gift model']].concat(D.selected_metrics.map(r=>{const a=D.sensitivity.find(a=>a.analysis.startsWith('Sensitivity')&&a.horizon===r.horizon&&a.scoring_date===r.scoring_date);return[r.scoring_date,String(r.horizon),r.normalized_rmse.toFixed(3),a.normalized_rmse.toFixed(3),a.model]})),64,250,1152,260,[190,80,270,270,342],22);
txt(s,'Dollar RMSE declines after excluding gift-card titles, while normalized errors worsen slightly.',64,543,1152,50,25,C.navy);
note(s,'Separate error tables cover short histories, inactive accounts, and high historical spenders. Feature importance measures predictive association.');

s=slide('Scope, limitations, and next steps','A reproducible historical portfolio with explicit limits on business claims');
txt(s,'What the evidence supports',64,255,560,45,31,C.teal,true);
txt(s,'Fixed-horizon recorded spending forecasts.\n\nRanked audience coverage under an assumed uniform contact cost.\n\nReproducible models, predictions, notebooks, and dashboard exports.',64,314,540,270,28);
txt(s,'What additional data must resolve',670,255,545,45,31,C.teal,true);
txt(s,'Consent and survival bias, shared accounts, incomplete tenure, and future-time drift.\n\nCampaign uplift and profit require randomized treatment outcomes, costs, and margins.',670,314,535,270,28);
note(s,'Technical walkthrough: README, work log, interview guide, split audit, model card, and measured results. Local release only.');

await fs.mkdir(path.join(ROOT,'tmp/deck/previews'),{recursive:true});
await fs.mkdir(path.join(ROOT,'reports'),{recursive:true});
const candidate=path.join(ROOT,'tmp/deck/candidate.pptx');
await (await PresentationFile.exportPptx(pres)).save(candidate);
for(const [i,s] of pres.slides.items.entries()){
 console.log('Render slide',i+1);
 const png=await pres.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(ROOT,`tmp/deck/previews/slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(ROOT,'reports',process.env.AMAZON_CLV_DECK_FILENAME ?? 'amazon_customer_value_presentation.pptx'),pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...[2,4,5,7,11].flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:12,requiredNativeTableOwnerSlides:[2,4,5,7,11],requiredNativeChartOwnerSlides:[3,6,8,9,10],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:path.join(ROOT,'tmp/deck/validation.json')});
console.log(JSON.stringify(result));
