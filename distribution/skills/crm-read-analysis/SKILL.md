---
name: crm-read-analysis
description: Read-only CRM analysis. No record mutation.
required_environment_variables:
  - COMPANY_KB_TOKEN
---

# Crm Read Analysis

Domain: crm-read. Spec 19.2 / 19.3. Safe defaults: read-only unless a
named approval skill is used. No credentials in this file.

## Use when

Use to summarize accounts, pipelines, or hygiene exceptions without writing.

## Procedure

1. Identify the requesting user and allowed CRM connection.
2. Read only objects in the approved scope (TODO: CRM_NAME / D020).
3. Produce an internal analysis with record ids and source timestamps.
4. If a write would help, stop and hand off to crm-write-with-approval.

## Safety

- Read-only. No create/update/delete.
- Do not export bulk customer data without approval.
- Do not assume Notion or any present tool is the CRM (ADR-0001).
