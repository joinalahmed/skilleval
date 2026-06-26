"""
Multi-provider agent executor supporting Anthropic and Google GenAI.

Allows switching between providers based on configuration.
Loads settings from .env file if available.
"""

import json
import time
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass
from enum import Enum

from skilleval.utils.env_config import load_env_config, get_active_provider, get_model_for_provider, get_api_key_for_provider

# Try importing both SDKs
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class Provider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass
class AgentConfig:
    """Configuration for multi-provider agent."""
    provider: Provider = Provider.GOOGLE  # Default to Google
    model: str = "gemini-2.0-flash-exp"  # Default Google model
    max_tokens: int = 8192
    max_turns: int = 25
    timeout_seconds: int = 300
    temperature: float = 1.0


class MultiProviderAgent:
    """
    Multi-provider LLM agent supporting Anthropic and Google GenAI.

    Automatically selects provider based on .env config and available API keys.
    """

    def __init__(self, config: AgentConfig, env_config=None):
        """
        Initialize multi-provider agent.

        Args:
            config: Agent configuration including provider selection
            env_config: Optional environment configuration (loaded from .env)
        """
        self.config = config
        self.provider = config.provider

        # Load environment config if not provided
        if env_config is None:
            env_config = load_env_config()

        self.env_config = env_config

        # Initialize client based on provider
        if self.provider == Provider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")

            # Get API key from env config or environment variable
            api_key = get_api_key_for_provider(env_config, "anthropic") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in .env or environment")

            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = config.model or env_config.anthropic_model

        elif self.provider == Provider.GOOGLE:
            if not GOOGLE_AVAILABLE:
                raise ImportError("google-genai package not installed. Run: pip install google-genai")

            # Get API key from env config or environment variable
            api_key = get_api_key_for_provider(env_config, "google") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in .env or environment")

            self.client = genai.Client(api_key=api_key)
            self.model = config.model or env_config.google_model

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

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
        if self.provider == Provider.ANTHROPIC:
            return await self._execute_anthropic(prompt, workspace, skill_path, files)
        elif self.provider == Provider.GOOGLE:
            return await self._execute_google(prompt, workspace, skill_path, files)

    async def _execute_anthropic(
        self,
        prompt: str,
        workspace: Path,
        skill_path: Optional[Path],
        files: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Execute using Anthropic Claude."""
        start_time = time.time()

        # Build system prompt
        system_prompt = self._build_system_prompt(skill_path, files)
        user_message = self._build_user_message(prompt, workspace, files)

        messages = []
        turn_count = 0
        total_input_tokens = 0
        total_output_tokens = 0
        tool_uses = []

        conversation = [{"role": "user", "content": user_message}]

        try:
            while turn_count < self.config.max_turns:
                turn_count += 1

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system_prompt,
                    messages=conversation,
                    tools=self._get_anthropic_tools(),
                )

                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens

                messages.append({
                    "turn": turn_count,
                    "role": "assistant",
                    "content": str(response.content),
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                })

                conversation.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "end_turn":
                    break
                elif response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_uses.append({
                                "turn": turn_count,
                                "tool": block.name,
                                "input": block.input,
                            })
                            result = await self._execute_tool(block.name, block.input, workspace)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })
                    if tool_results:
                        conversation.append({"role": "user", "content": tool_results})
                else:
                    break

            final_response = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_response += block.text

            return {
                "workspace": str(workspace),
                "prompt": prompt,
                "provider": "anthropic",
                "model": self.model,
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
                "duration_seconds": time.time() - start_time,
                "exit_code": 0,
            }

        except anthropic.APIError as e:
            return {
                "workspace": str(workspace),
                "prompt": prompt,
                "provider": "anthropic",
                "success": False,
                "error": str(e),
                "exit_code": 1,
                "duration_seconds": time.time() - start_time,
            }

    async def _execute_google(
        self,
        prompt: str,
        workspace: Path,
        skill_path: Optional[Path],
        files: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Execute using Google GenAI."""
        start_time = time.time()

        # Build system instruction
        system_instruction = self._build_system_prompt(skill_path, files)
        user_message = self._build_user_message(prompt, workspace, files)

        messages = []
        turn_count = 0
        total_input_tokens = 0
        total_output_tokens = 0
        tool_uses = []

        # Create config with tools
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
            tools=self._get_google_tools(),
        )

        # Initialize chat
        chat = self.client.aio.chats.create(
            model=self.model,
            config=config,
        )

        try:
            # First user message
            response = await chat.send_message(user_message)
            turn_count = 1

            # Track usage
            if hasattr(response, 'usage_metadata'):
                total_input_tokens += response.usage_metadata.prompt_token_count
                total_output_tokens += response.usage_metadata.candidates_token_count

            messages.append({
                "turn": turn_count,
                "role": "model",
                "text": response.text if hasattr(response, 'text') else "",
            })

            # Agentic loop
            while turn_count < self.config.max_turns:
                # Check for function calls
                if not hasattr(response, 'candidates') or not response.candidates:
                    break

                candidate = response.candidates[0]
                if not hasattr(candidate.content, 'parts'):
                    break

                # Look for function calls
                has_function_call = False
                function_responses = []

                for part in candidate.content.parts:
                    if hasattr(part, 'function_call'):
                        has_function_call = True
                        fc = part.function_call

                        tool_uses.append({
                            "turn": turn_count,
                            "tool": fc.name,
                            "input": dict(fc.args),
                        })

                        # Execute tool
                        result = await self._execute_tool(fc.name, dict(fc.args), workspace)

                        # Create function response
                        function_responses.append(
                            types.Part.from_function_response(
                                name=fc.name,
                                response={"result": result},
                            )
                        )

                if not has_function_call:
                    break

                # Send function responses
                turn_count += 1
                response = await chat.send_message(function_responses)

                if hasattr(response, 'usage_metadata'):
                    total_input_tokens += response.usage_metadata.prompt_token_count
                    total_output_tokens += response.usage_metadata.candidates_token_count

                messages.append({
                    "turn": turn_count,
                    "role": "model",
                    "text": response.text if hasattr(response, 'text') else "",
                })

            # Extract final response
            final_response = response.text if hasattr(response, 'text') else ""

            return {
                "workspace": str(workspace),
                "prompt": prompt,
                "provider": "google",
                "model": self.model,
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
                "duration_seconds": time.time() - start_time,
                "exit_code": 0,
            }

        except Exception as e:
            return {
                "workspace": str(workspace),
                "prompt": prompt,
                "provider": "google",
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
        parts.append("You are a helpful AI assistant. Complete the user's request to the best of your ability.")

        if skill_path and (skill_path / "SKILL.md").exists():
            skill_md = (skill_path / "SKILL.md").read_text()
            parts.append("\n## Skill Guidance\n")
            parts.append("You have access to the following skill guidance:\n")
            parts.append(skill_md)
            parts.append("\nFollow this guidance when completing the task.")

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
        parts.append(f"\nWorking directory: {workspace}")

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

    def _get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Anthropic."""
        return [
            {
                "name": "write_file",
                "description": "Write content to a file in the workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to workspace"},
                        "content": {"type": "string", "description": "File content to write"},
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
                        "path": {"type": "string", "description": "File path relative to workspace"},
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
                        "path": {"type": "string", "description": "Directory path", "default": "."},
                    },
                },
            },
            {
                "name": "execute_bash",
                "description": "Execute a bash command in the workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Bash command to execute"},
                    },
                    "required": ["command"],
                },
            },
        ]

    def _get_google_tools(self) -> List[types.Tool]:
        """Get tool definitions for Google GenAI."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="write_file",
                        description="Write content to a file in the workspace",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(type=types.Type.STRING, description="File path relative to workspace"),
                                "content": types.Schema(type=types.Type.STRING, description="File content to write"),
                            },
                            required=["path", "content"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="read_file",
                        description="Read content from a file in the workspace",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(type=types.Type.STRING, description="File path relative to workspace"),
                            },
                            required=["path"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="list_files",
                        description="List files in the workspace",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(type=types.Type.STRING, description="Directory path (default: workspace root)"),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="execute_bash",
                        description="Execute a bash command in the workspace",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "command": types.Schema(type=types.Type.STRING, description="Bash command to execute"),
                            },
                            required=["command"],
                        ),
                    ),
                ]
            )
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
                return file_path.read_text()

            elif tool_name == "list_files":
                dir_path = workspace / tool_input.get("path", ".")
                if not dir_path.exists():
                    return f"Error: Directory not found"
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


class MultiProviderExecutor:
    """Executor supporting multiple LLM providers with .env configuration."""

    def __init__(self, config=None):
        """Initialize executor with .env configuration."""
        # Load environment configuration
        self.env_config = load_env_config()

        # Determine active provider
        provider_str = get_active_provider(self.env_config)
        provider = Provider.GOOGLE if provider_str == "google" else Provider.ANTHROPIC

        # Get model for provider
        model = get_model_for_provider(self.env_config, provider_str)

        # Create agent config with settings from .env
        self.agent_config = AgentConfig(
            provider=provider,
            model=model,
            max_tokens=self.env_config.max_tokens,
            max_turns=self.env_config.max_turns,
            timeout_seconds=self.env_config.timeout_seconds,
            temperature=self.env_config.temperature,
        )

    def check_available(self) -> bool:
        """Check if executor is available."""
        provider = self.agent_config.provider

        if provider == Provider.ANTHROPIC:
            return ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY") is not None
        elif provider == Provider.GOOGLE:
            return GOOGLE_AVAILABLE and os.getenv("GOOGLE_API_KEY") is not None

        return False

    async def execute_baseline(
        self,
        skill_path: Path,
        eval_case: Dict[str, Any],
        workspace: Path,
    ) -> Dict[str, Any]:
        """Execute WITHOUT skill."""
        agent = MultiProviderAgent(self.agent_config, self.env_config)

        result = await agent.execute(
            prompt=eval_case["prompt"],
            workspace=workspace / "baseline",
            skill_path=None,
            files=eval_case.get("files"),
        )

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
        """Execute WITH skill."""
        agent = MultiProviderAgent(self.agent_config, self.env_config)

        result = await agent.execute(
            prompt=eval_case["prompt"],
            workspace=workspace / "with_skill",
            skill_path=skill_path,
            files=eval_case.get("files"),
        )

        trace_file = workspace / "with_skill" / "trace.json"
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        trace_file.write_text(json.dumps(result, indent=2))

        result["trace_file"] = trace_file
        result["workspace"] = workspace / "with_skill"

        return result


# Synchronous wrapper
class MultiProviderExecutorSync:
    """Synchronous wrapper for MultiProviderExecutor."""

    def __init__(self, config=None):
        self.executor = MultiProviderExecutor(config)

    def check_available(self) -> bool:
        return self.executor.check_available()

    def execute_baseline(self, skill_path: Path, eval_case: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        return asyncio.run(self.executor.execute_baseline(skill_path, eval_case, workspace))

    def execute_with_skill(self, skill_path: Path, eval_case: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        return asyncio.run(self.executor.execute_with_skill(skill_path, eval_case, workspace))


# TraceAnalyzer (same as before)
class TraceAnalyzer:
    """Analyze execution traces for behavioral issues."""

    def analyze_trace(self, trace_file: Path) -> Dict[str, Any]:
        """Load and parse trace file."""
        if not trace_file or not trace_file.exists():
            return {
                "total_tokens": 0,
                "turn_count": 0,
                "tool_uses": 0,
                "success": False,
                "tool_use_list": [],
                "messages": [],
            }

        try:
            with open(trace_file) as f:
                data = json.load(f)
            return {
                "total_tokens": data.get("total_tokens", 0),
                "turn_count": data.get("turn_count", 0),
                "tool_uses": len(data.get("tool_uses", [])),
                "tool_use_list": data.get("tool_uses", []),
                "messages": data.get("messages", []),
                "success": data.get("success", False),
                "duration_seconds": data.get("duration_seconds", 0),
                "provider": data.get("provider", "unknown"),
                "total_input_tokens": data.get("total_input_tokens", 0),
                "total_output_tokens": data.get("total_output_tokens", 0),
            }
        except:
            return {
                "total_tokens": 0,
                "turn_count": 0,
                "tool_uses": 0,
                "success": False,
                "tool_use_list": [],
                "messages": [],
            }

    def detect_unbounded_planning(self, trace_data: Dict) -> bool:
        """Detect endless planning without action."""
        turn_count = trace_data.get("turn_count", 0)
        tool_uses = trace_data.get("tool_uses", 0)

        # More than 10 turns but fewer than 3 tool uses = planning without action
        if turn_count > 10 and tool_uses < 3:
            return True

        # More than 25 turns regardless = unbounded
        if turn_count > 25:
            return True

        return False

    def detect_context_rot(self, trace_data: Dict) -> bool:
        """Detect context window exhaustion or degradation."""
        total_tokens = trace_data.get("total_tokens", 0)
        turn_count = trace_data.get("turn_count", 0)

        # More than 100K tokens = approaching limits
        if total_tokens > 100_000:
            return True

        # High token-per-turn ratio indicates bloat
        if turn_count > 0 and (total_tokens / turn_count) > 10_000:
            return True

        return False

    def detect_infinite_loops(self, trace_data: Dict) -> bool:
        """Detect repetitive tool use patterns."""
        tool_use_list = trace_data.get("tool_use_list", [])

        if len(tool_use_list) < 5:
            return False

        # Check for repeated identical tool calls
        tool_signatures = []
        for tool_use in tool_use_list:
            sig = f"{tool_use.get('tool')}:{tool_use.get('args', {}).get('path', '')}"
            tool_signatures.append(sig)

        # If same tool+path called 5+ times, likely loop
        from collections import Counter
        counts = Counter(tool_signatures)
        if any(count >= 5 for count in counts.values()):
            return True

        # Excessive tool uses relative to turns
        turn_count = trace_data.get("turn_count", 0)
        if turn_count > 0 and len(tool_use_list) > turn_count * 3:
            return True

        return False

    def detect_hallucinations(self, trace_data: Dict) -> List[str]:
        """Detect hallucinated success or tool usage."""
        issues = []

        if not trace_data.get("success", False):
            issues.append("Execution failed - may indicate hallucinated tools")

        # Check for claims of success without actual tool use
        messages = trace_data.get("messages", [])
        tool_uses = trace_data.get("tool_uses", 0)

        success_keywords = ["completed", "finished", "done", "success", "created"]
        for msg in messages:
            text = msg.get("text", "") or ""
            text = text.lower() if text else ""
            if text and any(keyword in text for keyword in success_keywords) and tool_uses == 0:
                issues.append("Claimed success without any tool use")
                break

        return issues

    def detect_planning_without_action(self, trace_data: Dict) -> bool:
        """Detect high ratio of thinking to doing."""
        turn_count = trace_data.get("turn_count", 0)
        tool_uses = trace_data.get("tool_uses", 0)

        # More than 5 turns with 0-1 tool uses
        if turn_count >= 5 and tool_uses <= 1:
            return True

        # More than 10 turns with less than 20% tool use ratio
        if turn_count >= 10 and tool_uses < (turn_count * 0.2):
            return True

        return False

    def detect_repetition(self, trace_data: Dict) -> bool:
        """Detect if agent is repeating itself."""
        messages = trace_data.get("messages", [])

        if len(messages) < 3:
            return False

        # Get last 5 messages
        recent_messages = messages[-5:]
        texts = [msg.get("text", "") for msg in recent_messages]

        # Check for very similar consecutive messages
        for i in range(len(texts) - 1):
            if texts[i] and texts[i+1]:
                # Simple similarity: check if 50%+ of words are same
                words1 = set(texts[i].lower().split())
                words2 = set(texts[i+1].lower().split())
                if words1 and words2:
                    overlap = len(words1 & words2)
                    similarity = overlap / min(len(words1), len(words2))
                    if similarity > 0.7:
                        return True

        return False

    def count_api_calls(self, trace_data: Dict) -> Dict[str, int]:
        """Count different types of API calls."""
        tool_use_list = trace_data.get("tool_use_list", [])

        api_counts = {
            "llm_calls": trace_data.get("turn_count", 0),
            "file_operations": 0,
            "bash_commands": 0,
            "total_tool_uses": len(tool_use_list),
        }

        for tool_use in tool_use_list:
            tool_name = tool_use.get("tool", "")
            if tool_name in ["write_file", "read_file", "list_files"]:
                api_counts["file_operations"] += 1
            elif tool_name == "execute_bash":
                api_counts["bash_commands"] += 1

        return api_counts

    def calculate_efficiency_score(self, trace_data: Dict) -> float:
        """Calculate how efficiently the agent operated."""
        turn_count = trace_data.get("turn_count", 0)
        tool_uses = trace_data.get("tool_uses", 0)
        success = trace_data.get("success", False)

        if turn_count == 0:
            return 0.0

        # Start at 100
        score = 100.0

        # Penalize excessive turns
        if turn_count > 15:
            score -= min(30, (turn_count - 15) * 2)

        # Penalize low tool use ratio (planning without action)
        if turn_count > 5:
            tool_ratio = tool_uses / turn_count
            if tool_ratio < 0.3:
                score -= 20

        # Penalize if didn't succeed
        if not success:
            score -= 30

        # Penalize high token usage
        tokens_per_turn = trace_data.get("total_tokens", 0) / turn_count if turn_count > 0 else 0
        if tokens_per_turn > 5000:
            score -= 15

        return max(0.0, min(100.0, score))

    def calculate_cost(self, trace_data: Dict) -> float:
        """Calculate cost based on provider."""
        total_tokens = trace_data.get("total_tokens", 0)
        provider = trace_data.get("provider", "google")

        if provider == "anthropic":
            # Claude Sonnet 4: $3/1M input, $15/1M output
            input_tokens = total_tokens * 0.6
            output_tokens = total_tokens * 0.4
            return (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0
        else:
            # Google Gemini 2.0 Flash: Free tier or very cheap
            # $0.075/1M input, $0.30/1M output
            input_tokens = total_tokens * 0.6
            output_tokens = total_tokens * 0.4
            return (input_tokens / 1_000_000) * 0.075 + (output_tokens / 1_000_000) * 0.30
