"""
Chat functionality and LLM integration using Claude's API.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Generator
import os
from pathlib import Path
from dotenv import load_dotenv

import anthropic

# Load environment variables from .env file
env_path = Path(__file__).parents[2] / '.env'
load_dotenv(env_path)

@dataclass
class TextContent:
    """Text content for a message."""
    text: str

@dataclass
class ImageContent:
    """Image content for a message."""
    url: str

@dataclass
class Message:
    """A chat message."""
    role: str
    content: Union[str, List[Union[TextContent, ImageContent, Dict[str, Any]]]]

@dataclass
class Citation:
    """A citation from Claude."""
    type: str
    document_title: str
    cited_text: str
    start_char_index: Optional[int] = None
    end_char_index: Optional[int] = None
    start_page_number: Optional[int] = None
    end_page_number: Optional[int] = None
    start_block_index: Optional[int] = None
    end_block_index: Optional[int] = None

@dataclass
class TextBlock:
    """A text block with optional citations."""
    type: str
    text: str
    citations: Optional[List[Citation]] = None

@dataclass
class StreamingEvent:
    """Streaming event from Claude."""
    type: str
    index: Optional[int] = None
    delta: Optional[Dict[str, Any]] = None
    content: Optional[List[TextBlock]] = None
    text: Optional[str] = None

class ClaudeClient:
    """Client for interacting with Claude API."""
    
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 8192,
        temperature: float = 0.8,
        top_p: float = 0.9,
        top_k: int = 10,
        api_key: Optional[str] = None,
    ):
        """Initialize Claude client.
        
        Args:
            model: Model ID to use
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0)
            top_p: Nucleus sampling parameter (0.0-1.0) 
            top_k: Top-k sampling parameter (1-100)
            api_key: Anthropic API key (optional, will use ANTHROPIC_API_KEY env var if not provided)
        """
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        
    def prepare_document_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document content for Claude.
        
        Args:
            content: Document content dictionary
            
        Returns:
            Formatted content for Claude API
        """
        if content["type"] == "document":
            source = content['source']
            
            # Handle custom content documents
            if source['type'] == 'content' and 'content' in source:
                doc = {
                    "type": "document",
                    "source": {
                        "type": "content",
                        "content": source['content']
                    },
                    "citations": {"enabled": True}
                }
                
                # Add optional fields if present
                if 'title' in content:
                    doc['title'] = content['title']
                if 'context' in content:
                    doc['context'] = content['context']
                    
                return doc
            
            # Handle simple text documents
            elif source['type'] == 'text':
                doc = {
                    "type": "document",
                    "source": {
                        "type": "text",
                        "text": source['text']
                    },
                    "citations": {"enabled": True}
                }
                
                # Add optional fields if present
                if 'title' in content:
                    doc['title'] = content['title']
                if 'context' in content:
                    doc['context'] = content['context']
                    
                return doc
            
        elif content["type"] == "text":
            return {
                "type": "text",
                "text": content["text"]
            }
        elif content["type"] == "image":
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": content["url"]
                }
            }
        else:
            raise ValueError(f"Unknown content type: {content['type']}")

    def format_citations(self, content: List[Dict[str, Any]]) -> str:
        """Format text with citations in a readable format.
        
        Args:
            content: List of content blocks from Claude response
            
        Returns:
            Formatted text with citations
        """
        if not content:
            return ""
            
        formatted_blocks = []
        for block in content:
            if block.type == 'text':
                text = block.text
                citations = getattr(block, 'citations', [])
                
                if not citations:
                    formatted_blocks.append(text)
                    continue
                
                # Sort citations by position (in reverse order to maintain indices)
                sorted_citations = sorted(
                    citations,
                    key=lambda x: getattr(x, 'start_char_index', 0),
                    reverse=True
                )
                
                # Apply citations
                formatted_text = text
                for citation in sorted_citations:
                    doc_idx = getattr(citation, 'document_index', 0)
                    doc_title = getattr(citation, 'document_title', f'Source {doc_idx + 1}')
                    end_idx = getattr(citation, 'end_char_index', len(formatted_text))
                    
                    # Insert citation marker
                    citation_marker = f'[{doc_title}]'
                    formatted_text = (
                        formatted_text[:end_idx] +
                        f" {citation_marker}" +
                        formatted_text[end_idx:]
                    )
                
                # Add references for this block
                if citations:
                    formatted_text += "\n\n**References:**"
                    cited_docs = {}
                    for citation in citations:
                        doc_idx = getattr(citation, 'document_index', 0)
                        if doc_idx not in cited_docs:
                            doc_title = getattr(citation, 'document_title', f'Source {doc_idx + 1}')
                            cited_text = getattr(citation, 'cited_text', '').strip()
                            cited_docs[doc_idx] = {
                                'title': doc_title,
                                'text': cited_text
                            }
                    
                    # Format references in Harvard style
                    for doc_idx, doc in sorted(cited_docs.items()):
                        formatted_text += f"\n{doc['title']}: \"{doc['text']}\""
                
                formatted_blocks.append(formatted_text)
        
        # Join all formatted blocks
        return "\n\n".join(formatted_blocks)

    def process_streaming_chunk(self, chunk: Any) -> StreamingEvent:
        """Process a streaming chunk from Claude and convert it to a StreamingEvent."""
        # Handle message start
        if chunk.type == 'message_start':
            return StreamingEvent(type='message_start')
            
        # Handle content block start
        elif chunk.type == 'content_block_start':
            return StreamingEvent(type='content_block_start', index=chunk.index)
            
        # Handle content block delta
        elif chunk.type == 'content_block_delta':
            if hasattr(chunk, 'delta'):
                delta = chunk.delta
                if isinstance(delta, dict):
                    delta_type = delta.get('type')
                    if delta_type == 'text_delta':
                        return StreamingEvent(
                            type='content_block_delta',
                            delta={'type': 'text_delta', 'text': delta.get('text', '')}
                        )
                    elif delta_type == 'citations_delta':
                        return StreamingEvent(
                            type='content_block_delta',
                            delta={'type': 'citations_delta', 'citation': delta.get('citation', {})}
                        )
                    else:
                        return StreamingEvent(type='content_block_delta', delta=delta)
                else:
                    # Handle as before for non-dict deltas
                    if hasattr(delta, 'type'):
                        if delta.type == 'text_delta':
                            return StreamingEvent(
                                type='content_block_delta',
                                delta={'type': 'text_delta', 'text': delta.text}
                            )
                        elif delta.type == 'citations_delta':
                            return StreamingEvent(
                                type='content_block_delta',
                                delta={'type': 'citations_delta', 'citation': delta.citation}
                            )
            return StreamingEvent(type='content_block_delta')
            
        # Handle content block stop
        elif chunk.type == 'content_block_stop':
            return StreamingEvent(type='content_block_stop', index=chunk.index)
            
        # Handle message stop
        elif chunk.type == 'message_stop':
            return StreamingEvent(type='message_stop')
            
        # Handle error
        elif chunk.type == 'error':
            return StreamingEvent(type='error', text=chunk.error)
            
        # Handle content
        elif hasattr(chunk, 'content'):
            content_blocks = []
            for block in chunk.content:
                citations = []
                if hasattr(block, 'citations') and block.citations:
                    for citation in block.citations:
                        citations.append(Citation(
                            type=getattr(citation, 'type', 'unknown'),
                            document_title=getattr(citation, 'document_title', 'unknown'),
                            cited_text=getattr(citation, 'cited_text', ''),
                            start_char_index=getattr(citation, 'start_char_index', None),
                            end_char_index=getattr(citation, 'end_char_index', None),
                            start_page_number=getattr(citation, 'start_page_number', None),
                            end_page_number=getattr(citation, 'end_page_number', None),
                            start_block_index=getattr(citation, 'start_block_index', None),
                            end_block_index=getattr(citation, 'end_block_index', None)
                        ))
                content_blocks.append(TextBlock(
                    type=getattr(block, 'type', 'text'),
                    text=getattr(block, 'text', str(block)),
                    citations=citations if citations else None
                ))
            return StreamingEvent(type='content', content=content_blocks)
            
        # Default case
        return StreamingEvent(type='unknown')

    def send_message(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        system: Optional[str] = None
    ) -> Generator[StreamingEvent, None, None]:
        """Send a message to Claude and get response.
        
        Args:
            messages: List of message dictionaries
            stream: Whether to stream the response
            temperature: Controls randomness (0.0-1.0), overrides instance default
            top_p: Nucleus sampling parameter (0.0-1.0), overrides instance default
            top_k: Top-k sampling parameter (1-100), overrides instance default
            system: System message to set context for the conversation
            
        Yields:
            StreamingEvent objects containing response chunks
        """
        # Prepare content parts
        formatted_messages = []
        for message in messages:
            if isinstance(message["content"], str):
                formatted_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
            elif isinstance(message["content"], list):
                content_parts = []
                for content in message["content"]:
                    if isinstance(content, dict):
                        content_parts.append(self.prepare_document_content(content))
                    else:
                        content_parts.append({
                            "type": "text",
                            "text": str(content)
                        })
                formatted_messages.append({
                    "role": message["role"],
                    "content": content_parts
                })
        
        # Prepare API parameters
        params = {
            "messages": formatted_messages,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "stream": stream,
            "temperature": temperature if temperature is not None else self.temperature,
            "top_p": top_p if top_p is not None else self.top_p,
            "top_k": top_k if top_k is not None else self.top_k
        }
        
        # Add system message if provided
        if system:
            params["system"] = system
        
        # Send request
        if stream:
            response = self.client.messages.create(**params)
            for chunk in response:
                yield self.process_streaming_chunk(chunk)
        else:
            response = self.client.messages.create(**params)
            content_blocks = []
            for block in response.content:
                citations = []
                if hasattr(block, 'citations') and block.citations:
                    for citation in block.citations:
                        citations.append(Citation(
                            type=getattr(citation, 'type', 'unknown'),
                            document_title=getattr(citation, 'document_title', 'unknown'),
                            cited_text=getattr(citation, 'cited_text', ''),
                            start_char_index=getattr(citation, 'start_char_index', None),
                            end_char_index=getattr(citation, 'end_char_index', None),
                            start_page_number=getattr(citation, 'start_page_number', None),
                            end_page_number=getattr(citation, 'end_page_number', None),
                            start_block_index=getattr(citation, 'start_block_index', None),
                            end_block_index=getattr(citation, 'end_block_index', None)
                        ))
                content_blocks.append(TextBlock(
                    type=getattr(block, 'type', 'text'),
                    text=getattr(block, 'text', str(block)),
                    citations=citations if citations else None
                ))
            yield StreamingEvent(type='content', content=content_blocks)

def get_llm_client(
    model: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    **kwargs
) -> ClaudeClient:
    """Get a configured LLM client.
    
    Args:
        model: Model name to use
        api_key: Anthropic API key (optional)
        **kwargs: Additional arguments for ClaudeClient
        
    Returns:
        Configured ClaudeClient instance
    """
    # Model configuration
    MODEL_CONFIG = {
        "Claude 3.5 Sonnet": {
            "id": "claude-3-5-sonnet-20241022",
            "max_tokens": 8192
        },
        "Claude 3.5 Haiku": {
            "id": "claude-3-haiku-20240307", 
            "max_tokens": 8192
        },
        "Claude 3.7 Sonnet": {
            "id": "claude-3-7-sonnet-20250219",
            "max_tokens": 8192
        }
    }
    
    # Get model configuration
    model_config = MODEL_CONFIG.get(model, MODEL_CONFIG["Claude 3.5 Sonnet"])
    
    return ClaudeClient(
        model=model_config["id"],
        max_tokens=model_config["max_tokens"],
        api_key=api_key,
        **kwargs
    ) 