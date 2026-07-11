# FSV Checklist

Before mutation:

- What source of truth proves current state?
- What exact delta is expected?
- What command or API will verify post-state?

After mutation:

- Did the authoritative state change exactly as expected?
- Did unrelated state remain unchanged?
- Is there any contradiction between logs, return values, and source of truth?
