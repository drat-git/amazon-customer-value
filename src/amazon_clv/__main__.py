"""CLI entrypoint. Both commands call the same make_snapshot and bundle.predict."""
import argparse
from pathlib import Path
import joblib
import pandas as pd
from threadpoolctl import threadpool_limits
from .data import load_transactions, OBSERVATION_END
from .features import make_snapshot
from .pipeline import run,predict_export

def main():
    parser=argparse.ArgumentParser(description="Historical Amazon customer spending forecasts")
    sub=parser.add_subparsers(dest="command",required=True)
    r=sub.add_parser("run",help="Audit, train, evaluate both horizons, sensitivity, charts")
    r.add_argument("--data",required=True)
    r.add_argument("--output",required=True)
    r.add_argument("--allow-unverified",action="store_true",help="Explicitly allow a non-original input, e.g. test fixture")
    r.add_argument("--bootstrap",type=int,default=500)
    r.add_argument("--skip-sensitivity",action="store_true",help="For smoke tests only; full release requires sensitivity")
    s=sub.add_parser("score",help="Score a historical date using a frozen bundle")
    for name in ["data","as-of","bundle","output"]:
        s.add_argument("--"+name,required=True)
    s.add_argument("--allow-unverified",action="store_true")
    a=parser.parse_args()
    if a.command=="run":
        if a.bootstrap<1:
            parser.error("--bootstrap must be positive")
        run(a.data,a.output,not a.allow_unverified,a.bootstrap,not a.skip_sensitivity)
    else:
        d=pd.Timestamp(a.as_of)
        if pd.isna(d) or d.tzinfo is not None or d!=d.normalize() or not pd.Timestamp("2019-01-01") <= d <= OBSERVATION_END:
            parser.error("--as-of must be a date from 2019-01-01 through 2022-11-01 for this historical dataset")
        bundle=joblib.load(Path(a.bundle)/"models.joblib")
        tx,_=load_transactions(a.data,verify_source=not a.allow_unverified)
        snapshot=make_snapshot(tx,d,bundle.categories,observation_end=bundle.observation_end)
        with threadpool_limits(limits=4):
            output=predict_export(bundle,snapshot)
        Path(a.output).parent.mkdir(parents=True,exist_ok=True)
        output.to_csv(a.output,index=False,float_format="%.10f")
        print(f"Exported {len(output):,} customer-horizon rows to {a.output}")

if __name__=="__main__":
    main()
