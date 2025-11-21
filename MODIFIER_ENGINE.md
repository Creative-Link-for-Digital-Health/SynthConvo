# Modifier Engine

The Modifier Engine is a core component of the Synthetic Conversation Generator that creates dynamic, coherent personality profiles for synthetic personas. It intelligently selects behavioral modifiers (adjectives) to shape how a persona interacts, ensuring consistency and depth.

## Features

- **Smart Selection**: Selects modifiers from requested categories (e.g., "emotional_intensity", "social_engagement").
- **Coherence Checking**: Ensures selected modifiers do not contradict each other (e.g., preventing "shy" and "outgoing" from appearing together).
- **Intensity Matching**: Balances the intensity of traits to create realistic personalities (e.g., avoiding a mix of "mildly" and "extremely" traits if they clash).
- **Context Awareness**: Can weight certain categories based on the scenario domain (e.g., prioritizing "empathy" in a social services context).

## Configuration

You can configure the Modifier Engine in your conversation JSON file under the `modifier_config` section:

```json
"modifier_config": {
  "modifiers_file": "../modifiers.json",
  "personality_coherence": "balanced",
  "target_modifier_count": 3
}
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `modifiers_file` | string | required | Path to the JSON file defining available modifiers and rules. |
| `personality_coherence` | string | "balanced" | Controls the strictness of personality consistency. Options: <br>• **`high`**: Strict rules, more attempts to find perfect non-contradictory combinations.<br>• **`balanced`**: Good balance of consistency and variety.<br>• **`low`**: More random, allows for potentially contradictory or chaotic combinations. |
| `target_modifier_count` | integer | 3 | The number of modifiers to apply to a persona. |

## How It Works

1.  **Input**: Takes a list of requested modifier categories (defined in the Persona Card) and the configuration settings.
2.  **Selection Strategy**:
    *   It attempts to find **complementary combinations** defined in the rules (e.g., "anxious" + "defensive").
    *   It fills remaining slots with random selections from the requested categories.
3.  **Validation**:
    *   **Contradiction Check**: Verifies against a list of incompatible pairs.
    *   **Intensity Check**: Ensures the "temperature" of the modifiers is relatively consistent.
4.  **Output**: A list of strings (e.g., `["highly anxious", "somewhat defensive", "rapidly speaking"]`) that are injected into the System Prompt.

## Modifiers File Structure

The default modifiers file is located at `input_libraries/modifiers.json`. This file contains:
*   **`modifying_adjectives`**: Hierarchical dictionary of categories -> spectrums -> list of modifiers.
*   **`modifier_application_rules`**: Rules for `avoid_contradictions`, `complementary_combinations`, etc.
