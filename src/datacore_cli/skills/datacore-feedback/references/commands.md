# Feedback commands

Authenticate with `datacore auth login`. Use the platform selected by the user; never put a token on a command line.

```sh
datacore feedback new --page /example
datacore feedback new --image redacted.png --tool example-tool --project 7
datacore feedback submit --json --file feedback.json --yes
datacore feedback list --json
datacore feedback show 0123456789abcdef0123456789abcdef --json
datacore feedback comment 0123456789abcdef0123456789abcdef "The example should also cover empty input." --yes
datacore feedback accept 0123456789abcdef0123456789abcdef --yes
datacore feedback reopen 0123456789abcdef0123456789abcdef --message "The confirmed example still fails." --yes
datacore feedback export 0123456789abcdef0123456789abcdef --output feedback-7.md
```

Synthetic request shape (replace every example with the user's confirmed words):

```json
{
  "message": "Please make the example table easier to filter.",
  "context": {"route": "/example", "tool_id": "example-tool"},
  "answers": {
    "location": "The filter above the example table.",
    "current": "Changing the filter clears every selection.",
    "expected": "Keep selected rows that still match the filter.",
    "example": "Select row A, filter for A, and A should stay selected.",
    "audience": "The person reviewing examples, several times a day.",
    "impact": "Repeated selection slows review; normal priority."
  },
  "summary": "Keep matching selections when a filter changes.",
  "plan": "Draft: verify selection behavior against the confirmed example.",
  "conversation": [],
  "public": false,
  "allow_incomplete": false
}
```

`--file -` reads JSON from stdin. `--json` works before `feedback` or after its subcommand. `submit --json` never prompts, calls the AI, or rewrites the user's answers. Missing required answers produce exit 2 with `error.code=feedback_incomplete` and `error.details.questions`; no clarified feedback is saved. Only explicit `allow_incomplete=true` requests a pending-clarification draft. The server is the source of truth for required fields.

`--image redacted.png` on `new` or `submit` adds that exact image (maximum 5 MiB); `--page`, `--tool`, and `--project` add only the chosen context. Images must already be flattened and redacted. Text, selected images, and conversation are sent to the platform; no other local files are read.

`new` requires a real terminal. It uses the platform's clarification AI and shared checklist, shows the final content and visibility, and asks before the final write. If the AI is unavailable, it lets the user fill the checklist manually; it never marks a partial AI result as a successful clarification.

List views are `mine` (default), `public`, and superadministrator-only `all`. Read access does not imply access to private feedback. Owner or superadministrator can accept/reopen only while awaiting acceptance. Exit 10 requests login, 11 indicates a permission/scope problem, and 12 includes unavailable or disabled feedback. Follow the structured error's `action` rather than retrying blindly.
