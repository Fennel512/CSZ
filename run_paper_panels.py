"""Portable replot of selected stored manuscript values, not full model retraining.

Run: python run_paper_panels.py
All inputs are package-relative; outputs are written to outputs/paper_replot.
"""
from pathlib import Path
import os,json,hashlib,importlib.metadata
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
DATA=ROOT/'paper_data';OUT=ROOT/'outputs/paper_replot';OUT.mkdir(parents=True,exist_ok=True)
for item in json.loads((DATA/'provenance.json').read_text(encoding='utf-8')):
    assert hashlib.sha256((ROOT/item['file']).read_bytes()).hexdigest()==item['sha256'],item['file']
def save(fig,name):
    fig.tight_layout();fig.savefig(OUT/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(fig)
report={'scope':'Replot of stored values; no full-image extraction, model refit or new inferential tests.','input_hashes':'pass','warnings':[]}

df=pd.read_csv(DATA/'fig1_three_methods.csv')
methods=['enhanced_csz','fsw_bvd','fsw_iwbvd']; labels=['CSZ base','CSZ+BVD','CSZ+iwBVD']
fig,axes=plt.subplots(1,2,figsize=(9,4))
for ax,col,title in zip(axes,['f1','total_runtime_s'],['Fig1f: stored F1','Fig1g: historical runtime (s)']):
    vals=[df.loc[df.method==m,col].dropna().to_numpy() for m in methods]
    ax.boxplot(vals,tick_labels=labels);ax.set_title(title);ax.tick_params(axis='x',rotation=20)
    for i,v in enumerate(vals):ax.scatter(np.linspace(i+0.86,i+1.14,len(v)),v,s=9,alpha=.5)
save(fig,'Fig1fg_stored_results')
df.groupby('method')[['f1','total_runtime_s']].agg(['count','mean','median']).to_csv(OUT/'Fig1fg_summary.csv')

df=pd.read_csv(DATA/'fig3_performance.csv')
order=['A_CSZ_base','B_A_plus_Fourier','C_B_plus_Haar_SWT','D_C_plus_BVD','E_FSW_core']
d=df.set_index('view').loc[order]
gain=float((d.macro_f1.iloc[-1]-d.macro_f1.iloc[0])*100)
assert abs(gain-4.46726479019001)<1e-8
fig,ax=plt.subplots(figsize=(7,4))
y=d.macro_f1.to_numpy();ax.errorbar(range(5),y,yerr=[y-d.macro_f1_ci_low,d.macro_f1_ci_high-y],fmt='o-',capsize=3)
ax.set_xticks(range(5),['CSZ base','+ Fourier','+ Haar-SWT','+ BVD','FSW core'],rotation=20)
ax.set_ylabel('Macro F1');ax.set_title(f'Fig3c: stored ablation; net +{gain:.2f} percentage points')
save(fig,'Fig3c_ablation');d.to_csv(OUT/'Fig3c_values.csv');report['fig3c_gain_percentage_points']=gain

df=pd.read_csv(DATA/'fig4_stage_states.csv')
fig,axes=plt.subplots(2,1,figsize=(8,6))
for ax,(group,d) in zip(axes,df.groupby('dataset',sort=True)):
    d=d.sort_values('stage_order_numeric')
    ax.plot(d.stage_short,d.trajectory_progress,'o-',label='Trajectory progress')
    ax.plot(d.stage_short,d.compactness_score,'s--',label='Compactness')
    ax.set_title('Fig4f: '+group+' stored states');ax.set_ylim(-.06,1.1);ax.legend(fontsize=8)
save(fig,'Fig4f_stage_states')

df=pd.read_csv(DATA/'fig5_region_medians.csv')
metrics=list(df.metric.unique());fig,axes=plt.subplots(3,3,figsize=(11,9))
for ax,metric in zip(axes.flat,metrics):
    sub=df[df.metric==metric]
    for region,d in sub.groupby('region_label'):
        d=d.sort_values('x_compact');ax.plot(d.x_compact,d.median_value,'o-',label=region)
    ticks=sub[['group','x_compact']].drop_duplicates().sort_values('x_compact')
    ax.set_title(str(sub.label.iloc[0]).replace('\n',' '),fontsize=9);ax.set_xticks(ticks.x_compact,ticks.group,rotation=12);ax.tick_params(labelsize=8)
for ax in list(axes.flat)[len(metrics):]:ax.axis('off')
axes.flat[0].legend(fontsize=7);fig.suptitle('Fig5b: stored regional medians (original table units)')
save(fig,'Fig5b_regional_medians')

df=pd.read_csv(DATA/'supp7_stored_metrics.tsv',sep='\t')
problems=[]
for _,r in df.iterrows():
    issue=[]
    if r.tp>r.pred_count:issue.append('TP exceeds pred_count')
    if r.tp+r.fp!=r.pred_count:issue.append('TP+FP differs from pred_count')
    den=r.tp+r.fp
    if den and abs(r.tp/den-r.precision)>1e-6:issue.append('precision differs from TP/(TP+FP)')
    if issue:problems.append({'relative_id':r.relative_id,'issues':issue})
assert len(problems)==5
report['supp7_count_consistency_failures']=problems
report['warnings'].append('Supp7 stored F1 can be replotted, but five non-control rows have inconsistent counts/precision; not validated detection performance.')
fig,ax=plt.subplots(figsize=(7,4));ax.bar(range(6),df.f1,color=['gray']+['#d8862e']*3+['#3988b2']*2)
ax.set_xticks(range(6),['T0','T3','T6','T12','T12+R12','T12+R24']);ax.set_ylim(0,1.18)
for i,v in enumerate(df.f1):ax.text(i,v+.015,f'{v:.3f}',ha='center')
ax.set_ylabel('Stored F1');ax.set_title('Supp7b: stored values ONLY; count consistency unresolved',fontsize=10)
save(fig,'Supp7b_stored_values_UNVERIFIED')
report['packages']={p:importlib.metadata.version(p) for p in ['numpy','pandas','matplotlib']}
(OUT/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
