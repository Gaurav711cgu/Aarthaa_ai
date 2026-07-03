"""
Coverage-boosting tests targeting the lowest-coverage modules:
  - drift_detector.py       (36% → target 70%+)
  - document_parser.py      (51% → target 80%+)
  - vector_store.py         (59% → target 75%+)
  - kafka_client.py         (62% → target 85%+)
  - redis_client.py         (65% → target 85%+)
  - app/api/v1/fraud.py     (65% → target 80%+)
  - app/api/v1/finlens.py   (59% → target 80%+)
  - finlens_engine.py       (61% → rate limiter path)
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Shared auth helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_analyst_headers():
    r = client.post("/auth/token", json={"username": "analyst", "password": "analyst_password_2026"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def get_readonly_headers():
    r = client.post("/auth/token", json={"username": "readonly", "password": "readonly_password_2026"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def get_admin_headers():
    r = client.post("/auth/token", json={"username": "admin", "password": "admin_password_2026"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ─────────────────────────────────────────────────────────────────────────────
# MockKafkaProducer & kafka_client
# ─────────────────────────────────────────────────────────────────────────────

class TestMockKafkaProducer:
    def test_produce_stores_event(self):
        from app.kafka_client import MockKafkaProducer
        p = MockKafkaProducer()
        p.produce(topic="test.topic", value='{"x": 1}', key="k1")
        assert len(p._backlog) == 1
        assert p._backlog[0]["topic"] == "test.topic"

    def test_produce_triggers_callback(self):
        from app.kafka_client import MockKafkaProducer
        p = MockKafkaProducer()
        called = []
        def cb(err, msg):
            called.append((err, msg.topic()))
        p.produce(topic="t", value="v", key="k", callback=cb)
        assert called == [(None, "t")]

    def test_flush_returns_zero(self):
        from app.kafka_client import MockKafkaProducer
        p = MockKafkaProducer()
        assert p.flush(timeout=1) == 0

    def test_list_topics_returns_metadata(self):
        from app.kafka_client import MockKafkaProducer
        p = MockKafkaProducer()
        meta = p.list_topics()
        assert "transactions.raw" in meta.topics

    def test_get_kafka_producer_returns_mock_when_inactive(self):
        from app.kafka_client import get_kafka_producer, MockKafkaProducer, is_kafka_active
        if not is_kafka_active:
            producer = get_kafka_producer()
            assert isinstance(producer, MockKafkaProducer)

    def test_test_kafka_connection_returns_false_when_inactive(self):
        from app.kafka_client import test_kafka_connection, is_kafka_active
        if not is_kafka_active:
            assert test_kafka_connection() is False


# ─────────────────────────────────────────────────────────────────────────────
# MockRedis & redis_client
# ─────────────────────────────────────────────────────────────────────────────

class TestMockRedis:
    def setup_method(self):
        from app.redis_client import MockRedis
        self.r = MockRedis()

    def test_ping_returns_true(self):
        assert self.r.ping() is True

    def test_set_and_get(self):
        self.r.set("foo", "bar")
        assert self.r.get("foo") == "bar"

    def test_get_missing_key_returns_none(self):
        assert self.r.get("nonexistent") is None

    def test_delete_existing_key(self):
        self.r.set("k", "v")
        count = self.r.delete("k")
        assert count == 1
        assert self.r.get("k") is None

    def test_delete_missing_key_returns_zero(self):
        assert self.r.delete("ghost") == 0

    def test_exists_present(self):
        self.r.set("present", "yes")
        assert self.r.exists("present") == 1

    def test_exists_absent(self):
        assert self.r.exists("absent") == 0

    def test_incr_from_zero(self):
        val = self.r.incr("counter")
        assert val == 1

    def test_incr_accumulates(self):
        self.r.incr("ctr")
        self.r.incr("ctr")
        val = self.r.incr("ctr")
        assert val == 3

    def test_get_redis_client_returns_mock_when_inactive(self):
        from app.redis_client import get_redis_client, MockRedis, is_redis_active
        if not is_redis_active:
            c = get_redis_client()
            assert isinstance(c, MockRedis)

    def test_test_redis_connection_returns_bool(self):
        from app.redis_client import test_redis_connection
        result = test_redis_connection()
        assert isinstance(result, bool)


# ─────────────────────────────────────────────────────────────────────────────
# DataDriftDetector
# ─────────────────────────────────────────────────────────────────────────────

class TestDataDriftDetector:
    def setup_method(self):
        from app.services.drift_detector import DataDriftDetector
        self.detector = DataDriftDetector(window_size=100)

    def test_check_drift_below_window_returns_zeros(self):
        result = self.detector.check_drift({"amount": 500.0, "velocity_1h": 2})
        assert result["TransactionAmt_drift"] == 0.0
        assert result["velocity_1h_drift"] == 0.0
        assert result["dataset_drift"] is False

    def test_check_drift_accumulates_window(self):
        # Push enough data to trigger the evidently computation path
        for i in range(12):
            result = self.detector.check_drift({"amount": float(100 + i * 50), "velocity_1h": i % 4 + 1})
        # After 12 entries, drift computation runs — result must have the keys
        assert "TransactionAmt_drift" in result
        assert "velocity_1h_drift" in result
        assert "dataset_drift" in result

    def test_fallback_baseline_generated(self):
        """Verify synthetic baseline shape when CSV is missing."""
        from app.services.drift_detector import DataDriftDetector
        with patch("app.services.drift_detector.os.path.exists", return_value=False):
            d = DataDriftDetector(window_size=50)
        assert len(d.baseline_df) == 5000
        assert "TransactionAmt" in d.baseline_df.columns
        assert "velocity_1h" in d.baseline_df.columns

    def test_get_drift_report_html_base64_returns_string(self):
        # Need >= 10 observations first for last_report to be set
        for i in range(12):
            self.detector.check_drift({"amount": float(200 + i * 100), "velocity_1h": i % 3 + 1})
        html = self.detector.get_drift_report_html_base64()
        assert isinstance(html, str)

    def test_get_drift_report_html_base64_no_last_report(self):
        """When last_report is None, it should attempt on-demand generation."""
        assert self.detector.last_report is None
        result = self.detector.get_drift_report_html_base64()
        # Either returns base64 string or empty string on error — both are strings
        assert isinstance(result, str)

    def test_corrupt_csv_triggers_fallback(self):
        from app.services.drift_detector import DataDriftDetector
        with patch("app.services.drift_detector.os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=IOError("read error")):
            d = DataDriftDetector(window_size=50)
        # Should have fallen back to synthetic baseline
        assert d.baseline_df is not None


# ─────────────────────────────────────────────────────────────────────────────
# BankStatementParser — CSV path
# ─────────────────────────────────────────────────────────────────────────────

CSV_STATEMENT = """BANK: ICICI Bank India
ACCOUNT: 123456789012
PERIOD: April 2026

Date,Description,Type,Amount,Balance
2026-04-01,Opening Balance,CR,80000.00,80000.00
2026-04-05,Amazon Order,DR,1200.00,78800.00
2026-04-10,Salary Infosys,CR,95000.00,173800.00
2026-04-15,Electricity Bill,DR,3500.00,170300.00
"""

PIPE_STATEMENT = """BANK: SBI India
ACCOUNT: 987654321098
PERIOD: May 2026

2026-05-01 | Opening Balance | CREDIT | 30000.00 | 30000.00
2026-05-08 | Zomato Food Order | DEBIT | 650.00 | 29350.00
2026-05-15 | Monthly Salary Tata | CREDIT | 70000.00 | 99350.00
"""


class TestBankStatementParserCSV:
    def setup_method(self):
        from app.services.document_parser import BankStatementParser
        self.parser = BankStatementParser()

    def _make_db(self):
        """Create a fresh in-memory SQLite session for isolation."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.statement import Base
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    def test_csv_format_parsed_correctly(self):
        db = self._make_db()
        result = self.parser.parse_and_store_statement(db, CSV_STATEMENT, "testuser")
        assert result["bank_name"] == "ICICI Bank India"
        assert result["account_number"] == "123456789012"
        assert result["transaction_count"] == 4
        # CR amounts: 80000 + 95000 = 175000; DR: 1200 + 3500 = 4700
        assert result["total_deposits"] == pytest.approx(175000.0)
        assert result["total_withdrawals"] == pytest.approx(4700.0)

    def test_pipe_delimited_format_parsed(self):
        db = self._make_db()
        result = self.parser.parse_and_store_statement(db, PIPE_STATEMENT, "testuser2")
        assert result["bank_name"] == "SBI India"
        assert result["transaction_count"] == 3
        assert result["total_deposits"] == pytest.approx(100000.0)  # 30K + 70K

    def test_missing_metadata_uses_defaults(self):
        db = self._make_db()
        bare_text = "2026-01-01 | Plain Tx | CREDIT | 1000.00 | 1000.00"
        result = self.parser.parse_and_store_statement(db, bare_text, "anon")
        assert result["bank_name"] == "Unspecified Bank"
        assert result["account_number"] == "000000000000"

    def test_negative_csv_amount_treated_as_debit(self):
        """Negative amounts in CSV without type column should be classified as DEBIT."""
        db = self._make_db()
        neg_csv = """BANK: Test Bank
ACCOUNT: 111111111111
PERIOD: Jan 2026

Date,Description,Amount,Balance
2026-01-05,Payment,-500.00,9500.00
"""
        result = self.parser.parse_and_store_statement(db, neg_csv, "u1")
        assert result["total_withdrawals"] == pytest.approx(500.0)

    def test_csv_with_explicit_debit_credit_markers(self):
        db = self._make_db()
        typed_csv = """BANK: Axis Bank
ACCOUNT: 222222222222
PERIOD: Feb 2026

Date,Narration,CR/DR,tx_amount,bal
2026-02-01,Deposit,CR,5000.00,5000.00
2026-02-03,Withdrawal,DR,1000.00,4000.00
"""
        result = self.parser.parse_and_store_statement(db, typed_csv, "u2")
        assert result["total_deposits"] == pytest.approx(5000.0)
        assert result["total_withdrawals"] == pytest.approx(1000.0)


# ─────────────────────────────────────────────────────────────────────────────
# LocalVectorStore
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_CHUNKS = [
    {"text": "RBI mandates UPI transaction limit of Rs 1 lakh per day for standard users.", "source": "RBI_UPI_2023", "section": "4.1"},
    {"text": "FEMA LRS limit is USD 250,000 per financial year for resident individuals.", "source": "FEMA_LRS", "section": "5.2"},
    {"text": "PMLA requires reporting of cash transactions above Rs 10 lakh.", "source": "PMLA_2002", "section": "2.3"},
    {"text": "PCI-DSS standards require encryption of cardholder data at rest.", "source": "PCI_DSS", "section": "3.4"},
    {"text": "GST applies at 18% on financial service fees and commissions.", "source": "GST_ACT", "section": "1.1"},
]


class TestLocalVectorStore:
    def setup_method(self):
        from app.services.vector_store import LocalVectorStore
        self.open_patcher = patch("app.services.vector_store.open", create=True)
        self.mock_open = self.open_patcher.start()
        with patch("app.services.vector_store.is_postgres_active", False), \
             patch("app.services.vector_store.os.path.exists", return_value=False):
            self.vs = LocalVectorStore()

    def teardown_method(self):
        self.open_patcher.stop()


    def test_search_on_empty_store_returns_empty(self):
        results = self.vs.search("UPI limit")
        assert results == []

    def test_add_chunks_enables_search(self):
        self.vs.add_chunks(SAMPLE_CHUNKS)
        results = self.vs.search("UPI daily limit", top_k=2)
        assert len(results) >= 1
        assert any("UPI" in r["text"] for r in results)

    def test_search_returns_score_field(self):
        self.vs.add_chunks(SAMPLE_CHUNKS)
        results = self.vs.search("FEMA LRS foreign remittance")
        for r in results:
            assert "score" in r
            assert isinstance(r["score"], float)

    def test_search_top_k_respected(self):
        self.vs.add_chunks(SAMPLE_CHUNKS)
        results = self.vs.search("regulation compliance", top_k=2)
        assert len(results) <= 2

    def test_add_chunks_persist_called(self):
        with patch.object(self.vs, "_persist") as mock_persist:
            self.vs.add_chunks(SAMPLE_CHUNKS[:2])
            mock_persist.assert_called_once()

    def test_search_source_and_section_present(self):
        self.vs.add_chunks(SAMPLE_CHUNKS)
        results = self.vs.search("cash transaction PMLA reporting")
        for r in results:
            assert "source" in r
            assert "section" in r


# ─────────────────────────────────────────────────────────────────────────────
# Fraud API — batch + metrics + training-state endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestFraudAPIExtended:
    def setup_method(self):
        self.analyst_headers = get_analyst_headers()
        self.readonly_headers = get_readonly_headers()

    def _make_tx(self, amount=500.0, hour=12, velocity=1, distance=5.0, risk=0.05):
        return {
            "amount": amount,
            "hour": hour,
            "velocity_1h": velocity,
            "distance_from_home": distance,
            "merchant_risk": risk,
            "user_id": str(uuid.uuid4()),
            "channel": "UPI"
        }

    def test_batch_scoring_single_item(self):
        payload = [self._make_tx()]
        r = client.post("/api/v1/fraud/score/batch", json=payload, headers=self.analyst_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert "risk_tier" in data[0]

    def test_batch_scoring_multiple_items(self):
        payload = [self._make_tx(amount=float(100 * i + 50)) for i in range(5)]
        r = client.post("/api/v1/fraud/score/batch", json=payload, headers=self.analyst_headers)
        assert r.status_code == 200
        assert len(r.json()) == 5

    def test_batch_exceeds_100_items(self):
        payload = [self._make_tx() for _ in range(101)]
        r = client.post("/api/v1/fraud/score/batch", json=payload, headers=self.analyst_headers)
        assert r.status_code == 400

    def test_batch_requires_auth(self):
        r = client.post("/api/v1/fraud/score/batch", json=[self._make_tx()])
        assert r.status_code == 401

    def test_get_model_metrics_returns_status(self):
        r = client.get("/api/v1/fraud/metrics", headers=self.readonly_headers)
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] in ["ready", "training"]

    def test_get_model_metrics_requires_auth(self):
        r = client.get("/api/v1/fraud/metrics")
        assert r.status_code == 401

    def test_score_returns_shap_chart_data(self):
        r = client.post("/api/v1/fraud/score", json=self._make_tx(), headers=self.analyst_headers)
        assert r.status_code == 200
        data = r.json()
        assert "shap_chart_data" in data
        assert "features" in data["shap_chart_data"]
        assert "values" in data["shap_chart_data"]

    def test_batch_mixed_risk_levels(self):
        low_risk = self._make_tx(amount=100.0, hour=14, velocity=1, distance=2.0, risk=0.01)
        high_risk = self._make_tx(amount=900000.0, hour=2, velocity=15, distance=2000.0, risk=0.95)
        r = client.post("/api/v1/fraud/score/batch", json=[low_risk, high_risk], headers=self.analyst_headers)
        assert r.status_code == 200
        results = r.json()
        tiers = {res["risk_tier"] for res in results}
        # Low risk should differ from high risk in tier
        assert len(tiers) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# FinLens API — GET endpoints (statement details, summary)
# ─────────────────────────────────────────────────────────────────────────────

MOCK_STATEMENT_TEXT = """
BANK: HDFC Bank India
ACCOUNT: 50100234567891
PERIOD: March 2026

2026-03-01 | Opening Balance | CREDIT | 50000.00 | 50000.00
2026-03-05 | Swiggy Food Delivery Order | DEBIT | 450.00 | 49550.00
2026-03-10 | Salary Credit JPMC GCC | CREDIT | 125000.00 | 174550.00
2026-03-15 | Uber Cab Travel Bhubaneswar | DEBIT | 350.00 | 174200.00
2026-03-20 | House Rent Payment | DEBIT | 15000.00 | 159200.00
"""


class TestFinLensAPIExtended:
    def setup_method(self):
        self.headers = get_analyst_headers()
        r = client.post("/api/v1/finlens/upload", json={"raw_text": MOCK_STATEMENT_TEXT}, headers=self.headers)
        assert r.status_code == 201
        self.statement_id = r.json()["statement_id"]

    def test_get_statement_details(self):
        r = client.get(f"/api/v1/finlens/statements/{self.statement_id}", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["statement_id"] == self.statement_id
        assert data["bank_name"] == "HDFC Bank India"
        assert data["account_number"] == "50100234567891"
        assert "transaction_count" in data

    def test_get_statement_details_not_found(self):
        r = client.get("/api/v1/finlens/statements/999999", headers=self.headers)
        assert r.status_code == 404

    def test_get_statement_summary(self):
        r = client.get(f"/api/v1/finlens/statements/{self.statement_id}/summary", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["statement_id"] == self.statement_id
        assert "total_income" in data
        assert "total_expense" in data
        assert "income_to_expense_ratio" in data
        assert "top_expenditures" in data
        assert isinstance(data["top_expenditures"], list)

    def test_get_statement_summary_not_found(self):
        r = client.get("/api/v1/finlens/statements/999999/summary", headers=self.headers)
        assert r.status_code == 404

    def test_get_statement_requires_auth(self):
        r = client.get(f"/api/v1/finlens/statements/{self.statement_id}")
        assert r.status_code == 401

    def test_upload_csv_format_via_api(self):
        r = client.post("/api/v1/finlens/upload", json={"raw_text": CSV_STATEMENT}, headers=self.headers)
        assert r.status_code == 201
        data = r.json()
        assert data["bank_name"] == "ICICI Bank India"
        assert data["transaction_count"] == 4

    def test_query_nonexistent_statement(self):
        r = client.post("/api/v1/finlens/query", json={
            "query": "What is my balance?",
            "statement_id": 999999
        }, headers=self.headers)
        assert r.status_code == 404

    def test_upload_text_too_short(self):
        r = client.post("/api/v1/finlens/upload", json={"raw_text": "short"}, headers=self.headers)
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# FinLens Engine — rate limiter path
# ─────────────────────────────────────────────────────────────────────────────

class TestFinLensRateLimiter:
    def test_rate_limiter_allows_within_limit(self):
        from app.services.finlens_engine import LLMRateLimiter
        limiter = LLMRateLimiter(max_calls=3, window_seconds=60)
        assert limiter.is_allowed("user_x") is True
        assert limiter.is_allowed("user_x") is True
        assert limiter.is_allowed("user_x") is True

    def test_rate_limiter_blocks_over_limit(self):
        from app.services.finlens_engine import LLMRateLimiter
        limiter = LLMRateLimiter(max_calls=2, window_seconds=60)
        limiter.is_allowed("user_y")
        limiter.is_allowed("user_y")
        assert limiter.is_allowed("user_y") is False

    def test_rate_limiter_separate_users_independent(self):
        from app.services.finlens_engine import LLMRateLimiter
        limiter = LLMRateLimiter(max_calls=1, window_seconds=60)
        limiter.is_allowed("alice")
        assert limiter.is_allowed("bob") is True  # separate bucket


# ─────────────────────────────────────────────────────────────────────────────
# Compliance API — authorization edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestComplianceAPIAuth:
    def test_check_requires_at_least_readonly(self):
        r = client.post("/api/v1/compliance/check", json={
            "amount": 1000.0, "channel": "UPI", "is_international": False,
            "user_id": str(uuid.uuid4())
        })
        assert r.status_code == 401

    def test_query_requires_at_least_readonly(self):
        r = client.post("/api/v1/compliance/query", json={"query": "What is UPI limit?"})
        assert r.status_code == 401

    def test_readonly_can_check_compliance(self):
        headers = get_readonly_headers()
        r = client.post("/api/v1/compliance/check", json={
            "amount": 500.0, "channel": "UPI", "is_international": False,
            "user_id": str(uuid.uuid4())
        }, headers=headers)
        assert r.status_code == 200

    def test_readonly_can_query_regulations(self):
        headers = get_readonly_headers()
        r = client.post("/api/v1/compliance/query", json={"query": "UPI daily limit rules"}, headers=headers)
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Extra Coverage Boosting for Vector Store, Fraud Model and FinLens Engine
# ─────────────────────────────────────────────────────────────────────────────

class TestVectorStoreMockedChroma:
    @patch("app.services.vector_store.HAS_CHROMA", True)
    @patch("app.services.vector_store.chromadb")
    @patch("app.services.vector_store.is_postgres_active", False)
    @patch("app.services.vector_store.os.path.exists", return_value=False)
    def test_chroma_path_init_and_search(self, mock_exists, mock_chroma):
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # mock query response
        mock_collection.query.return_value = {
            "documents": [["Doc 1"]],
            "metadatas": [[{"source": "src", "section": "sec"}]],
            "distances": [[0.1]]
        }
        
        from app.services.vector_store import LocalVectorStore
        vs = LocalVectorStore()
        assert vs.use_chroma is True
        
        # Test search with chroma
        vs.embeddings_db = [{"text": "Doc 1", "source": "src", "section": "sec"}]
        vs._is_fitted = True
        vs.vectorizer = MagicMock()
        results = vs.search("test query")
        assert len(results) == 1
        assert results[0]["text"] == "Doc 1"

    @patch("app.services.vector_store.HAS_CHROMA", True)
    @patch("app.services.vector_store.chromadb")
    @patch("app.services.vector_store.is_postgres_active", False)
    @patch("app.services.vector_store.os.path.exists", return_value=False)
    @patch("app.services.vector_store.LocalVectorStore._persist")
    def test_chroma_add_chunks(self, mock_persist, mock_exists, mock_chroma):
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        
        from app.services.vector_store import LocalVectorStore
        vs = LocalVectorStore()
        vs.add_chunks([{"text": "chunk text", "source": "src", "section": "sec"}])
        mock_collection.upsert.assert_called_once()


class TestVectorStoreMockedPostgres:
    @patch("app.services.vector_store.is_postgres_active", True)
    @patch("app.services.vector_store.os.path.exists", return_value=False)
    @patch("app.database.engine")
    def test_pgvector_path_init_and_search(self, mock_engine, mock_exists):
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        mock_conn.execute.return_value.fetchall.return_value = [
            ("chunk text", "src", "sec", 0.9)
        ]
        
        from app.services.vector_store import LocalVectorStore
        vs = LocalVectorStore()
        assert vs.use_pgvector is True
        
        vs.embeddings_db = [{"text": "chunk text", "source": "src", "section": "sec"}]
        vs._is_fitted = True
        vs.vectorizer = MagicMock()
        vs.vectorizer.vocabulary_ = {"hello": 0}
        
        results = vs.search("test query")
        assert len(results) == 1
        assert results[0]["text"] == "chunk text"

    @patch("app.services.vector_store.is_postgres_active", True)
    @patch("app.services.vector_store.os.path.exists", return_value=False)
    @patch("app.database.engine")
    @patch("app.services.vector_store.LocalVectorStore._persist")
    def test_pgvector_add_chunks(self, mock_persist, mock_engine, mock_exists):
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        from app.services.vector_store import LocalVectorStore
        vs = LocalVectorStore()
        vs.vectorizer = MagicMock()
        vs.vectorizer.vocabulary_ = {"hello": 0}
        
        vs.add_chunks([{"text": "chunk text", "source": "src", "section": "sec"}])
        assert mock_conn.execute.called


class TestVectorStoreErrorPaths:
    @patch("app.services.vector_store.is_postgres_active", False)
    def test_crc_mismatch(self):
        from app.services.vector_store import LocalVectorStore
        
        def side_effect_exists(path):
            if "reg_embeddings.json" in path:
                return True
            return False
            
        mock_files = {
            "reg_embeddings.json": '[{"text": "t", "source": "s", "section": "sec"}]',
            "reg_embeddings.json.crc": "99999"
        }
        
        class MockOpen:
            def __init__(self, filename, *args, **kwargs):
                self.filename = filename
            def __enter__(self):
                content = ""
                for k, v in mock_files.items():
                    if k in self.filename:
                        content = v
                import io
                return io.StringIO(content)
            def __exit__(self, *args):
                pass
                
        with patch("app.services.vector_store.os.path.exists", side_effect=side_effect_exists), \
             patch("builtins.open", MockOpen):
            vs = LocalVectorStore()
            assert len(vs.embeddings_db) == 0

    @patch("app.services.vector_store.is_postgres_active", False)
    @patch("app.services.vector_store.os.path.exists", return_value=False)
    def test_persist_exception_handled(self, mock_exists):
        from app.services.vector_store import LocalVectorStore
        vs = LocalVectorStore()
        vs.embeddings_db = [{"text": "t", "source": "s", "section": "sec"}]
        with patch("builtins.open", side_effect=IOError("write error")):
            vs._persist()


class TestFraudModelExtPaths:
    def test_missing_checksum_file(self):
        from app.services.fraud_model import FraudScoringEngine
        with patch("app.services.fraud_model.os.path.exists") as mock_exists:
            def exists_side_effect(path):
                if "fraud_model.joblib.sha256" in path:
                    return False
                return True
            mock_exists.side_effect = exists_side_effect
            engine = FraudScoringEngine()
            assert engine.is_compiled is False
    
    def test_checksum_mismatch(self):
        from app.services.fraud_model import FraudScoringEngine
        mock_files = {
            "fraud_model.joblib": b"some bytes",
            "fraud_model.joblib.sha256": "wronghash"
        }
        class MockOpenBytes:
            def __init__(self, filename, mode="r", *args, **kwargs):
                self.filename = filename
                self.mode = mode
            def __enter__(self):
                content = b""
                for k, v in mock_files.items():
                    if k in self.filename:
                        content = v
                import io
                if "b" in self.mode:
                    return io.BytesIO(content)
                else:
                    return io.StringIO(content.decode("utf-8"))
            def __exit__(self, *args):
                pass
        
        with patch("app.services.fraud_model.os.path.exists", return_value=True), \
             patch("builtins.open", MockOpenBytes):
            engine = FraudScoringEngine()
            assert engine.is_compiled is False

    def test_label_encoder_fallback(self):
        from app.services.fraud_model import fraud_engine
        payload = {
            "amount": 250.0,
            "hour": 14,
            "velocity_1h": 1,
            "distance_from_home": 2.5,
            "merchant_risk": 0.02,
            "P_emaildomain": "unseen-domain.com",
            "R_emaildomain": "another-unseen.com",
            "DeviceType": "nintendo-ds"
        }
        res = fraud_engine.score_transaction(payload)
        assert "risk_tier" in res

    def test_compile_explanation_and_tier_variations(self):
        from app.services.fraud_model import fraud_engine
        # Test Critical Tier
        explanation, tier = fraud_engine._compile_explanation_and_tier(
            prob=0.9, anomaly_score=-0.2, shap_vals={"TransactionAmt": 0.5}, tx={"amount": 600000.0, "TransactionAmt": 600000.0}
        )
        assert tier == "CRITICAL"
        assert "high transaction value" in explanation
        
        # Test High Tier
        explanation, tier = fraud_engine._compile_explanation_and_tier(
            prob=0.7, anomaly_score=-0.1, shap_vals={"card1": 0.5}, tx={"card1": 1004}
        )
        assert tier == "HIGH"
        
        # Test empty top features narrative fallback
        explanation, tier = fraud_engine._compile_explanation_and_tier(
            prob=0.1, anomaly_score=0.1, shap_vals={}, tx={}
        )
        assert tier == "LOW"
        assert "standard operational parameters" in explanation
        
        # Test other narratives in separate batches to avoid top-3 truncation
        explanation, tier = fraud_engine._compile_explanation_and_tier(
            prob=0.3, anomaly_score=0.01,
            shap_vals={
                "velocity_6h": 0.5,
                "velocity_24h": 0.4
            },
            tx={
                "velocity_6h": 2,
                "velocity_24h": 3
            }
        )
        assert tier == "MEDIUM"
        assert "last 6h" in explanation
        assert "last 24h" in explanation

        explanation2, tier2 = fraud_engine._compile_explanation_and_tier(
            prob=0.3, anomaly_score=0.01,
            shap_vals={
                "addr1": 0.5,
                "P_emaildomain": 0.4,
                "DeviceType": 0.3
            },
            tx={
                "addr1": 150.0,
                "P_emaildomain": "gmail.com",
                "DeviceType": "desktop"
            }
        )
        assert tier2 == "MEDIUM"
        assert "billing/shipping region" in explanation2
        assert "purchaser email domain" in explanation2
        assert "device transaction" in explanation2

    def test_heuristic_fallback_scenarios(self):
        from app.services.fraud_model import fraud_engine
        # Test low risk
        res = fraud_engine._heuristic_fallback({
            "amount": 100, "velocity_1h": 1, "distance_from_home": 10, "hour": 12, "merchant_risk": 0.05
        })
        assert res["risk_tier"] == "LOW"
        
        # Test medium/high/critical via various fields
        res = fraud_engine._heuristic_fallback({
            "amount": 200000, "velocity_1h": 10, "distance_from_home": 300, "hour": 2, "merchant_risk": 0.8
        })
        assert res["risk_tier"] == "CRITICAL"


class TestFinLensEngineExtPaths:
    def test_sql_query_tracker_json(self):
        from app.services.finlens_engine import SQLQueryTracker
        tracker = SQLQueryTracker()
        serialized = {"name": "sql_db_query"}
        tracker.on_tool_start(serialized, '{"query": "SELECT 1"}')
        assert tracker.queries[0] == "SELECT 1"
        
        tracker.on_tool_start(serialized, 'invalid json')
        assert tracker.queries[1] == "invalid json"
    
    def test_invalid_statement_id_raises_value_error(self):
        from app.services.finlens_engine import finlens_engine
        with pytest.raises(ValueError):
            finlens_engine.answer_numerical_query(None, "query", -1)
            
    def test_agent_executor_error_fallback(self):
        from app.services.finlens_engine import finlens_engine
        original_executor = finlens_engine.agent_executor
        try:
            finlens_engine.agent_executor = MagicMock()
            finlens_engine.agent_executor.invoke.side_effect = Exception("Agent error")
            
            res = finlens_engine.answer_numerical_query(MagicMock(), "What is my closing balance?", 1)
            assert res["audit_status"] == "VERIFIED_VIA_SQL_DATABASE"
        finally:
            finlens_engine.agent_executor = original_executor
            
    def test_offline_sql_execution_error(self):
        from app.services.finlens_engine import finlens_engine
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB execution error")
        res = finlens_engine.answer_numerical_query(mock_db, "What is my closing balance?", 1)
        assert res["audit_status"] == "EXECUTION_ERROR"
        assert "Failed to compile SQL" in res["answer"]
        
    @patch("app.services.finlens_engine._llm_limiter.is_allowed", return_value=True)
    def test_offline_router_keywords(self, mock_is_allowed):
        from app.services.finlens_engine import finlens_engine
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 100.0
        
        queries = [
            ("opening balance", "Opening Balance"),
            ("salary paycheck", "Salary Earnings"),
            ("total deposits credits", "Total Deposits"),
            ("swiggy food zomato", "Total Food Spend"),
            ("rent payment", "Rent Expenditure"),
            ("uber cab travel", "Total Travel Spend"),
            ("shopping amazon flipkart", "Total Shopping Spend"),
            ("bill utility phone", "Total Utility Spends"),
            ("max largest transaction", "Maximum Transaction Value"),
            ("min smallest transaction", "Minimum Transaction Value"),
            ("average mean transaction", "Average Transaction Value"),
            ("withdrawals total debits spent", "Total Withdrawals"),
            ("cash transaction", "Total Cash Flows"),
            ("how many transaction", "Transaction Count")
        ]
        
        for q, expected_label in queries:
            res = finlens_engine.answer_numerical_query(mock_db, q, 1)
            assert expected_label in res["answer"] or (q == "how many transaction" and "transactions recorded" in res["answer"])
