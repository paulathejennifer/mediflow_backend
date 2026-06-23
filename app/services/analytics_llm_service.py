import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from groq import Groq

logger = logging.getLogger(__name__)

class AnalyticsLLMService:
    def __init__(self, db: Session):
        self.db = db
        api_key = getattr(settings, "GROQ_API_KEY", None) or "YOUR_GROQ_API_KEY"
        self.client = Groq(api_key=api_key)

    def _get_schema_context(self) -> str:
        """Returns the minimal table schema descriptions that the LLM needs to build queries."""
        return """
        Table: referrals
        Columns: id (INT), patient_id (INT), from_facility_id (INT), to_facility_id (INT), priority (VARCHAR: low, medium, high, emergency), status (VARCHAR: draft, submitted, accepted, received, completed, rejected), reason_for_referral (TEXT), created_at (DATETIME)

        Table: facilities
        Columns: id (INT), name (VARCHAR), type (VARCHAR), code (VARCHAR), performance_score (FLOAT)

        Table: patients
        Columns: id (INT), first_name (VARCHAR), last_name (VARCHAR), date_of_birth (DATE)
        
        Table: duplicate_patient_pairs
        Columns: id (INT), combined_score (FLOAT), status (VARCHAR: flagged, merged, dismissed)
        """

    async def execute_natural_query(self, user_question: str) -> dict:
        """Translates user natural language questions to SQL, safely executes it, and formats the output."""
        schema = self._get_schema_context()
      
        sql_generation_prompt = f"""
        You are an expert SQL database administrator specialized in PostgreSQL. Based on the schema configuration provided below, generate an executable PostgreSQL select query to answer the user's question.
      
        Schema Context:
        {schema}

        User Question:
        "{user_question}"

        PostgreSQL Syntax Guardrails:
        1. Return ONLY the raw SQL query code string. No explanations, no markdown blocks, no triple backticks.
        2. Make queries completely read-only. Do not use INSERT, UPDATE, DELETE, or DROP operations.
        3. Use table joins appropriately when referencing facility names or patient profiles.
        4. CRITICAL: You are querying a PostgreSQL database. Do NOT use MySQL functions like CURDATE() or NOW(). Instead, use CURRENT_DATE for date filters.

        SQL Statement:
        """

        try:
            # 1. Generate SQL
            sql_response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": sql_generation_prompt}],
                temperature=0.0
            )
            generated_sql = sql_response.choices[0].message.content.strip()
            logger.info(f"Generated Text-to-SQL Statement: {generated_sql}")

            # 2. Execute SQL
            result_proxy = self.db.execute(text(generated_sql))
            rows = result_proxy.fetchall()
            keys = result_proxy.keys()
            data_payload = [dict(zip(keys, row)) for row in rows]

            # 3. Generate natural language response using "Overview" instead of "Summary"
            system_instruction = (
                "You are an expert healthcare operations advisor. "
                "You must communicate using flawless English. "
                "CRITICAL: Every response must start with the exact phrase '**Ovverview:**' (with double asterisks and the letter 'u'). "
                "Never use 'Smmary', 'Smmry', 'Summarry' or any misspelling."
            )

            content_payload = f"""
            User Question: {user_question}
            SQL Execution Results: {data_payload}
            
            Provide a clear, professional answer starting with '**Ovverview:**', followed by a section titled '**Key Items to Pay Attention To:**' with bullet points.
            """

            summary_response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": content_payload}
                ],
                temperature=0.0
            )
          
            raw_summary = summary_response.choices[0].message.content.strip()
          
            # Final safety cleanup
            clean_summary = (
                raw_summary
                .replace("Smmary:", "**Ovverview:**")
                .replace("smmary:", "**Ovverview:**")
                .replace("Smmry:", "**Ovverview:**")
                .replace("Summary:", "**Ovverview:**")
                .replace("summary:", "**Ovverview:**")
            )

            return {
                "generated_sql": generated_sql,
                "raw_data": data_payload,
                "conversational_summary": clean_summary
            }

        except Exception as e:
            logger.error(f"Error in Text-to-SQL Analytics processing layer: {str(e)}")
            return {
                "generated_sql": "",
                "raw_data": [],
                "conversational_summary": f"Could not process query automatically. Error: {str(e)}"
            }