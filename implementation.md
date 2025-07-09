### Implementation game-plan for the team

*(applies to every LLM adapter you maintain: OpenAI, Anthropic/Claude, Gemini, vLLM, etc.)*

---

## 1  Create one shared helper

| File                     | Function                                                                                                      | Contract                                                                                                                                                                                                                                                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `common/stream_utils.py` | `python\nmerge_tool_chunks(delta_tool_calls: list, scratch: dict, *, provider: str) -> list[CompletedCall]\n` | • **Takes** the raw `delta.tool_calls` list from a single streaming chunk + a per-turn scratch dict.<br>• **Stitches** fragments using `id if present else index`.<br>• **Returns** any *newly completed* calls (each = `{id, name, arguments}` dict).<br>• Removes completed entries from `scratch` so it can be reused next chunk. |

Implementation sketch:

```python
def merge_tool_chunks(chunks, buf, *, provider: str):
    completed = []
    for tc in chunks or []:
        key = getattr(tc, "id", None) or getattr(tc, "index", None)
        if key is None:
            continue
        item = buf.setdefault(
            key,
            {"id": getattr(tc, "id", "") or f"auto_{key}",
             "name": tc.function.name if tc.function else "",
             "arguments": ""}
        )
        if tc.function and tc.function.arguments:
            item["arguments"] += tc.function.arguments
        # OpenAI/Claude mark the END of a call via finish_reason *or* the stream’s final chunk.
        if getattr(tc, "finish_reason", None) or tc == chunks[-1]:
            completed.append(item)
            buf.pop(key, None)
    return completed
```

---

## 2  Light-weight changes inside every adapter

```python
from common.stream_utils import merge_tool_chunks

scratch_calls: dict = {}

async for chunk in stream:
    # 2-a  stream text immediately ───────────────────────────
    if chunk.delta.content and not paused_for_tool:
        ui.push(chunk.delta.content)
        assistant_text += chunk.delta.content

    # 2-b  stitch tool-call fragments ────────────────────────
    completed = merge_tool_chunks(
        getattr(chunk.delta, "tool_calls", None),
        scratch_calls,
        provider=self.provider_name,
    )
    if completed:
        paused_for_tool = True          # stop pushing further text
        pending_calls.extend(completed)
```

*Keep the rest exactly as before (yield `AdapterResponse(tool_calls=…)`, etc.).*

---

## 3  Turn-loop in the orchestrator

```python
while True:
    parts = await adapter.chat_completion(req)   # ← single turn
    for part in parts:
        if part.content:  ui.push(part.content)
        if part.tool_calls:
            results = await run_local_tools(part.tool_calls)
            history.extend(tool_messages(results))
            break   # end this turn, go start next
    if not part.tool_calls:
        break        # assistant is done
```

*Rule of thumb:* **one adapter request → ≤ 1 batch of calls** (unless you set
`parallel_tool_calls=True`, in which case handle the list).

---

## 4  Front-end behaviour

1. Display streaming text until the first tool call arrives.
2. Show a small “thinking / running tools…” indicator.
3. Resume streaming when the next assistant turn begins.

(Users never see the model’s half-sentence that precedes a tool call, because the model itself stops emitting text once it starts a call.)

---

## 5  Config & flags

| Flag                  | Recommended default      | Reason                                         |
| --------------------- | ------------------------ | ---------------------------------------------- |
| `stream=True`         | yes                      | Required for low latency.                      |
| `parallel_tool_calls` | **False**                | Simpler logic; turn may emit at most one call. |
| `tool_choice`         | `"auto"`                 | Lets the LLM decide.                           |
| Timeout / rate-limit  | keep existing try/except | No change needed.                              |

---

## 6  Unit tests

* Record real streaming traces from each provider.
* Feed them chunk-by-chunk through `merge_tool_chunks`; assert you get one fully-formed JSON call with exact arguments.
* Test id-missing case (OpenAI) and id-present case (Claude).

---

### Deliverable checklist

* [ ] `common/stream_utils.py` with `merge_tool_chunks`.
* [ ] Adapters import & use the helper; no provider-specific stitching logic left inside adapters.
* [ ] Orchestrator loop handles sequential turns (text → tool(s) → text …).
* [ ] UI pause/resume logic implemented.
* [ ] Unit tests cover OpenAI, Claude, Gemini traces.

No open questions from my side—this spec should let your team implement a portable, low-latency, multi-provider function-calling flow.
