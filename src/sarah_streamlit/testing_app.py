"""
Testing application for evaluating AI responses.
"""
import sqlite3
import streamlit as st
from datetime import datetime
import json
from typing import List, Dict, Any
import os

from sarah_streamlit.chat import get_llm_client, Message, TextContent, ImageContent
from sarah_streamlit.cloud_storage import download_db_from_storage, upload_db_to_storage
from sarah_streamlit.db import (
    Question,
    Prompt,
    Run,
    TestRun,
    RunResult,
    add_question,
    add_rating,
    add_prompt,
    add_run,
    get_questions,
    get_ratings,
    get_prompts,
    get_prompt,
    get_runs,
    get_test_runs,
    create_test_run,
    add_run_result,
    get_run_results,
    init_db,
    get_db_connection,
    get_question,
    add_source,
    get_sources,
    get_sources_for_question,
    update_run_rating,
    update_run_result,
    add_run_comparison,
    get_run_comparisons,
    delete_question,
    delete_prompt,
)

# Cloud Storage configuration
BUCKET_NAME = os.getenv('BUCKET_NAME', 'sarah-testing-db')
DB_NAME = "sarah_testing.db"

def setup_initial_data():
    """Set up initial data in the database."""
    # Download existing database from Cloud Storage if available
    if os.getenv('CLOUD_RUN_SERVICE', ''):  # Only in Cloud Run
        download_db_from_storage(BUCKET_NAME, DB_NAME)
    
    # Initialize the database
    init_db()
    
    # Check if we already have questions
    questions = get_questions()
    if not questions:
        # Sample question 1
        question_text = "What are our company's policies regarding remote work and flexible hours?"
        question_name = "Remote Work Policy"
        sources = [
            {
                "title": "Company Remote Work Policy",
                "content": [
                    {
                        "type": "text",
                        "text": "[Page 1]\n1. Remote Work Guidelines\n\n"
                        "Our company supports flexible working arrangements including remote work options. "
                        "The following guidelines apply:\n"
                        "- Employees may work remotely up to 3 days per week with manager approval\n"
                        "- Core hours are 10am-3pm when all employees should be available\n"
                        "- Remote work arrangements must not impact team collaboration or productivity\n"
                        "- Employees must have reliable internet and a suitable home office setup\n"
                    },
                    {
                        "type": "text",
                        "text": "[Page 2]\n2. Flexible Hours Policy\n\n"
                        "We offer flexible working hours to help employees maintain work-life balance:\n"
                        "- Standard workday is 8 hours between 7am-7pm\n"
                        "- Must be present during core hours (10am-3pm)\n" 
                        "- Schedule changes require manager approval\n"
                        "- Overtime must be pre-approved"
                    }
                ]
            },
            {
                "title": "Employee Handbook - Work Arrangements",
                "content": [
                    {
                        "type": "text",
                        "text": "[Page 1]\nWork Arrangements and Scheduling\n\n"
                        "TheKey Support recognizes the importance of work-life balance and offers "
                        "various flexible working arrangements to accommodate our employees' needs "
                        "while ensuring business continuity and team collaboration.\n\n"
                        "Remote work privileges may be revoked if:\n"
                        "- Performance or productivity declines\n"
                        "- Communication becomes ineffective\n"
                        "- Core hours are not maintained\n"
                        "- Technical requirements are not met"
                    },
                    {
                        "type": "text",
                        "text": "[Page 2]\nTechnology Requirements\n\n"
                        "Remote workers must have:\n"
                        "- High-speed internet (minimum 50Mbps)\n"
                        "- Dedicated workspace\n"
                        "- Company-provided laptop\n"
                        "- Secure VPN connection\n"
                        "- Video conferencing capability"
                    }
                ]
            }
        ]
        
        # Add the question with sources
        add_question(
            name=question_name,
            content=question_text,
            sources=sources
        )

# Initialize the database
init_db()
setup_initial_data()

# Page configuration
st.set_page_config(
    page_title="Prompt Testing",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

def sync_db_to_storage():
    """Sync the database to Cloud Storage if running in Cloud Run."""
    if os.getenv('CLOUD_RUN_SERVICE', ''):
        upload_db_to_storage(BUCKET_NAME, DB_NAME)

def add_question_section():
    """Section for adding new questions."""
    st.header("Add Question")
    
    # Initialize session state for page counts if not exists
    if 'source_page_counts' not in st.session_state:
        st.session_state.source_page_counts = {i: 1 for i in range(10)}
    
    # Store source pages in session state
    if 'source_pages' not in st.session_state:
        st.session_state.source_pages = {i: {} for i in range(10)}
    
    # Store source names in session state
    if 'source_names' not in st.session_state:
        st.session_state.source_names = {i: "" for i in range(10)}
    
    # Question details at the top
    question_name = st.text_input("Question Name", help="A short, descriptive name for the question")
    question_text = st.text_area("Question Text", height=100)
    
    # Sources section
    st.subheader("Sources")
    st.markdown("""
        Add up to 10 sources that should be referenced in the response.
        Each source can have multiple pages.
    """)
    
    sources = []
    for i in range(10):
        with st.expander(f"Source {i+1}", expanded=i == 0):
            # Source name input
            source_name = st.text_input(
                "Source Name",
                value=st.session_state.source_names.get(i, ""),
                key=f"source_name_{i}",
                placeholder="Enter source name (e.g., Remote Work Policy)"
            )
            st.session_state.source_names[i] = source_name
            
            source_pages = []
            
            # Get current number of pages for this source
            num_pages = st.session_state.source_page_counts[i]
            
            # Display existing pages
            for j in range(num_pages):
                # Load existing content from session state
                existing_content = st.session_state.source_pages[i].get(j, "")
                
                page_content = st.text_area(
                    f"Page {j+1}",
                    value=existing_content,
                    height=150,
                    key=f"source_{i}_page_{j+1}",
                    placeholder="Enter source content..."
                )
                
                # Save content to session state
                st.session_state.source_pages[i][j] = page_content
                
                if page_content:
                    source_pages.append({
                        "type": "text",
                        "text": f"[Page {j+1}]\n{page_content}"
                    })
            
            col1, col2 = st.columns(2)
            
            # Add Page button
            if num_pages < 10:  # Always show if under limit
                with col1:
                    if st.button(f"➕ Add Page to Source {i+1}", key=f"add_page_{i}"):
                        st.session_state.source_page_counts[i] += 1
                        st.rerun()
            
            # Remove Page button
            if num_pages > 1:  # Show if more than one page
                with col2:
                    if st.button(f"➖ Remove Last Page from Source {i+1}", key=f"remove_page_{i}"):
                        st.session_state.source_page_counts[i] -= 1
                        # Clean up the removed page's state
                        if num_pages - 1 in st.session_state.source_pages[i]:
                            del st.session_state.source_pages[i][num_pages - 1]
                        st.rerun()
            
            # Add source if it has content and a name
            if source_pages and source_name:
                sources.append({
                    "title": source_name,
                    "content": source_pages
                })
                
            # Show page counter
            if source_pages:
                st.caption(f"Pages: {len(source_pages)}/10")
    
    # Add Question button at the bottom
    if st.button("Add Question"):
        if not question_name:
            st.error("Please provide a question name")
            return
        if not question_text:
            st.error("Please provide question text")
            return
        if not sources:
            st.error("Please add at least one source with content")
            return
            
        try:
            # Add the question with sources
            add_question(
                name=question_name,
                content=question_text,
                sources=sources
            )
            
            # Sync to Cloud Storage
            sync_db_to_storage()
            
            # Reset form state
            st.session_state.source_page_counts = {i: 1 for i in range(10)}
            st.session_state.source_pages = {i: {} for i in range(10)}
            st.session_state.source_names = {i: "" for i in range(10)}
            
            st.success("Question added successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error adding question: {str(e)}")

def view_questions_section():
    """Section for viewing and rating questions."""
    st.header("View Questions")
    
    questions = get_questions()
    
    if not questions:
        st.info("No questions added yet. Go to 'Add Question' to create your first question.")
        return
    
    for question in questions:
        with st.expander(f"{question.name}"):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write("**Full Question:**")
                st.write(question.content)
            with col2:
                if st.button("🗑️ Delete", key=f"delete_question_{question.id}"):
                    if st.session_state.get(f"confirm_delete_question_{question.id}", False):
                        delete_question(question.id)
                        st.success("Question deleted!")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_question_{question.id}"] = True
                        st.warning("Click delete again to confirm.")
            
            st.write("**Sources:**")
            sources = get_sources_for_question(question.id)
            if sources:
                source_tabs = st.tabs([source["title"] for source in sources])
                for source_idx, (source_tab, source) in enumerate(zip(source_tabs, sources)):
                    with source_tab:
                        # Create tabs for each page in the source
                        pages = source["content"]  # Already a list of page dictionaries
                        st.caption(f"Total Pages: {len(pages)}")
                        
                        # Create tabs for pages
                        page_tabs = st.tabs([f"Page {j+1}" for j in range(len(pages))])
                        for page_idx, (tab, page) in enumerate(zip(page_tabs, pages)):
                            with tab:
                                st.text_area(
                                    "Content",
                                    value=page["text"],  # Each page is a dict with 'type' and 'text'
                                    height=150,
                                    disabled=True,
                                    key=f"view_source_{question.id}_{source_idx}_{page_idx}"
                                )
            else:
                st.info("No sources available")

def get_mock_response(question: str, sources: list[str]) -> str:
    """Generate a mock Claude response for testing."""
    return (
        f"Here is my response to your question about {question[:50]}...\n\n"
        "Based on the provided sources, I can offer the following analysis:\n\n"
        "1. Main Points:\n"
        "- First key point from the sources\n"
        "- Second key point from the sources\n"
        "- Third key point synthesized from multiple sources\n\n"
        "2. Supporting Evidence:\n"
        f"- From Source 1: {sources[0][:100] if sources else 'No source provided'}...\n"
        f"- From Source 2: {sources[1][:100] if len(sources) > 1 else 'No additional source'}...\n\n"
        "3. Conclusion:\n"
        "This analysis is based entirely on the provided sources. The information appears to be "
        "comprehensive, though there might be additional aspects not covered in the given materials."
    )

def main():
    """Main application entry point."""
    st.title("Question Testing Application")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Go to",
            ["Add Question", "View Questions", "Manage Prompts", "Prompt Testing"]
        )
    
    # Main content
    if page == "Add Question":
        add_question_section()
    elif page == "View Questions":
        view_questions_section()
    elif page == "Manage Prompts":
        manage_prompts_section()
    else:  # Prompt Testing
        prompt_testing_section()

def manage_prompts_section():
    """Section for managing prompts."""
    st.header("Manage Prompts")
    
    # Get existing prompts
    prompts = get_prompts()
    
    # Create new prompt section
    st.subheader("Create New Prompt")
    
    # Show existing prompts in a selectbox for reference
    existing_prompt = None
    if prompts:
        selected_prompt = st.selectbox(
            "Base on existing prompt",
            options=["None"] + [f"{p.name} (v{p.version})" for p in prompts],
            index=0
        )
        if selected_prompt != "None":
            existing_prompt = next(p for p in prompts if f"{p.name} (v{p.version})" == selected_prompt)
    
    # Prompt creation form
    with st.form("create_prompt"):
        prompt_name = st.text_input("Prompt Name")
        prompt_content = st.text_area(
            "Prompt Content",
            value=existing_prompt.content if existing_prompt else "",
            height=300,
            help="Use {question} and {sources} as placeholders for dynamic content"
        )
        
        if st.form_submit_button("Add Prompt"):
            if prompt_name and prompt_content:
                try:
                    add_prompt(prompt_name, prompt_content)
                    st.success(f"Added prompt: {prompt_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding prompt: {str(e)}")
    
    # View existing prompts
    if prompts:
        st.subheader("Existing Prompts")
        for prompt in prompts:
            with st.expander(f"{prompt.name} (v{prompt.version}) - {prompt.created_at}"):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.text_area(
                        "Content",
                        value=prompt.content,
                        height=200,
                        disabled=True,
                        key=f"prompt_{prompt.id}"
                    )
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_prompt_{prompt.id}"):
                        if st.session_state.get(f"confirm_delete_prompt_{prompt.id}", False):
                            delete_prompt(prompt.id)
                            st.success("Prompt deleted!")
                            st.rerun()
                        else:
                            st.session_state[f"confirm_delete_prompt_{prompt.id}"] = True
                            st.warning("Click delete again to confirm.")

def prompt_testing_section():
    """Section for managing prompts and running tests."""
    st.header("Prompt Testing")
    
    # Subsection navigation
    subsection = st.radio(
        "Section",
        ["Start Test", "View Runs", "Compare Runs", "Test History"],
        horizontal=True
    )
    
    if subsection == "Start Test":
        start_test_section()
    elif subsection == "View Runs":
        view_runs_section()
    elif subsection == "Compare Runs":
        compare_runs_section()
    else:
        test_history_section()

def start_test_section():
    """Section for starting new test runs."""
    st.subheader("Start New Test Run")
    
    try:
        # Get available prompts
        prompts = get_prompts()
        if not prompts:
            st.warning("No prompts available. Please create a prompt first in the 'Manage Prompts' section.")
            return
        
        # Select prompt
        selected_prompt = st.selectbox(
            "Select Prompt",
            options=prompts,
            format_func=lambda x: f"{x.name} (v{x.version})"
        )
        
        # Model selection
        st.subheader("Model Configuration")
        model_name = st.selectbox(
            "Select Model",
            options=["Claude 3.5 Sonnet", "Claude 3.5 Haiku"],
            help="Choose between Claude 3.5 Sonnet (most intelligent) or Haiku (fastest)"
        )
        
        # Parameter testing configuration
        st.subheader("Parameter Testing")
        test_type = st.radio(
            "Testing Mode",
            options=["Single Values", "Parameter Ranges"],
            help="Choose whether to test with single parameter values or explore ranges"
        )
        
        if test_type == "Single Values":
            col1, col2 = st.columns(2)
            with col1:
                temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
                top_p = st.slider("Top P", 0.0, 1.0, 0.9, 0.1)
            with col2:
                top_k = st.slider("Top K", 1, 100, 10)
            
            parameter_configs = [{
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k
            }]
        else:
            st.write("Define parameter ranges to test:")
            col1, col2 = st.columns(2)
            
            with col1:
                temp_range = st.slider("Temperature Range", 0.0, 1.0, (0.5, 0.9), 0.1)
                top_p_range = st.slider("Top P Range", 0.0, 1.0, (0.7, 1.0), 0.1)
                top_k_range = st.slider("Top K Range", 1, 100, (5, 20))
            
            with col2:
                num_points = st.number_input("Number of test points", min_value=2, max_value=10, value=3)
            
            # Generate parameter configurations
            parameter_configs = []
            for i in range(num_points):
                temp = temp_range[0] + (temp_range[1] - temp_range[0]) * i / (num_points - 1)
                top_p = top_p_range[0] + (top_p_range[1] - top_p_range[0]) * i / (num_points - 1)
                top_k = int(top_k_range[0] + (top_k_range[1] - top_k_range[0]) * i / (num_points - 1))
                parameter_configs.append({
                    "temperature": round(temp, 2),
                    "top_p": round(top_p, 2),
                    "top_k": top_k
                })
            
            # Show the test configurations
            st.write("Test configurations that will be run:")
            for i, config in enumerate(parameter_configs, 1):
                st.write(f"Test {i}: Temperature={config['temperature']}, Top P={config['top_p']}, Top K={config['top_k']}")
        
        # Test run details
        st.subheader("Test Run Details")
        run_name = st.text_input("Test Run Name", placeholder="e.g., Parameter Testing Run 1")
        run_description = st.text_area("Description", placeholder="Optional description of this test run")
        
        # Get questions
        questions = get_questions()
        if not questions:
            st.warning("No questions available. Please add questions first.")
            return
        
        # Question selection
        test_mode = st.radio(
            "Test Mode",
            options=["Single Question", "All Questions"],
            horizontal=True
        )
        
        if test_mode == "Single Question":
            selected_question = st.selectbox(
                "Select Question",
                options=questions,
                format_func=lambda x: x.content[:100] + "..."
            )
            questions_to_test = [selected_question] if selected_question else []
        else:
            questions_to_test = questions
        
        # Start test button
        if st.button("Start Test Run"):
            if not run_name:
                st.error("Please provide a name for the test run")
                return
            
            if not questions_to_test:
                st.error("No questions selected for testing")
                return
            
            try:
                # Create progress tracking
                progress_container = st.container()
                with progress_container:
                    st.write("Running tests...")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                total_tests = len(questions_to_test) * len(parameter_configs)
                test_counter = 0
                
                # Run tests for each parameter configuration
                for config_idx, param_config in enumerate(parameter_configs):
                    config_name = f"{run_name} (Config {config_idx + 1})"
                    if len(parameter_configs) == 1:
                        config_name = run_name
                    
                    # Create the test run for this configuration
                    run_id = create_test_run(
                        prompt_id=selected_prompt.id,
                        name=config_name,
                        description=f"{run_description}\nParameters: temp={param_config['temperature']}, top_p={param_config['top_p']}, top_k={param_config['top_k']}",
                        model=model_name
                    )
                    
                    # Initialize LLM client with this configuration
                    llm_client = get_llm_client(model=model_name)
                    
                    # Run tests for each question with current parameters
                    for question_idx, question in enumerate(questions_to_test):
                        try:
                            # Update status
                            test_counter += 1
                            progress = test_counter / total_tests
                            progress_bar.progress(progress)
                            status_text.write(
                                f"Config {config_idx + 1}/{len(parameter_configs)} - "
                                f"Question {question_idx + 1}/{len(questions_to_test)}: "
                                f"{question.content[:100]}..."
                            )
                            
                            # Get sources and prepare content blocks
                            sources = get_sources_for_question(question.id)
                            content_blocks = []
                            
                            # Add source documents
                            if sources:
                                for source in sources:
                                    # Source is already in the correct format with title and content list
                                    content_blocks.append({
                                        "type": "document",
                                        "source": {
                                            "type": "content",
                                            "content": source["content"]  # Already a list of page dictionaries
                                        },
                                        "title": source["title"],
                                        "citations": {"enabled": True}
                                    })
                            
                            # Add the formatted prompt
                            content_blocks.append({
                                "type": "text",
                                "text": selected_prompt.content.format(
                                    question=question.content,
                                    sources="\n\n".join(
                                        f"{source['title']}\n" + "\n".join(
                                            page["text"] for page in source["content"]
                                        )
                                        for source in sources
                                    )
                                )
                            })
                            
                            # Get response from Claude with current parameters
                            response = next(llm_client.send_message(
                                messages=[{"role": "user", "content": content_blocks}],
                                stream=False,
                                temperature=param_config["temperature"],
                                top_p=param_config["top_p"],
                                top_k=param_config["top_k"]
                            ))
                            
                            # Format and save the response
                            try:
                                # Use the process_claude_response function to handle citations consistently
                                formatted_text = process_claude_response(response)
                                
                                add_run_result(
                                    run_id=run_id,
                                    question_id=question.id,
                                    response=formatted_text.strip()
                                )
                            except Exception as e:
                                error_msg = f"Error processing response: {str(e)}"
                                st.error(error_msg)
                                add_run_result(
                                    run_id=run_id,
                                    question_id=question.id,
                                    response=f"Error: {error_msg}"
                                )
                        
                        except Exception as e:
                            st.error(f"Error processing question: {str(e)}")
                            continue
                
                # Clear status and show completion
                status_text.empty()
                st.success(f"Test run completed successfully!")
                
                # Add view button
                if st.button("View Results"):
                    st.session_state.page = "View Runs"
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error creating test run: {str(e)}")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

def display_result(result, col):
    """Display a test result with its sources."""
    # Create a visually distinct section for the model response
    col.markdown("---")
    col.markdown("### 🤖 Model Response")
    
    # Display the response directly as markdown to render citations properly
    col.markdown(result.response)
    
    col.markdown("---")
    
    # Display sources
    col.markdown("### Source Documents")
    sources = get_sources_for_question(result.question_id)
    if sources:
        for source in sources:
            col.markdown(f"**{source['title']}**")
            # Display each page of content
            for page in source['content']:
                col.markdown(page['text'])
            col.markdown("---")  # Add separator between sources
    else:
        col.write("No sources available")

def test_history_section():
    st.header("Test History")
    
    runs = get_test_runs()
    if not runs:
        st.write("No test runs available")
        return

    for run in runs:
        with st.expander(f"Run: {run.name} - {run.created_at}"):
            # Display prompt information
            prompt = get_prompt(run.prompt_id)
            if prompt:
                st.markdown(f"**Using Prompt:** {prompt.name} (v{prompt.version})")
                prompt_container = st.container()
                prompt_container.markdown("**Prompt Content:**")
                prompt_container.text_area(
                    "Content",
                    value=prompt.content,
                    height=200,
                    disabled=True,
                    key=f"prompt_history_{run.id}"
                )
            
            if run.description:
                st.write(f"Description: {run.description}")

            results = get_run_results(run.id)
            if not results:
                st.write("No results available")
                continue

            for result in results:
                question = get_question(result.question_id)
                st.markdown("---")  # Visual separator
                st.markdown(f"**Question:** {question.content}")
                display_result(result, st)

def export_test_run_to_csv(run_id: int) -> str:
    """Export a test run's results to CSV format.
    
    Args:
        run_id: ID of the test run
        
    Returns:
        CSV string containing the test results
    """
    import csv
    import io
    
    # Get run details
    run = next((run for run in get_test_runs() if run.id == run_id), None)
    if not run:
        raise ValueError(f"Test run {run_id} not found")
    
    # Get prompt details
    prompt = get_prompt(run.prompt_id)
    if not prompt:
        raise ValueError(f"Prompt {run.prompt_id} not found")
    
    # Get results
    results = get_run_results(run_id)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        "Test Run Name",
        "Test Run Description",
        "Model",
        "Prompt Name",
        "Prompt Version",
        "Prompt Content",
        "Question",
        "Response",
        "Created At"
    ])
    
    # Write data
    for result in results:
        question = get_question(result.question_id)
        if not question:
            continue
            
        writer.writerow([
            run.name,
            run.description or "",
            run.model,
            prompt.name,
            prompt.version,
            prompt.content,
            question.content,
            result.response,
            result.created_at
        ])
    
    return output.getvalue()

def view_runs_section():
    """Section for viewing and rating questions."""
    st.header("View Test Runs")
    
    runs = get_test_runs()
    if not runs:
        st.write("No test runs available")
        return

    for run in runs:
        with st.expander(f"Run: {run.name} - {run.created_at}"):
            # Add export button at the top
            if st.button("📥 Export as CSV", key=f"export_run_{run.id}"):
                try:
                    csv_data = export_test_run_to_csv(run.id)
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"test_run_{run.name}_{run.created_at}.csv",
                        mime="text/csv",
                        key=f"download_run_{run.id}"
                    )
                except Exception as e:
                    st.error(f"Error exporting test run: {str(e)}")
            
            # Display prompt information
            prompt = get_prompt(run.prompt_id)
            if prompt:
                st.markdown(f"**Using Prompt:** {prompt.name} (v{prompt.version})")
                prompt_container = st.container()
                prompt_container.markdown("**Prompt Content:**")
                prompt_container.text_area(
                    "Content",
                    value=prompt.content,
                    height=200,
                    disabled=True,
                    key=f"prompt_view_{run.id}"
                )
            else:
                st.warning("⚠️ The prompt used in this run no longer exists.")
            
            if run.description:
                st.write(f"Description: {run.description}")

            results = get_run_results(run.id)
            if not results:
                st.write("No results available")
                continue

            # Group results by question
            questions = {}
            for result in results:
                if result.question_id not in questions:
                    questions[result.question_id] = []
                questions[result.question_id].append(result)

            # Display results grouped by question
            for question_id, question_results in questions.items():
                question = get_question(question_id)
                st.markdown("---")  # Visual separator
                
                if question:
                    st.markdown(f"**Question:** {question.content}")
                else:
                    st.warning(f"⚠️ Question (ID: {question_id}) no longer exists in the database")
                    continue
                
                # If there are multiple results (parameter range testing)
                if len(question_results) > 1:
                    st.markdown("### Parameter Configurations")
                    tabs = st.tabs([f"Config {i+1}" for i in range(len(question_results))])
                    for i, (tab, result) in enumerate(zip(tabs, question_results)):
                        with tab:
                            # Extract parameters from run description
                            params = {}
                            if result.run_id == run.id and run.description:
                                param_line = [line for line in run.description.split('\n') if 'Parameters:' in line]
                                if param_line:
                                    params_str = param_line[0].split('Parameters:')[1].strip()
                                    params = dict(param.split('=') for param in params_str.split(', '))
                            
                            # Display parameters if available
                            if params:
                                st.markdown("**Parameters:**")
                                for param, value in params.items():
                                    st.write(f"- {param.strip()}: {value.strip()}")
                            
                            # Display the response
                            display_result(result, st)
                else:
                    # Single result display
                    display_result(question_results[0], st)

def compare_runs_section():
    st.header("Compare Test Runs")
    
    runs = get_test_runs()
    if len(runs) < 2:
        st.write("Need at least 2 test runs to compare")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        run1 = st.selectbox(
            "Select first run",
            options=runs,
            format_func=lambda x: f"{x.name} ({x.created_at})",
            key="run1"
        )
        if run1:
            prompt1 = get_prompt(run1.prompt_id)
            if prompt1:
                st.markdown(f"**Using Prompt:** {prompt1.name} (v{prompt1.version})")
                prompt_container = st.container()
                prompt_container.markdown("**Prompt Content:**")
                prompt_container.text_area(
                    "Content",
                    value=prompt1.content,
                    height=200,
                    disabled=True,
                    key=f"prompt_compare1_{run1.id}"
                )
    
    with col2:
        # Filter out the first selected run from options for the second dropdown
        remaining_runs = [run for run in runs if run != run1]
        run2 = st.selectbox(
            "Select second run",
            options=remaining_runs,
            format_func=lambda x: f"{x.name} ({x.created_at})",
            key="run2"
        )
        if run2:
            prompt2 = get_prompt(run2.prompt_id)
            if prompt2:
                st.markdown(f"**Using Prompt:** {prompt2.name} (v{prompt2.version})")
                prompt_container = st.container()
                prompt_container.markdown("**Prompt Content:**")
                prompt_container.text_area(
                    "Content",
                    value=prompt2.content,
                    height=200,
                    disabled=True,
                    key=f"prompt_compare2_{run2.id}"
                )

    if run1 and run2:
        results1 = get_run_results(run1.id)
        results2 = get_run_results(run2.id)

        if not results1 or not results2:
            st.write("One or both runs have no results")
            return

        # Group results by question for comparison
        questions = {}
        for result in results1:
            questions[result.question_id] = {"run1": result}
        for result in results2:
            if result.question_id in questions:
                questions[result.question_id]["run2"] = result

        for question_id, results in questions.items():
            question = get_question(question_id)
            if not question:
                st.warning(f"Could not find question with ID {question_id}")
                continue
                
            st.markdown("---")  # Visual separator
            st.markdown(f"**Question:** {question.content}")
            
            col1, col2 = st.columns(2)
            
            if "run1" in results:
                with col1:
                    st.markdown(f"**{run1.name}**")
                    display_result(results["run1"], col1)
            
            if "run2" in results:
                with col2:
                    st.markdown(f"**{run2.name}**")
                    display_result(results["run2"], col2)

def prepare_content_blocks(prompt: str, sources: List[Dict[str, Any]]) -> list:
    """Prepare content blocks with sources and prompt for Claude API.
    
    Args:
        prompt: The prompt text
        sources: List of source dictionaries with title and content
        
    Returns:
        List of content blocks formatted for Claude API
    """
    content_blocks = []
    
    # Add sources as documents
    for source in sources:
        try:
            # Create document block with pages from source
            doc_block = {
                "type": "document",
                "source": {
                    "type": "content",
                    "content": source["content"]  # Already in correct format with pages
                },
                "title": source["title"],
                "context": f"Document from source materials: {source['title']}",
                "citations": {"enabled": True}
            }
            content_blocks.append(doc_block)
            
        except (KeyError, TypeError) as e:
            # Handle case where source doesn't have expected structure
            st.error(f"Error processing source: {str(e)}")
            continue
    
    # Add the prompt text
    content_blocks.append({
        "type": "text",
        "text": prompt
    })
    
    return content_blocks

def process_claude_response(response) -> str:
    """Process Claude's response with citations into markdown with Harvard references.
    
    Args:
        response: Response from Claude with citations
        
    Returns:
        Formatted markdown text with Harvard citations and references section
    """
    # Get content blocks from response
    content_blocks = []
    if hasattr(response, 'content'):
        content_blocks = response.content
    elif isinstance(response, dict) and 'content' in response:
        content_blocks = response['content']
    else:
        return str(response)
    
    # Track all citations and references
    references = {}
    formatted_text = ""
    citation_counter = 1
    
    # Process each content block
    for block in content_blocks:
        # Get text and citations from block
        if isinstance(block, dict):
            text = block.get('text', '')
            citations = block.get('citations', [])
        else:
            text = getattr(block, 'text', str(block))
            citations = getattr(block, 'citations', [])
        
        if not citations:
            formatted_text += text
            continue
        
        # Sort citations by position (in reverse order to maintain text indices)
        sorted_citations = sorted(
            citations,
            key=lambda x: (
                getattr(x, 'end_char_index', None) or 
                getattr(x, 'end_page_number', None) or 
                getattr(x, 'end_block_index', None) or 
                float('inf')
            ),
            reverse=True
        )
        
        # Process each citation
        current_text = text
        for citation in sorted_citations:
            # Get citation details
            if isinstance(citation, dict):
                doc_title = citation.get('document_title', f'Source {citation_counter}')
                cited_text = citation.get('cited_text', '').strip()
                citation_type = citation.get('type', 'unknown')
                page_number = citation.get('start_page_number', None)
            else:
                doc_title = getattr(citation, 'document_title', f'Source {citation_counter}')
                cited_text = getattr(citation, 'cited_text', '').strip()
                citation_type = getattr(citation, 'type', 'unknown')
                page_number = getattr(citation, 'start_page_number', None)
            
            # Clean up cited text
            cited_text = cited_text.replace('\u0002', '').strip()
            
            # Extract page number from cited text if present
            if cited_text.startswith('[Page'):
                page_match = cited_text.split(']')[0].replace('[Page ', '')
                if not page_number:  # Only use if we don't have a page number from metadata
                    page_number = page_match
                cited_text = cited_text.split('\n', 2)[-1].strip()
            
            # Add to references if not already present
            ref_key = f"{doc_title}:{cited_text}"
            if ref_key not in references:
                references[ref_key] = {
                    'number': citation_counter,
                    'title': doc_title,
                    'cited_text': cited_text,
                    'type': citation_type,
                    'page_number': page_number
                }
                citation_counter += 1
            
            # Insert citation number at the end of the relevant text
            citation_text = f" [{references[ref_key]['number']}]"
            
            # Handle different citation types
            if citation_type == 'char_location':
                if isinstance(citation, dict):
                    end_idx = citation.get('end_char_index', len(current_text))
                else:
                    end_idx = getattr(citation, 'end_char_index', len(current_text))
            elif citation_type == 'page_location':
                end_idx = len(current_text)  # Append to end for page citations
            elif citation_type == 'content_block_location':
                # Find the end of the cited text in the current text
                if cited_text in current_text:
                    end_idx = current_text.find(cited_text) + len(cited_text)
                else:
                    end_idx = len(current_text)  # Default to end if text not found
            else:
                end_idx = len(current_text)  # Default to end of text
            
            # Insert citation number
            current_text = current_text[:end_idx] + citation_text + current_text[end_idx:]
        
        formatted_text += current_text
    
    # Add references section if there are any citations
    if references:
        formatted_text += "\n\n**References**\n\n"
        for ref_key, ref in sorted(references.items(), key=lambda x: x[1]['number']):
            # Format the reference entry
            ref_text = f"[{ref['number']}] {ref['title']}"
            
            if ref['cited_text']:
                # Clean up and format the cited text
                cited_text = ref['cited_text']
                # Clean up newlines and extra spaces
                cited_text = ' '.join(cited_text.split())
                # Truncate long citations
                if len(cited_text) > 150:
                    cited_text = cited_text[:147] + "..."
                ref_text += f": \"{cited_text}\""
            
            # Add page number if available
            if ref['page_number']:
                ref_text += f" (Page {ref['page_number']})"
            
            formatted_text += f"{ref_text}\n\n"
    
    return formatted_text

if __name__ == "__main__":
    main() 