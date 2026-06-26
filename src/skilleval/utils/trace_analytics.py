"""
Advanced trace analytics for comprehensive log analysis.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
import statistics


@dataclass
class PerformanceMetrics:
    """Performance analysis metrics."""
    total_duration: float
    avg_turn_time: float
    tokens_per_second: float
    tokens_per_turn: float
    tool_call_latency: float
    slowest_turn: int
    fastest_turn: int


@dataclass
class ToolPattern:
    """Tool usage pattern."""
    sequence: Tuple[str, ...]
    frequency: int
    success_rate: float
    avg_duration: float


@dataclass
class BehaviorMetrics:
    """Behavioral analysis metrics."""
    action_ratio: float
    think_act_pattern: List[str]
    decision_quality: float
    learning_detected: bool
    self_correction_count: int


@dataclass
class SecurityFinding:
    """Security issue found in trace."""
    severity: str
    type: str
    turn: int
    details: str
    pattern_matched: str


class TraceAnalytics:
    """Comprehensive trace file analysis."""

    # Security patterns
    SECRET_PATTERNS = {
        'api_key': r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})',
        'password': r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{8,})',
        'token': r'(?i)(token|secret)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})',
        'aws_key': r'AKIA[0-9A-Z]{16}',
        'google_key': r'AIza[a-zA-Z0-9_\-]{35}',
        'private_key': r'-----BEGIN.*PRIVATE KEY-----',
        'jwt': r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
    }

    DESTRUCTIVE_PATTERNS = {
        'rm_rf': r'rm\s+-rf',
        'drop_table': r'DROP\s+TABLE',
        'delete_from': r'DELETE\s+FROM',
        'git_reset_hard': r'git\s+reset\s+--hard',
        'force_flag': r'--force',
        'truncate': r'truncate\s+table',
        'chmod_777': r'chmod\s+777',
        'sudo': r'sudo\s+rm',
    }

    def __init__(self):
        """Initialize analytics."""
        pass

    def load_trace(self, trace_file: Path) -> Dict[str, Any]:
        """Load trace file."""
        if not trace_file or not trace_file.exists():
            return {}

        try:
            with open(trace_file) as f:
                return json.load(f)
        except:
            return {}

    # ========================================================================
    # 1. Performance Analytics
    # ========================================================================

    def analyze_performance(self, trace: Dict[str, Any]) -> PerformanceMetrics:
        """Detailed performance analysis."""
        if not trace:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0)

        total_duration = trace.get('duration_seconds', 0)
        turn_count = trace.get('turn_count', 1)
        total_tokens = trace.get('total_tokens', 0)
        tool_uses = trace.get('tool_uses', [])

        # Time metrics
        avg_turn_time = total_duration / turn_count if turn_count > 0 else 0
        tokens_per_second = total_tokens / total_duration if total_duration > 0 else 0
        tokens_per_turn = total_tokens / turn_count if turn_count > 0 else 0

        # Tool latency (estimate)
        tool_call_latency = total_duration / len(tool_uses) if tool_uses else 0

        return PerformanceMetrics(
            total_duration=total_duration,
            avg_turn_time=avg_turn_time,
            tokens_per_second=tokens_per_second,
            tokens_per_turn=tokens_per_turn,
            tool_call_latency=tool_call_latency,
            slowest_turn=turn_count if turn_count > 0 else 0,
            fastest_turn=1,
        )

    def calculate_bottlenecks(self, trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks."""
        bottlenecks = []

        perf = self.analyze_performance(trace)

        # High turn time
        if perf.avg_turn_time > 5.0:
            bottlenecks.append({
                'type': 'slow_turns',
                'severity': 'MEDIUM',
                'details': f'Average turn time {perf.avg_turn_time:.2f}s exceeds 5s threshold'
            })

        # Low throughput
        if perf.tokens_per_second < 100:
            bottlenecks.append({
                'type': 'low_throughput',
                'severity': 'LOW',
                'details': f'Token throughput {perf.tokens_per_second:.0f}/s is low'
            })

        # High tool latency
        if perf.tool_call_latency > 3.0:
            bottlenecks.append({
                'type': 'slow_tools',
                'severity': 'HIGH',
                'details': f'Tool calls taking {perf.tool_call_latency:.2f}s on average'
            })

        return bottlenecks

    # ========================================================================
    # 2. Tool Usage Patterns
    # ========================================================================

    def analyze_tool_patterns(self, trace: Dict[str, Any]) -> List[ToolPattern]:
        """Analyze tool usage sequences and patterns."""
        tool_uses = trace.get('tool_uses', [])

        if not tool_uses:
            return []

        # Extract sequences
        tool_sequence = [t.get('tool', 'unknown') for t in tool_uses]

        # Find common patterns (bigrams, trigrams)
        patterns = []

        # Bigrams
        for i in range(len(tool_sequence) - 1):
            patterns.append(tuple(tool_sequence[i:i+2]))

        # Trigrams
        for i in range(len(tool_sequence) - 2):
            patterns.append(tuple(tool_sequence[i:i+3]))

        # Count frequencies
        pattern_counts = Counter(patterns)

        # Convert to ToolPattern objects
        tool_patterns = []
        for pattern, count in pattern_counts.most_common(10):
            tool_patterns.append(ToolPattern(
                sequence=pattern,
                frequency=count,
                success_rate=1.0,  # Would need success tracking per pattern
                avg_duration=0.0,
            ))

        return tool_patterns

    def calculate_tool_effectiveness(self, trace: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Calculate effectiveness metrics per tool."""
        tool_uses = trace.get('tool_uses', [])

        tool_stats = defaultdict(lambda: {
            'calls': 0,
            'successes': 0,
            'failures': 0,
            'total_time': 0.0
        })

        for tool_use in tool_uses:
            tool_name = tool_use.get('tool', 'unknown')
            tool_stats[tool_name]['calls'] += 1

            # Check if successful (would need result tracking)
            if tool_use.get('result', {}).get('success', True):
                tool_stats[tool_name]['successes'] += 1
            else:
                tool_stats[tool_name]['failures'] += 1

        # Calculate rates
        effectiveness = {}
        for tool, stats in tool_stats.items():
            effectiveness[tool] = {
                'calls': stats['calls'],
                'success_rate': stats['successes'] / stats['calls'] if stats['calls'] > 0 else 0,
                'failure_rate': stats['failures'] / stats['calls'] if stats['calls'] > 0 else 0,
            }

        return effectiveness

    # ========================================================================
    # 3. Behavioral Analysis
    # ========================================================================

    def analyze_behavior(self, trace: Dict[str, Any]) -> BehaviorMetrics:
        """Analyze agent behavioral patterns."""
        messages = trace.get('messages', [])
        tool_uses = trace.get('tool_uses', [])
        turn_count = trace.get('turn_count', 0)

        # Build think/act pattern
        pattern = []
        tool_use_turns = set(t.get('turn', 0) for t in tool_uses)

        for i in range(1, turn_count + 1):
            if i in tool_use_turns:
                pattern.append('action')
            else:
                pattern.append('thinking')

        # Calculate action ratio
        action_ratio = pattern.count('action') / len(pattern) if pattern else 0

        # Detect learning (error reduction over time)
        learning_detected = False
        self_correction_count = 0

        # Look for correction patterns in messages
        for i in range(1, len(messages)):
            current_text = messages[i].get('text', '').lower()
            if any(word in current_text for word in ['sorry', 'mistake', 'correction', 'actually', 'instead']):
                self_correction_count += 1

        if self_correction_count > 0:
            learning_detected = True

        # Decision quality (ratio of productive actions)
        decision_quality = action_ratio * 100

        return BehaviorMetrics(
            action_ratio=action_ratio,
            think_act_pattern=pattern,
            decision_quality=decision_quality,
            learning_detected=learning_detected,
            self_correction_count=self_correction_count,
        )

    # ========================================================================
    # 4. Quality Metrics
    # ========================================================================

    def analyze_response_quality(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality of responses over time."""
        messages = trace.get('messages', [])

        if not messages:
            return {'avg_length': 0, 'coherence_score': 0, 'degradation': False}

        # Message lengths
        lengths = [len(msg.get('text', '')) for msg in messages]
        avg_length = sum(lengths) / len(lengths) if lengths else 0

        # Simple coherence: check for decreasing length (potential degradation)
        if len(lengths) >= 3:
            early_avg = sum(lengths[:len(lengths)//2]) / (len(lengths)//2)
            late_avg = sum(lengths[len(lengths)//2:]) / (len(lengths) - len(lengths)//2)
            degradation = late_avg < early_avg * 0.5  # 50% reduction
        else:
            degradation = False

        # Coherence score (simple heuristic)
        coherence_score = 100.0
        if degradation:
            coherence_score -= 30

        return {
            'avg_length': avg_length,
            'message_count': len(messages),
            'coherence_score': coherence_score,
            'degradation_detected': degradation,
            'length_trend': 'decreasing' if degradation else 'stable',
        }

    def analyze_tool_parameters(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quality of tool parameters."""
        tool_uses = trace.get('tool_uses', [])

        issues = []
        good_practices = []

        for tool_use in tool_uses:
            args = tool_use.get('args', {})
            tool = tool_use.get('tool', '')

            # Check path parameters
            if 'path' in args:
                path = args['path']

                # Absolute vs relative
                if path.startswith('/'):
                    issues.append({
                        'turn': tool_use.get('turn'),
                        'issue': 'absolute_path',
                        'details': f'Using absolute path: {path}'
                    })

                # Path traversal
                if '..' in path:
                    issues.append({
                        'turn': tool_use.get('turn'),
                        'issue': 'path_traversal',
                        'severity': 'HIGH',
                        'details': f'Potential path traversal: {path}'
                    })
                else:
                    good_practices.append('safe_paths')

            # Check content quality
            if 'content' in args:
                content = args['content']
                if len(content) > 10000:
                    issues.append({
                        'turn': tool_use.get('turn'),
                        'issue': 'large_content',
                        'details': f'Content size: {len(content)} bytes'
                    })

        return {
            'total_tools': len(tool_uses),
            'issues': issues,
            'good_practices': list(set(good_practices)),
            'quality_score': max(0, 100 - len(issues) * 10),
        }

    # ========================================================================
    # 5. Comparative Analysis
    # ========================================================================

    def compare_traces(self, baseline: Dict[str, Any], skill: Dict[str, Any]) -> Dict[str, Any]:
        """Compare baseline vs skill execution."""
        if not baseline or not skill:
            return {}

        comparison = {
            'turn_reduction': baseline.get('turn_count', 0) - skill.get('turn_count', 0),
            'turn_reduction_pct': 0,
            'token_reduction': baseline.get('total_tokens', 0) - skill.get('total_tokens', 0),
            'token_reduction_pct': 0,
            'time_savings': baseline.get('duration_seconds', 0) - skill.get('duration_seconds', 0),
            'time_savings_pct': 0,
            'tool_efficiency_improvement': 0,
            'success_improvement': 0,
        }

        # Calculate percentages
        if baseline.get('turn_count', 0) > 0:
            comparison['turn_reduction_pct'] = (comparison['turn_reduction'] / baseline['turn_count']) * 100

        if baseline.get('total_tokens', 0) > 0:
            comparison['token_reduction_pct'] = (comparison['token_reduction'] / baseline['total_tokens']) * 100

        if baseline.get('duration_seconds', 0) > 0:
            comparison['time_savings_pct'] = (comparison['time_savings'] / baseline['duration_seconds']) * 100

        # Tool efficiency
        baseline_ratio = len(baseline.get('tool_uses', [])) / baseline.get('turn_count', 1)
        skill_ratio = len(skill.get('tool_uses', [])) / skill.get('turn_count', 1)
        comparison['tool_efficiency_improvement'] = (skill_ratio - baseline_ratio) * 100

        # Success
        comparison['success_improvement'] = int(skill.get('success', False)) - int(baseline.get('success', False))

        return comparison

    # ========================================================================
    # 6. Error Analysis
    # ========================================================================

    def analyze_errors(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and analyze all errors."""
        tool_uses = trace.get('tool_uses', [])

        errors = []
        for tool_use in tool_uses:
            result = tool_use.get('result', {})
            if isinstance(result, dict) and 'error' in result:
                errors.append({
                    'turn': tool_use.get('turn'),
                    'tool': tool_use.get('tool'),
                    'error': result['error'],
                    'args': tool_use.get('args', {}),
                })

        # Categorize errors
        error_types = Counter([e['error'] for e in errors])
        error_tools = Counter([e['tool'] for e in errors])

        # Detect patterns
        patterns = []
        if len(errors) > 3:
            patterns.append('high_error_rate')

        if error_tools:
            most_problematic = error_tools.most_common(1)[0]
            patterns.append(f'tool_{most_problematic[0]}_problematic')

        return {
            'total_errors': len(errors),
            'error_rate': len(errors) / len(tool_uses) if tool_uses else 0,
            'errors': errors[:10],  # First 10
            'error_types': dict(error_types),
            'error_tools': dict(error_tools),
            'patterns': patterns,
        }

    def detect_stuck_points(self, trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect where agent got stuck."""
        tool_uses = trace.get('tool_uses', [])

        if len(tool_uses) < 5:
            return []

        stuck_points = []

        # Check for repeated tool calls
        for i in range(len(tool_uses) - 4):
            window = tool_uses[i:i+5]
            tools = [t.get('tool') for t in window]

            # Same tool 5 times in a row
            if len(set(tools)) == 1:
                stuck_points.append({
                    'turn': window[0].get('turn'),
                    'type': 'repeated_tool',
                    'tool': tools[0],
                    'count': 5,
                })

            # Check for same args
            signatures = [f"{t.get('tool')}:{str(t.get('args'))}" for t in window]
            if len(set(signatures)) == 1:
                stuck_points.append({
                    'turn': window[0].get('turn'),
                    'type': 'identical_calls',
                    'tool': tools[0],
                })

        return stuck_points

    # ========================================================================
    # 7. Security Analysis
    # ========================================================================

    def scan_for_secrets(self, trace: Dict[str, Any]) -> List[SecurityFinding]:
        """Scan for leaked secrets."""
        findings = []
        messages = trace.get('messages', [])
        tool_uses = trace.get('tool_uses', [])

        # Scan messages
        for msg in messages:
            text = msg.get('text', '')
            for secret_type, pattern in self.SECRET_PATTERNS.items():
                matches = re.finditer(pattern, text)
                for match in matches:
                    findings.append(SecurityFinding(
                        severity='CRITICAL',
                        type=f'secret_{secret_type}',
                        turn=msg.get('turn', 0),
                        details=f'Potential {secret_type} leaked: {match.group(0)[:20]}...',
                        pattern_matched=secret_type,
                    ))

        # Scan tool arguments
        for tool_use in tool_uses:
            args_str = str(tool_use.get('args', {}))
            for secret_type, pattern in self.SECRET_PATTERNS.items():
                if re.search(pattern, args_str):
                    findings.append(SecurityFinding(
                        severity='CRITICAL',
                        type=f'secret_{secret_type}_in_args',
                        turn=tool_use.get('turn', 0),
                        details=f'Potential {secret_type} in tool arguments',
                        pattern_matched=secret_type,
                    ))

        return findings

    def scan_for_destructive_actions(self, trace: Dict[str, Any]) -> List[SecurityFinding]:
        """Scan for destructive actions."""
        findings = []
        tool_uses = trace.get('tool_uses', [])

        for tool_use in tool_uses:
            if tool_use.get('tool') == 'execute_bash':
                command = tool_use.get('args', {}).get('command', '')

                for pattern_name, pattern in self.DESTRUCTIVE_PATTERNS.items():
                    if re.search(pattern, command, re.IGNORECASE):
                        findings.append(SecurityFinding(
                            severity='CRITICAL',
                            type=f'destructive_{pattern_name}',
                            turn=tool_use.get('turn', 0),
                            details=f'Destructive command detected: {command}',
                            pattern_matched=pattern_name,
                        ))

        return findings

    # ========================================================================
    # 8. Cost Optimization
    # ========================================================================

    def detailed_cost_analysis(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Detailed cost breakdown and optimization suggestions."""
        provider = trace.get('provider', 'google')
        total_input = trace.get('total_input_tokens', 0)
        total_output = trace.get('total_output_tokens', 0)
        total_tokens = trace.get('total_tokens', total_input + total_output)
        turn_count = trace.get('turn_count', 1)

        # Calculate costs
        if provider == 'anthropic':
            input_rate = 3.0 / 1_000_000
            output_rate = 15.0 / 1_000_000
        else:  # google
            input_rate = 0.075 / 1_000_000
            output_rate = 0.30 / 1_000_000

        input_cost = total_input * input_rate
        output_cost = total_output * output_rate
        total_cost = input_cost + output_cost

        # Calculate waste
        tool_uses = len(trace.get('tool_uses', []))
        if turn_count > 10 and tool_uses < 3:
            wasted_turns = turn_count - 5
            wasted_tokens = (total_tokens / turn_count) * wasted_turns
            wasted_cost = wasted_tokens * ((input_rate + output_rate) / 2)
        else:
            wasted_tokens = 0
            wasted_cost = 0

        return {
            'total_cost': total_cost,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'cost_per_turn': total_cost / turn_count if turn_count > 0 else 0,
            'cost_per_tool': total_cost / tool_uses if tool_uses > 0 else 0,
            'wasted_cost': wasted_cost,
            'wasted_tokens': wasted_tokens,
            'optimization_potential': wasted_cost / total_cost * 100 if total_cost > 0 else 0,
            'provider': provider,
        }


class TraceAggregator:
    """Aggregate analysis across multiple traces."""

    def __init__(self, traces: List[Dict[str, Any]]):
        """Initialize with list of traces."""
        self.traces = traces
        self.analytics = TraceAnalytics()

    def success_patterns(self) -> List[ToolPattern]:
        """Find common patterns in successful executions."""
        successful = [t for t in self.traces if t.get('success', False)]

        all_patterns = []
        for trace in successful:
            patterns = self.analytics.analyze_tool_patterns(trace)
            all_patterns.extend(patterns)

        # Aggregate by sequence
        pattern_map = defaultdict(lambda: {'count': 0, 'success_rate': 0})
        for pattern in all_patterns:
            key = pattern.sequence
            pattern_map[key]['count'] += pattern.frequency
            pattern_map[key]['success_rate'] = 1.0

        # Convert to list
        result = []
        for sequence, data in pattern_map.items():
            result.append(ToolPattern(
                sequence=sequence,
                frequency=data['count'],
                success_rate=data['success_rate'],
                avg_duration=0.0,
            ))

        return sorted(result, key=lambda x: x.frequency, reverse=True)[:10]

    def failure_analysis(self) -> Dict[str, Any]:
        """Analyze why executions failed."""
        failures = [t for t in self.traces if not t.get('success', False)]

        if not failures:
            return {'total_failures': 0}

        reasons = {
            'timeout': 0,
            'error': 0,
            'no_tool_use': 0,
            'excessive_turns': 0,
            'unknown': 0,
        }

        for trace in failures:
            if trace.get('duration_seconds', 0) > 300:
                reasons['timeout'] += 1
            elif 'error' in trace:
                reasons['error'] += 1
            elif len(trace.get('tool_uses', [])) == 0:
                reasons['no_tool_use'] += 1
            elif trace.get('turn_count', 0) > 25:
                reasons['excessive_turns'] += 1
            else:
                reasons['unknown'] += 1

        return {
            'total_failures': len(failures),
            'failure_rate': len(failures) / len(self.traces) * 100,
            'reasons': reasons,
        }

    def cost_distribution(self) -> Dict[str, float]:
        """Analyze cost distribution across traces."""
        costs = []
        for trace in self.traces:
            cost_data = self.analytics.detailed_cost_analysis(trace)
            costs.append(cost_data['total_cost'])

        if not costs:
            return {}

        sorted_costs = sorted(costs)
        return {
            'min': min(costs),
            'max': max(costs),
            'avg': statistics.mean(costs),
            'median': statistics.median(costs),
            'p95': sorted_costs[int(len(costs) * 0.95)] if len(costs) > 20 else max(costs),
            'total': sum(costs),
        }

    def performance_benchmarks(self) -> Dict[str, Any]:
        """Calculate performance benchmarks."""
        if not self.traces:
            return {}

        turn_counts = [t.get('turn_count', 0) for t in self.traces]
        durations = [t.get('duration_seconds', 0) for t in self.traces]
        token_counts = [t.get('total_tokens', 0) for t in self.traces]

        return {
            'avg_turns': statistics.mean(turn_counts) if turn_counts else 0,
            'avg_duration': statistics.mean(durations) if durations else 0,
            'avg_tokens': statistics.mean(token_counts) if token_counts else 0,
            'success_rate': sum(1 for t in self.traces if t.get('success', False)) / len(self.traces) * 100,
        }


class AnomalyDetector:
    """Detect anomalous execution patterns."""

    def detect_outliers(self, traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find statistical outliers in traces."""
        if len(traces) < 10:
            return []

        anomalies = []

        # Turn count outliers
        turn_counts = [t.get('turn_count', 0) for t in traces]
        mean_turns = statistics.mean(turn_counts)
        std_turns = statistics.stdev(turn_counts) if len(turn_counts) > 1 else 1

        for i, trace in enumerate(traces):
            turns = trace.get('turn_count', 0)
            z_score = (turns - mean_turns) / std_turns if std_turns > 0 else 0

            if abs(z_score) > 3:
                anomalies.append({
                    'index': i,
                    'type': 'unusual_turn_count',
                    'value': turns,
                    'z_score': z_score,
                    'severity': 'HIGH' if abs(z_score) > 4 else 'MEDIUM',
                })

        # Behavioral anomalies
        for i, trace in enumerate(traces):
            turns = trace.get('turn_count', 0)
            tools = len(trace.get('tool_uses', []))

            # Many turns, no tools
            if turns > 5 and tools == 0:
                anomalies.append({
                    'index': i,
                    'type': 'no_actions_taken',
                    'turns': turns,
                    'severity': 'HIGH',
                })

            # Excessive tokens
            tokens = trace.get('total_tokens', 0)
            if tokens > 100000:
                anomalies.append({
                    'index': i,
                    'type': 'excessive_tokens',
                    'tokens': tokens,
                    'severity': 'MEDIUM',
                })

        return anomalies
