# Tool Registry

Each tool must declare:

- name
- version
- description
- input schema
- output schema
- risk level
- required permissions
- offline/online availability
- reversibility
- verification method

Example:
```yaml
name: set_volume
version: 1
availability: offline
risk: low
reversible: true
permissions: []
```

## Tool discovery
The brain should know available tools at startup and after configuration changes.

## Tool selection
Choose:
1. exact deterministic tool;
2. specialized local tool;
3. online tool;
4. ask user if no safe route exists.

Never invent a tool that is not registered.
