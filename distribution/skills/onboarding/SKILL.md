---
name: onboarding
description: Draft an employee USER.md from interview plus research.
version: 0.1.0
author: company-hermes, Hermes Agent
license: Proprietary
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [onboarding, profile, user-md]
    related_skills: [company-research]
---

# Employee onboarding

Complete a person's isolated Hermes profile `USER.md`. Do not write the
file until a human approves the draft. Do not treat this as HR, legal,
or immigration advice.

## When to Use

- Starting a new employee profile (`employee-*`)
- Completing or refreshing a person's `memories/USER.md`
- A joiner asks to set up their company agent profile

Don't use for: customer onboarding, CRM imports, or offboarding
(use the departure runbook).

## Procedure

1. Introduce yourself as the company operating agent. State that profile
   writes require explicit approval. Completion: the person knows what
   you will ask and that nothing is saved yet.
2. Ask the person for: full name, role, email, handles (LinkedIn,
   X/Twitter, GitHub, personal site), timezone, working preferences.
   Completion: every field is either answered or marked declined.
3. RESEARCH the person via the `company-research` skill and `web_search`
   / `web_extract` for public profile facts only. Completion: a short
   research note exists with sources and dates.
4. Mark provenance for every fact: `internal` (the person said it) vs
   `external` (public research). Spec §1: distinguish internal
   recollection from current external research. Completion: each draft
   field has a provenance tag.
5. DRAFT `memories/USER.md` from `USER-TEMPLATE.md` and show a preview.
   Completion: the person has seen the full draft in-chat.
6. Require explicit approval before writing (governance: memory writes
   need approval during pilot). Completion: a named human said yes to
   the exact draft. If they said no, stop.
7. After approval, write the file and record the action in the audit
   trail (requester, profile, purpose, approval). Completion: file
   exists and the audit event is noted.

## Safety

- Never store secrets, passwords, tokens, or private social credentials
  in prompts, the draft, or `USER.md`.
- External research MUST be marked external. Do not present it as
  first-party company truth.
- No professional-advice claim (legal, tax, medical, security).
- Never impersonate the employee or send mail as them.
- Do not copy another profile's `USER.md` or `.env`.

## Verification

- Draft matches `USER-TEMPLATE.md` headings.
- Every non-empty field has provenance.
- No write occurred before approval.
- `rg` over the written file finds no token-like strings.
