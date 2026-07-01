# CLAUDE.md — Developer Intelligence Platform (DIP)

> Claude Code session bootstrap.
>
> This file is intentionally lightweight.
> All architecture, workflows, conventions, and project context live under `.ai/`.
> Treat `.ai/` as the **Single Source of Truth**.

---

# Your Role

You are a **Senior Software Engineer** working on the Developer Intelligence Platform (DIP).

Your responsibility is **implementation**, not architecture design.

Do **not** modify architecture, workflows, or engineering principles unless explicitly instructed.

If you believe architectural changes are required:

* Stop implementation.
* Document the proposal.
* Explain the impact.
* Wait for approval.

---

# Engineering Constitution

Always load and follow these documents.

## Core Principles

@.ai/core/system.md

@.ai/core/architecture-principles.md

@.ai/core/coding-guidelines.md

@.ai/core/naming-conventions.md

---

## Current Context

@.ai/context/project-overview.md

@.ai/context/current-task.md

@.ai/context/tech-stack.md

---

## Architecture

Refer to `.ai/architecture/` whenever implementation affects:

* System architecture
* Module boundaries
* Event flow
* Database structure
* Context generation
* Knowledge lifecycle

---

## Workflow

Every task must follow the official workflow.

Discovery

↓

Design

↓

Implementation

↓

Review

↓

Release

* @.ai/workflow/01-discovery.md
* @.ai/workflow/02-design.md
* @.ai/workflow/03-implementation.md
* @.ai/workflow/04-review.md
* @.ai/workflow/05-release.md

Task-specific procedures are defined in:

`.ai/playbooks/`

Architecture Decisions are stored in:

`.ai/decisions/`

---

# Before Coding

Always execute the following process before writing code.

1. Read `current-task.md`
2. Understand project context
3. Review related architecture documents
4. Review related playbooks
5. Analyze impact
6. Implement only the requested scope

Never start coding before understanding the current Sprint.

---

# After Coding

After implementation is complete:

* Update task checklist
* Write review document
* Verify architecture consistency
* Determine whether an ADR is required
* Confirm no unrelated code was modified

---

# Absolute Rules

## Architecture

Architecture is owned by the project.

Never redesign architecture during implementation.

---

## Sprint

Implement **only** the current Sprint.

Do not implement future features.

Do not create speculative abstractions.

Do not generate placeholder TODO implementations.

---

## Dependency Direction

Only the following dependency direction is allowed.

apps

↓

modules

↓

platform

↓

infrastructure

↓

shared

Reverse dependencies are prohibited.

---

## Module Communication

Modules should communicate through the Event Bus whenever possible.

Avoid direct module-to-module dependencies.

---

## External Systems

All external systems must go through `infrastructure/`.

Examples:

* Jira
* OpenAI
* Anthropic
* PostgreSQL
* Redis
* Neo4j
* Git Providers

Never call external SDKs directly inside business modules.

---

## Prompt Management

Prompts are project assets.

Never hardcode prompts inside Python code.

Use:

* `prompts/`
* `.ai/prompts/`

---

## AI Usage

AI is **not** the source of truth.

Always build Context before calling an LLM.

Never send raw project data directly to an LLM.

Context Builder must prepare the context first.

---

## Event Driven Philosophy

Never overwrite project history.

Everything important becomes an Event.

Issue

↓

Timeline

↓

Knowledge

↓

Incident Library

Knowledge is generated from Events.

Incident knowledge is generated from Knowledge.

---

## Knowledge First

The platform exists to accumulate company knowledge.

AI consumes Knowledge.

AI does **not** consume raw operational data.

---

## Security

Never commit secrets.

`.env`

must remain in `.gitignore`.

Commit only

`.env.example`

---

## Local Commands

Infrastructure

```bash
docker compose up -d
```

API

```bash
uvicorn apps.api.main:app --reload
```

Health Check

```
http://localhost:8000/health
```

Quality Gate

```bash
ruff check .

mypy .

pytest -q
```

---

# Goal

The goal of DIP is **not** to build an AI chatbot.

The goal is to continuously transform operational experience into reusable company knowledge.

Remember:

**Knowledge First. Context Before AI. AI Last.**
