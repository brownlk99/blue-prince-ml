# A thin wrapper that hides the differences between OpenAI, Gemini and Anthropic
# chat APIs. The public surface is only two methods:
#
#     client = LLMClient("openai:gpt-3.5-turbo")
#     reply, usage = client.chat(system="You are helpful.", user="Hello!")
#
# Add more providers exactly once, here, instead of sprinkling logic all over
# llm_agent.py

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any, TYPE_CHECKING


class LLMError(Exception):
    """
        Base exception for LLM client errors
    """
    pass


@dataclass
class UsageStats:
    """
        Token usage statistics

            Attributes:
                input_tokens: Number of tokens in the input
                output_tokens: Number of tokens in the output
                total_tokens: Total number of tokens used
    """
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class LLMClient:
    """
        A unified client for multiple LLM providers

            Attributes:
                model_name: Name of the model to use
                provider: Provider inferred from model name
                max_tokens: Maximum tokens for completion
                api_key: API key for authentication
                timeout: Request timeout in seconds
                max_retries: Maximum number of retries
                client: The underlying client instance
    """
    def __init__(self, model_name: str, max_tokens: Optional[int] = None, api_key: Optional[str] = None, timeout: Optional[int] = None, max_retries: Optional[int] = None) -> None:
        """
            Initialize an LLMClient instance

                Args:
                    model_name: Name of the model to use
                    max_tokens: Maximum tokens for completion
                    api_key: API key for authentication
                    timeout: Request timeout in seconds
                    max_retries: Maximum number of retries
        """
        self.model_name = self._clean_model_name(model_name)
        self.provider = self._infer_provider(self.model_name)
        self.max_tokens = max_tokens or self._get_default_max_tokens()
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize the client based on provider
        self.client = self._init_client()
        self._cached_gemini_models = {}  # cache for gemini models by system instruction
        self._cached_anthropic_client = None  # cache for anthropic client

    def _clean_model_name(self, model_name: str) -> str:
        """
            Remove provider prefix if present

                Args:
                    model_name: The model name to clean

                Returns:
                    The cleaned model name
        """
        if ":" in model_name:
            _, model_name = model_name.split(":", 1)
        return model_name

    def _infer_provider(self, model_name: str) -> str:
        """
            Infer the provider from the model name

                Args:
                    model_name: The model name to analyze

                Returns:
                    The provider name

                Raises:
                    ValueError: If provider cannot be inferred
        """
        name = model_name.lower()
        if name.startswith(("gpt", "o1", "o3", "o4")):
            return "openai"
        elif name.startswith(("gemini",)):
            return "gemini"
        elif name.startswith(("claude",)):
            return "anthropic"
        else:
            raise ValueError(f"Cannot infer provider from model name: {model_name}")

    def _get_default_max_tokens(self) -> int:
        """
            Get provider-specific default max tokens

                Returns:
                    The default max tokens for the provider
        """
        if self.provider == "gemini":
            return 8192
        elif self.provider == "anthropic":
            return 4096
        else:  # openai
            return 2048

    def _get_gemini_model(self, system_instruction: str) -> Any:
        """
            Get or create a Gemini model with the specified system instruction

                Args:
                    system_instruction: The system instruction for the model

                Returns:
                    The Gemini model instance
        """
        if system_instruction not in self._cached_gemini_models:
            import google.generativeai as genai  # type: ignore[import-untyped]
            self._cached_gemini_models[system_instruction] = genai.GenerativeModel(  # type: ignore[attr-defined]
                self.model_name,
                system_instruction={"role": "user", "parts": [{"text": system_instruction}]}
            )
        return self._cached_gemini_models[system_instruction]

    @property
    def _anthropic_client(self) -> Any:
        """
            Lazy-loaded Anthropic client to avoid re-auth costs

                Returns:
                    The Anthropic client instance
        """
        if self._cached_anthropic_client is None:
            import anthropic
            kwargs = {}
            if self.api_key:
                kwargs['api_key'] = self.api_key
            if self.timeout:
                kwargs['timeout'] = self.timeout
            if self.max_retries:
                kwargs['max_retries'] = self.max_retries
            self._cached_anthropic_client = anthropic.Anthropic(**kwargs)
        return self._cached_anthropic_client

    def _init_client(self) -> Any:
        """
            Initialize the appropriate client based on provider

                Returns:
                    The initialized client instance

                Raises:
                    LLMError: If provider is unsupported or SDK is not found
        """
        try:
            if self.provider == "openai":
                from openai import OpenAI
                kwargs = {}
                if self.api_key:
                    kwargs['api_key'] = self.api_key
                if self.timeout:
                    kwargs['timeout'] = self.timeout
                if self.max_retries:
                    kwargs['max_retries'] = self.max_retries
                return OpenAI(**kwargs)
            elif self.provider == "anthropic":
                import anthropic
                kwargs = {}
                if self.api_key:
                    kwargs['api_key'] = self.api_key
                if self.timeout:
                    kwargs['timeout'] = self.timeout
                if self.max_retries:
                    kwargs['max_retries'] = self.max_retries
                return anthropic.Anthropic(**kwargs)
            elif self.provider == "gemini":
                import google.generativeai as genai  # type: ignore[import-untyped]
                api_key = (
                    self.api_key
                    or os.getenv("GEMINI_API_KEY")  # primary per google docs
                    or os.getenv("GOOGLE_API_KEY")  # legacy
                )
                if api_key:
                    try:
                        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
                    except (AttributeError, TypeError):
                        pass  # some versions don't have configure or use different signature
                return genai
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except ImportError as e:
            provider_packages = {
                "openai": "openai",
                "anthropic": "anthropic", 
                "gemini": "google-generativeai"
            }
            package = provider_packages.get(self.provider, "unknown")
            raise LLMError(f"{self.provider.title()} SDK not found. Install with: pip install {package}") from e

    def _get_default_utility_model(self) -> str:
        """
            Get provider-appropriate cheap model for simple tasks

                Returns:
                    The default utility model name for the provider
        """
        if self.provider == "openai":
            return "gpt-4o-mini"
        elif self.provider == "anthropic":
            return "claude-3-5-haiku-20241022"
        elif self.provider == "gemini":
            return "gemini-1.5-flash"
        return self.model_name  # fallback to main model

    def chat(self, system: str, user: str, generation_config: Optional[Dict[str, Any]] = None) -> Tuple[str, UsageStats]:
        """
            Send a prompt and return the assistant message content and usage stats

                Args:
                    system: System prompt (required)
                    user: User message
                    generation_config: Provider-specific generation configuration

                Returns:
                    Tuple of response content and usage statistics

                Raises:
                    LLMError: If prompt exceeds context window or API call fails
        """
        # Check context window
        total_prompt_tokens = _count_tokens(user, self.model_name, system, self)
        ctx_limit = _context_window(self.model_name)
        if total_prompt_tokens + self.max_tokens > ctx_limit:
            raise LLMError(
                f"Prompt ({total_prompt_tokens} tok) + completion ({self.max_tokens}) "
                f"exceeds context window of {ctx_limit} for {self.model_name}."
            )
        
        # Enforce Gemini's hard output token cap
        if self.max_tokens > 8192 and self.provider == "gemini":
            raise LLMError("Gemini caps max_output_tokens at 8192.")

        try:
            if self.provider == "openai":
                return self._chat_openai(system, user)
            elif self.provider == "anthropic":
                return self._chat_anthropic(system, user)
            elif self.provider == "gemini":
                return self._chat_gemini(system, user, generation_config)
            else:
                raise LLMError(f"Provider {self.provider!r} not supported.")
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(f"Error calling {self.provider} API: {e}") from e

    def _chat_openai(self, system: str, user: str) -> Tuple[str, UsageStats]:
        """
            Chat with OpenAI models

                Args:
                    system: System message
                    user: User message

                Returns:
                    Tuple of response content and usage statistics
        """
        # O-series models use max_completion_tokens instead of max_tokens
        max_tokens_key = ("max_completion_tokens" if self.model_name.startswith(("o1", "o3", "o4"))
                         else "max_tokens")
        
        kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens_key: self.max_tokens,
        }
        
        resp = self.client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        
        usage = UsageStats(
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0
        )
        
        content = resp.choices[0].message.content or ""
        return content, usage

    def _chat_anthropic(self, system: str, user: str) -> Tuple[str, UsageStats]:
        """
            Chat with Anthropic models

                Args:
                    system: System message
                    user: User message

                Returns:
                    Tuple of response content and usage statistics
        """
        resp = self.client.messages.create(  # type: ignore[attr-defined]
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        
        usage = UsageStats(
            input_tokens=resp.usage.input_tokens if resp.usage else 0,
            output_tokens=resp.usage.output_tokens if resp.usage else 0,
            total_tokens=(resp.usage.input_tokens + resp.usage.output_tokens) if resp.usage else 0
        )
        
        content = ""
        if resp.content:
            for block in resp.content:
                if hasattr(block, 'text'):
                    content += block.text  # type: ignore[attr-defined]
        
        return content, usage

    def _chat_gemini(self, system: str, user: str, generation_config: Optional[Dict[str, Any]] = None) -> Tuple[str, UsageStats]:
        """
            Chat with Gemini models using the Google AI SDK

                Args:
                    system: System message
                    user: User message
                    generation_config: Generation configuration options

                Returns:
                    Tuple of response content and usage statistics
        """
        # Gemini only accepts "user" and "model" roles in contents
        # System instructions go in system_instruction parameter
        contents = [
            {"role": "user", "parts": [{"text": user}]},
        ]
        
        # Default generation config with ability to override
        default_config = {
            'max_output_tokens': self.max_tokens,
            'temperature': 0.7,
        }
        if generation_config:
            default_config.update(generation_config)
        
        resp = self._get_gemini_model(system).generate_content(
            contents,
            generation_config=default_config  # type: ignore[arg-type]
        )
        
        # Extract usage information if available
        input_tokens = 0
        output_tokens = 0
        if hasattr(resp, 'usage_metadata') and resp.usage_metadata:
            input_tokens = getattr(resp.usage_metadata, 'prompt_token_count', 0)
            output_tokens = getattr(resp.usage_metadata, 'candidates_token_count', 0)
        
        usage = UsageStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )
        
        content = ""
        # Try different ways to extract text from Gemini response
        try:
            content = getattr(resp, 'text', '')
        except Exception:
            try:
                if hasattr(resp, 'candidates') and resp.candidates:
                    content = resp.candidates[0].content.parts[0].text
            except Exception:
                content = str(resp)
        
        return content, usage


# ------------------------------------------------------------------ #
#  token helpers                                                     #
# ------------------------------------------------------------------ #
try:
    import tiktoken                 # openai encoder
except ImportError:
    tiktoken = None                 # fallback to naive estimator

# static fall-back table
_STATIC_CTX = {
    # OpenAI
    "gpt-3.5-turbo": 16385,
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "o1-preview": 128000,
    "o1-mini": 128000,
    "o3-mini": 200000,
    "o4-mini": 200000,
    # Gemini
    "gemini-1.5-pro": 2_097_152,
    "gemini-1.5-flash": 1_048_576,
    "gemini-2.0-flash-exp": 1_048_576,
    "gemini-2.5-pro": 1_048_576,
    # Anthropic
    "claude-3-opus-20240229": 200_000,
    "claude-3-sonnet-20240229": 200_000,
    "claude-3-haiku-20240307": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-5-haiku-20241022": 200_000,
}


def _context_window(model_name: str) -> int:
    """
        Get context window size for a model

            Args:
                model_name: Name of the model

            Returns:
                The context window size in tokens
    """
    name = model_name.lower()
    return _STATIC_CTX.get(name, 32000)  # conservative default


def _count_tokens(text: str, model_name: str, system: str, llm_client: Optional[LLMClient] = None) -> int:
    """
        Best-effort token estimate

            Args:
                text: User message text
                model_name: Name of the model
                system: System message (required for accurate counting)
                llm_client: LLM client instance (for provider-specific token counting)

            Returns:
                Estimated number of tokens
    """
    name = model_name.lower()
    
    # Use tiktoken for OpenAI models
    if tiktoken and name.startswith(("gpt", "o1", "o3", "o4")):
        try:
            enc = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # new models may not be registered – fall back to base encoding
            enc = tiktoken.get_encoding("cl100k_base")
        try:
            # include system message in token count
            full_text = f"{system}\n{text}"
            return len(enc.encode(full_text))
        except Exception as e:
            print(f"Warning: tiktoken failed for {model_name} ({e}), using heuristic token count")
    
    # Use Anthropic's official token counter for Claude models
    if name.startswith("claude") and llm_client:
        try:
            result = llm_client._anthropic_client.messages.count_tokens(
                model=model_name,
                system=system,
                messages=[{"role": "user", "content": text}]  # type: ignore[arg-type]
            )
            return result.input_tokens
        except Exception as e:
            print(f"Warning: Anthropic token counter failed for {model_name} ({e}), using heuristic token count")
    
    # Use Google's official token counter for Gemini models
    if name.startswith(("gemini",)) and llm_client:
        try:
            # use the actual system instruction that will be used
            return llm_client._get_gemini_model(system).count_tokens([{"role": "user", "parts": [{"text": text}]}]).total_tokens
        except Exception as e:
            print(f"Warning: Google AI token counter failed for {model_name} ({e}), using heuristic token count")
    
    # Naive estimate: roughly 4 characters per token
    print(f"Using heuristic token count for {model_name} (4 chars per token)")
    full_text = f"{system}\n{text}"
    return len(full_text) // 4


__all__ = ["LLMClient", "UsageStats", "LLMError"]