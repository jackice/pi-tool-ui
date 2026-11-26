import type { DiffHunk, DiffLine, EditViewModel } from "@jackice/pi-ui";

const hunkHeader = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$/;
const noNewline = "\\ No newline at end of file";

export function adaptNativeEdit(details: unknown, args: unknown, timing: Pick<EditViewModel, "toolCallId" | "durationMs">): EditViewModel | undefined {
	if (details === null || typeof details !== "object" || !("patch" in details) || typeof details.patch !== "string") return;
	if (args === null || typeof args !== "object" || !("path" in args) || typeof args.path !== "string" || args.path.length === 0) return;

	const rows = details.patch.split("\n");
	if (rows.at(-1) === "") rows.pop();
	// 原生 edit 只修改一个文件，多文件或其他格式交还原生渲染器。
	if (!rows[0]?.startsWith("--- ") || !rows[1]?.startsWith("+++ ") || rows[0].slice(4) !== rows[1].slice(4)) return;
	const hunks: DiffHunk[] = [];
	let additions = 0;
	let deletions = 0;
	let i = 2;
	while (i < rows.length) {
		const header = hunkHeader.exec(rows[i++]!);
		if (header === null) return;
		const oldStart = Number(header[1]);
		const oldLines = Number(header[2] ?? 1);
		const newStart = Number(header[3]);
		const newLines = Number(header[4] ?? 1);
		if (!Number.isSafeInteger(oldStart + oldLines) || !Number.isSafeInteger(newStart + newLines)) return;
		if ((oldStart === 0 && oldLines > 0) || (newStart === 0 && newLines > 0)) return;
		const lines: DiffLine[] = [];
		let oldUsed = 0;
		let newUsed = 0;
		while (oldUsed < oldLines || newUsed < newLines) {
			const row = rows[i++];
			if (row === undefined) return;
			const content = row.slice(1);
			switch (row[0]) {
				case " ":
					lines.push({ kind: "context", content, oldLine: oldStart + oldUsed++, newLine: newStart + newUsed++ });
					break;
				case "-":
					lines.push({ kind: "removed", content, oldLine: oldStart + oldUsed++ });
					deletions++;
					break;
				case "+":
					lines.push({ kind: "added", content, newLine: newStart + newUsed++ });
					additions++;
					break;
				default:
					return;
			}
			if (oldUsed > oldLines || newUsed > newLines) return;
			if (rows[i] === noNewline) i++;
		}
		if (lines.length === 0) return;
		hunks.push({ oldStart, oldLines, newStart, newLines, lines });
	}
	if (additions === 0 && deletions === 0) return;
	return { ...timing, status: "success", files: [{ path: args.path, operation: "update", status: "success", hunks, additions, deletions }] };
}
