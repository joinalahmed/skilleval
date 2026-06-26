"""
Container execution for harness testing using Podman.
"""

import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import time


class PodmanExecutor:
    """Execute skills in isolated Podman containers."""

    def __init__(self, config):
        """
        Initialize Podman executor.

        Args:
            config: HarnessConfig object
        """
        self.config = config
        self.runtime = config.container_runtime  # "podman"
        self.base_image = config.base_image
        self.timeout = config.timeout_seconds
        self.max_tokens = config.max_tokens
        self.max_turns = config.max_turns

    def check_available(self) -> bool:
        """Check if Podman is available."""
        try:
            result = subprocess.run(
                [self.runtime, "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def execute_baseline(
        self,
        skill_path: Path,
        eval_case: Dict[str, Any],
        workspace: Path,
    ) -> Dict[str, Any]:
        """
        Execute evaluation case WITHOUT the skill (baseline).

        Args:
            skill_path: Path to skill directory
            eval_case: Evaluation case definition
            workspace: Workspace directory

        Returns:
            Execution results
        """
        # Create baseline workspace
        baseline_workspace = workspace / "baseline"
        baseline_workspace.mkdir(parents=True, exist_ok=True)

        # Copy files if needed
        if eval_case.get("files"):
            for file_path in eval_case["files"]:
                src = skill_path / file_path
                if src.exists():
                    dst = baseline_workspace / Path(file_path).name
                    shutil.copy2(src, dst)

        # Execute without skill
        result = self._run_in_container(
            workspace=baseline_workspace,
            prompt=eval_case["prompt"],
            skill_enabled=False,
        )

        return result

    def execute_with_skill(
        self,
        skill_path: Path,
        eval_case: Dict[str, Any],
        workspace: Path,
    ) -> Dict[str, Any]:
        """
        Execute evaluation case WITH the skill activated.

        Args:
            skill_path: Path to skill directory
            eval_case: Evaluation case definition
            workspace: Workspace directory

        Returns:
            Execution results
        """
        # Create skill workspace
        skill_workspace = workspace / "with_skill"
        skill_workspace.mkdir(parents=True, exist_ok=True)

        # Copy files if needed
        if eval_case.get("files"):
            for file_path in eval_case["files"]:
                src = skill_path / file_path
                if src.exists():
                    dst = skill_workspace / Path(file_path).name
                    shutil.copy2(src, dst)

        # Copy skill into workspace
        skill_dir = skill_workspace / ".skills" / skill_path.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Copy SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            shutil.copy2(skill_md, skill_dir / "SKILL.md")

        # Execute with skill
        result = self._run_in_container(
            workspace=skill_workspace,
            prompt=eval_case["prompt"],
            skill_enabled=True,
            skill_name=skill_path.name,
        )

        return result

    def _run_in_container(
        self,
        workspace: Path,
        prompt: str,
        skill_enabled: bool,
        skill_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run LLM execution in container.

        Args:
            workspace: Workspace directory
            prompt: User prompt
            skill_enabled: Whether skill is enabled
            skill_name: Name of skill if enabled

        Returns:
            Execution results including trace
        """
        # For MVP: Simulate execution without actual LLM calls
        # In production, this would launch Claude Code in container

        result = {
            "workspace": workspace,
            "prompt": prompt,
            "skill_enabled": skill_enabled,
            "skill_name": skill_name,
            "trace_file": None,
            "exit_code": 0,
            "output": "",
            "token_count": 0,
            "turn_count": 0,
            "duration_seconds": 0,
        }

        # Check if we can actually execute
        if not self.check_available():
            # Return simulated results
            result["simulated"] = True
            return result

        # Create trace file
        trace_file = workspace / "trace.jsonl"

        try:
            # In real implementation, would:
            # 1. Build container with Claude Code
            # 2. Mount workspace
            # 3. Run prompt
            # 4. Capture trace
            # 5. Return results

            # For now, create minimal trace
            trace_data = {
                "timestamp": time.time(),
                "prompt": prompt,
                "skill_enabled": skill_enabled,
                "skill_name": skill_name,
                "turns": [],
            }

            with open(trace_file, "w") as f:
                json.dump(trace_data, f)

            result["trace_file"] = trace_file
            result["simulated"] = True

        except Exception as e:
            result["error"] = str(e)
            result["exit_code"] = 1

        return result

    def cleanup_container(self, container_id: str) -> None:
        """Clean up container after execution."""
        try:
            subprocess.run(
                [self.runtime, "rm", "-f", container_id],
                capture_output=True,
                timeout=30,
            )
        except Exception:
            pass


class TraceAnalyzer:
    """Analyze execution traces for LLM behavior."""

    def __init__(self):
        """Initialize trace analyzer."""
        pass

    def analyze_trace(self, trace_file: Path) -> Dict[str, Any]:
        """
        Analyze execution trace.

        Args:
            trace_file: Path to trace JSONL file

        Returns:
            Analysis results
        """
        if not trace_file or not trace_file.exists():
            return {
                "total_tokens": 0,
                "turn_count": 0,
                "unverified_executions": 0,
                "total_executions": 0,
                "hallucination_markers": [],
            }

        try:
            with open(trace_file) as f:
                data = json.load(f)

            return {
                "total_tokens": data.get("total_tokens", 0),
                "turn_count": len(data.get("turns", [])),
                "unverified_executions": 0,
                "total_executions": 0,
                "hallucination_markers": [],
            }
        except Exception:
            return {
                "total_tokens": 0,
                "turn_count": 0,
                "unverified_executions": 0,
                "total_executions": 0,
                "hallucination_markers": [],
            }

    def detect_unbounded_planning(self, trace_data: Dict[str, Any]) -> bool:
        """
        Detect if LLM got stuck in unbounded planning.

        Args:
            trace_data: Trace analysis data

        Returns:
            True if unbounded planning detected
        """
        # Check for excessive turns without action
        turn_count = trace_data.get("turn_count", 0)
        return turn_count > 20

    def detect_context_rot(self, trace_data: Dict[str, Any]) -> bool:
        """
        Detect context rot (repeated queries, circular logic).

        Args:
            trace_data: Trace analysis data

        Returns:
            True if context rot detected
        """
        # Would analyze turn patterns in real implementation
        return False

    def detect_infinite_loops(self, trace_data: Dict[str, Any]) -> bool:
        """
        Detect infinite loops in execution.

        Args:
            trace_data: Trace analysis data

        Returns:
            True if infinite loop detected
        """
        # Check for same actions repeated
        turn_count = trace_data.get("turn_count", 0)
        return turn_count > 50

    def detect_hallucinations(self, trace_data: Dict[str, Any]) -> List[str]:
        """
        Detect hallucination markers.

        Args:
            trace_data: Trace analysis data

        Returns:
            List of hallucination markers
        """
        # Would check for:
        # - References to non-existent files
        # - Invalid function calls
        # - Fabricated data
        return trace_data.get("hallucination_markers", [])

    def calculate_cost(self, trace_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate execution cost.

        Args:
            trace_data: Trace analysis data

        Returns:
            Cost breakdown
        """
        total_tokens = trace_data.get("total_tokens", 0)

        # Rough cost estimates (Claude Sonnet 4)
        input_cost_per_1k = 0.003  # $3 per 1M tokens
        output_cost_per_1k = 0.015  # $15 per 1M tokens

        # Assume 50/50 split for estimate
        estimated_cost = (total_tokens / 1000) * (
            (input_cost_per_1k + output_cost_per_1k) / 2
        )

        return {
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
        }
