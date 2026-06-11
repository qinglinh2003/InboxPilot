import React from "react";
import {
  Spinner,
  MessageBar,
  MessageBarBody,
  Badge,
  makeStyles,
} from "@fluentui/react-components";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface StatusBarProps {
  status: "idle" | "loading" | "success" | "error" | "applying";
  message: string;
  cacheHit: boolean;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
});

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const StatusBar: React.FC<StatusBarProps> = ({
  status,
  message,
  cacheHit,
}) => {
  const styles = useStyles();

  // Nothing to show in idle state with no messages
  if (status === "idle" && !message) {
    return null;
  }

  return (
    <div className={styles.root}>
      {/* Loading spinner */}
      {(status === "loading" || status === "applying") && (
        <div className={styles.row}>
          <Spinner size="tiny" />
          <span>
            {status === "loading"
              ? "Analyzing email..."
              : "Applying categories..."}
          </span>
        </div>
      )}

      {/* Error message */}
      {status === "error" && message && (
        <MessageBar intent="error">
          <MessageBarBody>{message}</MessageBarBody>
        </MessageBar>
      )}

      {/* Success message (from category apply) */}
      {status === "success" && message && (
        <MessageBar intent="success">
          <MessageBarBody>{message}</MessageBarBody>
        </MessageBar>
      )}

      {/* Cache hit indicator */}
      {status === "success" && cacheHit && (
        <div className={styles.row}>
          <Badge color="informative" appearance="outline" size="small">
            Cached result
          </Badge>
        </div>
      )}
    </div>
  );
};
