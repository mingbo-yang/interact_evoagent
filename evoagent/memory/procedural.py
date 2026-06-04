"""ProceduralMemory — reusable action sequences / skills."""

from evoagent.memory.schema import MemoryItem, MemoryType


class ProceduralMemory:
    """Utility for creating procedural (how-to) memories."""

    @staticmethod
    def from_procedure(
        trigger: str, procedure: str, success: bool = True
    ) -> MemoryItem:
        return MemoryItem(
            memory_type=MemoryType.PROCEDURAL,
            content=f"When {trigger}, do: {procedure}",
            metadata={"trigger": trigger, "procedure": procedure},
            success_count=1 if success else 0,
            failure_count=0 if success else 1,
        )
