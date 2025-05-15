import os
from dotenv import load_dotenv
from openai import OpenAI
import json

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENAI_ROUTER_API_KEY")

client_instance = None

def get_openai_client():
    global client_instance
    if client_instance is None:
        if not OPENROUTER_API_KEY:
            print("Error: OPENAI_ROUTER_API_KEY not found in environment variables.")
            raise ValueError("API Key not configured")
        client_instance = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    return client_instance

def get_ai_completion(prompt_text: str):
    """Interacts with the OpenRouter API to get a completion.

    Args:
        prompt_text (str): The text prompt for the AI.

    Returns:
        str: The content of the AI's response, or None if an error occurs.
    """
    if not OPENROUTER_API_KEY:
        print("Error: OPENAI_ROUTER_API_KEY not found in environment variables.")
        return None

    client = get_openai_client()

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt_text
                }
            ]
        }
    ]

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://openrouter.ai/", # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "openrouter.ai", # Optional. Site title for rankings on openrouter.ai.
            },
            extra_body={},
            model="google/gemini-2.0-flash-001", # You might want to make this configurable
            messages=messages
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"An error occurred during API call: {e}")
        return None

def get_column_mapping_from_ai(file_snippet: str, target_salesforce_schema: dict):
    """
    Asks the AI to map columns from a file snippet to a target Salesforce schema.

    Args:
        file_snippet (str): A text representation of the first few lines of the user's file.
        target_salesforce_schema (dict): A dictionary describing the desired Salesforce fields 
                                         and their descriptions/types for the AI.

    Returns:
        dict: A mapping from Salesforce field names (keys from target_salesforce_schema) 
              to detected column names from the file, or None if an error occurs.
    """
    prompt_lines = [
        "You are an expert data mapping assistant. Your task is to analyze the provided text snippet from a user's uploaded file and map its columns/data to the following Salesforce Lead fields.",
        "The goal is to identify which column header or data pattern in the uploaded file best corresponds to each Salesforce field.",
        "\nTarget Salesforce Lead Schema (field_api_name: description_for_ai):",
        json.dumps(target_salesforce_schema, indent=2, ensure_ascii=False),
        "\nUser's File Snippet (this is often a CSV representation of the first few rows, including headers if present):",
        "```text",
        file_snippet,
        "```",
        "\nPlease return ONLY a JSON object. This JSON object must have keys that are the exact Salesforce Lead field API names from the 'Target Salesforce Lead Schema' provided above (e.g., 'LastName', 'Company', 'MyCustomField__c').",
        "The values in the JSON object should be the exact column names (headers) found in the 'User's File Snippet' that you believe map to that Salesforce field.",
        "If you cannot find a clear or confident mapping for a Salesforce field, or if the field is not present in the snippet, use the JSON value null for that key (e.g., \"CustomFieldNotPresent__c\": null).",
        "Do not invent column names that are not present in the user's file snippet.",
        "Focus on matching the meaning and typical content of the fields based on their descriptions in the Target Schema.",
        "\nExample of a desired JSON output format (keys must match the Target Salesforce Lead Schema):",
        json.dumps({
            "LastName": "Nome do Contato",
            "Email": "Endereço de Email",
            "Company": "Nome da Organização",
            "Phone": None # Example if no phone column was found in the snippet
        }, indent=2, ensure_ascii=False),
        "\nNow, provide the JSON mapping for the given User's File Snippet and Target Salesforce Lead Schema. Ensure your entire response is a single valid JSON object and nothing else."
    ]
    prompt = "\n".join(prompt_lines)

    raw_json_response = ""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001", # Or another capable model like gpt-4o-mini
            response_format={"type": "json_object"}, # CRUCIAL for getting JSON
            messages=[
                # System prompt to reinforce JSON output, though response_format is stronger
                {"role": "system", "content": "You are an AI assistant that strictly outputs a single, valid JSON object mapping columns according to the user's instructions. Do not include any explanatory text before or after the JSON object."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.05, # Low temperature for more deterministic mapping
            max_tokens=1024 # Adjust as needed, depends on schema size and snippet size
        )
        
        raw_json_response = response.choices[0].message.content
        # Basic validation: does it look like JSON?
        if not (raw_json_response.strip().startswith('{') and raw_json_response.strip().endswith('}')):
            print(f"AI response does not appear to be a valid JSON object. Raw response:\n{raw_json_response}")
            # Potentially try to extract JSON if it's embedded, but for now, fail
            return None
            
        mapping = json.loads(raw_json_response)
        
        # Further validation: ensure all keys from target schema are present in AI response
        # This ensures the AI didn't forget any fields.
        validated_mapping = {}
        all_keys_present = True
        for key in target_salesforce_schema.keys():
            if key in mapping:
                validated_mapping[key] = mapping[key]
            else:
                print(f"Warning: AI mapping is missing key '{key}' from target schema. Will be treated as unmapped.")
                validated_mapping[key] = None # Treat as unmapped
                all_keys_present = False
        
        # If you want to be strict and fail if not all keys are present from target:
        # if not all_keys_present:
        #     print("AI did not return all target schema keys in its mapping.")
        #     return None
            
        return validated_mapping
    except json.JSONDecodeError as e:
        print(f"Error decoding AI JSON response for mapping: {e}")
        print(f"Prompt sent to AI:\n{prompt[:1000]}... (truncated)") # Log part of the prompt
        print(f"Raw response was: {raw_json_response}")
        return None
    except Exception as e:
        print(f"An error occurred during AI mapping call: {e}")
        print(f"Prompt sent to AI:\n{prompt[:1000]}... (truncated)")
        if raw_json_response: print(f"Raw response was: {raw_json_response}")
        return None

if __name__ == "__main__":
    # Example usage:
    sample_prompt = "Hello, how are you today?"

    response_content = get_ai_completion(sample_prompt)

    if response_content:
        print("AI Response:")
        print(response_content)
    else:
        print("Failed to get AI response for general completion.")

    # --- Test for get_column_mapping_from_ai ---
    print("\n--- Testing Column Mapping --- ")
    sample_schema = {
        "LastName": "O sobrenome da pessoa",
        "Company": "Empresa onde a pessoa trabalha",
        "Email": "Email principal da pessoa",
        "CustomNotes__c": "Any other relevant notes about the lead"
    }
    sample_file_data = "Full Name,Organization,Contact Email,Details\nJohn Doe,Example Corp,j.doe@example.com,Loves Python\nJane Smith,Test Inc.,jane@test.com,Needs follow-up"
    
    print(f"Sample Target Schema: {json.dumps(sample_schema, indent=2)}")
    print(f"Sample File Snippet:\n{sample_file_data}")
    
    mapping_result = get_column_mapping_from_ai(sample_file_data, sample_schema)
    
    if mapping_result:
        print("\nAI Column Mapping Result:")
        print(json.dumps(mapping_result, indent=2, ensure_ascii=False))
    else:
        print("\nFailed to get AI column mapping.")