# Pydantic AI Agents Documentation

## Agent Creation
```python
from pydantic_ai import Agent, RunContext

# Basic agent creation
agent = Agent(
    'openai:gpt-4o',  # Model
    deps_type=User,   # Dependency type
    output_type=bool, # Output type
    system_prompt="Use the customer's name while replying"
)
```

## Key Components

### 1. Dependencies
- Specify the type of context the agent can use
- Passed during agent run
- Can be any Python type

### 2. System Prompts
```python
@agent.system_prompt
def add_user_name(ctx: RunContext[str]) -> str:
    return f"The user's name is {ctx.deps}."
```

### 3. Tools
```python
@agent.tool(retries=2)
def get_user_by_name(ctx: RunContext[DatabaseConn], name: str) -> int:
    """Get a user's ID from their full name."""
    user_id = ctx.deps.users.get(name=name)
    if user_id is None:
        raise ModelRetry(f'No user found with name {name!r}')
    return user_id
```

### 4. Running Agents
- `agent.run()`: Async coroutine
- `agent.run_sync()`: Synchronous method
- `agent.run_stream()`: Streaming response
- `agent.iter()`: Detailed graph iteration

Example:
```python
result = agent.run_sync(
    'Send a message to John Doe',
    deps=database_connection
)
```