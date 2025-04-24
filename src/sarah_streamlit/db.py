"""Database operations for the testing application using Supabase."""
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://ivdqeruhniskfrgwllgi.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2ZHFlcnVobmlza2ZyZ3dsbGdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNzQ4ODMsImV4cCI6MjA1NDg1MDg4M30.i9n955aGnm01HhpaAX7oQ_HrMfW7G3F0FoF5H56nvOc')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    """Initialize the database schema."""
    # Tables are managed through Supabase dashboard or migrations
    pass

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

def add_source(question_id: int, source: dict) -> None:
    """Add a source to the database.
    
    Args:
        question_id: ID of the question
        source: Source dictionary containing title and content
    """
    content_json = json.dumps(source["content"])
    
    data = {
        'question_id': question_id,
        'title': source["title"],
        'content': content_json
    }
    
    supabase.table('sources').insert(data).execute()

def get_sources_for_question(question_id: int) -> List[Dict[str, Any]]:
    """Get sources for a question.
    
    Args:
        question_id: ID of the question
        
    Returns:
        List of source dictionaries with title and content
    """
    response = supabase.table('sources').select('title,content').eq('question_id', question_id).execute()
    
    sources = []
    for row in response.data:
        content = json.loads(row['content'])
        sources.append({
            "title": row['title'],
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
        ID of the newly created question
    """
    data = {
        'name': name,
        'content': content
    }
    
    response = supabase.table('questions').insert(data).execute()
    question_id = response.data[0]['id']
    
    for source in sources:
        add_source(question_id, source)
    
    return question_id

def get_questions() -> list[Question]:
    """Get all questions from the database.
    
    Returns:
        List of Question objects
    """
    response = supabase.table('questions').select('*').execute()
    
    return [
        Question(
            id=row['id'],
            name=row['name'],
            content=row['content'],
            created_at=row['created_at']
        )
        for row in response.data
    ]

def get_question(question_id: int) -> Question:
    """Get a specific question from the database.
    
    Args:
        question_id: ID of the question
        
    Returns:
        Question object
    """
    response = supabase.table('questions').select('*').eq('id', question_id).single().execute()
    row = response.data
    
    return Question(
        id=row['id'],
        name=row['name'],
        content=row['content'],
        created_at=row['created_at']
    )

def add_prompt(name: str, content: str) -> int:
    """Add a prompt to the database.
    
    Args:
        name: Prompt name
        content: Prompt content
        
    Returns:
        ID of the newly created prompt
    """
    # Get the latest version for this prompt name
    response = supabase.table('prompts').select('version').eq('name', name).order('version', desc=True).limit(
        1).execute()
    latest_version = response.data[0]['version'] if response.data else 0
    
    data = {
        'name': name,
        'content': content,
        'version': latest_version + 1
    }
    
    response = supabase.table('prompts').insert(data).execute()
    return response.data[0]['id']

def get_prompts() -> List[Prompt]:
    """Get all prompts from the database.
    
    Returns:
        List of Prompt objects
    """
    response = supabase.table('prompts').select('*').execute()
    
    return [
        Prompt(
            id=row['id'],
            name=row['name'],
            content=row['content'],
            version=row['version'],
            created_at=row['created_at']
        )
        for row in response.data
    ]

def get_prompt(prompt_id: int) -> Optional[Prompt]:
    """Get a specific prompt from the database.
    
    Args:
        prompt_id: ID of the prompt
        
    Returns:
        Prompt object or None if not found
    """
    response = supabase.table('prompts').select('*').eq('id', prompt_id).single().execute()
    
    if not response.data:
        return None
        
    row = response.data
    return Prompt(
        id=row['id'],
        name=row['name'],
        content=row['content'],
        version=row['version'],
        created_at=row['created_at']
    )

def create_test_run(
    prompt_id: int,
    name: str,
    model: str,
    description: Optional[str] = None,
) -> int:
    """Create a new test run.
    
    Args:
        prompt_id: ID of the prompt
        name: Name of the test run
        model: Model used for the test
        description: Optional description
        
    Returns:
        ID of the newly created test run
    """
    data = {
        'prompt_id': prompt_id,
        'name': name,
        'model': model,
        'description': description
    }
    
    response = supabase.table('test_runs').insert(data).execute()
    return response.data[0]['id']

def add_run_result(
    run_id: int,
    question_id: int,
    response: str,
) -> int:
    """Add a result for a specific question in a test run.
    
    Args:
        run_id: ID of the test run
        question_id: ID of the question
        response: Response text
        
    Returns:
        ID of the newly created run result
    """
    data = {
        'run_id': run_id,
        'question_id': question_id,
        'response': response
    }
    
    response = supabase.table('run_results').insert(data).execute()
    return response.data[0]['id']

def get_test_runs() -> list[TestRun]:
    """Get all test runs from the database, sorted from latest to oldest.
    
    Returns:
        List of TestRun objects
    """
    response = supabase.table('test_runs').select('*').order('created_at', desc=True).execute()
    
    return [
        TestRun(
            id=row['id'],
            prompt_id=row['prompt_id'],
            name=row['name'],
            description=row['description'],
            model=row['model'],
            created_at=row['created_at']
        )
        for row in response.data
    ]

def get_run_results(run_id: int) -> list[RunResult]:
    """Get all results for a specific test run.
    
    Args:
        run_id: ID of the test run
        
    Returns:
        List of RunResult objects
    """
    response = supabase.table('run_results').select('*').eq('run_id', run_id).execute()
    
    return [
        RunResult(
            id=row['id'],
            run_id=row['run_id'],
            question_id=row['question_id'],
            response=row['response'],
            created_at=row['created_at']
        )
        for row in response.data
    ]

def delete_question(question_id: int) -> None:
    """Delete a question and its associated sources.
    
    Args:
        question_id: ID of the question to delete
    """
    # Delete associated sources first
    supabase.table('sources').delete().eq('question_id', question_id).execute()
    # Delete the question
    supabase.table('questions').delete().eq('id', question_id).execute()

def delete_prompt(prompt_id: int) -> None:
    """Delete a prompt.
    
    Args:
        prompt_id: ID of the prompt to delete
    """
    supabase.table('prompts').delete().eq('id', prompt_id).execute()

def get_run_data_batch(run_id: int) -> dict:
    """Get all data related to a test run in a single batch.
    
    This function reduces the number of database queries by fetching
    the prompt, results, and related questions in a more efficient way.
    
    Args:
        run_id: ID of the test run
        
    Returns:
        Dictionary containing the prompt, results, and questions
    """
    # Get the run to get the prompt_id
    run_response = supabase.table('test_runs').select('*').eq('id', run_id).single().execute()
    if not run_response.data:
        return {"prompt": None, "results": [], "questions": {}}
    
    run = run_response.data
    prompt_id = run['prompt_id']
    
    # Get the prompt
    prompt_response = supabase.table('prompts').select('*').eq('id', prompt_id).single().execute()
    prompt = None
    if prompt_response.data:
        row = prompt_response.data
        prompt = Prompt(
            id=row['id'],
            name=row['name'],
            content=row['content'],
            version=row['version'],
            created_at=row['created_at']
        )
    
    # Get all results for this run
    results_response = supabase.table('run_results').select('*').eq('run_id', run_id).execute()
    results = [
        RunResult(
            id=row['id'],
            run_id=row['run_id'],
            question_id=row['question_id'],
            response=row['response'],
            created_at=row['created_at']
        )
        for row in results_response.data
    ]
    
    # Extract unique question IDs
    question_ids = list(set(result.question_id for result in results))
    
    # Get all questions in a single query if there are any
    questions = {}
    if question_ids:
        # Use 'in' filter to get all questions at once
        questions_response = supabase.table('questions').select('*').in_('id', question_ids).execute()
        questions = {
            row['id']: Question(
                id=row['id'],
                name=row['name'],
                content=row['content'],
                created_at=row['created_at']
            )
            for row in questions_response.data
        }
    
    return {
        "prompt": prompt,
        "results": results,
        "questions": questions
    } 