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
        Columns: id (INT), name (VARCHAR), type (VARCHAR), code (VARCHAR)

        Table: patients
        Columns: id (INT), first_name (VARCHAR), last_name (VARCHAR), date_of_birth (DATE)
        
        Table: duplicate_patient_pairs
        Columns: id (INT), combined_score (FLOAT), status (VARCHAR: flagged, merged, dismissed)
        """

    async def execute_natural_query(self, user_question: str) -> dict:
        """Translates user natural language questions to SQL, safely executes it, and formats the output."""
        schema = self._get_schema_context()
        
        sql_generation_prompt = f"""
        You are a SQL database master administrator. Based on the schema configuration provided below, generate an executable ANSI SQL select query to answer the user's question.
        
        Schema Context:
        {schema}

        User Question:
        "{user_question}"

        Rules:
        1. Return ONLY the raw SQL query code string. No explanations, no markdown blocks, no triple backticks.
        2. Make queries read-only. Do not use INSERT, UPDATE, DELETE, or DROP operations.
        3. Use table joins appropriately when referencing facility names or patient profiles.

        SQL Statement:
        """

        try:
            # 1. Ask Llama to output a valid SQL string
            sql_response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": sql_generation_prompt}],
                temperature=0.0
            )
            generated_sql = sql_response.choices[0].message.content.strip()
            logger.info(f"Generated Text-to-SQL Statement: {generated_sql}")

            # 2. Execute SQL query directly against the active DB connection context securely
            result_proxy = self.db.execute(text(generated_sql))
            
            # Map out database rows securely into key-value tuples
            rows = result_proxy.fetchall()
            keys = result_proxy.keys()
            data_payload = [dict(zip(keys, row)) for row in rows]

            # 3. Request LLM to format the data output back into a human conversational summary
            interpretation_prompt = f"""
            You are a healthcare operations advisor. Summarize the raw database analytical result sets provided below to answer the user's question clearly.
            
            User Question: {user_question}
            SQL Execution Results: {data_payload}
            
            Provide a short, direct summary, followed by any key items administrators should pay attention to.
            """

            summary_response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": interpretation_prompt}],
                temperature=0.3
            )
            
            return {
                "generated_sql": generated_sql,
                "raw_data": data_payload,
                "conversational_summary": summary_response.choices[0].message.content.strip()
            }

        except Exception as e:
            logger.error(f"Error in Text-to-SQL Analytics processing layer: {str(e)}")
            return {
                "generated_sql": "",
                "raw_data": [],
                "conversational_summary": f"Could not process query automatically. Error details: {str(e)}"
            }