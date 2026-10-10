---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0, on the openai Python SDK 3.19.2"
  spec_ref: "semantic-conventions-genai@e57c543b4889619eb2a05702471937db5119165d"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
---
<!-- ai-generated: 70% - the assistant ran the capture, read the spans, and drafted the attribute claims against its own knowledge of the GenAI semantic conventions; the student reviewed the file and ran it against the checker, which re-derives every in_spec/stability claim from its own snapshot of the named ref. -->

# What `opentelemetry-instrumentation-genai-openai` emits, against the spec

One chat completion call to Gemini's OpenAI-compatible endpoint (`gemini-3.8-flash`, via
`generativelanguage.googleapis.com`), instrumented with `OpenAIInstrumentor` from
`opentelemetry-instrumentation-genai-openai` 1.2b0 and exported as OTLP JSON to `genai/spans.json`
(`genai/capture.py`).

The span carries eight `gen_ai.*` attributes, all declared above with `emitted: true` - every key the
span actually has, no more and no fewer. Two request-side attributes (`gen_ai.operation.name`,
`gen_ai.request.model`, plus `gen_ai.provider.name`) are present on the span even on the earlier failed
call with the deprecated model name (captured and discarded before the final, clean run), which makes
sense: the instrumentation records what it is *about* to ask for before the request goes out, so these
survive a request that never got an answer. The five response-side attributes
(`gen_ai.response.model`, `gen_ai.response.id`, `gen_ai.response.finish_reasons`,
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) only appear once a response actually came
back, which is exactly what the failed call's span (not part of the committed file, but visible while
debugging) showed: none of the five, only an `error.type` and a `status.code`.

What the library does **not** emit that the spec defines for a chat completion: prompt or message
content itself (`gen_ai.input.messages` / `gen_ai.output.messages` in the newer conventions) - this
instrumentation, at this version, captures the shape and the cost of the call (model, token counts,
finish reason, a response id to correlate against provider-side logs) but not the conversation content,
which is a defensible default for a library that cannot know whether the content is safe to attach to a
trace by default. `gen_ai.system` - the older, now-superseded attribute name for the provider - never
appears either; this version already emits its replacement, `gen_ai.provider.name`, directly, with no
overlap between the two names on the same span.

`gen_ai.provider.name`'s value here is `"openai"`, not `"google"` or `"gemini"`: the instrumentation
names the *client library's own* provider identity (it wraps the `openai` Python SDK), not the actual
backend the request happened to reach through that SDK's OpenAI-compatible base URL. A dashboard built
on this attribute to split cost or latency by backend would need to know, out of band, that this
particular `svcdesk` deployment's "openai" traffic is actually Gemini - the attribute cannot tell that
apart from genuinely routing through OpenAI itself.
