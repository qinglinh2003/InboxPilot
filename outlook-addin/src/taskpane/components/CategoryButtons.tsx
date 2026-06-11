import React from "react";
import {
  Button,
  Checkbox,
  Tooltip,
  Badge,
  Subtitle2,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import type { CategoryRecommendation } from "../api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface CategoryButtonsProps {
  categories: CategoryRecommendation[];
  selectedCategories: Set<string>;
  onToggle: (name: string) => void;
  onApply: () => void;
  isApplying: boolean;
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
  list: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "4px 0",
  },
  confidence: {
    marginLeft: "auto",
    minWidth: "48px",
    textAlign: "right" as const,
  },
  footer: {
    display: "flex",
    justifyContent: "flex-end",
    paddingTop: "8px",
  },
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function confidenceColor(
  confidence: number,
): "success" | "warning" | "danger" {
  if (confidence >= 0.7) return "success";
  if (confidence >= 0.4) return "warning";
  return "danger";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const CategoryButtons: React.FC<CategoryButtonsProps> = ({
  categories,
  selectedCategories,
  onToggle,
  onApply,
  isApplying,
}) => {
  const styles = useStyles();

  if (categories.length === 0) {
    return null;
  }

  return (
    <div className={styles.root}>
      <Subtitle2>Recommended Categories</Subtitle2>

      <div className={styles.list}>
        {categories.map((cat) => (
          <Tooltip
            key={cat.name}
            content={cat.reason}
            relationship="description"
          >
            <div className={styles.row}>
              <Checkbox
                checked={selectedCategories.has(cat.name)}
                onChange={() => onToggle(cat.name)}
                label={cat.name}
              />
              <span className={styles.confidence}>
                <Badge
                  size="small"
                  color={confidenceColor(cat.confidence)}
                  appearance="tint"
                >
                  {Math.round(cat.confidence * 100)}%
                </Badge>
              </span>
            </div>
          </Tooltip>
        ))}
      </div>

      <div className={styles.footer}>
        <Button
          appearance="primary"
          disabled={selectedCategories.size === 0 || isApplying}
          onClick={onApply}
        >
          {isApplying
            ? "Applying..."
            : `Apply Selected (${selectedCategories.size})`}
        </Button>
      </div>
    </div>
  );
};
