<!-- ai-generated: 70% - Claude (AI assistant) drafted these justifications under the student's direction. -->

# Agent policy - denylist justifications

Each entry below is a blast-radius decision for the `reviewer` sub-agent (`.claude/agents/reviewer.md`): a
capability it is denied because the damage it could cause is larger than the value it adds to a review.

- Bash(rm *): the reviewer reads and comments; deleting files is the author's decision, not the reviewer's, and an agent that can delete could silently destroy uncommitted work while "reviewing" it.
- Bash(git push *): a reviewer that can push could publish an unreviewed or half-finished change under the student's identity, defeating the point of having a review step at all.
- Bash(docker *): starting or stopping containers is an operational action with side effects (ports, volumes, data loss on a bad `down -v`) that has nothing to do with reading a diff and forming an opinion on it.
- WebFetch: the review must be reproducible from the files already in this repository (REQUIREMENTS.md, API.md, DECISIONS.md); fetching arbitrary external pages would let an untrusted page's content silently steer the review's conclusions.
