import React, { useState, useCallback } from "react";
import {
  Button,
  Card,
  Divider,
  Title2,
  Subtitle2,
  tokens,
  makeStyles,
} from "@fluentui/react-components";
import { Summary } from "./components/Summary";
import { CategoryButtons } from "./components/CategoryButtons";
import { StatusBar } from "./components/StatusBar";
import { getCurrentEmail, applyCategories } from "./outlook";
import {
  analyzeEmail,
  type EmailAnalysisRequest,
  type EmailAnalysisResponse,
} from "./api";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const useStyles = makeStyles({
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    padding: "16px",
    fontFamily: tokens.fontFamilyBase,
    minHeight: "100vh",
    backgroundColor: tokens.colorNeutralBackground1,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  actions: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap",
  },
  card: {
    padding: "16px",
  },
});

// ---------------------------------------------------------------------------
// State type
// ---------------------------------------------------------------------------

type AppStatus = "idle" | "loading" | "success" | "error" | "applying";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const App: React.FC = () => {
  const styles = useStyles();

  const [status, setStatus] = useState<AppStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [result, setResult] = useState<EmailAnalysisResponse | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(
    new Set(),
  );
  const [applyMessage, setApplyMessage] = useState<string>("");

  // ---- Analyze handler ----------------------------------------------------

  const handleAnalyze = useCallback(async () => {
    try {
      setStatus("loading");
      setErrorMessage("");
      setApplyMessage("");
      setResult(null);
      setSelectedCategories(new Set());

      // 1. Read email from Outlook
      const email = await getCurrentEmail();

      // 2. Build request matching backend schema
      const request: EmailAnalysisRequest = {
        provider: "outlook",
        message_id: email.messageId || `outlook-${Date.now()}`,
        conversation_id: email.conversationId || null,
        subject: email.subject,
        sender: {
          name: null,
          email: email.sender || null,
        },
        to: email.recipients.map((r) => ({ name: null, email: r })),
        cc: [],
        received_at: new Date().toISOString(),
        body_text: email.body,
        existing_categories: email.existingCategories,
      };

      // 3. Call backend
      const response = await analyzeEmail(request);
      setResult(response);

      // Pre-select high-confidence categories (>= 0.7)
      const autoSelected = new Set(
        response.recommended_categories
          .filter((c) => c.confidence >= 0.7)
          .map((c) => c.name),
      );
      setSelectedCategories(autoSelected);

      setStatus("success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
      setStatus("error");
    }
  }, []);

  // ---- Category toggle ----------------------------------------------------

  const handleToggleCategory = useCallback((name: string) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }, []);

  // ---- Apply categories ---------------------------------------------------

  const handleApply = useCallback(async () => {
    if (selectedCategories.size === 0) return;
    try {
      setStatus("applying");
      setApplyMessage("");
      await applyCategories(Array.from(selectedCategories));
      setApplyMessage(
        `Applied ${selectedCategories.size} category${selectedCategories.size > 1 ? "ies" : "y"} successfully.`,
      );
      setStatus("success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setApplyMessage(`Failed to apply categories: ${msg}`);
      setStatus("error");
    }
  }, [selectedCategories]);

  // ---- Render -------------------------------------------------------------

  return (
    <div className={styles.root}>
      {/* Header */}
      <div className={styles.header}>
        <Title2>MailPilot</Title2>
        <Subtitle2 style={{ color: tokens.colorNeutralForeground3 }}>
          Email Assistant
        </Subtitle2>
      </div>

      <Divider />

      {/* Status bar */}
      <StatusBar
        status={status}
        message={errorMessage || applyMessage}
        cacheHit={result?.cache.hit ?? false}
      />

      {/* Primary action buttons */}
      <div className={styles.actions}>
        <Button
          appearance="primary"
          disabled={status === "loading" || status === "applying"}
          onClick={handleAnalyze}
        >
          {status === "loading" ? "Analyzing..." : "Summarize with MailPilot"}
        </Button>

        {result && (
          <Button
            appearance="subtle"
            disabled={status === "loading" || status === "applying"}
            onClick={handleAnalyze}
          >
            Re-analyze
          </Button>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          <Card className={styles.card}>
            <Summary
              summary={result.summary}
              priority={result.priority}
              suggestedAction={result.suggested_action}
              needsReply={result.needs_reply}
              deadline={result.deadline}
            />
          </Card>

          <Card className={styles.card}>
            <CategoryButtons
              categories={result.recommended_categories}
              selectedCategories={selectedCategories}
              onToggle={handleToggleCategory}
              onApply={handleApply}
              isApplying={status === "applying"}
            />
          </Card>
        </>
      )}
    </div>
  );
};
