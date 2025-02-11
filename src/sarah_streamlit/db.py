"""Database operations for the testing application."""
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import atexit
from google.cloud import storage

# Get database path from environment variable or use default
DB_PATH = os.getenv('DB_PATH', 'sarah_testing.db')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'sarah-testing-db')

def sync_db_with_cloud_storage():
    """Sync database with Cloud Storage."""
    if not os.getenv('CLOUD_RUN_SERVICE'):
        return
        
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob('sarah_testing.db')
    
    # Download if exists
    if blob.exists():
        blob.download_to_filename(DB_PATH)
    
    # Register upload on exit
    def upload_db():
        if os.path.exists(DB_PATH):
            blob.upload_from_filename(DB_PATH)
    
    atexit.register(upload_db)

def get_db_connection():
    """Get a database connection."""
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Sync with Cloud Storage if running in Cloud Run
    sync_db_with_cloud_storage()
    
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize the database schema."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create tables
    c.executescript('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY,
            question_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        );
        
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            version INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS test_runs (
            id INTEGER PRIMARY KEY,
            prompt_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            model TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prompt_id) REFERENCES prompts (id)
        );
        
        CREATE TABLE IF NOT EXISTS run_results (
            id INTEGER PRIMARY KEY,
            run_id INTEGER,
            question_id INTEGER,
            response TEXT NOT NULL,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES test_runs (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        );
        
        CREATE TABLE IF NOT EXISTS run_comparisons (
            id INTEGER PRIMARY KEY,
            run_id_1 INTEGER,
            run_id_2 INTEGER,
            question_id INTEGER,
            preferred_run_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id_1) REFERENCES test_runs (id),
            FOREIGN KEY (run_id_2) REFERENCES test_runs (id),
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (preferred_run_id) REFERENCES test_runs (id)
        );
    ''')
    
    conn.commit()
    conn.close()

@dataclass
class QuestionType:
    """Question type model."""
    id: int
    name: str

@dataclass
class Source:
    """Source model."""
    id: int
    title: str
    content: str
    created_at: str

@dataclass
class Question:
    """Question model."""
    id: int
    name: str
    content: str
    created_at: str

@dataclass
class Prompt:
    """Prompt model."""
    id: int
    name: str
    content: str
    version: int
    created_at: str

@dataclass
class Run:
    """Run model for tracking Claude responses."""
    id: int
    prompt_id: int
    question_id: int
    prompt_text: str
    response: str
    created_at: str
    accuracy: Optional[int] = None
    source_attribution: Optional[int] = None
    hallucination_rate: Optional[int] = None
    relevance: Optional[int] = None
    helpfulness: Optional[int] = None
    notes: Optional[str] = None

@dataclass
class RunComparison:
    """Comparison between two runs."""
    id: int
    run_id: int
    compared_to_run_id: int
    comparison: str  # 'better', 'worse', 'same'
    notes: Optional[str]
    created_at: str

@dataclass
class TestRun:
    """Test run model for tracking a batch of tests."""
    id: int
    prompt_id: int
    name: str
    description: Optional[str]
    model: str
    created_at: str

@dataclass
class RunResult:
    """Result model for an individual question response within a run."""
    id: int
    run_id: int
    question_id: int
    response: str
    created_at: str

def add_source(cursor: sqlite3.Cursor, question_id: int, source: dict) -> None:
    """Add a source to the database.
    
    Args:
        cursor: Database cursor
        question_id: ID of the question
        source: Source dictionary containing title and content
    """
    # Convert the content list to a JSON string
    content_json = json.dumps(source["content"])
    
    cursor.execute(
        """
        INSERT INTO sources (question_id, title, content)
        VALUES (?, ?, ?)
        """,
        (question_id, source["title"], content_json)
    )

def get_sources_for_question(question_id: int) -> List[Dict[str, Any]]:
    """Get sources for a question.
    
    Args:
        question_id: ID of the question
        
    Returns:
        List of source dictionaries with title and content
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT title, content
            FROM sources
            WHERE question_id = ?
            """,
            (question_id,)
        )
        
        sources = []
        for row in cursor.fetchall():
            title, content_json = row
            content = json.loads(content_json)
            sources.append({
                "title": title,
                "content": content
            })
        
        return sources

def add_question(name: str, content: str, sources: List[Dict[str, Any]]) -> int:
    """Add a question to the database.
    
    Args:
        name: Question name
        content: Question content
        sources: List of source dictionaries with title and content
        
    Returns:
        ID of the new question
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO questions (name, content)
            VALUES (?, ?)
            """,
            (name, content)
        )
        
        question_id = cursor.lastrowid
        
        # Add sources
        for source in sources:
            add_source(cursor, question_id, source)
        
        conn.commit()
        return question_id

def get_questions() -> list[Question]:
    """Get all questions with their sources from the database."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT q.id, q.name, q.content, q.created_at
            FROM questions q
            ORDER BY q.created_at DESC
            """
        )
        questions = []
        for row in c.fetchall():
            question = Question(
                id=row[0],
                name=row[1],
                content=row[2],
                created_at=row[3]
            )
            questions.append(question)
        return questions

def get_question(question_id: int) -> Question:
    """Get a single question by ID with its sources."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id, name, content, created_at
            FROM questions
            WHERE id = ?
            """,
            (question_id,)
        )
        row = c.fetchone()
        if row:
            return Question(
                id=row[0],
                name=row[1],
                content=row[2],
                created_at=row[3]
            )
        return None

def add_rating(
    question_id: int,
    accuracy: int,
    source_attribution: int,
    hallucination_rate: int,
    relevance: int,
    helpfulness: int,
    notes: str = "",
) -> None:
    """Add a rating for a question."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO ratings (
                question_id, accuracy, source_attribution,
                hallucination_rate, relevance, helpfulness, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (question_id, accuracy, source_attribution,
              hallucination_rate, relevance, helpfulness, notes))
        
        conn.commit()

def get_ratings(question_id: int) -> List[tuple]:
    """Get all ratings for a question."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            SELECT accuracy, source_attribution, hallucination_rate,
                   relevance, helpfulness, notes
            FROM ratings
            WHERE question_id = ?
        ''', (question_id,))
        
        ratings = c.fetchall()
        return ratings

def add_prompt(name: str, content: str) -> int:
    """Add a new prompt version."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Get the current version for this prompt name
        c.execute('SELECT MAX(version) FROM prompts WHERE name = ?', (name,))
        current_version = c.fetchone()[0] or 0
        
        # Add new version
        c.execute('''
            INSERT INTO prompts (name, content, version)
            VALUES (?, ?, ?)
        ''', (name, content, current_version + 1))
        
        prompt_id = c.lastrowid
        conn.commit()
        return prompt_id

def get_prompts() -> List[Prompt]:
    """Get all prompts."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            SELECT id, name, content, version, created_at
            FROM prompts
            ORDER BY name, version DESC
        ''')
        
        prompts = [
            Prompt(id=row[0], name=row[1], content=row[2], version=row[3], created_at=row[4])
            for row in c.fetchall()
        ]
        
        return prompts

def get_prompt(prompt_id: int) -> Optional[Prompt]:
    """Get a specific prompt by ID."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('''
            SELECT id, name, content, version, created_at
            FROM prompts
            WHERE id = ?
        ''', (prompt_id,))
        
        row = c.fetchone()
        
        if row:
            return Prompt(id=row[0], name=row[1], content=row[2], version=row[3], created_at=row[4])
        return None

def add_run(
    prompt_id: int,
    question_id: int,
    response: str,
    model: str,
    accuracy: Optional[int] = None,
    source_attribution: Optional[int] = None,
    hallucination_rate: Optional[int] = None,
    relevance: Optional[int] = None,
    helpfulness: Optional[int] = None,
    notes: Optional[str] = None,
) -> int:
    """Add a new run."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Get the prompt content to use as prompt_text
        c.execute('SELECT content FROM prompts WHERE id = ?', (prompt_id,))
        prompt_text = c.fetchone()[0]
        
        c.execute('''
            INSERT INTO runs (
                prompt_id, question_id, prompt_text, response,
                accuracy, source_attribution, hallucination_rate,
                relevance, helpfulness, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            prompt_id, question_id, prompt_text, response,
            accuracy, source_attribution, hallucination_rate,
            relevance, helpfulness, notes
        ))
        
        run_id = c.lastrowid
        conn.commit()
        return run_id

def get_runs(prompt_id: Optional[int] = None) -> list[Run]:
    """Get all runs, optionally filtered by prompt_id."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        query = """
            SELECT id, prompt_id, question_id, prompt_text, response,
                   accuracy, source_attribution, hallucination_rate,
                   relevance, helpfulness, notes, created_at
            FROM runs
        """
        params = []
        
        if prompt_id is not None:
            query += " WHERE prompt_id = ?"
            params.append(prompt_id)
        
        query += " ORDER BY created_at DESC"
        
        c.execute(query, params)
        return [
            Run(
                id=row[0],
                prompt_id=row[1],
                question_id=row[2],
                prompt_text=row[3],
                response=row[4],
                accuracy=row[5],
                source_attribution=row[6],
                hallucination_rate=row[7],
                relevance=row[8],
                helpfulness=row[9],
                notes=row[10],
                created_at=row[11]
            )
            for row in c.fetchall()
        ]

def get_sources() -> list[Source]:
    """Get all sources from the database."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id, title, content, created_at
            FROM sources
            ORDER BY created_at DESC
            """
        )
        return [
            Source(
                id=row[0],
                title=row[1],
                content=row[2],
                created_at=row[3]
            )
            for row in c.fetchall()
        ]

def update_run_rating(
    run_id: int,
    accuracy: int,
    source_attribution: int,
    hallucination_rate: int,
    relevance: int,
    helpfulness: int,
    notes: str,
) -> None:
    """Update a run with ratings."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE runs
            SET accuracy = ?,
                source_attribution = ?,
                hallucination_rate = ?,
                relevance = ?,
                helpfulness = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                accuracy,
                source_attribution,
                hallucination_rate,
                relevance,
                helpfulness,
                notes,
                run_id
            )
        )
        conn.commit()

def add_run_comparison(
    run_id: int,
    compared_to_run_id: int,
    comparison: str,
    notes: Optional[str] = None
) -> int:
    """Add a comparison between two runs."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO run_comparisons (run_id, compared_to_run_id, comparison, notes)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, compared_to_run_id, comparison, notes)
        )
        conn.commit()
        return c.lastrowid

def get_run_comparisons(run_id: Optional[int] = None) -> list[RunComparison]:
    """Get all run comparisons, optionally filtered by run_id."""
    with get_db_connection() as conn:
        c = conn.cursor()
        
        query = """
            SELECT id, run_id, compared_to_run_id, comparison, notes, created_at
            FROM run_comparisons
        """
        params = []
        
        if run_id is not None:
            query += " WHERE run_id = ? OR compared_to_run_id = ?"
            params.extend([run_id, run_id])
        
        query += " ORDER BY created_at DESC"
        
        c.execute(query, params)
        return [
            RunComparison(
                id=row[0],
                run_id=row[1],
                compared_to_run_id=row[2],
                comparison=row[3],
                notes=row[4],
                created_at=row[5]
            )
            for row in c.fetchall()
        ]

def create_test_run(
    prompt_id: int,
    name: str,
    model: str,
    description: Optional[str] = None,
) -> int:
    """Create a new test run."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO test_runs (prompt_id, name, description, model)
            VALUES (?, ?, ?, ?)
        ''', (prompt_id, name, description, model))
        run_id = c.lastrowid
        conn.commit()
        return run_id

def add_run_result(
    run_id: int,
    question_id: int,
    response: str,
) -> int:
    """Add a result for a specific question in a test run."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO run_results (run_id, question_id, response)
            VALUES (?, ?, ?)
        ''', (run_id, question_id, response))
        result_id = c.lastrowid
        conn.commit()
        return result_id

def get_test_runs() -> list[TestRun]:
    """Get all test runs."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, prompt_id, name, description, model, created_at
            FROM test_runs
            ORDER BY created_at DESC
        ''')
        return [
            TestRun(
                id=row[0],
                prompt_id=row[1],
                name=row[2],
                description=row[3],
                model=row[4],
                created_at=row[5]
            )
            for row in c.fetchall()
        ]

def get_run_results(run_id: int) -> list[RunResult]:
    """Get all results for a specific test run."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, run_id, question_id, response, created_at
            FROM run_results
            WHERE run_id = ?
            ORDER BY created_at ASC
        ''', (run_id,))
        return [
            RunResult(
                id=row[0],
                run_id=row[1],
                question_id=row[2],
                response=row[3],
                created_at=row[4]
            )
            for row in c.fetchall()
        ]

def update_run_result(
    result_id: int,
    accuracy: int,
    source_attribution: int,
    hallucination_rate: int,
    relevance: int,
    helpfulness: int,
    notes: str,
) -> None:
    """Update a run result with ratings."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE run_results
            SET accuracy = ?,
                source_attribution = ?,
                hallucination_rate = ?,
                relevance = ?,
                helpfulness = ?,
                notes = ?
            WHERE id = ?
        ''', (
            accuracy,
            source_attribution,
            hallucination_rate,
            relevance,
            helpfulness,
            notes,
            result_id
        ))
        conn.commit()

def delete_question(question_id: int) -> None:
    """Delete a question and its associated sources from the database.
    
    Args:
        question_id: ID of the question to delete
    """
    with get_db_connection() as conn:
        c = conn.cursor()
        # First delete associated sources
        c.execute('DELETE FROM sources WHERE question_id = ?', (question_id,))
        # Then delete the question
        c.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        conn.commit()

def delete_prompt(prompt_id: int) -> None:
    """Delete a prompt from the database.
    
    Args:
        prompt_id: ID of the prompt to delete
    """
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM prompts WHERE id = ?', (prompt_id,))
        conn.commit() 