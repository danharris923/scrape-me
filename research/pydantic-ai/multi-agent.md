# Multi-Agent Applications in Pydantic AI

## Key Patterns

### Agent Delegation (Agent-as-Tool)
```python
joke_selection_agent = Agent(
    'openai:gpt-4o',
    system_prompt='Use the `joke_factory` to generate some jokes, then choose the best.'
)

joke_generation_agent = Agent(
    'google-gla:gemini-1.5-flash', 
    output_type=list[str]
)

@joke_selection_agent.tool 
async def joke_factory(ctx: RunContext[None], count: int) -> list[str]:
    r = await joke_generation_agent.run(
        f'Please generate {count} jokes.',
        usage=ctx.usage,  # CRITICAL: Pass usage for token tracking
    )
    return r.output
```

### Agent Delegation with Dependencies
```python
@dataclass 
class ClientAndKey:
    http_client: httpx.AsyncClient
    api_key: str

joke_selection_agent = Agent(
    'openai:gpt-4o',
    deps_type=ClientAndKey,
    system_prompt='Use the `joke_factory` tool to generate jokes.'
)

@joke_selection_agent.tool 
async def joke_factory(ctx: RunContext[ClientAndKey], count: int) -> list[str]:
    r = await joke_generation_agent.run(
        f'Please generate {count} jokes.',
        deps=ctx.deps,  # Pass dependencies
        usage=ctx.usage,  # Pass usage tracking
    )
    return r.output
```

### Key Characteristics
- Agents are stateless and global
- Always pass `ctx.usage` between agents for token tracking
- Can use `UsageLimits` to control costs
- Dependencies can be shared or subset between agents
- Agents can use different models