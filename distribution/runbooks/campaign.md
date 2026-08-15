# Runbook: campaign

Phase 4 §4490. Skill `campaign-preflight`.
Specialists: `marketing.*`.
Normative: matrix §3 Publish / External send,
`policies/capabilities.yaml` `publishing.company.send`.

## When to use

Drafting or preflighting a marketing email, social post, or multi-
channel campaign. Not live send. Not CRM commercial commits.

## Inputs

- Requester (marketing / executive)
- Campaign brief and claims to check
- Target channels (TODO: `<CHANNEL_LIST>` — **D023**)
- Audience definition (TODO: which accounts the agent MAY use — **D024**)

## Steps

1. Identify requester and campaign owner. Load a marketing specialist
   only.
2. Search approved brand / claim sources (`kb_search`). Label
   unreviewed social posts as evidence, not facts (classification
   policy).
3. Draft copy internally. Run campaign-preflight: claims, audience
   scope, unsubscribe/legal lines, prohibited topics.
4. Build a send/publish preview (channel, audience count, body hash).
   Do not send.
5. `publishing.company.send` → `approval: campaign-owner`,
   `preview: required`. If the copy makes a legal or contractual
   claim, also require `legal-approvers` (TODO **D011**).
6. Apply only the approved preview. Autonomous publish is disabled
   (spec 8).
7. Trace campaign id, channel, approval id, specialist.

## Approval gates

| Action | Tier | Gate |
|---|---|---|
| Draft / preflight | R1 | Automatic |
| Company publish / campaign send | R2 (R3 if contractual) | Campaign owner; legal if claim |
| Personal-attributed mail | R2 | Accountable employee; automation MUST NOT send as that human |

## Outputs

- Draft pack + preflight checklist
- Preview hash and approval request (if a send is requested)
- Citation list for factual claims

## What must NEVER happen

- Publish or send without campaign-owner approval
- Invent a channel while **D023** is open
- Pull audience lists outside **D024**
- Promote an unreviewed claim to a public company statement
- Use outreach mailboxes as an undeclared publish channel (D026)
