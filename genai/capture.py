# ai-generated: 85% - Claude (AI assistant) generated this capture script from HANDOUT.md's Stretch 1 instructions under the student's direction; the student supplied their own Gemini API key and ran it.
"""Captures the spans of one instrumented LLM call for L3-STRETCH-1 (genai-diff, MONITORING-SPEC.md
M-28, M-29). Uses Gemini's OpenAI-compatible endpoint (Google AI Studio) through the `openai` Python
client, instrumented with the OpenTelemetry GenAI semantic-conventions instrumentation for openai, and
exports spans as OTLP JSON (one batch per line) to genai/spans.json.

Run from the repository root, with GEMINI_API_KEY set in the environment (never commit the key itself):
    python genai/capture.py
"""
import os

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


def main() -> None:
    api_key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    provider = TracerProvider(resource=Resource.create({"service.name": "svcdesk-genai-diff"}))
    exporter = FileSpanExporter("genai/spans.json")
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    OpenAIInstrumentor().instrument()

    client = OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "In one sentence, what does a Prometheus histogram bucket boundary control?",
            }
        ],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
