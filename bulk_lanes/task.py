"""Task definition abstractions."""
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

class Task:
    """Base class for defining bulk triage tasks."""
    name: str = "custom_task"
    description: str = "Generic bulk extraction task"
    batch_size: int = 6
    max_slice_chars: int = 6000
    quote_field: str = "quotes"
    min_quote_chars: int = 15
    
    system_prompt: str = (
        "You are an air-gapped data triage worker. "
        "Analyze the provided text items and extract the required structured information. "
        "Strictly adhere to the output schema. "
        "You MUST provide exact verbatim quotes from the supplied source text as evidence for every item. "
        "Never invent information or hallucinate facts not present in the text."
    )
    
    user_prompt_template: str = """
Extract information for each item according to the schema.
Return valid JSON matching this schema:
{
  "items": [
    {
      "item_id": "<id>",
      "summary": "<1-2 sentence overview>",
      "category": "<classification>",
      "quotes": ["<exact quote from text>"]
    }
  ]
}

Items to analyze:
{items_json}
"""

def load_task(task_path: str) -> Task:
    """Loads a Task instance from a Python file or returns a default task."""
    p = Path(task_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Task file not found: {task_path}")
    
    spec = importlib.util.spec_from_file_location("dynamic_task", str(p))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec from {task_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, Task) and attr is not Task:
            return attr()
            
    # Also check if an instance 'task' is exported
    if hasattr(module, "task") and isinstance(module.task, Task):
        return module.task

    raise ValueError(f"No subclass of Task found in {task_path}")
