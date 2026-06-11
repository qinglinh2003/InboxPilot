import React from "react";
import {
  Badge,
  Body1,
  Caption1,
  Subtitle2,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { Deadline } from "../api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface SummaryProps {
  summary: string;
  priority: "high" | "medium" | "low";
  suggestedAction: string;
  needsReply: boolean;
  deadline: Deadline;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  meta: {
    display: "flex",
    gap: "12px",
    flexWrap: "wrap",
    alignItems: "center",
  },
  deadlineWarning: {
    padding: "6px 10px",
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorPaletteYellowBackground2,
    color: tokens.colorPaletteYellowForeground2,
    fontWeight: tokens.fontWeightSemibold,
  },
});

// ---------------------------------------------------------------------------
// Priority color mapping
// ---------------------------------------------------------------------------

const PRIORITY_COLOR: Record<
  SummaryProps["priority"],
  "danger" | "warning" | "success"
> = {
  high: "danger",
  medium: "warning",
  low: "success",
};

const PRIORITY_LABEL: Record<SummaryProps["priority"], string> = {
  high: "High Priority",
  medium: "Medium Priority",
  low: "Low Priority",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const Summary: React.FC<SummaryProps> = ({
  summary,
  priority,
  suggestedAction,
  needsReply,
  deadline,
}) => {
  const styles = useStyles();

  return (
    <div className={styles.root}>
      {/* Section title + priority badge */}
      <div className={styles.header}>
        <Subtitle2>Summary</Subtitle2>
        <Badge color={PRIORITY_COLOR[priority]} appearance="filled">
          {PRIORITY_LABEL[priority]}
        </Badge>
      </div>

      {/* Summary text */}
      <Body1>{summary}</Body1>

      {/* Meta row: needs reply + suggested action */}
      <div className={styles.meta}>
        {needsReply && (
          <Badge color="informative" appearance="outline">
            Reply needed
          </Badge>
        )}
        <Caption1>
          <strong>Suggested action:</strong> {suggestedAction}
        </Caption1>
      </div>

      {/* Deadline warning */}
      {deadline.exists && (
        <div className={styles.deadlineWarning}>
          Deadline: {deadline.date ?? "Date not specified"}
          {deadline.evidence && (
            <Caption1 style={{ display: "block", marginTop: "4px" }}>
              Evidence: &ldquo;{deadline.evidence}&rdquo;
            </Caption1>
          )}
        </div>
      )}
    </div>
  );
};
