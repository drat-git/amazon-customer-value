import pandas as pd
import pytest

@pytest.fixture
def transactions():
    rows=[("a","2018-01-01",10000,"BOOK"),("a","2019-01-01",2000,"NEW"),("a","2019-03-31",3000,"UNKNOWN"),("b","2018-12-31",5000,"UNKNOWN"),("c","2019-02-01",9000,"BOOK")]
    return pd.DataFrame([{"customer_id":c,"date":pd.Timestamp(d),"value_cents":v,"quantity":1,"category":cat,"product_id":"P","title":"Item","is_gift":False} for c,d,v,cat in rows])
