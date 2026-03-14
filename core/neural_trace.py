import os
from typing import Optional, Dict, Any
from opentelemetry import trace, propagate
from opentelemetry.sdk.resources import Resource
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
from arize.otel import register

# Configuración del Tracer v6.0
# Soporta Arize (Cloud) o Phoenix (Local)

ARIZE_SPACE_ID = os.getenv("ARIZE_SPACE_ID", "default")
ARIZE_API_KEY = os.getenv("ARIZE_API_KEY", "")
OTEL_PROJECT_NAME = os.getenv("OTEL_PROJECT_NAME", "AgentOrquestor-v6")

def initialize_tracer(service_name: str = "AgentOrquestor"):
    """Inicializa el TracerProvider global."""
    if ARIZE_API_KEY:
        # Exportar a Arize
        tracer_provider = register(
            space_id=ARIZE_SPACE_ID,
            api_key=ARIZE_API_KEY,
            project_name=OTEL_PROJECT_NAME
        )
    else:
        # Silencioso o Phoenix local si está configurado vía variables de entorno estándar de OTel
        # opentelemetry-sdk ya maneja variables como OTEL_EXPORTER_OTLP_ENDPOINT
        pass

    return trace.get_tracer(service_name)

def get_tracer(name: str = "neural_trace"):
    return trace.get_tracer(name)

def inject_trace_context(data: Dict[str, Any]):
    """Inyecta el contexto de traza actual en un diccionario para propagación."""
    carrier = {}
    propagate.get_global_textmap().inject(carrier)
    data["_trace_context"] = carrier

def extract_trace_context(data: Dict[str, Any]):
    """Extrae y activa el contexto de traza desde un diccionario."""
    carrier = data.get("_trace_context", {})
    if carrier:
        context = propagate.get_global_textmap().extract(carrier)
        return context
    return None

class NeuralSpan:
    """Helper para crear spans con semántica de OpenInference."""
    
    @staticmethod
    def agent_span(tracer, name: str, input_value: str = ""):
        return tracer.start_as_current_span(
            name=name,
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.AGENT.value,
                SpanAttributes.INPUT_VALUE: input_value,
            }
        )

    @staticmethod
    def llm_span(tracer, name: str, model: str, input_value: str = ""):
        return tracer.start_as_current_span(
            name=name,
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.LLM.value,
                SpanAttributes.LLM_MODEL_NAME: model,
                SpanAttributes.INPUT_VALUE: input_value,
            }
        )

    @staticmethod
    def tool_span(tracer, name: str, tool_name: str, input_value: str = ""):
        return tracer.start_as_current_span(
            name=name,
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                "tool.name": tool_name,
                SpanAttributes.INPUT_VALUE: input_value,
            }
        )
