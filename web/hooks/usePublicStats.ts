"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

export interface TierImpact {
  tier: number;
  verified_report_count: number;
  impact_per_report_uzs: number;
  subtotal_uzs: number;
}

export interface CivicRoiSummary {
  currency: string;
  total_estimated_funds_protected: number;
  by_tier: TierImpact[];
  tier_impact_table: Record<string, number>;
}

export interface DepartmentBreakdown {
  department_id: string;
  verified_report_count: number;
}

export interface RecentBadge {
  badge_id: string;
  name: string;
  earned_at: string;
}

export interface PublicStats {
  total_verified_reports: number;
  reports_by_department: DepartmentBreakdown[];
  total_civic_impact: number;
  civic_roi_summary: CivicRoiSummary;
  recent_corruption_fighter_badges: RecentBadge[];
  generated_at: string;
  cache_ttl_seconds: number;
}

export function usePublicStats() {
  return useSWR<PublicStats>("/public/stats", fetcher, {
    refreshInterval: 30_000,
    revalidateOnFocus: false,
  });
}
