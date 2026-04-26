"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";

export interface MediaFeedItem {
  report_id: number;
  tier: number;
  trust_score: number;
  target_department_id: string | null;
  verification_status: string | null;
  text: string;
  created_at: string;
}

export interface MediaFeedResponse {
  count: number;
  reports: MediaFeedItem[];
}

export function useMediaFeed(limit = 5) {
  return useSWR<MediaFeedResponse>(`/admin/media-feed?limit=${limit}`, fetcher, {
    refreshInterval: 30_000,
    revalidateOnFocus: false,
  });
}
