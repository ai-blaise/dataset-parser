#!/bin/bash
# Multi-turn Rerollout Demo
# Shows how to regenerate assistant responses while maintaining context

set -e

API_URL="http://localhost:30000/v1/chat/completions"
MODEL="deepseek-ai/DeepSeek-V3.2-Speciale"
RECORD_FILE="parsed_datasets/interactive_agent_parsed.jsonl"

# Get first record
RECORD=$(head -1 "$RECORD_FILE")

# Extract tools (stays constant)
TOOLS=$(echo "$RECORD" | jq '.tools')

# Extract all messages
MESSAGES=$(echo "$RECORD" | jq '.messages')

# Count messages
MSG_COUNT=$(echo "$MESSAGES" | jq 'length')
echo "=== Multi-turn Rerollout Demo ==="
echo "Record has $MSG_COUNT messages"
echo ""

# Build context incrementally
CONTEXT="[]"
TURN=0

for ((i=0; i<MSG_COUNT; i++)); do
    MSG=$(echo "$MESSAGES" | jq ".[$i]")
    ROLE=$(echo "$MSG" | jq -r '.role')

    echo "--- Message $i: $ROLE ---"

    if [ "$ROLE" = "assistant" ]; then
        TURN=$((TURN + 1))
        echo ">> TURN $TURN: Calling model to regenerate assistant response..."
        echo "   Context size: $(echo "$CONTEXT" | jq 'length') messages"

        # Build request payload
        PAYLOAD=$(jq -n \
            --arg model "$MODEL" \
            --argjson messages "$CONTEXT" \
            --argjson tools "$TOOLS" \
            '{
                model: $model,
                messages: $messages,
                tools: $tools,
                temperature: 0.7,
                max_tokens: 2048
            }')

        # Call the model
        RESPONSE=$(curl -s "$API_URL" \
            -H "Content-Type: application/json" \
            -d "$PAYLOAD")

        # Extract the new assistant message
        NEW_ASSISTANT=$(echo "$RESPONSE" | jq '.choices[0].message')

        # Check if it has tool_calls
        HAS_TOOL_CALLS=$(echo "$NEW_ASSISTANT" | jq 'has("tool_calls") and (.tool_calls | length > 0)')

        echo "   Model response:"
        if [ "$HAS_TOOL_CALLS" = "true" ]; then
            TOOL_NAME=$(echo "$NEW_ASSISTANT" | jq -r '.tool_calls[0].function.name')
            echo "   -> Tool call: $TOOL_NAME"
        else
            CONTENT=$(echo "$NEW_ASSISTANT" | jq -r '.content' | head -c 200)
            echo "   -> Content: ${CONTENT}..."
        fi
        echo ""

        # Add NEW assistant message to context (not the original)
        CONTEXT=$(echo "$CONTEXT" | jq --argjson msg "$NEW_ASSISTANT" '. + [$msg]')

    else
        # For system, user, tool messages - add as-is to context
        echo "   Adding to context as-is"

        # Clean the message (remove empty fields for cleaner context)
        CLEAN_MSG=$(echo "$MSG" | jq '{role, content} +
            (if .tool_calls then {tool_calls} else {} end) +
            (if .tool_call_id then {tool_call_id} else {} end)')

        CONTEXT=$(echo "$CONTEXT" | jq --argjson msg "$CLEAN_MSG" '. + [$msg]')
        echo ""
    fi
done

echo "=== Rerollout Complete ==="
echo "Final context has $(echo "$CONTEXT" | jq 'length') messages"
echo ""
echo "Final conversation:"
echo "$CONTEXT" | jq -r '.[] | "[\(.role)]: \(.content // .tool_calls[0].function.name // "(tool response)")" | .[0:100]'
