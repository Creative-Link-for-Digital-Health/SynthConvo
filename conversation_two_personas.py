import os
import pandas as pd

import personas
from llm_calls import generate_completion
from random_string import generate_random_string


def generate_conversation(vignette, num_turns):

    # Setup output file
    random_suffix = generate_random_string()
    output_file = f"./output/synthetic_conversation_{random_suffix}.csv"
    conversation_df = pd.DataFrame(columns=['Turn', 'Role', 'Persona', 'Model', 'Content'])

    # Generate personas for SOCIAL_WORKER and SOCIAL_SERVICES_CLIENT based on the vignette
    prompts = personas.generate_prompts(vignette)

    conversation_agent_A = {
        'name': 'SOCIAL_WORKER',
        'prompt': prompts['SOCIAL_WORKER'],
        'model': 'LLAMA_3_1',       # change model here but make sure this corresponds to a value from .secrets.toml file
        'messages':[]

    }

    conversation_agent_B = {
        'name': 'SOCIAL_SERVICES_CLIENT',
        'prompt': prompts['SOCIAL_SERVICES_CLIENT'],
        'model': 'ABLITERATED',     # change model here but make sure this corresponds to a value from .secrets.toml file
        'messages': []
    }

    # Load in system prompt for the social services client persona
    # Dataframe is created to track this persona 
    # In the future iterations messages passed to the personas can be summarized or history truncated 
    # This is the reason to keep redundant tracking in the current iteration
    new_row = pd.DataFrame([{
        'Turn': 0,
        'Role': 'system',
        'Persona': 'none',
        'Model': conversation_agent_B['model'],
        'Content': conversation_agent_B['prompt']
    }])
    conversation_df = pd.concat([conversation_df, new_row], ignore_index=True)

    # Load system prompts into message cues for both personas
    conversation_agent_A['messages'].append({'role': 'system', 'content': conversation_agent_A['prompt']})
    conversation_agent_B['messages'].append({'role': 'system', 'content': conversation_agent_B['prompt']})

    # llama 3.1 needs a little kick to start a conversation - produces no output if it doesn't see a user role 
    conversation_agent_A['messages'].append({'role': 'user', 'content': ''}) 

    print("\n--------------------------------------------")
    print("\n-- Personas Generated. Begin Conversation --")
    print("\n--------------------------------------------")

    for i in range(num_turns):

        # social worker generates a question
        question = generate_completion(conversation_agent_A['model'], conversation_agent_A['messages'])
        
        # question is added to the dataframe
        turn = i + 1
        new_row = pd.DataFrame([{'Turn': turn,'Role': 'user', 'Persona': 'SOCIAL_WORKER','Model': conversation_agent_A['model'], 'Content': question}])
        conversation_df = pd.concat([conversation_df, new_row], ignore_index=True)

        # question is added to the messages cue for Social Worker 
        conversation_agent_A['messages'].append({'role': 'assitant', 'content': question})

        # question is added to the messages cue for Social Services Client 
        conversation_agent_B['messages'].append({'role': 'user', 'content': question})    

        # ---------------------------

        # social services client responds
        answer = generate_completion(conversation_agent_B['model'], conversation_agent_B['messages'])

        # response is added to the dataframe
        new_row = pd.DataFrame([{'Turn': turn,'Role': 'assistant', 'Persona': 'SOCIAL_SERVICES_CLIENT','Model': conversation_agent_B['model'], 'Content': answer}])
        conversation_df = pd.concat([conversation_df, new_row], ignore_index=True)

        # response is added to the messages cue for Social Worker
        conversation_agent_A['messages'].append({'role': 'user', 'content': answer})

        # response is added to the messages cue for Social Services Client
        conversation_agent_B['messages'].append({'role': 'assistant', 'content': answer})

        print(f"""Generated {turn} dialog turn.""")

    # Save to CSV
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        conversation_df.to_csv(output_file, index=False)
        print(f"Conversation saved to {output_file}")
    except IOError as e:
        print(f"Error writing to file: {e}")


