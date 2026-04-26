import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}

export function GlassCard({ children, className = "", as: Tag = "section" }: GlassCardProps) {
  return (
    <Tag
      className={[
        "relative overflow-hidden",
        "rounded-2xl border border-white/10",
        "bg-white/[0.03] backdrop-blur-xl",
        "shadow-glass",
        "before:pointer-events-none before:absolute before:inset-0 before:rounded-2xl",
        "before:bg-gradient-to-br before:from-white/[0.04] before:to-transparent",
        className,
      ].join(" ")}
    >
      {children}
    </Tag>
  );
}
