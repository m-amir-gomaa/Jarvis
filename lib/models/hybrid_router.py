"""
Hybrid Router Module
Implements a hybrid local-first routing mechanism.
"""

import logging
import psutil

log = logging.getLogger(__name__)

class HybridRouter:
    """
    Selects the best model for a given task using a scoring heuristic.
    Prefers local capabilities (Ollama) before falling back to cloud.
    """
    def __init__(self, config: dict, capabilities: dict, initial_budget: float = 10.0):
        self.config = config
        self.capabilities = capabilities
        self.budget = initial_budget
        
        # Determine threshold from config
        self.local_threshold = self.config.get("local_threshold", 0.7)
        self.cloud_enabled = self.config.get("cloud_enabled", True)

    def assess_task_complexity(self, prompt: str) -> float:
        """
        Heuristic to score task complexity based on prompt length and keywords.
        0.0 to 1.0.
        """
        length_score = min(len(prompt) / 2000.0, 1.0)
        
        complex_keywords = ["analyze", "synthesize", "architect", "reason", "refactor"]
        keyword_score = sum(0.1 for kw in complex_keywords if kw in prompt.lower())
        
        return min(length_score + keyword_score, 1.0)

    def check_system_load(self) -> float:
        """
        Returns a system health score (0.0 to 1.0) where 1.0 is completely free.
        """
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=None) # non-blocking
            
            # Weighted average of available mem % and idle cpu %
            mem_score = mem.available / mem.total
            cpu_score = max((100.0 - cpu) / 100.0, 0.0)
            
            return (mem_score * 0.7) + (cpu_score * 0.3)
        except Exception as e:
            log.warning(f"Failed to check system load: {e}")
            return 0.5 # Unknown load

    def score_model(self, model_name: str, task_complexity: float, system_load: float) -> float:
        """
        Calculates a compatibility score for a model given the task and system state.
        """
        cap = self.capabilities.get(model_name, {})
        base_capability = cap.get("capability_score", 0.5)
        is_local = cap.get("is_local", False)
        cost_per_k = cap.get("cost_per_1k", 0.0)
        
        score = base_capability
        
        # Penalize models whose capability is significantly lower than task complexity
        if base_capability < task_complexity - 0.2:
            score -= 0.3
            
        # Adjust for system load if local
        if is_local:
            if system_load < 0.2: # Very high load
                score -= 0.4
            elif system_load < 0.4:
                score -= 0.2
        else:
            # Penalize cloud models slightly to encourage local fallback
            score -= 0.1
            
            # Penalize if it exceeds budget entirely
            if cost_per_k > self.budget:
                score -= 1.0
                
        return max(score, 0.0)

    def route(self, prompt: str) -> str:
        """
        Executes the routing fallback chain:
        local_primary -> local_secondary -> cloud_primary -> cloud_error
        """
        complexity = self.assess_task_complexity(prompt)
        sys_load = self.check_system_load()
        
        local_primary = self.config.get("local_primary")
        local_secondary = self.config.get("local_secondary")
        cloud_primary = self.config.get("cloud_primary")
        
        candidates = []
        if local_primary: candidates.append(local_primary)
        if local_secondary: candidates.append(local_secondary)
        
        # Evaluate locals
        best_local = None
        best_local_score = -1.0
        
        for cand in candidates:
            score = self.score_model(cand, complexity, sys_load)
            if score > best_local_score:
                best_local_score = score
                best_local = cand
                
        # Return best local if it exceeds threshold
        if best_local and best_local_score >= self.local_threshold:
            return best_local
            
        # Fallback to cloud if allowed
        if self.cloud_enabled and cloud_primary:
            cloud_score = self.score_model(cloud_primary, complexity, sys_load)
            if cloud_score > 0.0:
                cost = self.capabilities.get(cloud_primary, {}).get("cost_per_1k", 0.0)
                if self.budget >= cost:
                    return cloud_primary
                    
        # If all fail, return the best local even if below threshold (local fallback)
        if best_local:
            return best_local
            
        raise RuntimeError("No models available in configuration for routing.")
