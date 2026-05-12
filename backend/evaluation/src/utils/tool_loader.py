"""
Tool Description Loader
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class ToolDescription:

    def __init__(self, tool_id: str, desc: str, input_types: List[str], output_types: List[str]):
        self.id = tool_id
        self.desc = desc
        self.input_types = input_types
        self.output_types = output_types

    def accepts_input(self, input_type: str) -> bool:
        return input_type in self.input_types

    def produces_output(self, output_type: str) -> bool:
        return output_type in self.output_types

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'desc': self.desc,
            'input_types': self.input_types,
            'output_types': self.output_types
        }


class ToolDescriptionLoader:

    def __init__(self, tool_desc_path: str = "/data/raw/tool_desc.json"):
        self.tool_desc_path = Path(tool_desc_path)
        self._tools: Optional[Dict[str, ToolDescription]] = None

    def load(self) -> Dict[str, ToolDescription]:
        if self._tools is not None:
            return self._tools
        with open(self.tool_desc_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._tools = {}
        for tool_data in data.get('nodes', []):
            tool = ToolDescription(
                tool_id=tool_data['id'],
                desc=tool_data.get('desc', ''),
                input_types=tool_data.get('input-type', []),
                output_types=tool_data.get('output-type', [])
            )
            self._tools[tool.id] = tool
        return self._tools

    def get_tool(self, tool_id: str) -> Optional[ToolDescription]:
        if self._tools is None:
            self.load()

        return self._tools.get(tool_id)

    def get_all_tools(self) -> Dict[str, ToolDescription]:
        if self._tools is None:
            self.load()

        return self._tools

    def validate_type_compatibility(
        self,
        source_type: str,
        target_type: str,
        tool_id: str
    ) -> tuple[bool, str]:
        tool = self.get_tool(tool_id)
        if tool is None:
            return False, f"Tool '{tool_id}' not found in tool descriptions"

        if not tool.accepts_input(target_type):
            available_inputs = ", ".join(tool.input_types)
            return False, f"Tool '{tool_id}' expects input types: {available_inputs}, but got: {target_type}"

        return True, "Compatible"

    def get_tool_summary(self) -> Dict:
        tools = self.get_all_tools()

        input_types = set()
        output_types = set()

        for tool in tools.values():
            input_types.update(tool.input_types)
            output_types.update(tool.output_types)

        return {
            'total_tools': len(tools),
            'input_modalities': sorted(list(input_types)),
            'output_modalities': sorted(list(output_types)),
            'modality_count': {
                'input': len(input_types),
                'output': len(output_types)
            }
        }

    def find_tools_by_modality(
        self,
        input_type: Optional[str] = None,
        output_type: Optional[str] = None
    ) -> List[str]:
        tools = self.get_all_tools()
        matching_tools = []

        for tool_id, tool in tools.items():
            if input_type and not tool.accepts_input(input_type):
                continue
            if output_type and not tool.produces_output(output_type):
                continue
            matching_tools.append(tool_id)

        return matching_tools
