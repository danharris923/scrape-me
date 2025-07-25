# Pydantic AI Tools Documentation

## Tool Registration Methods

### 1. Decorator-based Registration
```python
# Default decorator with agent context access
@agent.tool
def get_player_name(ctx: RunContext[str]) -> str:
    """Get the player's name."""
    return ctx.deps

# Plain tool without context
@agent.tool_plain
def roll_dice() -> str:
    """Roll a six-sided die and return the result."""
    return str(random.randint(1, 6))
```

### 2. Tool with Retry Mechanism
```python
def my_flaky_tool(query: str) -> str:
    if query == 'bad':
        # Tell the LLM the query was bad and it should try again
        raise ModelRetry("The query 'bad' is not allowed. Please provide a different query.")
    return 'Success!'
```

### 3. Dynamic Tool with Prepare Method
```python
async def only_if_42(
    ctx: RunContext[int], tool_def: ToolDefinition
) -> Union[ToolDefinition, None]:
    if ctx.deps == 42:
        return tool_def

@agent.tool(prepare=only_if_42)
def hitchhiker(ctx: RunContext[int], answer: str) -> str:
    return f'{ctx.deps} {answer}'
```

## Key Features
- Automatic parameter schema extraction
- Support for error handling and retries
- Dynamic tool enable/disable
- Multi-modal content support
- Integration with third-party tools