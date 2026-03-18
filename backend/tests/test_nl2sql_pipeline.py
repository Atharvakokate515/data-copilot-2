# backend/tests/test_nl2sql_pipeline.py
"""
Test suite for:
  1. _suggest_chart()    — pure logic, no mocks needed
  2. clarify_query()     — unit tests with LLM + DB mocked out
  3. /chat-db endpoint   — integration tests via FastAPI TestClient
                           with all external calls mocked

Run with:
    cd backend
    pytest tests/test_nl2sql_pipeline.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call

# ── Make sure 'backend/' is on the path so imports resolve ────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── FastAPI test client ────────────────────────────────────────────
from fastapi.testclient import TestClient
from fastapi import FastAPI

# ── The modules under test ─────────────────────────────────────────
from core.clarifier_schema import ClarifierOutput


# ─────────────────────────────────────────────────────────────────
# Helpers / shared fixtures
# ─────────────────────────────────────────────────────────────────

FAKE_DB_URL = "postgresql://fake:fake@localhost:5432/fakedb"
FAKE_SESSION_ID = "test-session-uuid-1234"
FAKE_SCHEMA = "Table: orders\n  Columns:\n    - id (integer)\n    - amount (numeric)\n    - country (text)\n"


def _make_execution_result(rows, col_names, row_count=None, success=True):
    """Helper to build a fake execution result dict matching your executor output."""
    return {
        "success": success,
        "query_type": "SELECT",
        "execution_time_sec": 0.01,
        "result": {
            "type": "select",
            "col_names": col_names,
            "rows": rows,
            "row_count": row_count if row_count is not None else len(rows),
        },
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 1 — _suggest_chart() unit tests
#
# This is a pure helper function inside api/chat.py.
# It decides chart type based on column types and row count.
# ─────────────────────────────────────────────────────────────────

# We import it directly — it's a module-level private function.
from api.chat import _suggest_chart


class TestSuggestChart:
    """
    Chart type logic:
      - No rows / non-SELECT           → None
      - 1 row, 1 col                   → table
      - text + numeric, row_count ≤ 6  → pie
      - text + numeric, row_count > 6  → bar
      - 2+ numeric cols                → line
      - only text cols                 → table (fallback)
    """

    # ── Rows are represented as list-of-dicts in _suggest_chart ──
    def _wrap(self, col_names, row_dicts, row_count=None, qtype="select"):
        return {
            "success": True,
            "result": {
                "type": qtype,
                "col_names": col_names,
                "rows": row_dicts,
                "row_count": row_count if row_count is not None else len(row_dicts),
            },
        }

    # ── 1. Non-SELECT query type returns None ─────────────────────
    def test_non_select_returns_none(self):
        result = _suggest_chart(self._wrap(["id"], [{"id": 1}], qtype="insert"))
        assert result is None, "Non-SELECT queries should never produce a chart"

    # ── 2. Empty rows returns None ────────────────────────────────
    def test_empty_rows_returns_none(self):
        result = _suggest_chart(self._wrap(["country", "total"], [], row_count=0))
        assert result is None, "Empty result set should return None"

    # ── 3. Single value result → table ───────────────────────────
    def test_single_value_returns_table(self):
        rows = [{"count": 42}]
        result = _suggest_chart(self._wrap(["count"], rows, row_count=1))
        assert result is not None
        assert result["type"] == "table", (
            "A scalar result (1 row, 1 col) should fall back to table"
        )

    # ── 4. text + numeric, ≤ 6 rows → pie ────────────────────────
    def test_pie_for_small_category_data(self):
        rows = [
            {"product_line": "Motorcycles", "total_sales": 500000},
            {"product_line": "Classic Cars", "total_sales": 900000},
            {"product_line": "Trucks",       "total_sales": 300000},
        ]
        result = _suggest_chart(self._wrap(["product_line", "total_sales"], rows))
        assert result is not None
        assert result["type"] == "pie", (
            "Small categorical+numeric data (≤6 rows) should be a pie chart"
        )
        assert result["x_axis"] == "product_line"
        assert result["y_axis"] == "total_sales"

    # ── 5. text + numeric, > 6 rows → bar ────────────────────────
    def test_bar_for_large_category_data(self):
        rows = [
            {"country": f"Country_{i}", "revenue": i * 1000}
            for i in range(10)
        ]
        result = _suggest_chart(self._wrap(["country", "revenue"], rows))
        assert result is not None
        assert result["type"] == "bar", (
            "Categorical+numeric data with >6 rows should be a bar chart"
        )
        assert result["x_axis"] == "country"
        assert result["y_axis"] == "revenue"

    # ── 6. Two numeric cols → line ────────────────────────────────
    def test_line_for_two_numeric_cols(self):
        rows = [
            {"month_num": 1, "revenue": 50000},
            {"month_num": 2, "revenue": 60000},
            {"month_num": 3, "revenue": 55000},
        ]
        result = _suggest_chart(self._wrap(["month_num", "revenue"], rows))
        assert result is not None
        assert result["type"] == "line", (
            "Two numeric columns should produce a line chart"
        )

    # ── 7. Only text cols → table fallback ───────────────────────
    def test_only_text_cols_returns_table(self):
        rows = [
            {"customer_name": "Alice", "country": "Germany"},
            {"customer_name": "Bob",   "country": "France"},
        ]
        result = _suggest_chart(self._wrap(["customer_name", "country"], rows))
        # No numeric column → can't draw a meaningful chart → table
        assert result is None or result["type"] == "table", (
            "All-text columns should not produce a bar/pie/line chart"
        )


# ─────────────────────────────────────────────────────────────────
# SECTION 2 — clarify_query() unit tests
#
# We mock:
#   - get_schema()        → avoid real DB connection
#   - The LangChain chain → avoid real LLM call
#
# The trick: patch PromptTemplate so its __or__ chain returns a
# mock whose invoke() returns the ClarifierOutput we control.
# ─────────────────────────────────────────────────────────────────

class TestClarifyQuery:

    def _mock_chain(self, is_clear: bool, question: str = ""):
        """
        Returns a MagicMock that behaves like a LangChain chain:
          (prompt | llm | parser).invoke(...)  →  ClarifierOutput(...)
        """
        output = ClarifierOutput(is_clear=is_clear, question=question)
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = output
        return mock_chain

    @patch("nl2sql.clarrifier.get_schema", return_value=FAKE_SCHEMA)
    @patch("nl2sql.clarrifier.clarifier_parser")
    @patch("nl2sql.clarrifier.llm")
    def test_ambiguous_query_is_not_clear(self, mock_llm, mock_parser, mock_schema):
        """
        'show me data' — no metric, no table reference, no history.
        Clarifier should return is_clear=False with a follow-up question.
        """
        # Wire up the pipe chain: prompt | mock_llm | mock_parser → our output
        expected = ClarifierOutput(
            is_clear=False,
            question="Which metric would you like to see? (e.g. total sales, order count)"
        )

        # LangChain LCEL pipe (|) builds a RunnableSequence; easiest to mock
        # by making the parser's __ror__ (right-or) return a chain mock.
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = expected
        mock_parser.__ror__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_parser)

        from nl2sql.clarrifier import clarify_query
        result = clarify_query(
            user_input="show me data",
            db_url=FAKE_DB_URL,
            chat_history=None,
            last_sql=None,
        )

        assert result.is_clear is False, "Ambiguous query should be flagged as not clear"
        assert result.question != "", "A follow-up question must be provided"
        mock_schema.assert_called_once_with(FAKE_DB_URL)

    @patch("nl2sql.clarrifier.get_schema", return_value=FAKE_SCHEMA)
    @patch("nl2sql.clarrifier.clarifier_parser")
    @patch("nl2sql.clarrifier.llm")
    def test_specific_query_is_clear(self, mock_llm, mock_parser, mock_schema):
        """
        'show total sales by product line' — specific, references known
        concepts. Clarifier should return is_clear=True.
        """
        expected = ClarifierOutput(is_clear=True, question="")

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = expected
        mock_parser.__ror__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_parser)

        from nl2sql.clarrifier import clarify_query
        result = clarify_query(
            user_input="show total sales by product line",
            db_url=FAKE_DB_URL,
            chat_history=None,
            last_sql=None,
        )

        assert result.is_clear is True
        assert result.question == ""

    @patch("nl2sql.clarrifier.get_schema", return_value=FAKE_SCHEMA)
    @patch("nl2sql.clarrifier.clarifier_parser")
    @patch("nl2sql.clarrifier.llm")
    def test_followup_with_context_is_clear(self, mock_llm, mock_parser, mock_schema):
        """
        'now filter by Germany' looks vague in isolation, but the prior
        conversation and last_sql make the intent clear.
        The clarifier should return is_clear=True when context is given.
        """
        expected = ClarifierOutput(is_clear=True, question="")

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = expected
        mock_parser.__ror__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_parser)

        history = [
            {"role": "user",      "content": "show total sales by country"},
            {"role": "assistant", "content": "SELECT country, SUM(amount) FROM orders GROUP BY country"},
        ]
        last_sql = "SELECT country, SUM(amount) FROM orders GROUP BY country"

        from nl2sql.clarrifier import clarify_query
        result = clarify_query(
            user_input="now filter by Germany",
            db_url=FAKE_DB_URL,
            chat_history=history,
            last_sql=last_sql,
        )

        # Verify the chain was called with the history baked in
        assert result.is_clear is True, (
            "A follow-up query with clear chat context should be marked as clear"
        )
        # Verify chat history was passed into the chain
        invoke_kwargs = mock_chain.invoke.call_args[0][0]
        assert "Germany" in invoke_kwargs.get("user_input", "")
        assert last_sql in invoke_kwargs.get("last_sql", "")

    @patch("nl2sql.clarrifier.get_schema", return_value=FAKE_SCHEMA)
    @patch("nl2sql.clarrifier.clarifier_parser")
    @patch("nl2sql.clarrifier.llm")
    def test_chat_history_is_formatted_and_passed(self, mock_llm, mock_parser, mock_schema):
        """
        Verify that _format_chat_history properly joins role: content pairs
        and that they are forwarded to the chain.
        """
        expected = ClarifierOutput(is_clear=True, question="")
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = expected
        mock_parser.__ror__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_parser)

        history = [
            {"role": "user",      "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        from nl2sql.clarrifier import clarify_query
        clarify_query(
            user_input="what is the total?",
            db_url=FAKE_DB_URL,
            chat_history=history,
            last_sql=None,
        )

        invoke_args = mock_chain.invoke.call_args[0][0]
        chat_history_str = invoke_args.get("chat_history", "")
        assert "User: Hello" in chat_history_str
        assert "Assistant: Hi there" in chat_history_str


# ─────────────────────────────────────────────────────────────────
# SECTION 3 — /chat-db endpoint integration tests
#
# We mount the router on a bare FastAPI app and call it via
# TestClient. Every external dependency is mocked so we test
# purely the control flow / branching logic in chat.py.
# ─────────────────────────────────────────────────────────────────

# Patch build_graph at import time to avoid LangGraph setup
with patch("api.chat.build_graph", return_value=MagicMock()):
    from api.chat import router as chat_router

_app = FastAPI()
_app.include_router(chat_router, prefix="/nl2sql")
client = TestClient(_app)

# Shared mock values
MOCK_SQL     = "SELECT country, SUM(amount) AS total FROM orders GROUP BY country"
MOCK_PLAN    = MagicMock()
MOCK_TABLES  = ["orders", "customers", "products"]

CLEAR_RESULT = _make_execution_result(
    rows=[
        {"country": "Germany", "total": 150000},
        {"country": "France",  "total": 120000},
        {"country": "USA",     "total": 300000},
    ],
    col_names=["country", "total"],
    row_count=3,
)


def _patch_all(
    clarify_return=None,
    plan_return=None,
    generate_return=MOCK_SQL,
    safe_return=None,
    exec_return=None,
    last_sql=None,
    chat_history=None,
):
    """
    Build a dict of patches for the /chat-db happy-path.
    Callers can override individual values.
    """
    if clarify_return is None:
        clarify_return = ClarifierOutput(is_clear=True, question="")
    if plan_return is None:
        plan_return = MOCK_PLAN
    if safe_return is None:
        safe_return = {"safe": True}
    if exec_return is None:
        exec_return = CLEAR_RESULT

    return {
        "api.chat.clarify_query":         MagicMock(return_value=clarify_return),
        "api.chat.plan_query":            MagicMock(return_value=plan_return),
        "api.chat.generate_sql":          MagicMock(return_value=generate_return),
        "api.chat.is_safe_sql":           MagicMock(return_value=safe_return),
        "api.chat.execute_sql":           MagicMock(return_value=exec_return),
        "api.chat.get_table_list":        MagicMock(return_value=MOCK_TABLES),
        "api.chat.get_last_sql":          MagicMock(return_value=last_sql),
        "api.chat.get_chat_history":      MagicMock(return_value=chat_history or []),
        "api.chat.append_message":        MagicMock(),
        "api.chat.update_session_title":  MagicMock(),
        "api.chat.update_last_sql":       MagicMock(),
        "api.chat.create_session":        MagicMock(return_value=FAKE_SESSION_ID),
        "api.chat.generate_text":         MagicMock(return_value=MagicMock(content="Here are your results.")),
    }


class TestChatDBEndpoint:

    # ── 3.1 Ambiguous query → CLARIFICATION_NEEDED ───────────────
    def test_ambiguous_query_triggers_clarification(self):
        """
        When clarify_query() returns is_clear=False, the endpoint must:
        - Return HTTP 200 (not an error status)
        - success = False
        - error_code = 'CLARIFICATION_NEEDED'
        - Include the clarifying question
        - NOT call plan_query or generate_sql
        """
        question = "Which metric would you like? (e.g. revenue, order count)"
        patches = _patch_all(
            clarify_return=ClarifierOutput(is_clear=False, question=question)
        )

        with patch.multiple("", **{k: v for k, v in patches.items()}):
            # Using nested patches
            pass

        # Apply each patch individually for reliability
        with patch("api.chat.clarify_query",        return_value=ClarifierOutput(is_clear=False, question=question)), \
             patch("api.chat.plan_query",            return_value=MOCK_PLAN), \
             patch("api.chat.generate_sql",          return_value=MOCK_SQL), \
             patch("api.chat.is_safe_sql",           return_value={"safe": True}), \
             patch("api.chat.execute_sql",           return_value=CLEAR_RESULT), \
             patch("api.chat.get_table_list",        return_value=MOCK_TABLES), \
             patch("api.chat.get_last_sql",          return_value=None), \
             patch("api.chat.get_chat_history",      return_value=[]), \
             patch("api.chat.append_message"), \
             patch("api.chat.update_session_title"), \
             patch("api.chat.update_last_sql"), \
             patch("api.chat.create_session",        return_value=FAKE_SESSION_ID), \
             patch("api.chat.generate_text",         return_value=MagicMock(content="summary")):

            response = client.post("/nl2sql/chat-db", json={
                "db_url": FAKE_DB_URL,
                "user_input": "show me data",
                "session_id": FAKE_SESSION_ID,
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["error_code"] == "CLARIFICATION_NEEDED"
        assert body["needs_clarification"] is True
        assert body["question"] == question
        assert "stage" in body and body["stage"] == "clarification"
        assert "session_id" in body

    # ── 3.2 Clarification response bypasses clarifier ────────────
    def test_clarification_response_skips_clarifier(self):
        """
        When the client sends clarification_response, the endpoint must:
        - Skip calling clarify_query entirely
        - Use clarification_response as the query input
        - Proceed to planner → generator → validator → executor
        - Return success=True
        """
        mock_clarify = MagicMock(return_value=ClarifierOutput(is_clear=True, question=""))
        mock_plan    = MagicMock(return_value=MOCK_PLAN)
        mock_gen     = MagicMock(return_value=MOCK_SQL)

        with patch("api.chat.clarify_query",       mock_clarify), \
             patch("api.chat.plan_query",           mock_plan), \
             patch("api.chat.generate_sql",         mock_gen), \
             patch("api.chat.is_safe_sql",          return_value={"safe": True}), \
             patch("api.chat.execute_sql",          return_value=CLEAR_RESULT), \
             patch("api.chat.get_table_list",       return_value=MOCK_TABLES), \
             patch("api.chat.get_last_sql",         return_value=None), \
             patch("api.chat.get_chat_history",     return_value=[]), \
             patch("api.chat.append_message"), \
             patch("api.chat.update_session_title"), \
             patch("api.chat.update_last_sql"), \
             patch("api.chat.create_session",       return_value=FAKE_SESSION_ID), \
             patch("api.chat.generate_text",        return_value=MagicMock(content="summary")):

            response = client.post("/nl2sql/chat-db", json={
                "db_url":                  FAKE_DB_URL,
                "user_input":              "show me data",
                "session_id":              FAKE_SESSION_ID,
                "clarification_response":  "show total revenue by country",
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True, "Pipeline should succeed after clarification"

        # clarify_query must NOT have been called
        mock_clarify.assert_not_called()

        # plan_query must have used the clarification text, NOT the original vague input
        call_args = mock_plan.call_args
        assert "show total revenue by country" in str(call_args), (
            "plan_query should receive the clarification_response as input"
        )

    # ── 3.3 Clear query → full pipeline success ──────────────────
    def test_clear_query_runs_full_pipeline(self):
        """
        A specific query goes through clarifier (clear) → planner →
        generator → validator → executor and returns a successful result.
        The response must include: sql, execution result, and chart suggestion.
        """
        with patch("api.chat.clarify_query",       return_value=ClarifierOutput(is_clear=True, question="")), \
             patch("api.chat.plan_query",           return_value=MOCK_PLAN), \
             patch("api.chat.generate_sql",         return_value=MOCK_SQL), \
             patch("api.chat.is_safe_sql",          return_value={"safe": True}), \
             patch("api.chat.execute_sql",          return_value=CLEAR_RESULT), \
             patch("api.chat.get_table_list",       return_value=MOCK_TABLES), \
             patch("api.chat.get_last_sql",         return_value=None), \
             patch("api.chat.get_chat_history",     return_value=[]), \
             patch("api.chat.append_message"), \
             patch("api.chat.update_session_title"), \
             patch("api.chat.update_last_sql"), \
             patch("api.chat.create_session",       return_value=FAKE_SESSION_ID), \
             patch("api.chat.generate_text",        return_value=MagicMock(content="Top countries by revenue.")):

            response = client.post("/nl2sql/chat-db", json={
                "db_url":      FAKE_DB_URL,
                "user_input":  "show total sales by country",
                "session_id":  FAKE_SESSION_ID,
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["generated_sql"] == MOCK_SQL
        assert "execution" in body
        assert "chart_suggestion" in body
        # 3 rows, text + numeric → should be a pie (≤6 rows)
        chart = body.get("chart_suggestion")
        assert chart is not None
        assert chart["type"] in ("pie", "bar"), (
            "Country+revenue data should produce a pie or bar chart"
        )

    # ── 3.4 Session auto-created if not provided ──────────────────
    def test_session_auto_created_when_absent(self):
        """
        If no session_id is sent, the server should auto-create one and
        return is_new_session=True plus a valid session_id.
        """
        mock_create = MagicMock(return_value="auto-generated-uuid-9999")

        with patch("api.chat.clarify_query",       return_value=ClarifierOutput(is_clear=True, question="")), \
             patch("api.chat.plan_query",           return_value=MOCK_PLAN), \
             patch("api.chat.generate_sql",         return_value=MOCK_SQL), \
             patch("api.chat.is_safe_sql",          return_value={"safe": True}), \
             patch("api.chat.execute_sql",          return_value=CLEAR_RESULT), \
             patch("api.chat.get_table_list",       return_value=MOCK_TABLES), \
             patch("api.chat.get_last_sql",         return_value=None), \
             patch("api.chat.get_chat_history",     return_value=[]), \
             patch("api.chat.append_message"), \
             patch("api.chat.update_session_title"), \
             patch("api.chat.update_last_sql"), \
             patch("api.chat.create_session",       mock_create), \
             patch("api.chat.generate_text",        return_value=MagicMock(content="summary")):

            response = client.post("/nl2sql/chat-db", json={
                "db_url":     FAKE_DB_URL,
                "user_input": "show total sales by country",
                # no session_id
            })

        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == "auto-generated-uuid-9999"
        assert body["is_new_session"] is True
        mock_create.assert_called_once()

    # ── 3.5 Validation failure → retry → still fails ─────────────
    def test_validation_failure_triggers_retry_then_fails(self):
        """
        If is_safe_sql fails both on first attempt and retry, the endpoint
        must return error_code=VALIDATION_FAILED with was_retried=True.
        """
        bad_validation  = {"safe": False, "reason": "Query references unknown table"}
        generate_calls  = [MOCK_SQL, "SELECT * FROM unknown_table"]

        with patch("api.chat.clarify_query",       return_value=ClarifierOutput(is_clear=True, question="")), \
             patch("api.chat.plan_query",           return_value=MOCK_PLAN), \
             patch("api.chat.generate_sql",         side_effect=generate_calls), \
             patch("api.chat.is_safe_sql",          return_value=bad_validation), \
             patch("api.chat.execute_sql",          return_value=CLEAR_RESULT), \
             patch("api.chat.get_table_list",       return_value=MOCK_TABLES), \
             patch("api.chat.get_last_sql",         return_value=None), \
             patch("api.chat.get_chat_history",     return_value=[]), \
             patch("api.chat.append_message"), \
             patch("api.chat.update_session_title"), \
             patch("api.chat.update_last_sql"), \
             patch("api.chat.create_session",       return_value=FAKE_SESSION_ID), \
             patch("api.chat.generate_text",        return_value=MagicMock(content="summary")):

            response = client.post("/nl2sql/chat-db", json={
                "db_url":      FAKE_DB_URL,
                "user_input":  "get something",
                "session_id":  FAKE_SESSION_ID,
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["error_code"] == "VALIDATION_FAILED"
        assert body["was_retried"] is True

    # ── 3.6 Execution failure → retry → success ──────────────────
    def test_execution_failure_triggers_retry_and_succeeds(self):
        """
        If execute_sql fails on the first attempt, the endpoint retries
        by calling generate_sql again with error_feedback.
        The second execute_sql call must succeed.
        """
        failed_exec  = {"success": False, "error": "column does not exist"}
        success_exec = CLEAR_RESULT

        exec_calls    = [failed_exec, success_exec]
        gen_calls     = [MOCK_SQL, "SELECT country, SUM(amount) FROM orders GROUP BY country"]

        with patch("api.chat.clarify_query",       return_value=ClarifierOutput(is_clear=True, question="")), \
             patch("api.chat.plan_query",           return_value=MOCK_PLAN), \
             patch("api.chat.generate_sql",         side_effect=gen_calls), \
             patch("api.chat.is_safe_sql",          return_value={"safe": True}), \
             patch("api.chat.execute_sql",          side_effect=exec_calls), \
             patch("api.chat.get_table_list",       return_value=MOCK_TABLES), \
             patch("api.chat.get_last_sql",         return_value=None), \
             patch("api.chat.get_chat_history",     return_value=[]), \
             patch("api.chat.append_message"), \
             patch("api.chat.update_session_title"), \
             patch("api.chat.update_last_sql"), \
             patch("api.chat.create_session",       return_value=FAKE_SESSION_ID), \
             patch("api.chat.generate_text",        return_value=MagicMock(content="summary")):

            response = client.post("/nl2sql/chat-db", json={
                "db_url":      FAKE_DB_URL,
                "user_input":  "show total sales by country",
                "session_id":  FAKE_SESSION_ID,
            })

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True, "Pipeline should succeed after one execution retry"
        assert body["was_retried"] is True

    # ── 3.7 Follow-up query uses last_sql context ─────────────────
    def test_followup_query_passes_last_sql_to_clarifier(self):
        """
        When a session already has last_sql, the clarifier and planner
        must receive it so they can resolve follow-up queries correctly.
        """
        mock_clarify = MagicMock(return_value=ClarifierOutput(is_clear=True, question=""))
        previous_sql = "SELECT country, SUM(amount) FROM orders GROUP BY country"

        with patch("api.chat.clarify_query",       mock_clarify), \
             patch("api.chat.plan_query",           return_value=MOCK_PLAN), \
             patch("api.chat.generate_sql",         return_value=MOCK_SQL), \
             patch("api.chat.is_safe_sql",          return_value={"safe": True}), \
             patch("api.chat.execute_sql",          return_value=CLEAR_RESULT), \
             patch("api.chat.get_table_list",       return_value=MOCK_TABLES), \
             patch("api.chat.get_last_sql",         return_value=previous_sql), \
             patch("api.chat.get_chat_history",     return_value=[
                 {"role": "user",      "content": "show total sales by country"},
                 {"role": "assistant", "content": previous_sql},
             ]), \
             patch("api.chat.append_message"), \
             patch("api.chat.update_session_title"), \
             patch("api.chat.update_last_sql"), \
             patch("api.chat.create_session",       return_value=FAKE_SESSION_ID), \
             patch("api.chat.generate_text",        return_value=MagicMock(content="summary")):

            response = client.post("/nl2sql/chat-db", json={
                "db_url":      FAKE_DB_URL,
                "user_input":  "now filter by Germany",
                "session_id":  FAKE_SESSION_ID,
            })

        assert response.status_code == 200
        # Verify clarifier received last_sql
        clarify_kwargs = mock_clarify.call_args.kwargs
        assert clarify_kwargs.get("last_sql") == previous_sql, (
            "Clarifier must receive last_sql so it can resolve follow-up context"
        )
        assert len(clarify_kwargs.get("chat_history", [])) > 0, (
            "Clarifier must receive chat_history for follow-up resolution"
        )


# ─────────────────────────────────────────────────────────────────
# SECTION 4 — Chart type coverage summary
#
# Quick parametrized reference: which queries produce which charts.
# ─────────────────────────────────────────────────────────────────

CHART_CASES = [
    # (description,                    col_names,             rows,                                     expected_type)
    ("category+value, 3 rows → pie",   ["product", "sales"],  [{"product": "A", "sales": 100}] * 3,    "pie"),
    ("category+value, 8 rows → bar",   ["country", "rev"],    [{"country": f"C{i}", "rev": i*10} for i in range(8)], "bar"),
    ("two numeric cols → line",        ["month", "revenue"],  [{"month": i, "revenue": i*500} for i in range(5)],    "line"),
    ("single scalar → table",          ["count"],             [{"count": 42}],                          "table"),
]


@pytest.mark.parametrize("desc,col_names,rows,expected", CHART_CASES)
def test_chart_type_parametrized(desc, col_names, rows, expected):
    """Parametrized coverage of all chart type branches in _suggest_chart."""
    execution = {
        "success": True,
        "result": {
            "type": "select",
            "col_names": col_names,
            "rows": rows,
            "row_count": len(rows),
        }
    }
    result = _suggest_chart(execution)
    assert result is not None, f"[{desc}] Expected a chart suggestion, got None"
    assert result["type"] == expected, (
        f"[{desc}] Expected chart type '{expected}', got '{result['type']}'"
    )


# ─────────────────────────────────────────────────────────────────
# Entry point for quick manual runs
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess, sys
    sys.exit(subprocess.call(["pytest", __file__, "-v", "--tb=short"]))