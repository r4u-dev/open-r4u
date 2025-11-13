import React, { useMemo } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { ArrowRight } from "lucide-react";
import type { TaskVersion } from "@/lib/mock-data/taskDetails";
import { formatSettingLabel } from "@/lib/implementations";

interface ImplementationDiffDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    versions: TaskVersion[];
    baseVersionId: string | null;
    targetVersionId: string | null;
    onBaseVersionChange: (versionId: string) => void;
    onTargetVersionChange: (versionId: string) => void;
}

type DiffSegment = {
    type: "equal" | "delete" | "insert";
    value: string;
};

const getVersionLabel = (version: TaskVersion) =>
    `v${version.version} · ${version.model}`;

const tokenizeText = (text: string): string[] =>
    text.length === 0 ? [] : text.split(/(\s+)/).filter(Boolean);

const buildDiffSegments = (beforeText: string, afterText: string): DiffSegment[] => {
    const beforeTokens = tokenizeText(beforeText);
    const afterTokens = tokenizeText(afterText);
    const n = beforeTokens.length;
    const m = afterTokens.length;
    const lcs: number[][] = Array.from({ length: n + 1 }, () =>
        new Array(m + 1).fill(0),
    );

    for (let i = n - 1; i >= 0; i--) {
        for (let j = m - 1; j >= 0; j--) {
            if (beforeTokens[i] === afterTokens[j]) {
                lcs[i][j] = lcs[i + 1][j + 1] + 1;
            } else {
                lcs[i][j] = Math.max(lcs[i + 1][j], lcs[i][j + 1]);
            }
        }
    }

    const segments: DiffSegment[] = [];
    let i = 0;
    let j = 0;
    while (i < n && j < m) {
        if (beforeTokens[i] === afterTokens[j]) {
            segments.push({ type: "equal", value: beforeTokens[i] });
            i += 1;
            j += 1;
        } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
            segments.push({ type: "delete", value: beforeTokens[i] });
            i += 1;
        } else {
            segments.push({ type: "insert", value: afterTokens[j] });
            j += 1;
        }
    }
    while (i < n) {
        segments.push({ type: "delete", value: beforeTokens[i++] });
    }
    while (j < m) {
        segments.push({ type: "insert", value: afterTokens[j++] });
    }
    return segments;
};

const normalizeComparable = (value: unknown): unknown => {
    if (typeof value === "string") {
        const trimmed = value.trim();
        if (trimmed === "") return "";
        const numeric = Number(trimmed);
        if (!Number.isNaN(numeric) && `${numeric}` === trimmed) {
            return numeric;
        }
        return trimmed;
    }
    if (Array.isArray(value)) {
        return value.map(normalizeComparable);
    }
    if (value && typeof value === "object") {
        return Object.keys(value as Record<string, unknown>)
            .sort()
            .reduce<Record<string, unknown>>((acc, key) => {
                acc[key] = normalizeComparable(
                    (value as Record<string, unknown>)[key],
                );
                return acc;
            }, {});
    }
    return value;
};

const valuesEqual = (a: unknown, b: unknown): boolean =>
    JSON.stringify(normalizeComparable(a)) ===
    JSON.stringify(normalizeComparable(b));

const stringifyValue = (value: unknown): string => {
    if (value === null || value === undefined) return "—";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") {
        return String(value);
    }
    if (Array.isArray(value)) {
        return value.length > 0 ? value.join(", ") : "[]";
    }
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
};

const DiffSection: React.FC<{ title: string; children: React.ReactNode }> = ({
    title,
    children,
}) => (
    <div className="space-y-3 rounded-xl border border-border/70 bg-background/70 p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <div className="space-y-3">{children}</div>
    </div>
);

const renderSimpleDiff = (beforeValue: unknown, afterValue: unknown) => {
    const beforeText = stringifyValue(beforeValue);
    const afterText = stringifyValue(afterValue);

    if (valuesEqual(beforeValue, afterValue)) {
        return (
            <span className="text-sm text-muted-foreground whitespace-pre-wrap">
                {afterText}
            </span>
        );
    }

    const beforeClass =
        beforeText === "—"
            ? "text-muted-foreground"
            : "text-destructive line-through";
    const afterClass =
        afterText === "—"
            ? "text-muted-foreground"
            : "font-medium text-foreground";

    return (
        <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className={`${beforeClass} whitespace-pre-wrap`}>
                {beforeText}
            </span>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <span className={`${afterClass} whitespace-pre-wrap`}>{afterText}</span>
        </div>
    );
};

const renderTextDiff = (beforeText: string, afterText: string) => {
    if (valuesEqual(beforeText, afterText)) {
        return (
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                {beforeText || "—"}
            </div>
        );
    }

    const segments = buildDiffSegments(beforeText, afterText);

    return (
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {segments.map((segment, index) => {
                const isWhitespace = /^\s+$/.test(segment.value);
                const className =
                    segment.type === "delete"
                        ? isWhitespace
                            ? ""
                            : "text-destructive line-through decoration-2 decoration-destructive/60"
                        : segment.type === "insert"
                          ? isWhitespace
                              ? ""
                              : "text-primary font-semibold"
                          : "";
                return (
                    <span key={index} className={className}>
                        {segment.value}
                    </span>
                );
            })}
        </div>
    );
};

const renderToolsDiff = (
    beforeTools: string[],
    afterTools: string[],
) => {
    if (valuesEqual(beforeTools, afterTools)) {
        return (
            <div className="flex flex-wrap gap-2 text-sm text-foreground">
                {afterTools.length > 0
                    ? afterTools.map((tool) => (
                          <span key={tool} className="rounded-md bg-muted px-2 py-1">
                              {tool}
                          </span>
                      ))
                    : "None"}
            </div>
        );
    }

    const beforeSet = new Set(beforeTools);
    const afterSet = new Set(afterTools);

    const removed = beforeTools.filter((tool) => !afterSet.has(tool));
    const added = afterTools.filter((tool) => !beforeSet.has(tool));

    const renderChips = (
        tools: string[],
        highlightRemoved: boolean,
        highlightAdded: boolean,
    ) =>
        tools.length > 0 ? (
            tools.map((tool) => {
                const isRemoved = highlightRemoved && removed.includes(tool);
                const isAdded = highlightAdded && added.includes(tool);
                const className = [
                    "rounded-md px-2 py-1",
                    "border",
                    isRemoved
                        ? "border-destructive/60 bg-destructive/10 text-destructive line-through"
                        : isAdded
                          ? "border-primary/60 bg-primary/10 text-primary font-medium"
                          : "border-border bg-muted/60 text-foreground",
                ].join(" ");
                return (
                    <span key={tool} className={className}>
                        {tool}
                    </span>
                );
            })
        ) : (
            <span className="text-muted-foreground">None</span>
        );

    return (
        <div className="space-y-2 text-sm">
            <div className="flex flex-wrap gap-2">
                {renderChips(beforeTools, true, false)}
            </div>
            <div className="flex items-start gap-2">
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="flex flex-wrap gap-2">
                    {renderChips(afterTools, false, true)}
                </div>
            </div>
        </div>
    );
};

const LabeledDiffRow: React.FC<{
    label: string;
    beforeValue: unknown;
    afterValue: unknown;
}> = ({ label, beforeValue, afterValue }) => (
    <div className="space-y-1">
        <div className="text-sm font-medium text-foreground">{label}</div>
        {renderSimpleDiff(beforeValue, afterValue)}
    </div>
);

export const ImplementationDiffDialog: React.FC<
    ImplementationDiffDialogProps
> = ({
    open,
    onOpenChange,
    versions,
    baseVersionId,
    targetVersionId,
    onBaseVersionChange,
    onTargetVersionChange,
}) => {
    const baseVersion = useMemo(
        () => versions.find((version) => version.id === baseVersionId) ?? null,
        [versions, baseVersionId],
    );
    const targetVersion = useMemo(
        () => versions.find((version) => version.id === targetVersionId) ?? null,
        [versions, targetVersionId],
    );

    const baseSettings = baseVersion?.settings ?? {};
    const targetSettings = targetVersion?.settings ?? {};
    const settingsDiff = useMemo(() => {
        if (!baseVersion || !targetVersion) return [];
        const keys = Array.from(
            new Set([...Object.keys(baseSettings), ...Object.keys(targetSettings)]),
        ).sort();
        return keys.map((key) => {
            const beforeValue = baseSettings[key];
            const afterValue = targetSettings[key];
            return {
                key,
                label: formatSettingLabel(key),
                beforeValue,
                afterValue,
                changed: !valuesEqual(beforeValue, afterValue),
            };
        });
    }, [baseVersion, targetVersion, baseSettings, targetSettings]);

    const baseReasoning = (baseVersion?.reasoning ?? {}) as Record<
        string,
        unknown
    >;
    const targetReasoning = (targetVersion?.reasoning ?? {}) as Record<
        string,
        unknown
    >;
    const reasoningDiff = useMemo(() => {
        if (!baseVersion || !targetVersion) return [];
        const keys = Array.from(
            new Set([
                ...Object.keys(baseReasoning),
                ...Object.keys(targetReasoning),
            ]),
        );
        const labelMap: Record<string, string> = {
            effort: "Reasoning Effort",
            summary: "Reasoning Summary",
        };
        return keys.map((key) => {
            const beforeValue = baseReasoning[key];
            const afterValue = targetReasoning[key];
            return {
                key,
                label: labelMap[key] ?? formatSettingLabel(key),
                beforeValue,
                afterValue,
                changed: !valuesEqual(beforeValue, afterValue),
            };
        });
    }, [baseVersion, targetVersion, baseReasoning, targetReasoning]);

    const toolChoiceDiff = useMemo(() => {
        if (!baseVersion || !targetVersion) return null;
        const beforeValue = baseVersion.toolChoice ?? "auto";
        const afterValue = targetVersion.toolChoice ?? "auto";
        const changed = !valuesEqual(beforeValue, afterValue);
        return { beforeValue, afterValue, changed };
    }, [baseVersion, targetVersion]);

    const toolsDiff = useMemo(() => {
        if (!baseVersion || !targetVersion) {
            return { changed: false, beforeTools: [], afterTools: [] };
        }
        const beforeTools = baseVersion.tools ?? [];
        const afterTools = targetVersion.tools ?? [];
        return {
            changed: !valuesEqual(beforeTools, afterTools),
            beforeTools,
            afterTools,
        };
    }, [baseVersion, targetVersion]);

    const modelChanged =
        baseVersion && targetVersion
            ? !valuesEqual(baseVersion.model, targetVersion.model)
            : false;
    const promptChanged =
        baseVersion && targetVersion
            ? !valuesEqual(baseVersion.prompt, targetVersion.prompt)
            : false;

    const changedSettings = settingsDiff.filter((item) => item.changed);
    const changedReasoning = reasoningDiff.filter((item) => item.changed);

    const hasDifferences =
        modelChanged ||
        promptChanged ||
        changedSettings.length > 0 ||
        changedReasoning.length > 0 ||
        (toolChoiceDiff?.changed ?? false) ||
        toolsDiff.changed;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl">
                <DialogHeader>
                    <DialogTitle>Compare implementation versions</DialogTitle>
                    <DialogDescription>
                        Spot the behavioral and configuration differences between any
                        two saved versions.
                    </DialogDescription>
                </DialogHeader>

                {versions.length < 2 ? (
                    <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                        You need at least two versions to compare. Create another
                        implementation to unlock the diff view.
                    </div>
                ) : (
                    <div className="space-y-6">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="diff-base-version">
                                    Base version (reference)
                                </Label>
                                <Select
                                    value={baseVersionId ?? ""}
                                    onValueChange={onBaseVersionChange}
                                >
                                    <SelectTrigger id="diff-base-version">
                                        <SelectValue placeholder="Select base version" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {versions.map((version) => (
                                            <SelectItem key={version.id} value={version.id}>
                                                {getVersionLabel(version)}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="diff-target-version">
                                    Comparison version
                                </Label>
                                <Select
                                    value={targetVersionId ?? ""}
                                    onValueChange={onTargetVersionChange}
                                >
                                    <SelectTrigger id="diff-target-version">
                                        <SelectValue placeholder="Select comparison version" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {versions.map((version) => (
                                            <SelectItem key={version.id} value={version.id}>
                                                {getVersionLabel(version)}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {!baseVersion || !targetVersion ? null : (
                            <div className="space-y-6">
                                {hasDifferences ? (
                                    <div className="space-y-6">
                                        {modelChanged && (
                                            <DiffSection title="Model">
                                                {renderSimpleDiff(
                                                    baseVersion.model,
                                                    targetVersion.model,
                                                )}
                                            </DiffSection>
                                        )}

                                        {promptChanged && (
                                            <DiffSection title="Prompt">
                                                {renderTextDiff(
                                                    baseVersion.prompt ?? "",
                                                    targetVersion.prompt ?? "",
                                                )}
                                            </DiffSection>
                                        )}

                                        {changedSettings.length > 0 && (
                                            <DiffSection title="Generation settings">
                                                {changedSettings.map((item) => (
                                                    <LabeledDiffRow
                                                        key={item.key}
                                                        label={item.label}
                                                        beforeValue={item.beforeValue}
                                                        afterValue={item.afterValue}
                                                    />
                                                ))}
                                            </DiffSection>
                                        )}

                                        {changedReasoning.length > 0 && (
                                            <DiffSection title="Reasoning controls">
                                                {changedReasoning.map((item) => (
                                                    <LabeledDiffRow
                                                        key={item.key}
                                                        label={item.label}
                                                        beforeValue={item.beforeValue}
                                                        afterValue={item.afterValue}
                                                    />
                                                ))}
                                            </DiffSection>
                                        )}

                                        {toolChoiceDiff?.changed && (
                                            <DiffSection title="Tool selection">
                                                {renderSimpleDiff(
                                                    toolChoiceDiff.beforeValue,
                                                    toolChoiceDiff.afterValue,
                                                )}
                                            </DiffSection>
                                        )}

                                        {toolsDiff.changed && (
                                            <DiffSection title="Tools">
                                                {renderToolsDiff(
                                                    toolsDiff.beforeTools,
                                                    toolsDiff.afterTools,
                                                )}
                                            </DiffSection>
                                        )}
                                    </div>
                                ) : (
                                    <DiffSection title="No changes detected">
                                        <p className="text-sm text-muted-foreground">
                                            These versions share the same prompt, model,
                                            tooling, and configuration values.
                                        </p>
                                    </DiffSection>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
};

export default ImplementationDiffDialog;

