#!/bin/bash
# Minimal example: Multi-turn rerollout with curl
#
# KEY CONCEPT:
# - Turn 1: [system, user1] → model → assistant1
# - Turn 2: [system, user1, assistant1, tool_result, ...] → model → assistant2
# - Each turn ACCUMULATES prior context including NEW model outputs

API="http://localhost:30000/v1/chat/completions"
MODEL="deepseek-ai/DeepSeek-V3.2-Speciale"

# Get first record's data
RECORD=$(head -1 parsed_datasets/interactive_agent_parsed.jsonl)
SYSTEM=$(echo "$RECORD" | jq '.messages[0]')
USER1=$(echo "$RECORD" | jq '.messages[1]')
TOOL_RESULT=$(echo "$RECORD" | jq '.messages[3]')  # Tool response from original
TOOLS=$(echo "$RECORD" | jq '.tools')

echo "=== TURN 1: Initial user message ==="
echo "Context: [system, user1]"
echo ""

# TURN 1: system + user → get assistant response
TURN1_RESPONSE=$(curl -s "$API" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg model "$MODEL" \
    --argjson system "$SYSTEM" \
    --argjson user "$USER1" \
    --argjson tools "$TOOLS" \
    '{
      model: $model,
      messages: [$system, $user],
      tools: $tools,
      temperature: 0.7
    }')")

# Extract assistant message from response
ASSISTANT1=$(echo "$TURN1_RESPONSE" | jq '.choices[0].message')
echo "Model response (Turn 1):"
echo "$ASSISTANT1" | jq '{role, content: (.content // ""), tool_calls: [.tool_calls[]?.function.name]}'
echo ""

# Check if model made a tool call
HAS_TOOL_CALL=$(echo "$ASSISTANT1" | jq 'has("tool_calls") and (.tool_calls | length > 0)')

if [ "$HAS_TOOL_CALL" = "true" ]; then
    echo "=== TURN 2: After tool execution ==="
    echo "Context: [system, user1, NEW_assistant1, tool_result]"
    echo ""

    # TURN 2: system + user + NEW_assistant + tool_result → get next response
    # NOTE: We use ASSISTANT1 (model's NEW response), not the original!
    TURN2_RESPONSE=$(curl -s "$API" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg model "$MODEL" \
        --argjson system "$SYSTEM" \
        --argjson user "$USER1" \
        --argjson assistant1 "$ASSISTANT1" \
        --argjson tool_result "$TOOL_RESULT" \
        --argjson tools "$TOOLS" \
        '{
          model: $model,
          messages: [$system, $user, $assistant1, $tool_result],
          tools: $tools,
          temperature: 0.7
        }')")

    ASSISTANT2=$(echo "$TURN2_RESPONSE" | jq '.choices[0].message')
    echo "Model response (Turn 2):"
    echo "$ASSISTANT2" | jq '{role, content: (.content[:200] // ""), tool_calls: [.tool_calls[]?.function.name]}'
fi

echo ""
echo "=== KEY INSIGHT ==="
echo "Each turn uses the NEWLY GENERATED assistant response as context,"
echo "not the original dataset's assistant message."
echo ""
echo "This is how you 'reroll' - the model rewrites all assistant turns"
echo "while preserving user inputs and tool results from the original."
