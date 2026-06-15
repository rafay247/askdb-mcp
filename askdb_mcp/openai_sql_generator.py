"""OpenAI-backed natural language to SQL generation."""

from __future__ import annotations

import json
import re

from openai import OpenAI

from askdb_mcp.config import Settings
from askdb_mcp.models import GeneratedSql, SqlOperation


SQL_GENERATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "sql": {"type": "string"},
        "operation": {"type": "string", "enum": ["read", "write", "unsupported"]},
        "explanation": {"type": "string"},
        "risk_summary": {"type": "string"},
    },
    "required": ["sql", "operation", "explanation", "risk_summary"],
}


class OpenAISqlGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate(self, question: str, schema_context: str) -> GeneratedSql:
        fallback = _local_sample_fallback(question, schema_context)
        if _uses_placeholder_key(self.settings.openai_api_key) and fallback is not None:
            return fallback

        system_prompt = (
            "You translate natural language into one SQLite SQL statement. "
            "Return JSON that matches the provided schema. "
            "Use only tables and columns present in the schema. "
            "For reads, generate SELECT or WITH. "
            "For writes, generate only INSERT, UPDATE, or DELETE. "
            "Do not generate schema changes, PRAGMA, ATTACH, DETACH, comments, or multiple statements."
        )
        user_prompt = (
            f"SQLite schema:\n{schema_context}\n\n"
            f"User request:\n{question}\n\n"
            "Generate the best SQLite statement for this request."
        )

        try:
            response = self.client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "askdb_sql_generation",
                        "strict": True,
                        "schema": SQL_GENERATION_SCHEMA,
                    }
                },
            )
        except Exception:
            if fallback is not None:
                return fallback
            raise

        payload = json.loads(response.output_text)
        return GeneratedSql(
            sql=payload["sql"],
            operation=SqlOperation(payload["operation"]),
            explanation=payload["explanation"],
            risk_summary=payload["risk_summary"],
        )


def _uses_placeholder_key(api_key: str) -> bool:
    key = api_key.strip().lower()
    return not key or key.startswith("replace_") or key in {"sk-your-key", "your_openai_key_here"}


def _local_sample_fallback(question: str, schema_context: str) -> GeneratedSql | None:
    """Handle common sample DB questions when OpenAI is unavailable."""

    if not {"customers", "products", "orders"}.issubset(set(schema_context.lower().split())):
        return None

    write = _customer_insert_fallback(question)
    if write is not None:
        return write

    normalized = question.strip().lower()
    city_match = re.search(r"\b(?:in|from)\s+([a-z][a-z\s-]*)$", normalized)
    if "customer" in normalized:
        if city_match:
            city = city_match.group(1).strip().title().replace("'", "''")
            return GeneratedSql(
                sql=f"SELECT id, name, email, city FROM customers WHERE lower(city) = lower('{city}')",
                operation=SqlOperation.READ,
                explanation="Local fallback query for customers filtered by city.",
                risk_summary="Read-only SELECT statement.",
            )
        return GeneratedSql(
            sql="SELECT id, name, email, city FROM customers ORDER BY id",
            operation=SqlOperation.READ,
            explanation="Local fallback query for all customers.",
            risk_summary="Read-only SELECT statement.",
        )

    if "product" in normalized:
        return GeneratedSql(
            sql="SELECT id, name, price FROM products ORDER BY id",
            operation=SqlOperation.READ,
            explanation="Local fallback query for all products.",
            risk_summary="Read-only SELECT statement.",
        )

    if "order" in normalized:
        return GeneratedSql(
            sql=(
                "SELECT orders.id, customers.name AS customer, products.name AS product, "
                "orders.quantity, orders.ordered_at "
                "FROM orders "
                "JOIN customers ON customers.id = orders.customer_id "
                "JOIN products ON products.id = orders.product_id "
                "ORDER BY orders.id"
            ),
            operation=SqlOperation.READ,
            explanation="Local fallback query for orders with customer and product names.",
            risk_summary="Read-only SELECT statement.",
        )

    return None


def _customer_insert_fallback(question: str) -> GeneratedSql | None:
    normalized = question.strip().lower()
    if not re.search(r"\b(add|create|insert)\b", normalized) or "customer" not in normalized:
        return None

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", question)
    if email_match is None:
        return None

    before_email = question[: email_match.start()]
    after_email = question[email_match.end() :]
    name_text = re.sub(
        r"\b(add|create|insert|new|customer|with|email|named|name|city|in|from)\b",
        " ",
        before_email,
        flags=re.IGNORECASE,
    ).strip()
    city_text = re.sub(
        r"\b(city|in|from|is|at)\b",
        " ",
        after_email,
        flags=re.IGNORECASE,
    ).strip()

    if not name_text or not city_text:
        return None

    name = " ".join(name_text.split()).replace("'", "''")
    email = email_match.group(0).replace("'", "''")
    city = " ".join(city_text.split()).replace("'", "''")
    return GeneratedSql(
        sql=f"INSERT INTO customers (name, email, city) VALUES ('{name}', '{email}', '{city}')",
        operation=SqlOperation.WRITE,
        explanation="Local fallback write proposal for adding a customer.",
        risk_summary="Adds one row to the customers table after approval.",
    )
