/**
 * Project workflow scaffold for implementing a single issue as a PR.
 */

export async function run(context) {
  return {
    status: "scaffold",
    task: "issue-to-pr",
    requiredInput: "issueUrlOrNumber",
    steps: [
      "read issue",
      "confirm finding",
      "create branch",
      "implement minimal fix",
      "run verification",
      "open PR",
      "read PR state after creation"
    ]
  };
}
