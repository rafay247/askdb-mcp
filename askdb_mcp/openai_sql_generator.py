"""OpenAI-backed natural language to SQL generation."""

from __future__ import annotations

import json

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
        payload = json.loads(response.output_text)
        return GeneratedSql(
            sql=payload["sql"],
            operation=SqlOperation(payload["operation"]),
            explanation=payload["explanation"],
            risk_summary=payload["risk_summary"],
        )

