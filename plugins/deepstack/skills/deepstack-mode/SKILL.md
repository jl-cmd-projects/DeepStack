---
name: deepstack-mode
description: "Raise a task in altitude, depth, and range, then prove it. Use for DeepStack, /deepstack-mode, /deepen plus a task, or a first task."
---

# DeepStack mode

Bundled skills live at `../<name>/SKILL.md` from this file. The cited article and the one allowed quote are in [source](references/source.md).

Speed is the same work in less time. DeepStack leaves that kind alone. The work here is altitude, depth, and range. Read [principle-speed-is-settled](../principle-speed-is-settled/SKILL.md) when a request is only about going faster.

## When it runs

On a first task, `/deepen` plus a task, `/deepstack-mode`, or a routine wake that has work, write the three lines and the worker prompt in [intake](references/intake.md) before any plan. The deepening pass writes that prompt and stops. The worker runs it.

Skip when the prompt already carries `CDE_DEEPEN:v1`, when the text is thanks or a yes/no or a status line, when it is a slash command other than `/deepen`, or when it is a helper report.

## Remaining triggers

- The outcome sits above the task. Open [altitude](../altitude/SKILL.md).
- The task should be done the way a top person in the field would do it. Open [depth](../depth/SKILL.md).
- The noun is hiding other fields. Open [range](../range/SKILL.md).
- A claim that the work is done. Open [trust-card](references/trust-card.md) and [outside-judge](../outside-judge/SKILL.md).
- The work is stuck. Open [stuck](references/stuck.md).
- A new rule, hook, or skill. Open [archive-trigger](references/archive-trigger.md).
- A search before a build. Open [search](references/search.md).
- A new feature or a change in behavior. Open [reproducible-check](references/reproducible-check.md).

## Principles

Read the leaf before you apply it.

- [Speed is settled](../principle-speed-is-settled/SKILL.md)
- [Goal beyond the goal](../principle-goal-beyond-the-goal/SKILL.md)
- [Same instruments](../principle-same-instruments/SKILL.md)
- [Unreasonable and solvable](../principle-unreasonable-and-solvable/SKILL.md)
- [Challenge from raw data](../principle-challenge-from-raw-data/SKILL.md)
- [Produce new knowledge](../principle-produce-new-knowledge/SKILL.md)
- [Outside judge](../principle-outside-judge/SKILL.md)
- [Nouns to verbs](../principle-nouns-to-verbs/SKILL.md)
- [Assemble the crew](../principle-assemble-the-crew/SKILL.md)
- [Methods, leave impersonation out](../principle-methods-leave-impersonation-out/SKILL.md)
- [Specific hard goals](../principle-specific-hard-goals/SKILL.md)
- [A seen success](../principle-seen-success/SKILL.md)
- [Room to miss](../principle-room-to-miss/SKILL.md)
- [Durable loop](../principle-durable-loop/SKILL.md)

## Playbooks

Copy the matched playbook's steps into the todo list before task-specific items. A skipped step stays, with `skip: <reason>`.

- [Altitude](playbooks/altitude.md)
- [Depth](playbooks/depth.md)
- [Instruments](playbooks/instruments.md)
- [Unreasonable goal](playbooks/unreasonable-goal.md)
- [Raw check](playbooks/raw-check.md)
- [New knowledge](playbooks/new-knowledge.md)
- [Outside judge](playbooks/outside-judge.md)
- [Range](playbooks/range.md)
- [Durable loop](playbooks/durable-loop.md)
- [Self-efficacy](playbooks/self-efficacy.md)

## Subagents

Spawn `deepstack-agent` for a helper. The chat that received the mode runs the playbook. Read [the delegate](../../../agents/deepstack-agent.md). Give new work to a fresh agent. Resume one only when it still holds a checkout or a live process.

## Models

Role defaults live in [models.json](../../models.json). `/setup-deepstack` writes the override sheet. A role with no line runs on the parent session's model.

## Replacements

These names are the triggers the archive table cites.

- DeepStack intake is [intake](references/intake.md).
- DeepStack search leaf is [search](references/search.md).
- DeepStack reproducible-check leaf is [reproducible-check](references/reproducible-check.md).

## Report

A report says what was asked, whether it is done, what is left, and the links. It stands alone. Shape: [report](references/report.md).
