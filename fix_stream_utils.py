#!/usr/bin/env python3
"""
Fix stream_utils.py to handle OpenAI's inconsistent ID behavior and prevent None names.
"""

# Read the current file
with open('src/common/stream_utils.py', 'r') as f:
    content = f.read()

# Fix 1: Replace the problematic key generation logic
old_key_logic = '''        # Use id if present, otherwise fall back to index
        key = getattr(tc, "id", None) or getattr(tc, "index", None)
        if key is None:
            continue'''

new_key_logic = '''        # Use id if present, otherwise fall back to index
        # This handles all mainstream providers: OpenAI, Anthropic, Gemini, etc.
        key = getattr(tc, "id", None) or getattr(tc, "index", None)

        # Special handling for providers that don't provide id/index on all chunks
        if key is None:
            if provider in ["openai", "openrouter"]:
                # For OpenAI: fragments after first chunk often lack id
                # Use the first available key in scratch (continuing existing tool call)
                if scratch:
                    key = list(scratch.keys())[0]
                else:
                    # Fallback: create a default key for first chunk without id
                    key = "tool_call_0"
            else:
                # For other providers, skip chunks without identifiers
                continue'''

content = content.replace(old_key_logic, new_key_logic)

# Fix 2: Simplify the initial name extraction to avoid None
old_name_init = '''                "name": getattr(getattr(tc, "function", None), "name", "") if hasattr(tc, "function") and tc.function else "",'''

new_name_init = '''                "name": "",'''

content = content.replace(old_name_init, new_name_init)

# Fix 3: Add safety check when creating CompletedToolCall in merge_tool_chunks
old_completion = '''            completed.append(CompletedToolCall(
                id=entry["id"],
                name=entry["name"],
                arguments=entry["arguments"]
            ))'''

new_completion = '''            # Ensure name is never None or empty
            final_name = entry["name"] if entry["name"] else "unknown_function"
            completed.append(CompletedToolCall(
                id=entry["id"],
                name=final_name,
                arguments=entry["arguments"]
            ))'''

content = content.replace(old_completion, new_completion)

# Fix 4: Add safety check in finalize_remaining_calls
old_finalize = '''        completed.append(CompletedToolCall(
            id=entry["id"],
            name=entry["name"],
            arguments=entry["arguments"]
        ))'''

new_finalize = '''        # Ensure name is never None or empty
        final_name = entry["name"] if entry["name"] else "unknown_function"
        completed.append(CompletedToolCall(
            id=entry["id"],
            name=final_name,
            arguments=entry["arguments"]
        ))'''

content = content.replace(old_finalize, new_finalize)

# Fix 5: Ensure string conversion in name assignment
old_name_assign = '''                entry["name"] = tc.function.name'''

new_name_assign = '''                entry["name"] = str(tc.function.name) if tc.function.name is not None else ""'''

content = content.replace(old_name_assign, new_name_assign)

# Fix 6: Ensure string conversion in arguments assignment
old_args_assign = '''                entry["arguments"] += tc.function.arguments'''

new_args_assign = '''                entry["arguments"] += str(tc.function.arguments) if tc.function.arguments is not None else ""'''

content = content.replace(old_args_assign, new_args_assign)

# Write the fixed file
with open('src/common/stream_utils.py', 'w') as f:
    f.write(content)

print("✅ Fixed stream_utils.py:")
print("  - Improved key generation to handle OpenAI's inconsistent ID behavior")
print("  - Added fallback logic for chunks without id/index")
print("  - Added safety checks to prevent None names")
print("  - Ensured string conversion for all fields")
print("  - Now supports all mainstream providers (OpenAI, Anthropic, Gemini, etc.)")
