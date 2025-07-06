"""
MCP service for AI self-configuration and natural language parameter adjustment.

This service provides LLM-agnostic capability discovery and execution,
allowing any LLM to modify its own parameters through natural language.
"""

import re
from typing import Dict, Any, Optional, List

from common.logging import get_logger
from .parameter_schemas import (
    ModelParameterSchemas,
    PopularModels,
    ParameterConstraint,
    ParameterType,
)

logger = get_logger(__name__)


class MCPSelfConfigService:
    """MCP service for AI self-configuration capabilities."""

    def __init__(self, runtime_config_manager=None):
        """Initialize the MCP self-configuration service."""
        self.runtime_config_manager = runtime_config_manager
        self.capability_id = "ai_self_configuration"

        logger.info(
            "MCP service initialized",
            service="self_configuration",
            supported_providers=list(PopularModels.PHASE_1_MODELS.keys()),
        )

    async def discover_capabilities(self) -> Dict[str, Any]:
        """
        Discover available self-configuration capabilities.

        Returns capability information with current provider context and constraints.
        """
        try:
            # Get current configuration
            current_config = self._get_current_config()
            provider = current_config.get("provider", "openai")
            model = current_config.get("model", "gpt-4o-mini")

            # Get parameter schema for current model
            schema = ModelParameterSchemas.get_model_schema(provider, model)

            # Build capability response with full context
            capability = {
                "id": self.capability_id,
                "name": "AI Self-Configuration",
                "description": "Modify AI response parameters using natural language commands",
                "current_context": {
                    "provider": provider,
                    "model": model,
                    "supported": PopularModels.is_supported_model(provider, model),
                    "current_parameters": self._extract_current_parameters(current_config, schema),
                    "available_parameters": self._build_parameter_descriptions(schema),
                },
                "usage_examples": [
                    "Make responses more creative and detailed",
                    "Reduce randomness and be more focused",
                    "Set temperature to 0.8",
                    "Make responses shorter and more concise",
                    "Turn up creativity to maximum",
                    "Reset to default settings",
                ],
                "confidence_framework": {
                    "high_confidence": "Act immediately (>80% confidence)",
                    "medium_confidence": "Act with explanation (40-80% confidence)",
                    "low_confidence": "Ask for clarification (<40% confidence)",
                    "explicit_wild": "Creative interpretation on request",
                },
            }

            logger.info(
                "MCP capability discovered",
                provider=provider,
                model=model,
                parameters_available=len(schema),
                supported=capability["current_context"]["supported"],
            )

            return capability

        except Exception as e:
            logger.error("MCP discovery error", error=str(e), service="self_configuration")
            raise

    async def execute_natural_language_adjustment(
        self, natural_request: str, user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a natural language parameter adjustment request.

        Args:
            natural_request: User's natural language request
            user_context: Optional additional context from user

        Returns:
            Execution result with status, confidence, and explanation
        """
        try:
            # Get current configuration and schema
            current_config = self._get_current_config()
            provider = current_config.get("provider", "openai")
            model = current_config.get("model", "gpt-4o-mini")
            schema = ModelParameterSchemas.get_model_schema(provider, model)

            # Interpret the natural language request
            interpretation = await self._interpret_request(
                natural_request, schema, current_config, provider, model
            )

            # Execute based on confidence level
            if interpretation["confidence"] > 0.8:
                # High confidence - apply immediately
                result = await self._apply_adjustments(
                    interpretation["adjustments"], provider, model, schema
                )

                return {
                    "status": "applied",
                    "confidence": interpretation["confidence"],
                    "adjustments": interpretation["adjustments"],
                    "explanation": interpretation["explanation"],
                    "applied_values": result["applied_values"],
                    "message": f"✅ Applied changes with {interpretation['confidence'] * 100:.0f}% confidence: {interpretation['explanation']}",
                }

            elif interpretation["confidence"] > 0.4:
                # Medium confidence - apply with explanation
                result = await self._apply_adjustments(
                    interpretation["adjustments"], provider, model, schema
                )

                return {
                    "status": "applied_with_explanation",
                    "confidence": interpretation["confidence"],
                    "adjustments": interpretation["adjustments"],
                    "explanation": interpretation["explanation"],
                    "applied_values": result["applied_values"],
                    "message": f"⚠️ Applied changes with {interpretation['confidence'] * 100:.0f}% confidence: {interpretation['explanation']}. Let me know if this isn't what you wanted!",
                }

            else:
                # Low confidence - ask for clarification
                return {
                    "status": "clarification_needed",
                    "confidence": interpretation["confidence"],
                    "suggested_adjustments": interpretation.get("adjustments", {}),
                    "explanation": interpretation["explanation"],
                    "clarification_request": self._build_clarification_request(
                        schema, current_config, provider
                    ),
                    "message": f"🤔 I'm not sure how to interpret '{natural_request}'. Could you be more specific?",
                }

        except Exception as e:
            logger.error(
                "MCP execution error",
                error=str(e),
                request=natural_request,
                service="self_configuration",
            )

            return {
                "status": "error",
                "confidence": 0.0,
                "error": str(e),
                "message": f"❌ Error processing request: {str(e)}",
            }

    async def _interpret_request(
        self,
        request: str,
        schema: Dict[str, ParameterConstraint],
        current_config: Dict[str, Any],
        provider: str,
        model: str,
    ) -> Dict[str, Any]:
        """
        Interpret natural language request and determine parameter adjustments.

        This uses pattern matching and semantic analysis to understand user intent.
        In production, this could be enhanced with LLM-based interpretation.
        """
        request_lower = request.lower()
        adjustments = {}
        confidence = 0.5  # Start with medium confidence
        explanations = []

        # Temperature adjustments
        if "temperature" in schema:
            temp_constraint = schema["temperature"]
            temp_adjustment, temp_confidence, temp_explanation = self._interpret_temperature(
                request_lower, temp_constraint, current_config
            )
            if temp_adjustment is not None:
                adjustments["temperature"] = temp_adjustment
                confidence = max(confidence, temp_confidence)
                explanations.append(temp_explanation)

        # Token limit adjustments
        token_param = self._get_token_parameter_name(schema)
        if token_param and token_param in schema:
            token_constraint = schema[token_param]
            token_adjustment, token_confidence, token_explanation = self._interpret_tokens(
                request_lower, token_constraint, current_config, token_param
            )
            if token_adjustment is not None:
                adjustments[token_param] = token_adjustment
                confidence = max(confidence, token_confidence)
                explanations.append(token_explanation)

        # Top-p adjustments
        if "top_p" in schema and any(
            word in request_lower for word in ["top_p", "nucleus", "focus"]
        ):
            top_p_adjustment, top_p_confidence, top_p_explanation = self._interpret_top_p(
                request_lower, schema["top_p"], current_config
            )
            if top_p_adjustment is not None:
                adjustments["top_p"] = top_p_adjustment
                confidence = max(confidence, top_p_confidence)
                explanations.append(top_p_explanation)

        # Penalty adjustments (OpenAI only)
        if "frequency_penalty" in schema:
            penalty_adjustments, penalty_confidence, penalty_explanations = (
                self._interpret_penalties(request_lower, schema, current_config)
            )
            adjustments.update(penalty_adjustments)
            if penalty_adjustments:
                confidence = max(confidence, penalty_confidence)
                explanations.extend(penalty_explanations)

        # Explicit value assignments (e.g., "set temperature to 0.8")
        explicit_adjustments, explicit_confidence, explicit_explanations = (
            self._interpret_explicit_values(request_lower, schema, current_config)
        )
        adjustments.update(explicit_adjustments)
        if explicit_adjustments:
            confidence = max(confidence, explicit_confidence)
            explanations.extend(explicit_explanations)

        # Reset to defaults
        if any(phrase in request_lower for phrase in ["reset", "default", "restore"]):
            adjustments = self._get_default_values(schema)
            confidence = 0.9
            explanations = ["Reset all parameters to defaults"]

        # Wild guess request
        if any(phrase in request_lower for phrase in ["wild guess", "surprise me", "random"]):
            confidence = 0.6  # Medium confidence for creative requests

        return {
            "adjustments": adjustments,
            "confidence": confidence,
            "explanation": (
                "; ".join(explanations)
                if explanations
                else "No clear parameter adjustments identified"
            ),
        }

    def _interpret_temperature(
        self, request: str, constraint: ParameterConstraint, current_config: Dict[str, Any]
    ) -> tuple[Optional[float], float, str]:
        """Interpret temperature-related requests."""

        current_temp = current_config.get("temperature", constraint.default or 0.7)

        # Creative/high temperature terms
        creative_terms = [
            ("creative", 0.9, 0.85),
            ("colorful", 1.2, 0.9),
            ("whimsical", 1.1, 0.9),
            ("wild", 1.5, 0.95),
            ("artistic", 1.3, 0.9),
            ("experimental", 1.4, 0.9),
            ("chaotic", 1.6, 0.95),
            ("spicy", 1.1, 0.8),
            ("intense", 1.7, 0.95),
            ("exciting", 1.0, 0.8),
            ("effervescent", 1.2, 0.75),
        ]

        # Conservative/low temperature terms
        conservative_terms = [
            ("precise", 0.1, 0.9),
            ("focused", 0.3, 0.9),
            ("conservative", 0.2, 0.85),
            ("strict", 0.1, 0.85),
            ("deterministic", 0.0, 0.95),
            ("boring", 0.1, 0.8),
            ("safe", 0.3, 0.8),
            ("professional", 0.4, 0.8),
        ]

        # Balanced terms
        balanced_terms = [
            ("balanced", 0.7, 0.85),
            ("normal", 0.7, 0.8),
            ("standard", 0.7, 0.8),
            ("default", constraint.default or 0.7, 0.9),
        ]

        # Check for explicit temperature values
        temp_match = re.search(r"temperature.*?(\d+\.?\d*)", request)
        if temp_match:
            value = float(temp_match.group(1))
            # Clamp to valid range
            if constraint.min_value is not None and constraint.max_value is not None:
                value = max(constraint.min_value, min(constraint.max_value, value))
            elif constraint.min_value is not None:
                value = max(constraint.min_value, value)
            elif constraint.max_value is not None:
                value = min(constraint.max_value, value)
            return value, 0.95, f"Set temperature to {value}"

        # Check for creative terms
        for term, openai_value, confidence in creative_terms:
            if term in request:
                # Adjust for provider constraints
                value = openai_value
                if constraint.max_value is not None:
                    value = min(openai_value, constraint.max_value)
                if constraint.min_value is not None:
                    value = max(constraint.min_value, value)
                return value, confidence, f"Increased creativity ('{term}' → temp: {value})"

        # Check for conservative terms
        for term, value, confidence in conservative_terms:
            if term in request:
                return value, confidence, f"Reduced randomness ('{term}' → temp: {value})"

        # Check for balanced terms
        for term, value, confidence in balanced_terms:
            if term in request:
                return value, confidence, f"Set to balanced setting ('{term}' → temp: {value})"

        # Check for relative adjustments
        if any(phrase in request for phrase in ["more creative", "increase creativity", "turn up"]):
            new_value = min(current_temp + 0.3, constraint.max_value)
            return new_value, 0.8, f"Increased creativity (temp: {current_temp} → {new_value})"

        if any(phrase in request for phrase in ["less creative", "reduce randomness", "turn down"]):
            new_value = max(current_temp - 0.3, constraint.min_value)
            return new_value, 0.8, f"Reduced creativity (temp: {current_temp} → {new_value})"

        if "maximum" in request or "max" in request:
            return (
                constraint.max_value,
                0.9,
                f"Set to maximum creativity (temp: {constraint.max_value})",
            )

        if "minimum" in request or "min" in request:
            return (
                constraint.min_value,
                0.9,
                f"Set to minimum creativity (temp: {constraint.min_value})",
            )

        return None, 0.0, ""

    def _interpret_tokens(
        self,
        request: str,
        constraint: ParameterConstraint,
        current_config: Dict[str, Any],
        param_name: str,
    ) -> tuple[Optional[int], float, str]:
        """Interpret token limit requests."""

        current_tokens = current_config.get(param_name, constraint.default or 2048)
        if current_tokens is None:
            current_tokens = 2048

        # Length terms
        length_terms = [
            ("verbose", 3000, 0.9),
            ("detailed", 2500, 0.85),
            ("long", 3000, 0.8),
            ("extensive", 4000, 0.8),
            ("comprehensive", 3500, 0.8),
            ("brief", 800, 0.9),
            ("concise", 1000, 0.9),
            ("short", 800, 0.85),
            ("laconic", 600, 0.9),
            ("terse", 500, 0.8),
        ]

        # Check for explicit token values
        token_match = re.search(r"(?:tokens?|length).*?(\d+)", request)
        if token_match:
            value = int(token_match.group(1))
            if constraint.min_value is not None and constraint.max_value is not None:
                value = max(int(constraint.min_value), min(int(constraint.max_value), value))
            elif constraint.min_value is not None:
                value = max(int(constraint.min_value), value)
            elif constraint.max_value is not None:
                value = min(int(constraint.max_value), value)
            return value, 0.95, f"Set {param_name} to {value}"

        # Check for length terms
        for term, target_value, confidence in length_terms:
            if term in request:
                value = int(target_value)  # Ensure integer for token values
                if constraint.min_value is not None and constraint.max_value is not None:
                    value = max(int(constraint.min_value), min(int(constraint.max_value), value))
                elif constraint.min_value is not None:
                    value = max(int(constraint.min_value), value)
                elif constraint.max_value is not None:
                    value = min(int(constraint.max_value), value)
                return value, confidence, f"Adjusted length ('{term}' → {param_name}: {value})"

        # Relative adjustments
        if any(phrase in request for phrase in ["longer", "more detailed", "increase length"]):
            new_value = min(current_tokens + 1000, constraint.max_value)
            return (
                new_value,
                0.8,
                f"Increased length ({param_name}: {current_tokens} → {new_value})",
            )

        if any(phrase in request for phrase in ["shorter", "more concise", "reduce length"]):
            new_value = max(current_tokens - 1000, constraint.min_value)
            return new_value, 0.8, f"Reduced length ({param_name}: {current_tokens} → {new_value})"

        return None, 0.0, ""

    def _interpret_top_p(
        self, request: str, constraint: ParameterConstraint, current_config: Dict[str, Any]
    ) -> tuple[Optional[float], float, str]:
        """Interpret top-p nucleus sampling requests."""

        # Look for explicit top_p values
        top_p_match = re.search(r"top_p.*?(\d+\.?\d*)", request)
        if top_p_match:
            value = float(top_p_match.group(1))
            if constraint.min_value is not None and constraint.max_value is not None:
                value = max(constraint.min_value, min(constraint.max_value, value))
            elif constraint.min_value is not None:
                value = max(constraint.min_value, value)
            elif constraint.max_value is not None:
                value = min(constraint.max_value, value)
            return value, 0.95, f"Set top_p to {value}"

        if "focus" in request or "narrow" in request:
            return 0.8, 0.7, "Increased focus (top_p: 0.8)"

        if "diverse" in request or "broad" in request:
            return 1.0, 0.7, "Increased diversity (top_p: 1.0)"

        return None, 0.0, ""

    def _interpret_penalties(
        self, request: str, schema: Dict[str, ParameterConstraint], current_config: Dict[str, Any]
    ) -> tuple[Dict[str, float], float, List[str]]:
        """Interpret penalty parameter requests (OpenAI only)."""

        adjustments = {}
        explanations = []
        confidence = 0.0

        if "repetition" in request or "repeat" in request:
            if "frequency_penalty" in schema:
                adjustments["frequency_penalty"] = 0.5
                explanations.append("Added repetition penalty (frequency_penalty: 0.5)")
                confidence = 0.8

        if "new topic" in request or "presence" in request:
            if "presence_penalty" in schema:
                adjustments["presence_penalty"] = 0.5
                explanations.append("Encouraged new topics (presence_penalty: 0.5)")
                confidence = 0.8

        return adjustments, confidence, explanations

    def _interpret_explicit_values(
        self, request: str, schema: Dict[str, ParameterConstraint], current_config: Dict[str, Any]
    ) -> tuple[Dict[str, Any], float, List[str]]:
        """Interpret explicit parameter value assignments."""

        adjustments = {}
        explanations = []
        confidence = 0.0

        # Pattern: "set X to Y"
        for param_name, constraint in schema.items():
            pattern = f"(?:set\\s+)?{param_name}\\s+(?:to\\s+)?(\\d+\\.?\\d*)"
            match = re.search(pattern, request)
            if match:
                value = float(match.group(1))
                if constraint.param_type == ParameterType.INTEGER:
                    value = int(value)

                # Validate against constraints
                if constraint.min_value is not None:
                    value = max(constraint.min_value, value)
                if constraint.max_value is not None:
                    value = min(constraint.max_value, value)

                adjustments[param_name] = value
                explanations.append(f"Set {param_name} to {value}")
                confidence = 0.95

        return adjustments, confidence, explanations

    def _get_token_parameter_name(self, schema: Dict[str, ParameterConstraint]) -> Optional[str]:
        """Get the token parameter name for the current schema."""
        if "max_tokens" in schema:
            return "max_tokens"
        elif "max_output_tokens" in schema:
            return "max_output_tokens"
        elif "max_completion_tokens" in schema:
            return "max_completion_tokens"
        return None

    def _get_default_values(self, schema: Dict[str, ParameterConstraint]) -> Dict[str, Any]:
        """Get default values for all parameters in schema."""
        defaults = {}
        for param_name, constraint in schema.items():
            if constraint.default is not None:
                defaults[param_name] = constraint.default
        return defaults

    async def _apply_adjustments(
        self,
        adjustments: Dict[str, Any],
        provider: str,
        model: str,
        schema: Dict[str, ParameterConstraint],
    ) -> Dict[str, Any]:
        """Apply parameter adjustments to the runtime configuration."""

        applied_values = {}

        for param_name, value in adjustments.items():
            if param_name in schema:
                constraint = schema[param_name]

                # Validate value against constraints
                validated_value = self._validate_parameter_value(value, constraint)
                applied_values[param_name] = validated_value

                # Apply to runtime config (this would integrate with your runtime config system)
                if self.runtime_config_manager:
                    await self.runtime_config_manager.update_parameter(
                        provider, model, param_name, validated_value
                    )

        logger.info(
            "MCP parameters applied", provider=provider, model=model, adjustments=applied_values
        )

        return {"applied_values": applied_values}

    def _validate_parameter_value(self, value: Any, constraint: ParameterConstraint) -> Any:
        """Validate a parameter value against its constraints."""

        # Type conversion
        if constraint.param_type == ParameterType.INTEGER and isinstance(value, float):
            value = int(value)
        elif constraint.param_type == ParameterType.FLOAT and isinstance(value, int):
            value = float(value)

        # Range validation
        if constraint.min_value is not None and isinstance(value, (int, float)):
            value = max(constraint.min_value, value)
        if constraint.max_value is not None and isinstance(value, (int, float)):
            value = min(constraint.max_value, value)

        # Enum validation
        if constraint.enum_values and value not in constraint.enum_values:
            value = constraint.default or constraint.enum_values[0]

        return value

    def _extract_current_parameters(
        self, config: Dict[str, Any], schema: Dict[str, ParameterConstraint]
    ) -> Dict[str, Any]:
        """Extract current parameter values from config."""
        current = {}
        for param_name, constraint in schema.items():
            value = config.get(param_name, constraint.default)
            current[param_name] = {
                "value": value,
                "default": constraint.default,
                "is_default": value == constraint.default,
            }
        return current

    def _build_parameter_descriptions(
        self, schema: Dict[str, ParameterConstraint]
    ) -> Dict[str, Any]:
        """Build human-readable parameter descriptions."""
        descriptions = {}
        for param_name, constraint in schema.items():
            descriptions[param_name] = {
                "type": constraint.param_type.value,
                "range": (
                    f"{constraint.min_value}-{constraint.max_value}"
                    if constraint.min_value is not None
                    else "any"
                ),
                "default": constraint.default,
                "required": constraint.required,
                "description": constraint.description,
            }
        return descriptions

    def _build_clarification_request(
        self, schema: Dict[str, ParameterConstraint], current_config: Dict[str, Any], provider: str
    ) -> str:
        """Build a clarification request with available options."""

        lines = [f"I can adjust these parameters for {provider}:"]

        for param_name, constraint in schema.items():
            current_value = current_config.get(param_name, constraint.default)
            range_info = ""
            if constraint.min_value is not None and constraint.max_value is not None:
                range_info = f" (range: {constraint.min_value}-{constraint.max_value})"

            lines.append(f"• {param_name}: {constraint.description}{range_info}")
            lines.append(f"  Currently: {current_value}")

        lines.append("\nTry being more specific, like:")
        lines.append("• 'Make it more creative' (temperature)")
        lines.append("• 'Make responses longer' (tokens)")
        lines.append("• 'Set temperature to 0.8'")

        return "\n".join(lines)

    def _get_current_config(self) -> Dict[str, Any]:
        """Get current configuration from runtime config manager."""
        if self.runtime_config_manager:
            return self.runtime_config_manager.get_active_provider_config()
        else:
            # Fallback for testing
            return {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2048,
            }
