import base64
from app.services.drift_detector import DataDriftDetector

def test_drift_detector_initialization():
    """Verify that DataDriftDetector initializes with a 5000-row baseline."""
    detector = DataDriftDetector(window_size=50)
    assert len(detector.baseline_df) >= 5000
    assert "TransactionAmt" in detector.baseline_df.columns
    assert "velocity_1h" in detector.baseline_df.columns

def test_check_drift_evaluation():
    """Verify check_drift evaluates metrics and returns dict of features drift scores."""
    detector = DataDriftDetector(window_size=20)
    
    # Send less than 10 transactions: shouldn't compute drift yet
    for _ in range(5):
        res = detector.check_drift({"amount": 100.0, "velocity_1h": 1, "card1": 1004})
    assert res["dataset_drift"] is False
    
    # Send enough transactions to fill minimum window (10)
    for _ in range(10):
        res = detector.check_drift({
            "amount": 250.0,
            "card1": 1004,
            "addr1": 150.0,
            "P_emaildomain": "gmail.com",
            "R_emaildomain": "gmail.com",
            "DeviceType": "desktop",
            "velocity_1h": 2,
            "velocity_6h": 4,
            "velocity_24h": 6
        })
    
    assert "dataset_drift" in res
    assert "TransactionAmt_drift" in res
    assert "velocity_1h_drift" in res

def test_drift_report_html():
    """Verify get_drift_report_html_base64 returns a base64 encoded string."""
    detector = DataDriftDetector(window_size=15)
    
    for i in range(12):
        detector.check_drift({"amount": 10.0 * i, "velocity_1h": i})
        
    b64_report = detector.get_drift_report_html_base64()
    assert isinstance(b64_report, str)
    if len(b64_report) > 0:
        decoded = base64.b64decode(b64_report)
        assert len(decoded) > 0
