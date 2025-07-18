import csv
import os
from pathlib import Path

import yaml
from guardrail_system import validate_input
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace
from arize.otel import register


with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

os.environ['OPENAI_API_KEY'] = config['openai']['api_key']

def init_arize_tracing():    

    tracer_provider = register(
        space_id = config['arize']['space_id'],
        api_key = config['arize']['api_key'],
        project_name = config['arize']['project_name'],
        log_to_console = True
    )
    #return tracer_provider.get_tracer(__name__)
    return trace.get_tracer(config['arize']['project_name'])


def load_prompts_from_csv(csv_file, prompt_index, max_prompts=None):
    csv_path = Path(csv_file)

    prompts = []

    with open(csv_path, "r", encoding="utf-8") as file:
        reader = csv.reader(file)

        # first_row = next(reader, None)  # Skip header row

        for row in reader:
            if row and len(row) > 0:
                prompts.append(row[prompt_index])  # Take prompt

                # Limit number of prompts if specified
                if max_prompts and len(prompts) >= max_prompts:
                    break
    return prompts


tracer = init_arize_tracing()

test_queries = load_prompts_from_csv(
    config["data"]["csv_file"],
    config["data"]["prompt_column"],
    max_prompts=2,  # Limit to 10 for testing
)
    
# Test each query
for query in test_queries:
    with tracer.start_as_current_span("RAG") as rag_span:
        rag_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.CHAIN.value)
        rag_span.set_attribute(SpanAttributes.INPUT_VALUE, query)
                    
        # Apply guardrails with detailed tracing
        validation_result = validate_input(query)
        
        # Check if query passed validation
        if not validation_result["valid"]:
            print(f"Query blocked by guardrails: {validation_result['errors']}")
            rag_span.set_attribute("guardrail_blocked", True)
            rag_span.set_attribute("blocked_reasons", str(validation_result['errors']))
            rag_span.set_attribute(SpanAttributes.OUTPUT_VALUE, "BLOCKED")
            continue

        rag_span.set_attribute(SpanAttributes.OUTPUT_VALUE, "PASS")

