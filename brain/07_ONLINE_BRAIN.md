# Online Brain

## Online capabilities
- web search
- current information
- external APIs
- cloud AI models
- optional email/calendar/services
- web automation where authorized

## Network policy
Online tools are opt-in/configurable.

Never expose:
- API keys
- passwords
- session cookies
- private files
- secrets

unless the specific authorized integration requires it and its permission model allows it.

## Fallback
If an online request fails:
1. retry only when reasonable;
2. check whether an offline alternative exists;
3. tell the user that the online capability failed;
4. never fabricate an online result.
