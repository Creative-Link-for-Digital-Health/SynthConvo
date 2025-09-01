# Synthetic Conversation Generator

Use for generating synthetic conversations for system testing, development, finetuning, training robots and humans and all sorts of other tasks where synthetic personas conversing with each other are useful ;)

![alt text](assets/synth_convo_diagram.png)

## Description
The process begins with a Vignette (Conversation Context) - a predefined scenario or setting that establishes the conversational framework and context for the synthetic dialogue. Store your vignette in the `vignette_library` directory.

*Persona Generation:* The vignette uses two distinct Persona Cards (A and B), which define specific LLM and Prompt. The choice of different models allows us additional flexibility. For example, using abliterated or specially fine-tuned local models to get closer to the persona parameters that we want or testing specific completion API.

Both persona cards feed into the gen_conversations script, which orchestrates the actual dialogue generation between the two synthetic personas based on their defined characteristics and the original vignette context.

The script produces a Conversation File (JSON) containing the generated dialogue exchanges.

## Setup

Create `secrets.toml` file following the example provided in `secrets.example.toml`. Add your API endpoints and keys to this file.  

## Generation Process

Validate that all of the conversation components are present and no mistakes in the setup where made
`python utils/interface_validator.py input_libraries/conversations/conversation_001.example.json`

Generate a conversation
`python gen_conversations.py --config input_libraries/conversations/conversation_001.example.json --turns 3 --count 2 --output-dir outputs/test_run --debug-prompts`

## TODO 

+ simplify interface validator
+ allow for two different LLM provider services to run at the same time
+ review modifier engine and strategies 
+ clean vignette directory
+ add explanation for opt-in nature of gitignore files
+ add human eval interface for realism
+ add token length param and test it with longer synthetic conversations
+ Explore implementation of repetition penalties (https://www.reddit.com/r/LocalLLaMA/comments/1g383mq/repetition_penalties_are_terribly_implemented_a/)
+ add testing for topic collapse 
+ refactor gen_train_dataset script to output to multiple training formats


## Training dataset generator
-- rewrite me ---

Default behavior (no history, default timestamped output file.) All of the content in *output* directory located in distinct synthetic conversation CSV filews is packed into a single JSON file for traing an LLM or LoRA.
`python gen_train_dataset.py`

To test output on a single conversation file
`python gen_train_dataset.py --mode file --input /path/to/file`

Specify input and custom base name for output (no history)
`python gen_train_dataset.py -i /path/to/csv/files -o my_custom_training_data.json`

#### Todo:
-- rewrite me ---
Generate data with history (timestamped output file)
`python gen_train_dataset.py --history`

Specify all options with history and custom base name
`python gen_train_dataset.py -i /path/to/csv/files -o my_custom_training_data.json --history`

## Example datasets with and without histoy 

### No History
`{
  "instruction": "Explain the concept of photosynthesis to a 10-year-old.",
  "input": "",
  "output": "Photosynthesis is like a plant's way of making its own food. Imagine plants are like tiny factories. They take in sunlight, water from the soil, and a gas called carbon dioxide from the air. Using these ingredients, they create their own food, which is a type of sugar. It's kind of like how you might use ingredients to bake a cake, but plants do it using sunlight as their oven! This process also produces oxygen, which is great for us because we need it to breathe."
}`

### With History
`{
  "instruction": "Respond to the user's latest message.",
  "input": "What's your favorite color?",
  "output": "My favorite color is blue. I find it calming and reminds me of the sky and ocean. Do you have a favorite color?",
  "history": [
    {"role": "user", "content": "Hi there! How are you today?"},
    {"role": "assistant", "content": "Hello! I'm doing well, thank you for asking. How can I assist you today?"},
    {"role": "user", "content": "I'm just chatting. Tell me something about yourself."},
    {"role": "assistant", "content": "Well, as an AI assistant, I don't have personal experiences, but I'm designed to be helpful, friendly, and knowledgeable on a wide range of topics. Is there anything specific you'd like to know or discuss?"}
  ]
}
`