/**
 * Project workflow scaffold for upstream audit orchestration.
 */

export async function run(context) {
  const result = {
    status: "scaffold",
    task: "upstream-audit",
    steps: [
      "read project instructions",
      "inspect repository evidence",
      "deduplicate findings",
      "create one issue per confirmed finding",
      "verify issue state after each mutation"
    ],
    findings: []
  };

  return result;
}
