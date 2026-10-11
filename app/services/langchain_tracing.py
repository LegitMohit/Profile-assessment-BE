"""LangChain tracing configuration and callbacks for LLM call logging."""
import os
import json
import time
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langsmith import Client

logger = logging.getLogger(__name__)


class LLMCallTracer(BaseCallbackHandler):
    """Callback handler to trace all LLM calls with detailed logging."""
    
    def __init__(
        self,
        log_level: int = logging.INFO,
        log_prompts: bool = True,
        log_responses: bool = True,
        log_to_file: bool = False,
        log_file_path: str = "llm_calls.log",
    ):
        self.log_level = log_level
        self.log_prompts = log_prompts
        self.log_responses = log_responses
        self.log_to_file = log_to_file
        self.log_file_path = log_file_path
        
        # Setup file handler if needed
        if log_to_file:
            self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Setup file logging for LLM calls."""
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(self.log_level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(self.log_level)
    
    def _log(self, message: str, level: int = logging.INFO):
        """Log message to both console and file."""
        logger.log(level, message)
        if self.log_to_file:
            print(message)
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts processing."""
        timestamp = datetime.now().isoformat()
        
        self._log(f"\n{'='*80}")
        self._log(f"LLM CALL STARTED - {timestamp}")
        self._log(f"Run ID: {run_id}")
        self._log(f"Parent Run ID: {parent_run_id}")
        self._log(f"Tags: {tags}")
        self._log(f"Metadata: {metadata}")
        
        if self.log_prompts and prompts:
            for i, prompt in enumerate(prompts):
                self._log(f"\n--- Prompt {i+1}/{len(prompts)} ---")
                # Truncate very long prompts
                prompt_preview = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
                self._log(prompt_preview)
        
        # Store start time for duration calculation
        if not hasattr(self, '_start_times'):
            self._start_times = {}
        self._start_times[run_id] = time.time()
    
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM finishes processing."""
        timestamp = datetime.now().isoformat()
        duration = 0
        
        if hasattr(self, '_start_times') and run_id in self._start_times:
            duration = time.time() - self._start_times[run_id]
            del self._start_times[run_id]
        
        self._log(f"\nLLM CALL COMPLETED - {timestamp}")
        self._log(f"Run ID: {run_id}")
        self._log(f"Duration: {duration:.2f}s")
        
        if self.log_responses:
            self._log(f"\n--- Response ---")
            for i, gen in enumerate(response.generations):
                for j, chunk in enumerate(gen):
                    if hasattr(chunk, 'text') and chunk.text:
                        response_text = chunk.text
                        # Truncate very long responses
                        if len(response_text) > 2000:
                            response_text = response_text[:2000] + "..."
                        self._log(f"Generation {i+1}, Chunk {j+1}: {response_text}")
        
        # Log token usage if available
        if response.llm_output and 'token_usage' in response.llm_output:
            self._log(f"\n--- Token Usage ---")
            self._log(json.dumps(response.llm_output['token_usage'], indent=2))
        
        self._log(f"{'='*80}\n")
    
    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM encounters an error."""
        timestamp = datetime.now().isoformat()
        duration = 0
        
        if hasattr(self, '_start_times') and run_id in self._start_times:
            duration = time.time() - self._start_times[run_id]
            del self._start_times[run_id]
        
        self._log(f"\nLLM CALL ERROR - {timestamp}")
        self._log(f"Run ID: {run_id}")
        self._log(f"Duration before error: {duration:.2f}s")
        self._log(f"Error: {type(error).__name__}: {str(error)}")
        self._log(f"{'='*80}\n")


class LangSmithTracer:
    """LangSmith integration for cloud-based tracing (optional)."""
    
    def __init__(self, api_key: Optional[str] = None, project_name: str = "student-eligibility-ai"):
        self.api_key = api_key or os.getenv("LANGSMITH_API_KEY")
        self.project_name = project_name
        self.client = None
        
        if self.api_key:
            try:
                self.client = Client(api_key=self.api_key)
                logger.info(f"LangSmith client initialized for project: {project_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith client: {e}")
        else:
            logger.info("LangSmith API key not provided, skipping cloud tracing")
    
    def is_enabled(self) -> bool:
        return self.client is not None
    
    def create_run(
        self,
        name: str,
        run_type: str,
        inputs: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a run in LangSmith."""
        if not self.client:
            return None
        try:
            run = self.client.create_run(
                name=name,
                run_type=run_type,
                inputs=inputs,
                project_name=self.project_name,
                tags=tags or [],
                metadata=metadata or {},
            )
            return run.id
        except Exception as e:
            logger.warning(f"Failed to create LangSmith run: {e}")
            return None
    
    def update_run(
        self,
        run_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        end_time: Optional[datetime] = None,
    ) -> None:
        """Update a run in LangSmith."""
        if not self.client:
            return
        try:
            self.client.update_run(
                run_id=run_id,
                outputs=outputs,
                error=error,
                end_time=end_time or datetime.now(),
            )
        except Exception as e:
            logger.warning(f"Failed to update LangSmith run: {e}")


# Global instances
_llm_tracer: Optional[LLMCallTracer] = None
_langsmith_tracer: Optional[LangSmithTracer] = None


def get_llm_tracer(
    log_level: int = logging.INFO,
    log_prompts: bool = True,
    log_responses: bool = True,
    log_to_file: bool = False,
    log_file_path: str = "llm_calls.log",
) -> LLMCallTracer:
    """Get or create the global LLM tracer."""
    global _llm_tracer
    if _llm_tracer is None:
        _llm_tracer = LLMCallTracer(
            log_level=log_level,
            log_prompts=log_prompts,
            log_responses=log_responses,
            log_to_file=log_to_file,
            log_file_path=log_file_path,
        )
    return _llm_tracer


def get_langsmith_tracer(
    api_key: Optional[str] = None,
    project_name: str = "student-eligibility-ai",
) -> LangSmithTracer:
    """Get or create the global LangSmith tracer."""
    global _langsmith_tracer
    if _langsmith_tracer is None:
        _langsmith_tracer = LangSmithTracer(api_key=api_key, project_name=project_name)
    return _langsmith_tracer


def init_tracing(
    log_level: int = logging.INFO,
    log_prompts: bool = True,
    log_responses: bool = True,
    log_to_file: bool = False,
    log_file_path: str = "llm_calls.log",
    langsmith_api_key: Optional[str] = None,
    langsmith_project: str = "student-eligibility-ai",
) -> tuple[LLMCallTracer, LangSmithTracer]:
    """Initialize all tracing components."""
    tracer = get_llm_tracer(
        log_level=log_level,
        log_prompts=log_prompts,
        log_responses=log_responses,
        log_to_file=log_to_file,
        log_file_path=log_file_path,
    )
    langsmith = get_langsmith_tracer(
        api_key=langsmith_api_key,
        project_name=langsmith_project,
    )
    return tracer, langsmith