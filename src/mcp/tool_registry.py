"""
Tool Registry for MCP Server

This module implements a vendor-agnostic tool registry that provides
runtime tool discovery and execution following MCP standards.

Key Features:
- Runtime tool registration and discovery
- Vendor-agnostic tool interface
- Parameter validation and type checking
- Execution context management
"""

import time
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from common.logging import get_logger

logger = get_logger(__name__)


class ToolParameterType(str, Enum):
    """Standard parameter types for MCP tools."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Standard MCP tool parameter definition."""

    name: str
    type: ToolParameterType
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    pattern: Optional[str] = None  # For string validation
    properties: Optional[Dict[str, "ToolParameter"]] = None  # For object types
    items: Optional["ToolParameter"] = None  # For array types


class Tool(BaseModel):
    """Standard MCP tool definition."""

    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    category: str = "general"
    version: str = "1.0.0"

    class Config:
        arbitrary_types_allowed = True


@dataclass
class ToolExecution:
    """Result of tool execution."""

    success: bool
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class ToolHandler(ABC):
    """Abstract base class for tool handlers."""

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        pass

    @abstractmethod
    def get_tool_definition(self) -> Tool:
        """Get the tool definition for this handler."""
        pass


class ToolRegistry:
    """
    Registry for managing MCP tools with runtime discovery.

    Provides vendor-agnostic tool registration, discovery, and execution.
    """

    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, Tool] = {}
        self.handlers: Dict[str, ToolHandler] = {}

        logger.info(event="tool_registry_initialized", builtin_tools=list(self.tools.keys()))

    async def register_tool(self, tool: Tool) -> None:
        """Register a tool definition."""
        self.tools[tool.name] = tool

        logger.info(
            event="tool_registered",
            tool_name=tool.name,
            parameters_count=len(tool.parameters),
            category=tool.category,
        )

    async def register_tool_handler(self, handler: ToolHandler) -> None:
        """Register a tool with its handler."""
        tool = handler.get_tool_definition()
        await self.register_tool(tool)
        self.handlers[tool.name] = handler

        logger.info(
            event="tool_handler_registered",
            tool_name=tool.name,
            handler_type=type(handler).__name__,
        )

    async def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            if tool_name in self.handlers:
                del self.handlers[tool_name]

            logger.info(event="tool_unregistered", tool_name=tool_name)
            return True

        return False

    async def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return list(self.tools.values())

    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a specific tool definition."""
        return self.tools.get(tool_name)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolExecution:
        """
        Execute a tool with given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            ToolExecution result with success status and results
        """
        start_time = time.time()

        try:
            # Check if tool exists
            if tool_name not in self.tools:
                return ToolExecution(
                    success=False,
                    error=f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}",
                )

            # Check if handler exists
            if tool_name not in self.handlers:
                return ToolExecution(
                    success=False, error=f"No handler found for tool '{tool_name}'"
                )

            tool = self.tools[tool_name]
            handler = self.handlers[tool_name]

            # Validate arguments
            validation_error = self._validate_arguments(tool, arguments)
            if validation_error:
                return ToolExecution(
                    success=False, error=f"Argument validation failed: {validation_error}"
                )

            # Execute tool
            result = await handler.execute(arguments)

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            logger.info(
                event="tool_executed",
                tool_name=tool_name,
                execution_time_ms=execution_time,
                success=True,
            )

            return ToolExecution(success=True, result=result, execution_time_ms=execution_time)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            logger.error(
                event="tool_execution_error",
                tool_name=tool_name,
                error=str(e),
                execution_time_ms=execution_time,
            )

            return ToolExecution(success=False, error=str(e), execution_time_ms=execution_time)

    def _validate_arguments(self, tool: Tool, arguments: Dict[str, Any]) -> Optional[str]:
        """
        Validate tool arguments against parameter schema.

        Returns:
            None if valid, error message if invalid
        """
        try:
            # Check required parameters
            for param in tool.parameters:
                if param.required and param.name not in arguments:
                    return f"Required parameter '{param.name}' is missing"

            # Check parameter types and constraints
            for param_name, value in arguments.items():
                # Find parameter definition
                param_def = None
                for param in tool.parameters:
                    if param.name == param_name:
                        param_def = param
                        break

                if param_def is None:
                    return f"Unknown parameter '{param_name}'"

                # Type validation
                type_error = self._validate_parameter_type(param_def, value)
                if type_error:
                    return f"Parameter '{param_name}': {type_error}"

            return None

        except Exception as e:
            return f"Validation error: {str(e)}"

    def _validate_parameter_type(self, param: ToolParameter, value: Any) -> Optional[str]:
        """
        Validate a single parameter value.

        Returns:
            None if valid, error message if invalid
        """
        if value is None:
            if param.required:
                return "is required but got null"
            return None

        # Type checking
        if param.type == ToolParameterType.STRING:
            if not isinstance(value, str):
                return f"expected string, got {type(value).__name__}"

            if param.pattern and not __import__("re").match(param.pattern, value):
                return f"does not match pattern {param.pattern}"

        elif param.type == ToolParameterType.INTEGER:
            if not isinstance(value, int):
                return f"expected integer, got {type(value).__name__}"

            if param.minimum is not None and value < param.minimum:
                return f"must be >= {param.minimum}"
            if param.maximum is not None and value > param.maximum:
                return f"must be <= {param.maximum}"

        elif param.type == ToolParameterType.NUMBER:
            if not isinstance(value, (int, float)):
                return f"expected number, got {type(value).__name__}"

            if param.minimum is not None and value < param.minimum:
                return f"must be >= {param.minimum}"
            if param.maximum is not None and value > param.maximum:
                return f"must be <= {param.maximum}"

        elif param.type == ToolParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return f"expected boolean, got {type(value).__name__}"

        elif param.type == ToolParameterType.ARRAY:
            if not isinstance(value, list):
                return f"expected array, got {type(value).__name__}"

            # Validate array items if schema provided
            if param.items:
                for i, item in enumerate(value):
                    item_error = self._validate_parameter_type(param.items, item)
                    if item_error:
                        return f"item {i}: {item_error}"

        elif param.type == ToolParameterType.OBJECT:
            if not isinstance(value, dict):
                return f"expected object, got {type(value).__name__}"

        # Enum validation
        if param.enum and value not in param.enum:
            return f"must be one of {param.enum}, got {value}"

        return None

    async def get_tool_categories(self) -> List[str]:
        """Get list of all tool categories."""
        categories = set()
        for tool in self.tools.values():
            categories.add(tool.category)
        return sorted(list(categories))

    async def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category."""
        return [tool for tool in self.tools.values() if tool.category == category]

    async def search_tools(self, query: str) -> List[Tool]:
        """Search tools by name or description."""
        query_lower = query.lower()
        results = []

        for tool in self.tools.values():
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                results.append(tool)

        return results
