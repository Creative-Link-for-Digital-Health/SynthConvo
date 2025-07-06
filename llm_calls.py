#  Send requests OpenAI compatible endpoints -- LLM Factory or local Ollama server
import sys
import toml

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
import time
import random
import json


def load_api_params() -> str:
    try:
        with open('.secrets.toml', 'r') as f:
            secrets = toml.load(f)
        return {
            'API_KEY': secrets['API_KEY'], 
            'API_URL': secrets['API_URL'],
            'LLAMA_3_1': secrets['LLAMA_3_1'], 
            'ABLITERATED': secrets['ABLITERATED'],
        }
    except Exception as e:
        print(f"Error loading API key: {e}", file=sys.stderr)
        sys.exit(1)


API_CALL_PARAMS = load_api_params()

client = OpenAI(
    base_url = API_CALL_PARAMS['API_URL'],
    api_key = API_CALL_PARAMS['API_KEY']
)

def generate_completion(model, messages):
    MODEL = API_CALL_PARAMS[model]
    # MODEL = API_CALL_PARAMS['LLAMA_3_1']

    # print(MODEL)
    # print(messages)

    # Generate the response using the API
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    
    # Extract and return the content of the response
    return response.choices[0].message.content



# --------------- Function call - Output JSON ---------------------------------------

JSON_output_client = instructor.patch(
    OpenAI(
        base_url = API_CALL_PARAMS['API_URL'],
        api_key = API_CALL_PARAMS['API_KEY']
    ),
    mode=instructor.Mode.JSON
)

class PersonInfo(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    age: str = Field(..., min_length=1, max_length=10)
    gender: str = Field(..., min_length=1, max_length=50)
    ethnicity: str = Field(..., min_length=1, max_length=50)
    narrative_setting: str = Field(..., min_length=1, max_length=100)
    support_structure: str = Field(..., min_length=1, max_length=200)

SYSTEM_PROMPT = """Identify the main character from the narrative provided by the user. 
Provide the following information about the main character: name, age, gender, ethnicity, narative setting, support structure. If you can't find this information answer "unknown"
Support structure is any family or church or school friends that can help this young person. 
Narrative setting is a place where the narrative is taking place like a home, or emergency shelter or a hospital.

Here are some examples. Important. Coinsider these examples when providing the information about the main character. 

Example 1:
{
    "name": "Jamela",
    "age": "15",
    "gender": "Female",
    "ethnicity": "African American",
    "narrative_setting": "emergency shelter",
    "support_structure": "unknown" 
}

Example 2:
{
    "name": "Kevin",
    "age": "9",
    "gender": "Male",
    "ethnicity": "unknown",
    "narrative_setting": "hospital",
    "support_structure": "mother and sisters visit him at the hospital" 
}

Example 3:
{
    "name": "David",
    "age": "17",
    "gender": "Male",
    "ethnicity": "Latino",
    "narrative_setting": "unknown",
    "support_structure": "grandparents and sopmetimes aunt" 
}

Keep output in JSON format. 
Only JSON format.
Do not try to explain the code you generated.
Do not add any other text to your JSON output."""


def extract_main_character(vignette: str, max_retries: int = 5, base_wait_time: float = 1.0) -> PersonInfo:
    MODEL = API_CALL_PARAMS['LLAMA_3_1']

    messages = [
        {"role":"system", "content": SYSTEM_PROMPT},
        {"role":"user", "content": vignette }
    ]

    for attempt in range(max_retries):
        try:
            completion = JSON_output_client.chat.completions.create(
                model = MODEL,
                messages = messages
            )

            raw_content = completion.choices[0].message.content
            print(f"Raw LLM output (Attempt {attempt + 1}):")
            print(raw_content)
            print("\nAttempting to parse and validate...")

            # Try to parse the content as JSON
            try:
                json_content = json.loads(raw_content)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                raise ValueError("LLM output is not valid JSON")

            return PersonInfo(**json_content)
        
        except (ValueError, ValidationError) as e:
            print(f"Validation error: {e}")
            if attempt < max_retries - 1:
                wait_time = base_wait_time * (2 ** attempt) + random.uniform(0, 0.1 * (2 ** attempt))
                print(f"Waiting for {wait_time:.2f} seconds before retrying...")
                time.sleep(wait_time)
            else:
                raise ValueError(f"Failed to generate valid person info after {max_retries} attempts.")
