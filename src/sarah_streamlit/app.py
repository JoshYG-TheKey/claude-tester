"""
Sarah Streamlit Chat Application with Claude integration.
"""
import os
from typing import Dict, List, Optional, Any

import streamlit as st

from sarah_streamlit.chat import Message, TextContent, ImageContent, get_llm_client
from sarah_streamlit.db import (
    get_prompts,
    get_questions,
    get_sources_for_question,
    get_question,
)

# Page configuration
st.set_page_config(
    page_title="Sarah Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Available Claude models and their regions
CLAUDE_MODELS = {
    "Claude 3.7 Sonnet": {
        "id": "claude-3-7-sonnet-20250219",
        "max_tokens": 8192,

    },
    "Claude 3.5 Sonnet": {
        "id": "claude-3-5-sonnet-20241022",
        "regions": ["us-east5", "europe-west1"],
        "max_tokens": 8192,
        "description": "Our most intelligent model - Highest level of intelligence and capability"
    },
    "Claude 3.5 Haiku": {
        "id": "claude-3-5-haiku-20241022",
        "regions": ["us-east5", "europe-west1"],
        "max_tokens": 8192,
        "description": "Our fastest model - Intelligence at blazing speeds"
    }
}

def initialize_session_state() -> None:
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "llm_model" not in st.session_state:
        st.session_state.llm_model = CLAUDE_MODELS["Claude 3.5 Sonnet"]["id"]
    if "region" not in st.session_state:
        st.session_state.region = "europe-west1"
    if "selected_prompt" not in st.session_state:
        st.session_state.selected_prompt = None
    if "current_sources" not in st.session_state:
        st.session_state.current_sources = []

def display_chat_history() -> None:
    """Display chat history from session state."""
    for message in st.session_state.messages:
        with st.chat_message(message.role):
            if isinstance(message.content, str):
                st.markdown(message.content)
            else:
                for content in message.content:
                    if isinstance(content, ImageContent):
                        st.image(content.url)
                    elif isinstance(content, TextContent):
                        st.markdown(content.text)
                    elif isinstance(content, dict) and content.get("type") == "document":
                        st.markdown(f"**Source:** {content.get('title', 'Untitled')}")
                        st.markdown(content["source"]["data"])

def setup_sidebar() -> None:
    """Setup the sidebar with model selection and configuration."""
    with st.sidebar:
        st.header("Configuration")
        
        # Model selection
        selected_model_name = st.selectbox(
            "Select Claude Model",
            options=list(CLAUDE_MODELS.keys()),
            index=0,
        )
        selected_model = CLAUDE_MODELS[selected_model_name]
        st.session_state.llm_model = selected_model["id"]
        
        # Region selection
        st.session_state.region = st.selectbox(
            "Vertex AI Region",
            options=selected_model["regions"],
            index=1,  # Default to europe-west1
            help="Region where Claude is deployed",
        )
        
        # Prompt selection
        st.subheader("Prompt Selection")
        prompts = get_prompts()
        if prompts:
            selected_prompt = st.selectbox(
                "Select Prompt",
                options=prompts,
                format_func=lambda x: f"{x.name} (v{x.version})",
                key="prompt_selector"
            )
            if selected_prompt:
                st.session_state.selected_prompt = selected_prompt
                st.markdown("**Prompt Content:**")
                st.text_area(
                    "",
                    value=selected_prompt.content,
                    height=200,
                    disabled=True
                )
        else:
            st.warning("No prompts available. Please create prompts in the testing application.")
        
        # Question bank
        st.subheader("Question Bank")
        questions = get_questions()
        if questions:
            selected_question = st.selectbox(
                "Select Question",
                options=questions,
                format_func=lambda x: x.content[:100] + "...",
                key="question_selector"
            )
            if selected_question and st.button("Use Selected Question"):
                # Add the question to the chat
                user_message = Message(role="user", content=selected_question.content)
                st.session_state.messages.append(user_message)
                # Store the sources for this question
                st.session_state.current_sources = get_sources_for_question(selected_question.id)
                st.rerun()
        
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.session_state.current_sources = []
            st.rerun()

def prepare_content_blocks(prompt: str, sources: list) -> list:
    """Prepare content blocks with sources and prompt."""
    content_blocks = []
    
    # Add sources as documents
    for idx, source in enumerate(sources):
        content_blocks.append({
            "type": "document",
            "source": {
                "type": "text",
                "media_type": "text/plain",
                "data": source.content
            },
            "title": f"Source {idx + 1}",
            "citations": {"enabled": True}
        })
    
    # Add the prompt text
    content_blocks.append({
        "type": "text",
        "text": prompt
    })
    
    return content_blocks

def format_response_text(text: str, citations: List[Dict[str, Any]]) -> str:
    """Format text with citations in Harvard style.
    
    Args:
        text: The text to format
        citations: List of citation objects
        
    Returns:
        Formatted text with citations
    """
    if not citations:
        return text
        
    # Sort citations by position (in reverse order to maintain indices)
    sorted_citations = sorted(
        citations,
        key=lambda x: x.get('start_char_index', 0) if x.get('type') == 'char_location' else 0,
        reverse=True
    )
    
    # Apply citations
    formatted_text = text
    for citation in sorted_citations:
        doc_idx = citation.get('document_index', 0)
        doc_title = citation.get('document_title', f'Source {doc_idx + 1}')
        
        # Format citation marker based on citation type
        if citation.get('type') == 'char_location':
            citation_marker = f'[{doc_title}]'
        elif citation.get('type') == 'page_location':
            page_start = citation.get('page_number', 1)
            page_end = citation.get('end_page', page_start)
            citation_marker = f'[{doc_title}, p.{page_start}{"" if page_start == page_end else f"-{page_end}"}]'
        else:
            citation_marker = f'[{doc_title}]'
        
        # Insert citation marker at the appropriate position
        if citation.get('type') == 'char_location':
            end_idx = citation.get('end_char_index', len(formatted_text))
            formatted_text = (
                formatted_text[:end_idx] +
                f" {citation_marker}" +
                formatted_text[end_idx:]
            )
    
    # Add references section
    formatted_text += "\n\n**References:**\n"
    cited_docs = {}
    for citation in citations:
        doc_idx = citation.get('document_index', 0)
        if doc_idx not in cited_docs:
            doc_title = citation.get('document_title', f'Source {doc_idx + 1}')
            cited_text = citation.get('cited_text', '').strip()
            cited_docs[doc_idx] = {
                'title': doc_title,
                'text': cited_text
            }
    
    # Format references in Harvard style
    for doc_idx, doc in sorted(cited_docs.items()):
        formatted_text += f"\n{doc['title']}: \"{doc['text']}\""
    
    return formatted_text

def handle_streaming_response(response_stream, has_sources: bool) -> str:
    """Handle streaming response from Claude with citation support.
    
    Args:
        response_stream: Stream of response events from Claude
        has_sources: Whether the message includes sources
        
    Returns:
        Final formatted response text
    """
    # Initialize state for building response
    current_text = ""
    current_citations = []
    text_blocks = []
    placeholder = st.empty()
    
    for chunk in response_stream:
        if hasattr(chunk, 'type'):
            if chunk.type == 'message_start':
                continue
            elif chunk.type == 'content_block_start':
                # Reset state for new block
                current_text = ""
                current_citations = []
                text_blocks.append("")  # Initialize new block
            elif chunk.type == 'content_block_delta':
                if chunk.delta.type == 'text_delta':
                    current_text += chunk.delta.text
                    if has_sources:
                        # Create a content block for formatting
                        content_block = type('TextBlock', (), {
                            'type': 'text',
                            'text': current_text,
                            'citations': current_citations
                        })
                        formatted_text = llm_client.format_citations([content_block])
                        text_blocks[-1] = formatted_text
                    else:
                        text_blocks[-1] = current_text
                    placeholder.markdown("\n\n".join(text_blocks))
                elif chunk.delta.type == 'citations_delta':
                    current_citations.append(chunk.delta.citation)
                    if has_sources:
                        # Update with new citation
                        content_block = type('TextBlock', (), {
                            'type': 'text',
                            'text': current_text,
                            'citations': current_citations
                        })
                        formatted_text = llm_client.format_citations([content_block])
                        text_blocks[-1] = formatted_text
                        placeholder.markdown("\n\n".join(text_blocks))
            elif chunk.type == 'content_block_stop':
                # Store the completed block if not already stored
                if current_text and (not text_blocks or text_blocks[-1] != current_text):
                    if has_sources:
                        content_block = type('TextBlock', (), {
                            'type': 'text',
                            'text': current_text,
                            'citations': current_citations
                        })
                        formatted_text = llm_client.format_citations([content_block])
                    else:
                        formatted_text = current_text
                    text_blocks.append(formatted_text)
            elif chunk.type == 'message_stop':
                break
        elif hasattr(chunk, 'content'):
            # Handle non-streaming response
            formatted_text = llm_client.format_citations(chunk.content) if has_sources else str(chunk)
            text_blocks.append(formatted_text)
            placeholder.markdown("\n\n".join(text_blocks))
    
    # Return final formatted text
    return "\n\n".join(text_blocks)

def main() -> None:
    """Main application entry point."""
    st.title("Claude Prompt Testing 🤖")
    
    # Initialize session state
    initialize_session_state()
    
    # Setup sidebar
    setup_sidebar()
    
    # Display chat history
    display_chat_history()
    
    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Create user message
        user_message = Message(role="user", content=prompt)
        st.session_state.messages.append(user_message)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get LLM client
        llm_client = get_llm_client(
            model=st.session_state.llm_model,
            region=st.session_state.region,
        )
        
        # Prepare message with sources if available
        has_sources = bool(st.session_state.current_sources)
        if has_sources:
            content_blocks = prepare_content_blocks(prompt, st.session_state.current_sources)
            messages = [{"role": "user", "content": content_blocks}]
        else:
            messages = [{"role": "user", "content": prompt}]
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            response_stream = llm_client.send_message(
                messages=messages,
                stream=True
            )
            response_text = handle_streaming_response(response_stream, has_sources)
            
        # Add assistant response to chat history
        assistant_message = Message(role="assistant", content=response_text)
        st.session_state.messages.append(assistant_message)

if __name__ == "__main__":
    main() 