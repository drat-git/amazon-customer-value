"""Integration checks run when the real-data release outputs are available."""
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize("run_name", ["runs/main", "demo"])
def test_all_views_and_budget_controls(monkeypatch, run_name):
    run = ROOT/run_name
    if not (run/"manifest.json").exists():
        pytest.skip("Dashboard bundle not present")
    monkeypatch.setenv("AMAZON_CLV_RUN", str(run))
    app=AppTest.from_file(str(ROOT/"dashboard.py"),default_timeout=60).run()
    assert len(app.exception)==0
    assert app.selectbox[0].value=="2022-01-01"
    assert app.selectbox[1].value==90
    for view in ["Model performance","Customer explorer","Methodology","Marketing prioritization"]:
        app.radio[0].set_value(view).run()
        assert len(app.exception)==0,view
        assert any("Historical demonstration" in a.value for a in app.info)
    displayed=app.dataframe[-1].value
    assert len(displayed)==1000
    app.number_input[0].set_value(0).run()
    assert len(app.exception)==0
    assert len(app.dataframe[-1].value)==0
    app.number_input[0].set_value(1000000).run()
    assert len(app.exception)==0
    assert len(app.dataframe[-1].value)==4991
    app.selectbox[0].set_value("2022-05-01").run()
    app.selectbox[1].set_value(180).run()
    assert len(app.exception)==0
    assert len(app.dataframe[-1].value)==5004


def test_public_bundle_contract():
    pred = pd.read_parquet(ROOT/"demo/customer_predictions.parquet")
    daily = pd.read_parquet(ROOT/"demo/daily_history.parquet")
    assert set(daily.columns) == {"customer_id", "date", "quantity", "value_cents"}
    assert pred.customer_id.str.fullmatch(r"Account-\d{5}").all()
    assert daily.customer_id.str.fullmatch(r"Account-\d{5}").all()
    assert not daily.duplicated(["customer_id", "date"]).any()
    assert set(pred.customer_id) <= set(daily.customer_id)
    assert len(pred) == 19990
    assert daily.value_cents.sum() == 4125895383


def test_public_predictions_preserve_local_values_and_ranking():
    from amazon_clv.marketing import select_audience
    source = ROOT/"runs/main/customer_predictions.parquet"
    if not source.exists():
        pytest.skip("Local analytical run not present")
    original = pd.read_parquet(source)
    public = pd.read_parquet(ROOT/"demo/customer_predictions.parquet")
    pd.testing.assert_frame_equal(original.drop(columns="customer_id"), public.drop(columns="customer_id"))
    aliases = dict(zip(original.customer_id, public.customer_id))
    for (date, horizon), frame in original.groupby(["scoring_date", "horizon"]):
        demo = public.loc[public.scoring_date.eq(date) & public.horizon.eq(horizon)]
        for strategy in ["Predicted spending", "Historical spending", "Recency", "Seeded random"]:
            expected = select_audience(frame, strategy=strategy).customer_id.map(aliases).tolist()
            assert expected == select_audience(demo, strategy=strategy).customer_id.tolist()
