"""
Agent-based skill execution using SkillEval template-agent pattern.

This replaces the container-based execution with a direct LLM agent approach.
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Import Anthropic SDK
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class AgentConfig:
    """Configuration for agent execution."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_turns: int = 25
    timeout_seconds: int = 300
    temperature: float = 1.0


class SkillAgent:
    """
    LLM Agent for executing skill evaluations.

    Based on SkillEval template-agent pattern but simplified for eval purposes.
    """

    def __init__(self, config: AgentConfig, api_key: Optional[str] = None):
        """
        Initialize skill agent.

        Args:
            config: Agent configuration
            api_key: Anthropic API key (or from env ANTHROPIC_API_KEY)
        """
        self.config = config

        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=api_key)

    async def execute(
        self,
        prompt: str,
        workspace: Path,
        skill_path: Optional[Path] = None,
        files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a prompt with optional skill context.

        Args:
            prompt: User prompt to execute
            workspace: Working directory
            skill_path: Optional path to skill directory
            files: Optional list of files to include in context

        Returns:
            Execution results with trace data
        """
        start_time = time.time()

        # Build system prompt
        system_prompt = self._build_system_prompt(skill_path, files)

        # Build user message
        user_message = self._build_user_message(prompt, workspace, files)

        # Execute conversation
        messages = []
        turn_count = 0
        total_input_tokens = 0
        total_output_tokens = 0
        tool_uses = []

        conversation = [{"role": "user", "content": user_message}]

        try:
            # Agentic loop
            while turn_count < self.config.max_turns:
                turn_count += 1

                # Call Claude API
                response = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system_prompt,
                    messages=conversation,
                    tools=self._get_tools(),
                )

                # Track tokens
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens

                # Save turn
                messages.append({
                    "turn": turn_count,
                    "role": "assistant",
                    "content": response.content,
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                })

                # Add assistant response to conversation
                conversation.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Agent is done
                    break

                elif response.stop_reason == "tool_use":
                    # Execute tools
                    tool_results = []

                    for block in response.content:
                        if block.type == "tool_use":
                            tool_uses.append({
                                "turn": turn_count,
                                "tool": block.name,
                                "input": block.input,
                            })

                            # Execute tool
                            result = await self._execute_tool(
                                block.name,
                                block.input,
                                workspace,
                            )

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                    # Add tool results to conversation
                    if tool_results:
                        conversation.append({
                            "role": "user",
                            "content": tool_results,
                        })
                else:
                    # max_tokens or other stop reason
                    break

            # Build result
            duration = time.time() - start_time

            # Extract final text response
            final_response = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_response += block.text

            return {
                "workspace": str(workspace),
                "prompt": prompt,
                "skill_enabled": skill_path is not None,
                "skill_name": skill_path.name if skill_path else None,
                "success": True,
                "final_response": final_response,
                "turn_count": turn_count,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "tool_uses": tool_uses,
                "messages": messages,
                "duration_seconds": duration,
                "exit_code": 0,
            }

        except anthropic.APIError as e:
            return {
                "workspace": str(workspace),
                "prompt": prompt,
                "success": False,
                "error": str(e),
                "exit_code": 1,
                "duration_seconds": time.time() - start_time,
            }

    def _build_system_prompt(
        self,
        skill_path: Optional[Path],
        files: Optional[List[str]],
    ) -> str:
        """Build system prompt with optional skill context."""

        parts = []

        # Base system prompt
        parts.append(
            "You are a helpful AI assistant. Complete the user's request to the best of your ability."
        )

        # Add skill context if provided
        if skill_path and (skill_path / "SKILL.md").exists():
            skill_md = (skill_path / "SKILL.md").read_text()
            parts.append("\n## Skill Guidance\n")
            parts.append("You have access to the following skill guidance:\n")
            parts.append(skill_md)
            parts.append("\nFollow this guidance when completing the task.")

        # Add file context
        if files:
            parts.append("\n## Available Files\n")
            parts.append(f"The following files are available in the workspace: {', '.join(files)}")

        return "\n".join(parts)

    def _build_user_message(
        self,
        prompt: str,
        workspace: Path,
        files: Optional[List[str]],
    ) -> str:
        """Build user message with workspace context."""

        parts = [prompt]

        # Add workspace info
        parts.append(f"\nWorking directory: {workspace}")

        # Add file contents if small
        if files:
            for file_name in files:
                file_path = workspace / file_name
                if file_path.exists() and file_path.stat().st_size < 10000:
                    try:
                        content = file_path.read_text()
                        parts.append(f"\n### {file_name}\n```\n{content}\n```")
                    except:
                        pass

        return "\n".join(parts)

    def _get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Claude."""

        return [
            {
                "name": "write_file",
                "description": "Write content to a file in the workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to workspace",
                        },
                        "content": {
                            "type": "string",
                            "description": "File content to write",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "read_file",
                "description": "Read content from a file in the workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to workspace",
                        },
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "list_files",
                "description": "List files in the workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path (default: workspace root)",
                            "default": ".",
                        },
                    },
                },
            },
            {
                "name": "execute_bash",
                "description": "Execute a bash command in the workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Bash command to execute",
                        },
                    },
                    "required": ["command"],
                },
            },
        ]

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        workspace: Path,
    ) -> str:
        """Execute a tool call."""

        try:
            if tool_name == "write_file":
                file_path = workspace / tool_input["path"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(tool_input["content"])
                return f"File written successfully: {tool_input['path']}"

            elif tool_name == "read_file":
                file_path = workspace / tool_input["path"]
                if not file_path.exists():
                    return f"Error: File not found: {tool_input['path']}"
                content = file_path.read_text()
                return content

            elif tool_name == "list_files":
                dir_path = workspace / tool_input.get("path", ".")
                if not dir_path.exists():
                    return f"Error: Directory not found: {tool_input.get('path', '.')}"

                files = [f.name for f in dir_path.iterdir()]
                return "\n".join(files)

            elif tool_name == "execute_bash":
                import subprocess

                result = subprocess.run(
                    tool_input["command"],
                    shell=True,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                output = result.stdout
                if result.stderr:
                    output += f"\nSTDERR:\n{result.stderr}"
                if result.returncode != 0:
                    output = f"Exit code: {result.returncode}\n{output}"

                return output

            else:
                return f"Error: Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"


class AgentExecutor:
    """
    Executor for running skill evaluations with LLM agents.

    Replaces PodmanExecutor with direct API-based execution.
    """

    def __init__(self, config=None):
        """Initialize executor."""
        self.agent_config = AgentConfig()

        # Check for API key
        import os
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Set it with: export ANTHROPIC_API_KEY=your-key-here"
            )

    def check_available(self) -> bool:
        """Check if agent execution is available."""
        return ANTHROPIC_AVAILABLE and self.api_key is not None

    async def execute_baseline(
        self,
        skill_path: Path,
        eval_case: Dict[str, Any],
        workspace: Path,
    ) -> Dict[str, Any]:
        """
        Execute WITHOUT skill (baseline).

        Args:
            skill_path: Path to skill (not used for baseline)
            eval_case: Evaluation case definition
            workspace: Working directory

        Returns:
            Execution results
        """
        agent = SkillAgent(self.agent_config, self.api_key)

        result = await agent.execute(
            prompt=eval_case["prompt"],
            workspace=workspace / "baseline",
            skill_path=None,  # No skill
            files=eval_case.get("files"),
        )

        # Save trace
        trace_file = workspace / "baseline" / "trace.json"
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        trace_file.write_text(json.dumps(result, indent=2))

        result["trace_file"] = trace_file
        result["workspace"] = workspace / "baseline"

        return result

    async def execute_with_skill(
        self,
        skill_path: Path,
        eval_case: Dict[str, Any],
        workspace: Path,
    ) -> Dict[str, Any]:
        """
        Execute WITH skill activated.

        Args:
            skill_path: Path to skill directory
            eval_case: Evaluation case definition
            workspace: Working directory

        Returns:
            Execution results
        """
        agent = SkillAgent(self.agent_config, self.api_key)

        result = await agent.execute(
            prompt=eval_case["prompt"],
            workspace=workspace / "with_skill",
            skill_path=skill_path,  # Skill provided
            files=eval_case.get("files"),
        )

        # Save trace
        trace_file = workspace / "with_skill" / "trace.json"
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        trace_file.write_text(json.dumps(result, indent=2))

        result["trace_file"] = trace_file
        result["workspace"] = workspace / "with_skill"

        return result


# Synchronous wrapper for backward compatibility
class AgentExecutorSync:
    """Synchronous wrapper for AgentExecutor."""

    def __init__(self, config=None):
        self.executor = AgentExecutor(config)

    def check_available(self) -> bool:
        return self.executor.check_available()

    def execute_baseline(self, skill_path: Path, eval_case: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        """Sync wrapper for execute_baseline."""
        return asyncio.run(self.executor.execute_baseline(skill_path, eval_case, workspace))

    def execute_with_skill(self, skill_path: Path, eval_case: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        """Sync wrapper for execute_with_skill."""
        return asyncio.run(self.executor.execute_with_skill(skill_path, eval_case, workspace))


class TraceAnalyzer:
    """Analyze execution traces for safety and quality metrics."""

    def analyze_trace(self, trace_file: Path) -> Dict[str, Any]:
        """
        Analyze execution trace from agent.

        Args:
            trace_file: Path to trace JSON file

        Returns:
            Analysis results
        """
        if not trace_file or not trace_file.exists():
            return {
                "total_tokens": 0,
                "turn_count": 0,
                "tool_uses": 0,
                "success": False,
            }

        try:
            with open(trace_file) as f:
                data = json.load(f)

            return {
                "total_tokens": data.get("total_tokens", 0),
                "turn_count": data.get("turn_count", 0),
                "tool_uses": len(data.get("tool_uses", [])),
                "success": data.get("success", False),
                "duration_seconds": data.get("duration_seconds", 0),
            }
        except Exception:
            return {
                "total_tokens": 0,
                "turn_count": 0,
                "tool_uses": 0,
                "success": False,
            }

    def detect_unbounded_planning(self, trace_data: Dict) -> bool:
        """Detect unbounded planning loops."""
        turn_count = trace_data.get("turn_count", 0)
        return turn_count > 50  # More than 50 turns is excessive

    def detect_context_rot(self, trace_data: Dict) -> bool:
        """Detect context window issues."""
        total_tokens = trace_data.get("total_tokens", 0)
        return total_tokens > 100000  # Over 100K tokens

    def detect_infinite_loops(self, trace_data: Dict) -> bool:
        """Detect infinite loops."""
        turn_count = trace_data.get("turn_count", 0)
        tool_uses = trace_data.get("tool_uses", 0)

        # Too many tool uses relative to turns
        if turn_count > 10 and tool_uses > turn_count * 5:
            return True

        return False

    def detect_hallucinations(self, trace_data: Dict) -> List[str]:
        """Detect potential hallucinations."""
        # For now, just check if execution failed
        if not trace_data.get("success", False):
            return ["Execution failed - may indicate hallucinated tools"]
        return []

    def calculate_cost(self, trace_data: Dict) -> float:
        """Calculate estimated cost."""
        total_tokens = trace_data.get("total_tokens", 0)

        # Claude Sonnet 4 pricing (approximate)
        # Input: $3 per 1M tokens
        # Output: $15 per 1M tokens

        # Estimate: assume 60% input, 40% output
        input_tokens = total_tokens * 0.6
        output_tokens = total_tokens * 0.4

        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0

        return input_cost + output_cost
