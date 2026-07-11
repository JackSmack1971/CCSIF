/**
 * Discover open repository-hygiene issues, implement each as an isolated
 * branch/PR via implementation-agent, review each PR via pr-reviewer, and
 * record every outcome in the issue-to-pr journal.
 *
 * This is the multi-agent-orchestration counterpart to the
 * `.claude/skills/issue-to-pr` skill: use it when a user has explicitly
 * asked for workflow-based fan-out across a batch of issues. For a single
 * issue or a small, human-supervised batch, follow the skill directly
 * instead — it processes sequentially by default, which is easier to
 * review as it goes.
 */

export const meta = {
  name: 'issue-to-pr',
  description: 'Discover open repository-hygiene issues, implement each as an isolated branch/PR, review it, and journal the outcome.',
  phases: [
    { title: 'Plan', detail: 'discover open hygiene issues and build a digest-bound work plan' },
    { title: 'Implement', detail: 'one worktree-isolated implementation-agent per ready issue' },
    { title: 'Review', detail: 'one pr-reviewer per opened PR' },
    { title: 'Record', detail: 'journal every outcome' },
  ],
}

const PLAN_ITEM_SCHEMA = {
  type: 'object',
  properties: {
    issue_number: { type: 'integer' },
    issue_url: { type: 'string' },
    title: { type: 'string' },
    fingerprint: { type: 'string' },
    branch: { type: 'string' },
    destructive: { type: 'boolean' },
    status: { type: 'string', enum: ['ready', 'blocked', 'destructive-skip', 'pr-exists'] },
    block_reason: { type: ['string', 'null'] },
    existing_pr_url: { type: ['string', 'null'] },
  },
  required: ['issue_number', 'title', 'branch', 'status'],
}

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    repository: { type: 'string' },
    digest: { type: 'string' },
    order: { type: 'array', items: { type: 'integer' } },
    items: { type: 'array', items: PLAN_ITEM_SCHEMA },
    validation_errors: { type: 'array', items: { type: 'string' } },
  },
  required: ['ok'],
}

const IMPLEMENT_SCHEMA = {
  type: 'object',
  properties: {
    issue_number: { type: 'integer' },
    status: { type: 'string', enum: ['opened', 'failed'] },
    branch: { type: 'string' },
    pr_url: { type: ['string', 'null'] },
    verification: { type: 'string' },
    risk: { type: 'string' },
    rollback: { type: 'string' },
    error: { type: ['string', 'null'] },
  },
  required: ['issue_number', 'status'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'request changes', 'needs info'] },
    blocking_issues: { type: 'array', items: { type: 'string' } },
    non_blocking_suggestions: { type: 'array', items: { type: 'string' } },
    verification_gaps: { type: 'array', items: { type: 'string' } },
    merge_safety_notes: { type: 'string' },
  },
  required: ['verdict'],
}

const RECORD_SCHEMA = {
  type: 'object',
  properties: {
    issue_number: { type: 'integer' },
    recorded: { type: 'boolean' },
  },
  required: ['issue_number', 'recorded'],
}

const repo = (args && args.repo) || '.'
const label = (args && args.label) || 'repository-hygiene'
const issueFilter = (args && args.issue) || null
const planPath = (args && args.planPath) || '.issue-to-pr/plan.json'
const journalPath = (args && args.journalPath) || '.issue-to-pr/journal.json'
const issueFlags = issueFilter ? issueFilter.map(n => `--issue ${n}`).join(' ') : ''

phase('Plan')
const plan = await agent(
  `Run the issue-to-pr skill's deterministic planner against the repository at "${repo}":
python3 .claude/skills/issue-to-pr/scripts/issue_to_pr.py plan --repo ${repo} --label ${label} ${issueFlags} --out ${planPath}
Then run:
python3 .claude/skills/issue-to-pr/scripts/issue_to_pr.py validate --plan ${planPath}
If validate reports a non-zero exit or any errors, return {"ok": false, "validation_errors": [...]} and stop — do not proceed. Otherwise read ${planPath} and return {"ok": true, "repository": <repository>, "digest": <digest>, "order": <order>, "items": <items>} with those four fields copied verbatim from the file (do not reformat, reorder, or invent any field).`,
  { schema: PLAN_SCHEMA, label: 'discover-and-plan' }
)

if (!plan || !plan.ok) {
  log(`Planning failed or found nothing to do: ${plan ? plan.validation_errors.join('; ') : 'agent returned no result'}`)
  return {
    status: 'failed',
    task: 'issue-to-pr',
    steps: ['discover and plan'],
    findings: plan && plan.validation_errors ? plan.validation_errors.map(message => ({ status: 'plan-invalid', message })) : [],
  }
}

const readyItems = plan.items.filter(item => plan.order.includes(item.issue_number))
const skippedItems = plan.items.filter(item => !plan.order.includes(item.issue_number))
log(`Plan: ${readyItems.length} ready, ${skippedItems.length} skipped (blocked / destructive / pr-exists).`)

const results = await pipeline(
  readyItems,
  item => agent(
    `Repository: ${plan.repository}. Issue: #${item.issue_number} (${item.issue_url}). Branch: ${item.branch}. Title: "${item.title}". Implement this issue exactly as your instructions specify and return your structured output.`,
    { schema: IMPLEMENT_SCHEMA, agentType: 'implementation-agent', phase: 'Implement', label: `implement-#${item.issue_number}`, isolation: 'worktree' }
  ),
  (implementResult, item) => (implementResult && implementResult.status === 'opened')
    ? agent(
        `Review ${implementResult.pr_url} against issue #${item.issue_number} (${item.issue_url}). Return your structured verdict.`,
        { schema: REVIEW_SCHEMA, agentType: 'pr-reviewer', phase: 'Review', label: `review-#${item.issue_number}` }
      ).then(review => ({ implementResult, review }))
    : { implementResult, review: null },
  (stage2, item) => {
    const status = !stage2.implementResult || stage2.implementResult.status !== 'opened'
      ? 'failed'
      : (stage2.review && stage2.review.verdict === 'approve' ? 'opened' : 'needs-changes')
    const prUrlFlag = stage2.implementResult && stage2.implementResult.pr_url ? `--pr-url "${stage2.implementResult.pr_url}"` : ''
    const verdictFlag = stage2.review ? `--review-verdict "${stage2.review.verdict}"` : ''
    const errorFlag = stage2.implementResult && stage2.implementResult.error ? `--error "${stage2.implementResult.error}"` : ''
    return agent(
      `Run: python3 .claude/skills/issue-to-pr/scripts/issue_to_pr.py record --journal ${journalPath} --plan ${planPath} --issue ${item.issue_number} --status ${status} ${prUrlFlag} ${verdictFlag} ${errorFlag}
Return {"issue_number": ${item.issue_number}, "recorded": true} if the command exited 0, otherwise {"issue_number": ${item.issue_number}, "recorded": false}.`,
      { schema: RECORD_SCHEMA, phase: 'Record', label: `record-#${item.issue_number}` }
    ).then(recordResult => ({ implementResult: stage2.implementResult, review: stage2.review, recordResult, status }))
  }
)

const findings = skippedItems.map(item => ({
  issue_number: item.issue_number,
  title: item.title,
  status: item.status,
  reason: item.block_reason || (item.existing_pr_url ? `PR already exists: ${item.existing_pr_url}` : null),
}))

readyItems.forEach((item, index) => {
  const r = results[index]
  if (!r) {
    findings.push({ issue_number: item.issue_number, title: item.title, branch: item.branch, status: 'failed', reason: 'pipeline stage threw before completion' })
    return
  }
  findings.push({
    issue_number: item.issue_number,
    title: item.title,
    branch: item.branch,
    status: r.status,
    pr_url: r.implementResult ? r.implementResult.pr_url : null,
    verdict: r.review ? r.review.verdict : null,
    recorded: r.recordResult ? r.recordResult.recorded : false,
  })
})

log(`Done: ${findings.filter(f => f.status === 'opened').length} opened, ${findings.filter(f => f.status === 'needs-changes').length} need changes, ${findings.filter(f => f.status === 'failed').length} failed, ${skippedItems.length} skipped.`)

return {
  status: 'completed',
  task: 'issue-to-pr',
  steps: [
    'discover and plan',
    'validate plan',
    'implement each ready issue (worktree-isolated)',
    'review each opened PR',
    'record every outcome in the journal',
  ],
  findings,
}
