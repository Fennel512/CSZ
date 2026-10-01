"""Portable entry points. Inputs are read-only; outputs stay in this package."""
from pathlib import Path
import argparse, hashlib, importlib.metadata, json, os, platform, sys, time
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/.mplconfig'))
sys.path.insert(0,str(ROOT/'src'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tifffile
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import csz_core

def save_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

def match(gt,pred,radius=8.0):
    """Maximize valid one-to-one matches, then minimize distance within radius.

    A penalty larger than all possible valid distances combined prevents an
    invalid match from displacing a feasible match. No test-time tuning.
    """
    n,m=len(gt),len(pred)
    distances=np.empty(0)
    if n and m:
        d=cdist(gt[['x','y']],pred[['x','y']])
        cost=np.where(d<=radius,d,(min(n,m)+1)*(radius+1))
        a,b=linear_sum_assignment(cost); distances=d[a,b][d[a,b]<=radius]
    tp=len(distances); fp=m-tp; fn=n-tp
    precision=tp/m if m else float(n==0)
    recall=tp/n if n else 1.0
    return dict(n_gt=n,n_pred=m,tp=tp,fp=fp,fn=fn,precision=precision,recall=recall,
                f1=2*precision*recall/(precision+recall) if precision+recall else 0.0,
                localization_rmse_px=float(np.sqrt(np.mean(distances**2))) if tp else None)

def overlay(image,pred,gt,path,title):
    fig,ax=plt.subplots(figsize=(7,7))
    ax.imshow(image,cmap='gray',vmin=np.percentile(image,1),vmax=np.percentile(image,99.8))
    if len(gt): ax.scatter(gt.x,gt.y,s=40,facecolors='none',edgecolors='#00ffff',linewidths=.7,label='Ground truth')
    if len(pred): ax.scatter(pred.x,pred.y,s=14,c='#ff5577',marker='+',linewidths=.6,label='Detected')
    ax.set_title(title); ax.set_xlabel('x (px)'); ax.set_ylabel('y (px)')
    if len(gt) or len(pred): ax.legend(loc='upper right',fontsize=8)
    fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)

def synthetic(out):
    rows=[]
    for r in pd.read_csv(ROOT/'data/synthetic/cases.csv').to_dict('records'):
        image=tifffile.imread(ROOT/r['image'])
        assert image.ndim==2 and np.isfinite(image).all()
        gt=pd.read_csv(ROOT/r['truth']).rename(columns={'x_true':'x','y_true':'y'})
        t=time.perf_counter(); pred,maps=csz_core.detect(image)
        feat=csz_core.extract_object_features(image,pred,maps)
        folder=out/r['case_id']; folder.mkdir(parents=True,exist_ok=True)
        pred.to_csv(folder/'predictions.csv',index=False)
        feat.to_csv(folder/'object_features.csv',index=False)
        overlay(image,pred,gt,folder/'overlay.png',r['scene']+' | CSZ-v1 default')
        rows.append(dict(case_id=r['case_id'],scene=r['scene'],**match(gt,pred),runtime_s=time.perf_counter()-t))
    pd.DataFrame(rows).to_csv(out/'metrics.csv',index=False)
    save_json(out/'parameters.json',dict(method='CSZ-v1',parameters=csz_core.parameter_payload(),match_radius_px=8,selection='case 0001 per scene; not a held-out benchmark'))

def analyze(path,out):
    from PIL import Image
    path=Path(path).expanduser().resolve()
    a=tifffile.imread(path) if path.suffix.lower() in {'.tif','.tiff'} else np.asarray(Image.open(path))
    if a.ndim!=2 or not np.isfinite(a).all():
        raise ValueError('Expected a finite, 2D single-channel image; explicitly select/project the intended channel before running.')
    pred,maps=csz_core.detect(a)
    features=csz_core.extract_object_features(a,pred,maps)
    pred.to_csv(out/'predictions.csv',index=False)
    features.to_csv(out/'object_features.csv',index=False)
    overlay(a,pred,pd.DataFrame(),out/'overlay.png',path.name+' | CSZ-v1')
    save_json(out/'parameters.json',dict(input_name=path.name,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),shape=list(a.shape),parameters=csz_core.parameter_payload(),n_predictions=len(pred)))

def fsw(out):
    import fsw_bvd_exact_core as core
    from dataclasses import asdict
    r=pd.read_csv(ROOT/'data/synthetic/cases.csv').query("scene == 'HS_REG_ISO'").iloc[0]
    full=tifffile.imread(ROOT/r.image); image=full[:256,:256]
    gt=pd.read_csv(ROOT/r.truth).rename(columns={'x_true':'x','y_true':'y'})
    gt=gt[(gt.x>=0)&(gt.x<256)&(gt.y>=0)&(gt.y<256)]
    tifffile.imwrite(out/'crop_256.tif',image)
    gt.to_csv(out/'crop_truth.csv',index=False)
    # Invoke only inference components. Never run the legacy GT threshold sweep.
    normalized=core.robust_normalize(image)
    fourier=core.fourier_screen(normalized)
    seeds=core.generate_seeds(normalized,fourier)
    pre=core.precheck_seeds(normalized,seeds,'swt_mean')
    scored,info=core.score_fsw(normalized,pre,'swt_mean')
    pred=core.select_predictions(scored,core.NPAR.default_quantile,core.NPAR.nms_radius)
    pred.to_csv(out/'predictions.csv',index=False)
    scored.to_csv(out/'scored_candidates.csv',index=False)
    save_json(out/'metrics.json',match(gt,pred))
    save_json(out/'parameters.json',dict(method='FSW-BVD (mean-SWT)',crop_xywh=[0,0,256,256],fourier=asdict(core.FP),fsw=asdict(core.NPAR),match_radius_px=8,threshold_tuning=False))
    overlay(image,pred,gt,out/'overlay.png','FSW-BVD | 256 px crop | fixed defaults')

def real(out):
    import csz_features as core
    images=[]; objects=[]
    for record in pd.read_csv(ROOT/'data/real/manifest.csv').to_dict('records'):
        original=record.copy()
        for key in ['dna_channel_path','gfp_channel_path']: record[key]=str(ROOT/record[key])
        feat,puncta=core.process_record(record)
        for k in ['meta__dna_path','meta__gfp_path']: feat.pop(k,None)
        images.append(feat); objects.extend(puncta)
        image=tifffile.imread(record['gfp_channel_path'])
        p=pd.DataFrame(puncta)
        # The feature extractor's centroid columns use x/y pixels.
        if len(p):
            coords=p.rename(columns={'centroid_x':'x','centroid_y':'y'})
        else: coords=pd.DataFrame(columns=['x','y'])
        overlay(image,coords,pd.DataFrame(),out/(original['gene']+'_overlay.png'),original['gene']+' | exploratory CSZ features')
    pd.DataFrame(images).to_csv(out/'image_features.csv',index=False)
    pd.DataFrame(objects).to_csv(out/'puncta_features.csv',index=False)
    save_json(out/'parameters.json',core.CSZConfig().to_dict())

def augment(out):
    """Image augmentation with coordinate-preserving photometric transforms."""
    from scipy.ndimage import gaussian_filter
    r=pd.read_csv(ROOT/'data/synthetic/cases.csv').query("scene == 'HS_REG_ISO'").iloc[0]
    image=tifffile.imread(ROOT/r.image).astype(np.float32)
    gt=pd.read_csv(ROOT/r.truth).rename(columns={'x_true':'x','y_true':'y'})
    rng=np.random.default_rng(20260920)
    noise_sigma=.03*float(np.percentile(image,99.8)-np.percentile(image,1))
    variants={'original':image,'gain_0p5':image*.5,'blur_sigma_1':gaussian_filter(image,1),
              'noise_3pct':image+rng.normal(0,noise_sigma,image.shape).astype(np.float32),
              'horizontal_flip':np.fliplr(image)}
    rows=[]
    fig,axes=plt.subplots(1,5,figsize=(16,3.5))
    for ax,(name,a) in zip(axes,variants.items()):
        truth=gt.copy()
        if name=='horizontal_flip': truth['x']=image.shape[1]-1-truth.x
        tifffile.imwrite(out/(name+'.tif'),a)
        truth.to_csv(out/(name+'_truth.csv'),index=False)
        pred,_=csz_core.detect(a)
        pred.to_csv(out/(name+'_predictions.csv'),index=False)
        rows.append(dict(variant=name,**match(truth,pred)))
        ax.imshow(a,cmap='gray',vmin=np.percentile(a,1),vmax=np.percentile(a,99.8)); ax.set_title(name); ax.axis('off')
    fig.tight_layout(); fig.savefig(out/'augmentation.png',dpi=140); plt.close(fig)
    pd.DataFrame(rows).to_csv(out/'metrics.csv',index=False)
    save_json(out/'parameters.json',dict(seed=20260920,noise_sigma=noise_sigma,blur_sigma_px=1,gain=.5,flip='x_new = width - 1 - x_old',scope='augmentation demo, no biological replication claim'))

def function(out):
    from sklearn.ensemble import ExtraTreesClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.metrics import balanced_accuracy_score,f1_score,confusion_matrix
    data=pd.read_csv(ROOT/'data/function/image_features.csv')
    assert not data['meta__image_id'].duplicated().any()
    assert data.groupby('meta__gene')['meta__category'].nunique().max()==1
    y=data.meta__category.astype(str); groups=data.meta__gene.astype(str)
    classes=sorted(y.unique()); split=list(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=20260630).split(data,y,groups))
    families={'baseline':['base__'],'csz':['csz__'],'csz_composition':['csz__','comp__'],'all':['base__','csz__','comp__']}
    fold_rows=[]; metrics=[]
    for fold,(train,test) in enumerate(split):
        assert not set(groups.iloc[train]) & set(groups.iloc[test])
        assert set(y.iloc[train])==set(classes)
        fold_rows.extend(dict(image_id=data.iloc[i].meta__image_id,gene=groups.iloc[i],fold=fold,category=y.iloc[i]) for i in test)
    pd.DataFrame(fold_rows).to_csv(out/'fold_assignments.csv',index=False)
    for name,prefixes in families.items():
        columns=[c for c in data if any(c.startswith(p) for p in prefixes)]
        X=data[columns].apply(pd.to_numeric,errors='raise').replace([np.inf,-np.inf],np.nan)
        probs=np.zeros((len(data),len(classes)))
        for fold,(train,test) in enumerate(split):
            model=make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),ExtraTreesClassifier(n_estimators=100,random_state=20260630+fold,class_weight='balanced',n_jobs=1))
            model.fit(X.iloc[train],y.iloc[train])
            probs[test]=model.predict_proba(X.iloc[test])[:,[list(model.classes_).index(c) for c in classes]]
        oof=pd.DataFrame(probs,columns=classes)
        oof.insert(0,'gene',groups); oof.insert(1,'truth',y)
        gene=oof.groupby(['gene','truth'],as_index=False)[classes].mean()
        gene['prediction']=gene[classes].idxmax(axis=1)
        gene.to_csv(out/(name+'_gene_oof.csv'),index=False)
        metrics.append(dict(feature_set=name,n_features=len(columns),n_genes=len(gene),balanced_accuracy=balanced_accuracy_score(gene.truth,gene.prediction),macro_f1=f1_score(gene.truth,gene.prediction,average='macro')))
        cm=confusion_matrix(gene.truth,gene.prediction,labels=classes)
        pd.DataFrame(cm,index=classes,columns=classes).to_csv(out/(name+'_confusion.csv'))
    result=pd.DataFrame(metrics); result.to_csv(out/'metrics.csv',index=False)
    ax=result.set_index('feature_set')[['balanced_accuracy','macro_f1']].plot.bar(figsize=(8,4),ylim=(0,1),rot=0)
    ax.set_ylabel('Gene-level grouped OOF score'); ax.figure.tight_layout(); ax.figure.savefig(out/'comparison.png',dpi=160); plt.close(ax.figure)
    save_json(out/'parameters.json',dict(seed=20260630,folds=5,trees=100,n_jobs=1,group='gene',aggregation='mean OOF probability per gene',feature_selection='none; all four predeclared sets reported',scope='table-level reproduction; no new extraction of all 313 images'))

def verify(out):
    rows=[]
    for r in pd.read_csv(ROOT/'catalog/source_manifest.csv').to_dict('records'):
        if r['operation']!='byte-identical copy': continue
        p=ROOT/r['destination']; actual=hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual==r['sha256'],r['destination']
        rows.append(dict(file=r['destination'],status='SHA256 pass'))
    # An adversarial assignment where post-filtering a min-distance assignment
    # can lose a valid match. This check protects the new matching definition.
    gt=pd.DataFrame({'x':[0.,1.],'y':[0.,0.]})
    pred=pd.DataFrame({'x':[0.,-.805],'y':[0.,float(np.sqrt(1-.805**2))]})
    assert match(gt,pred,1.01)['tp']==2
    assert match(pd.DataFrame(),pd.DataFrame())['f1']==1
    pred,_=csz_core.detect(np.zeros((64,64),np.float32))
    assert len(pred)==0
    for r in pd.read_csv(ROOT/'data/synthetic/cases.csv').to_dict('records'):
        a=tifffile.imread(ROOT/r['image']); gt=pd.read_csv(ROOT/r['truth'])
        assert a.ndim==2 and np.isfinite(a).all()
        assert gt.x_true.between(0,a.shape[1]-1).all() and gt.y_true.between(0,a.shape[0]-1).all()
    pd.DataFrame(rows).to_csv(out/'copy_integrity.csv',index=False)
    save_json(out/'checks.json',dict(status='pass',identical_copies=len(rows),checks=['SHA256 source copies','blank image gives no detections','maximum-cardinality point matching','empty point matching','nine image/GT dimensions and coordinates']))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['verify','synthetic','analyze','fsw','real','augment','function','all'])
    p.add_argument('--image',help='For analyze: a 2D grayscale TIFF or PNG; read-only')
    p.add_argument('--output',default='outputs/run',help='Directory inside this Examples package')
    args=p.parse_args(); dest=(ROOT/args.output).resolve()
    if not dest.is_relative_to(ROOT/'outputs'): p.error('--output must be below the package outputs directory')
    dest.mkdir(parents=True,exist_ok=True)
    save_json(dest/'environment.json',dict(python=sys.version,platform=platform.platform(),packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-image','scikit-learn','tifffile','matplotlib','PyWavelets','Pillow']}))
    stages=['verify','synthetic','fsw','real','augment','function'] if args.stage=='all' else [args.stage]
    for stage in stages:
        out=dest/stage; out.mkdir(exist_ok=True)
        t=time.perf_counter(); print('Running',stage,flush=True)
        if stage=='analyze':
            if not args.image: p.error('analyze requires --image')
            analyze(args.image,out)
        else: globals()[stage](out)
        print('PASS',stage,round(time.perf_counter()-t,2),'seconds',flush=True)

if __name__=='__main__': main()
