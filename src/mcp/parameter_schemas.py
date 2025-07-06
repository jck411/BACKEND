"""
Comprehensive parameter schemas for AI providers based on official API documentation.

This module defines the complete parameter space for each provider and model,
including constraints, defaults, and model-specific variations.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum


class ParameterType(Enum):
    """Parameter data types."""

    FLOAT = "float"
    INTEGER = "integer"
    STRING = "string"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ParameterConstraint:
    """Parameter constraint definition."""

    name: str
    param_type: ParameterType
    min_value: Optional[Union[float, int]] = None
    max_value: Optional[Union[float, int]] = None
    default: Optional[Any] = None
    required: bool = False
    enum_values: Optional[List[str]] = None
    max_items: Optional[int] = None
    description: str = ""


class ModelParameterSchemas:
    """Comprehensive parameter schemas for all supported models."""

    # OpenAI Standard Models (gpt-4o, gpt-4o-mini, gpt-4-turbo)
    OPENAI_STANDARD = {
        "temperature": ParameterConstraint(
            name="temperature",
            param_type=ParameterType.FLOAT,
            min_value=0.0,
            max_value=2.0,
            default=1.0,
            description="Controls randomness in responses. 0=deterministic, 2=very creative",
        ),
        "max_tokens": ParameterConstraint(
            name="max_tokens",
            param_type=ParameterType.INTEGER,
            min_value=1,
            max_value=4096,
            default=None,
            description="Maximum number of tokens to generate",
        ),
        "top_p": ParameterConstraint(
            name="top_p",
            param_type=ParameterType.FLOAT,
            min_value=0.0,
            max_value=1.0,
            default=1.0,
            description="Nucleus sampling: only consider tokens with top p probability mass",
        ),
        "frequency_penalty": ParameterConstraint(
            name="frequency_penalty",
            param_type=ParameterType.FLOAT,
            min_value=-2.0,
            max_value=2.0,
            default=0.0,
            description="Penalty for token frequency. Positive values reduce repetition",
        ),
        "presence_penalty": ParameterConstraint(
            name="presence_penalty",
            param_type=ParameterType.FLOAT,
            min_value=-2.0,
            max_value=2.0,
            default=0.0,
            description="Penalty for token presence. Positive values encourage new topics",
        ),
        "seed": ParameterConstraint(
            name="seed",
            param_type=ParameterType.INTEGER,
            default=None,
            description="Random seed for reproducible outputs",
        ),
        "response_format": ParameterConstraint(
            name="response_format",
            param_type=ParameterType.STRING,
            enum_values=["text", "json_object", "json_schema"],
            default="text",
            description="Format of the response",
        ),
        "stop": ParameterConstraint(
            name="stop",
            param_type=ParameterType.ARRAY,
            max_items=4,
            default=None,
            description="Sequences that will stop generation",
        ),
    }

    # OpenAI Reasoning Models (o1-preview, o1-mini)
    OPENAI_REASONING = {
        "max_completion_tokens": ParameterConstraint(
            name="max_completion_tokens",
            param_type=ParameterType.INTEGER,
            min_value=1,
            max_value=32768,
            default=None,
            description="Maximum tokens in completion (reasoning models use this instead of max_tokens)",
        )
        # Note: Reasoning models don't support temperature, top_p, penalties, or streaming
    }

    # Anthropic Claude Models
    ANTHROPIC_CLAUDE = {
        "temperature": ParameterConstraint(
            name="temperature",
            param_type=ParameterType.FLOAT,
            min_value=0.0,
            max_value=1.0,
            default=1.0,
            description="Controls randomness in responses. 0=deterministic, 1=creative",
        ),
        "max_tokens": ParameterConstraint(
            name="max_tokens",
            param_type=ParameterType.INTEGER,
            min_value=1,
            max_value=4096,
            default=4096,
            required=True,
            description="Maximum number of tokens to generate (required for Claude)",
        ),
        "top_p": ParameterConstraint(
            name="top_p",
            param_type=ParameterType.FLOAT,
            min_value=0.0,
            max_value=1.0,
            default=None,
            description="Nucleus sampling parameter",
        ),
        "top_k": ParameterConstraint(
            name="top_k",
            param_type=ParameterType.INTEGER,
            min_value=1,
            max_value=200,
            default=None,
            description="Top-k sampling parameter",
        ),
        "stop_sequences": ParameterConstraint(
            name="stop_sequences",
            param_type=ParameterType.ARRAY,
            max_items=4,
            default=None,
            description="Sequences that will stop generation",
        ),
        "system": ParameterConstraint(
            name="system",
            param_type=ParameterType.STRING,
            default=None,
            description="System message for the conversation",
        ),
    }

    # Google Gemini Models
    GOOGLE_GEMINI = {
        "temperature": ParameterConstraint(
            name="temperature",
            param_type=ParameterType.FLOAT,
            min_value=0.0,
            max_value=1.0,
            default=1.0,
            description="Controls randomness in responses",
        ),
        "max_output_tokens": ParameterConstraint(
            name="max_output_tokens",
            param_type=ParameterType.INTEGER,
            min_value=1,
            max_value=8192,
            default=None,
            description="Maximum number of output tokens",
        ),
        "top_p": ParameterConstraint(
            name="top_p",
            param_type=ParameterType.FLOAT,
            min_value=0.0,
            max_value=1.0,
            default=None,
            description="Nucleus sampling parameter",
        ),
        "top_k": ParameterConstraint(
            name="top_k",
            param_type=ParameterType.INTEGER,
            min_value=1,
            max_value=40,
            default=None,
            description="Top-k sampling parameter",
        ),
        "candidate_count": ParameterConstraint(
            name="candidate_count",
            param_type=ParameterType.INTEGER,
            min_value=1,
            max_value=8,
            default=1,
            description="Number of response candidates to generate",
        ),
        "stop_sequences": ParameterConstraint(
            name="stop_sequences",
            param_type=ParameterType.ARRAY,
            default=None,
            description="Sequences that will stop generation",
        ),
        "safety_settings": ParameterConstraint(
            name="safety_settings",
            param_type=ParameterType.OBJECT,
            default=None,
            description="Safety filter configuration",
        ),
        "response_mime_type": ParameterConstraint(
            name="response_mime_type",
            param_type=ParameterType.STRING,
            enum_values=["text/plain", "application/json"],
            default="text/plain",
            description="MIME type of the response",
        ),
    }

    @classmethod
    def get_model_schema(cls, provider: str, model: str) -> Dict[str, ParameterConstraint]:
        """Get parameter schema for a specific provider and model."""

        # OpenAI models
        if provider == "openai":
            if model in ["o1-preview", "o1-mini"]:
                return cls.OPENAI_REASONING
            else:
                return cls.OPENAI_STANDARD

        # Anthropic models
        elif provider == "anthropic":
            return cls.ANTHROPIC_CLAUDE

        # Gemini models
        elif provider == "gemini":
            return cls.GOOGLE_GEMINI

        # OpenRouter models - use pattern matching
        elif provider == "openrouter":
            return cls._get_openrouter_schema(model)

        else:
            # Unknown provider - return conservative defaults
            return cls._get_conservative_schema()

    @classmethod
    def _get_openrouter_schema(cls, model: str) -> Dict[str, ParameterConstraint]:
        """Get schema for OpenRouter model based on pattern matching."""
        import re

        # Claude-like models
        if re.match(r"anthropic/claude", model):
            return cls.ANTHROPIC_CLAUDE

        # GPT-like models
        elif re.match(r"openai/gpt", model):
            return cls.OPENAI_STANDARD

        # Gemini-like models
        elif re.match(r"google/gemini", model):
            return cls.GOOGLE_GEMINI

        # Unknown OpenRouter model - use conservative defaults
        else:
            return cls._get_conservative_schema()

    @classmethod
    def _get_conservative_schema(cls) -> Dict[str, ParameterConstraint]:
        """Conservative parameter schema for unknown models."""
        return {
            "temperature": ParameterConstraint(
                name="temperature",
                param_type=ParameterType.FLOAT,
                min_value=0.0,
                max_value=1.0,
                default=0.7,
                description="Controls randomness (conservative range)",
            ),
            "max_tokens": ParameterConstraint(
                name="max_tokens",
                param_type=ParameterType.INTEGER,
                min_value=1,
                max_value=2048,
                default=2048,
                description="Maximum tokens (conservative limit)",
            ),
        }


class PopularModels:
    """Most popular models for Phase 1 implementation."""

    PHASE_1_MODELS = {
        "openai": [
            "gpt-4o-mini",  # Current default - fast and cost-effective
            "gpt-4o",  # Most capable standard model
            "o1-preview",  # Reasoning model
            "o1-mini",  # Faster reasoning model
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",  # Current default - balanced capability
            "claude-3-5-haiku-20241022",  # Fast and efficient
        ],
        "gemini": [
            "gemini-1.5-flash",  # Current default - fast
            "gemini-1.5-pro",  # Most capable
        ],
        "openrouter": [
            "anthropic/claude-3-sonnet",  # Popular Claude via OpenRouter
            "openai/gpt-4o",  # Popular GPT via OpenRouter
            "google/gemini-1.5-pro",  # Popular Gemini via OpenRouter
        ],
    }

    @classmethod
    def is_supported_model(cls, provider: str, model: str) -> bool:
        """Check if a model is supported in Phase 1."""
        return model in cls.PHASE_1_MODELS.get(provider, [])

    @classmethod
    def get_supported_models(cls, provider: str) -> List[str]:
        """Get list of supported models for a provider."""
        return cls.PHASE_1_MODELS.get(provider, [])
