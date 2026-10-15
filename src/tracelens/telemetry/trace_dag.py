"""Trace DAG tree assembly and performance bottleneck analysis.

Constructs directed acyclic execution graphs from distributed spans,
calculates self-times, identifies the critical path, and detects bottlenecks.
"""

from __future__ import annotations
from tracelens.models.telemetry import TraceSpan


class SpanNode:
    """Node in the trace execution tree representing a single operation span."""

    def __init__(self, span: TraceSpan) -> None:
        self.span: TraceSpan = span
        self.children: list[SpanNode] = []
        self.parent: SpanNode | None = None
        self.duration_ms: float = max(0.0, span.end_time_ms - span.start_time_ms)
        self.self_time_ms: float = self.duration_ms

    def add_child(self, child: SpanNode) -> None:
        """Add child span node and set parent backreference."""
        self.children.append(child)
        child.parent = self

    def __repr__(self) -> str:
        return f"<SpanNode id={self.span.span_id} name={self.span.name} duration={self.duration_ms}ms>"


class TraceDAG:
    """Directed acyclic graph representation of a distributed trace."""

    def __init__(self, nodes: dict[str, SpanNode], root_spans: list[SpanNode]) -> None:
        self.nodes: dict[str, SpanNode] = nodes
        self.root_spans: list[SpanNode] = root_spans

    @classmethod
    def from_spans(cls, spans: list[TraceSpan]) -> TraceDAG:
        """Assemble a hierarchical tree from a flat list of TraceSpans.

        Includes cycle detection to prevent recursion errors when span trees
        contain malformed circular parent references.

        Args:
            spans: List of TraceSpan objects.

        Returns:
            Constructed TraceDAG.
        """
        nodes: dict[str, SpanNode] = {s.span_id: SpanNode(s) for s in spans}
        root_spans: list[SpanNode] = []

        def would_create_cycle(parent_node: SpanNode, child_node: SpanNode) -> bool:
            """Check if adding child_node to parent_node creates a cycle."""
            curr: SpanNode | None = parent_node
            visited = set()
            while curr is not None:
                if curr.span.span_id == child_node.span.span_id or curr.span.span_id in visited:
                    return True
                visited.add(curr.span.span_id)
                curr = curr.parent
            return False

        for span in spans:
            node = nodes[span.span_id]
            parent_id = span.parent_span_id

            if parent_id and parent_id in nodes:
                parent_node = nodes[parent_id]
                if would_create_cycle(parent_node, node):
                    # Prevent cycle by treating node as root instead of cyclical child
                    root_spans.append(node)
                else:
                    parent_node.add_child(node)
            else:
                root_spans.append(node)

        dag = cls(nodes=nodes, root_spans=root_spans)
        dag.calculate_self_times()
        return dag

    def calculate_self_times(self) -> dict[str, float]:
        """Calculate self-time for each span: delta t = t_span - sum(t_children).

        Returns:
            Mapping of span_id to self-time in milliseconds.
        """
        self_times: dict[str, float] = {}

        for span_id, node in self.nodes.items():
            child_durations = sum(child.duration_ms for child in node.children)
            self_time = max(0.0, node.duration_ms - child_durations)
            node.self_time_ms = self_time
            self_times[span_id] = self_time

        return self_times

    def find_critical_path(self, root_span_id: str | None = None) -> list[SpanNode]:
        """Identify the critical path (longest latency path from root to leaf).

        Args:
            root_span_id: Optional specific root span ID to start from.

        Returns:
            List of SpanNodes forming the critical execution path.
        """
        if not self.root_spans:
            return []

        if root_span_id and root_span_id in self.nodes:
            curr: SpanNode | None = self.nodes[root_span_id]
        else:
            # Pick the root span with largest duration
            curr = max(self.root_spans, key=lambda r: r.duration_ms)

        path: list[SpanNode] = [curr]
        visited: set[str] = {curr.span.span_id}

        while curr and curr.children:
            # Pick unvisited child with longest duration
            eligible_children = [c for c in curr.children if c.span.span_id not in visited]
            if not eligible_children:
                break
            next_node = max(eligible_children, key=lambda c: c.duration_ms)
            visited.add(next_node.span.span_id)
            path.append(next_node)
            curr = next_node

        return path

    def detect_bottlenecks(self, threshold_pct: float = 0.5) -> list[SpanNode]:
        """Detect spans whose self-time consumes a significant fraction of total trace duration.

        Args:
            threshold_pct: Fraction of total trace duration threshold (0.0 to 1.0).

        Returns:
            List of bottleneck SpanNodes sorted by self-time descending.
        """
        if not self.root_spans:
            return []

        total_duration = max(r.duration_ms for r in self.root_spans)
        if total_duration <= 0.0:
            return []

        threshold_ms = total_duration * threshold_pct
        bottlenecks = [
            node for node in self.nodes.values()
            if node.self_time_ms >= threshold_ms
        ]
        bottlenecks.sort(key=lambda n: n.self_time_ms, reverse=True)
        return bottlenecks
