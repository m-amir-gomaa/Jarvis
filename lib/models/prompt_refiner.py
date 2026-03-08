"""
Prompt Refiner Module
Maintains prompt templates, formats them for specific models, and tracks metrics.
"""

import os
import yaml
import logging
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

class PromptRefiner:
    def __init__(self, templates_dir: str = "~/.jarvis/prompts/"):
        self.templates_dir = os.path.expanduser(templates_dir)
        self.templates: Dict[str, str] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Loads prompt templates from YAML files in the templates directory."""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir, exist_ok=True)
            log.info(f"Created templates directory at {self.templates_dir}")
            return

        for filename in os.listdir(self.templates_dir):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(self.templates_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = yaml.safe_load(f)
                        if data and isinstance(data, dict):
                            for name, template in data.items():
                                if isinstance(template, str):
                                    self.templates[name] = template
                except Exception as e:
                    log.error(f"Failed to load prompt template from {filepath}: {e}")

    def get_template(self, task_type: str, default: str = "") -> str:
        """Retrieves a template by task type classification."""
        return self.templates.get(task_type, default)

    def format_prompt(self, task_type: str, context: Dict[str, str], model_provider: str,
                      dry_run: bool = False, custom_template: Optional[str] = None) -> str:
        """
        Retrieves the appropriate template, injects context, and formats targeting the model provider.
        """
        template = custom_template if custom_template else self.get_template(task_type)
        if not template:
            # Fallback if no template exists
            template = "{query}"
            
        # Inject Context (basic string format)
        try:
            prompt = template.format(**context)
        except KeyError as e:
            log.warning(f"Missing context key for template: {e}")
            # simple fallback
            prompt = template
            for k, v in context.items():
                prompt = prompt.replace(f"{{{k}}}", str(v))

        # Model-Specific Formatting
        formatted_prompt = self._apply_provider_formatting(prompt, model_provider)

        if not dry_run:
            self._track_metric(task_type, "invocations", 1)

        return formatted_prompt

    def _apply_provider_formatting(self, prompt: str, provider: str) -> str:
        """Applies model-specific formatting like XML tags vs Markdown."""
        if provider.lower() in ["anthropic", "claude"]:
            # Claude prefers explicit XML-like structure
            formatted = f"<prompt>\n{prompt}\n</prompt>"
            # Also convert naive markdown codeblocks to xml if requested, but keep simple for now
            return formatted
        elif provider.lower() in ["ollama", "local"]:
            # Local models often prefer markdown
            return f"### Instruction:\n{prompt}\n### Response:\n"
        
        # Default pass-through
        return prompt

    def _track_metric(self, task_type: str, metric_name: str, value: int) -> None:
        """Tracks performance/usage metrics per task type."""
        if task_type not in self.metrics:
            self.metrics[task_type] = {"invocations": 0, "corrections": 0}
        
        self.metrics[task_type][metric_name] = self.metrics[task_type].get(metric_name, 0) + value

    def flag_correction(self, task_type: str) -> None:
        """Flags that a prompt resulted in a correction/re-prompt."""
        self._track_metric(task_type, "corrections", 1)
        
    def get_high_correction_templates(self, threshold_ratio: float = 0.3) -> list:
        """Returns a list of task types that exceed the correction ratio threshold."""
        high_corr = []
        for task_type, data in self.metrics.items():
            invocations = data.get("invocations", 0)
            if invocations > 5: # Require minimum sample size
                corrections = data.get("corrections", 0)
                if (corrections / invocations) >= threshold_ratio:
                    high_corr.append(task_type)
        return high_corr
