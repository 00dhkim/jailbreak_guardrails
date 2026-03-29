from typing import Dict, Any
from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
from guardrails import Guard
from guardrails.hub import ArizeDatasetEmbeddings
from guardrails.hub import ValidLength
from guardrails.hub import BanList
from guardrails.hub import RestrictToTopic
from guardrails.hub import WebSanitization
import yaml

with open("config.yaml", "r") as f:
    _config = yaml.safe_load(f)
_guardrail_flags = _config.get("guardrails", {})

# from guardrails import install
# install("hub://arize-ai/dataset_embeddings_guardrails", quiet=True, install_local_models=True)
# https://hub.guardrailsai.com/validator/arize-ai/dataset_embeddings_guardrails
def arize_embeddings_guardrail(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    
    guard = Guard().use(
        ArizeDatasetEmbeddings, 
        on_fail="exception", 
        threshold=config["threshold"])
    
    guard._disable_tracer = True

    try:
        guard.validate(query)
        return {"output": "PASS"}
    except Exception as e:
        return {"output": "BLOCKED","error": f"{e}"}


# guardrails hub install hub://guardrails/valid_length
# https://hub.guardrailsai.com/validator/guardrails/valid_length
def max_length_guardrail(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    
    guard = Guard().use(
        ValidLength,
        max=config["max"], 
        on_fail="exception"
    )
    
    try:
        guard.validate(query)
        return {"output": "PASS"}
    except Exception as e:
        return {"output": "BLOCKED","error": f"{e}"}


# guardrails hub install hub://guardrails/ban_list
# https://hub.guardrailsai.com/validator/guardrails/ban_list
def ban_list_guardrail(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    
    guard = Guard().use(
        BanList(banned_words=config["banned_words"])
    )
    
    try:
        guard.validate(query)
        return {"output": "PASS"}
    except Exception as e:
        return {"output": "BLOCKED","error": f"{e}"}


# guardrails hub install hub://tryolabs/restricttotopic
# https://hub.guardrailsai.com/validator/tryolabs/restricttotopic
def restrict_topic_guardrail(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    
    guard = Guard().use(
        RestrictToTopic(
            valid_topics=config["valid_topics"],
            invalid_topics=config["invalid_topics"],
            disable_classifier=config["disable_classifier"],
            disable_llm=config["disable_llm"],
            on_fail="exception"
        )
    )
    
    try:
        guard.validate(query)
        return {"output": "PASS"}
    except Exception as e:
        return {"output": "BLOCKED","error": f"{e}"}


# guardrails hub install hub://guardrails/web_sanitization
# https://hub.guardrailsai.com/validator/guardrails/web_sanitization
def web_sanitization_guardrail(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    
    guard = Guard().use(
        WebSanitization, 
        on_fail="exception"
    )
    
    try:
        guard.validate(query)
        return {"output": "PASS"}
    except Exception as e:
        return {"output": "BLOCKED","error": f"{e}"}


def validate_input(query: str, actual: str = "PASS", embedding_threshold: float = None) -> Dict[str, Any]:
    if embedding_threshold is None:
        embedding_threshold = _config.get("embedding_threshold", 0.25)

    tracer = trace.get_tracer("guardrail-system")

    #################################
    ### CUSTOMIZE GUARDRAILS HERE ###
    #################################
    all_guardrails = [
        {"key": "arize_embeddings", "function": arize_embeddings_guardrail, "config": {"threshold": embedding_threshold}},
        {"key": "max_length", "function": max_length_guardrail, "config": {"max": "1500"}},
        {"key": "ban_list", "function": ban_list_guardrail, "config": {
            "banned_words": ["jailbreak", "bypass", "override", "ignore previous",
                             "disregard instructions", "unfiltered", "unrestricted",
                             "prompt injection", "DAN", "simulate", "pretend", "roleplay",
                             "act as", "do anything now", "forget you are", "disable safety",
                             "system prompt", "memory hack"]}},
        {"key": "restrict_topic", "function": restrict_topic_guardrail, "config": {
            "valid_topics": ["arize", "tracing", "experiments", "datasets", "api", "phoneix",
                             "observability", "machine learning", "performance", "drift",
                             "data", "monitoring", "alerts", "bias", "prediction", "model",
                             "accuracy", "precision", "recall", "auc", "f1", "score",
                             "evaluations", "prompting", "prompt playground", "monitors"],
            "invalid_topics": ["drugs", "sex", "violence", "hate", "racism", "crime"],
            "disable_classifier": True,
            "disable_llm": False}},
        {"key": "web_sanitization", "function": web_sanitization_guardrail, "config": {}}
    ]
    guardrails = [g for g in all_guardrails if _guardrail_flags.get(g["key"], True)]
    
    with tracer.start_as_current_span("guardrail_validation") as span:
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.CHAIN.value)
        span.set_attribute(SpanAttributes.INPUT_VALUE, query)
        span.set_attribute("guardrail.count", len(guardrails))
        
        results = []
        errors = []
        
        # Run each guardrail with individual tracing
        for guardrail in guardrails:
            guardrail_func = guardrail["function"]
            guardrail_name = guardrail_func.__name__
            guardrail_config = guardrail["config"]
            
            with tracer.start_as_current_span(f"{guardrail_name}") as guardrail_span:
                guardrail_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.GUARDRAIL.value)
                guardrail_span.set_attribute(SpanAttributes.INPUT_VALUE, query)
                guardrail_span.set_attribute("guardrail.name", guardrail_name)
                guardrail_span.set_attribute("guardrail.config", str(guardrail_config))

                try:
                    result = guardrail_func(query, guardrail_config)
                    results.append(result)
                    
                    if result["output"]=="BLOCKED":
                        errors.append(result["error"])
                        guardrail_span.set_attribute("guardrail.error", result["error"])

                    guardrail_span.set_attribute("guardrail.output", result["output"]) 
                    guardrail_span.set_attribute("guardrail.actual", actual)
                    guardrail_span.set_attribute(SpanAttributes.OUTPUT_VALUE, result["output"])
                    
                except Exception as e:
                    error_msg = f"Guardrail {guardrail_name} failed: {str(e)}"
                    errors.append(error_msg)
                    guardrail_span.set_attribute("guardrail.error", error_msg)
                    guardrail_span.record_exception(e)
                    
                    results.append({
                        "name": guardrail_name,
                        "valid": False,
                        "error": error_msg
                    })

                    guardrail_span.set_attribute(SpanAttributes.OUTPUT_VALUE, "ERROR")
        
        is_valid = len(errors) == 0
        
        # Set final span attributes
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, is_valid)
        span.set_attribute("guardrail.blocked_count", len(errors))
        span.set_attribute("guardrail.actual", actual)

        if not is_valid:
            span.set_attribute("guardrail.blocked_reasons", str(errors))
        
        return {
            "valid": is_valid,
            "errors": errors,
            "results": results
        }

