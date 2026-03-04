import { apiClient } from "./client";
import type { DiscussionReply, DiscussionThread } from "@/types";

interface ThreadDetailResponse {
  thread: DiscussionThread;
  replies: DiscussionReply[];
}

interface VoteResponse {
  action: string;
  vote: 1 | -1 | null;
}

export const discussionsApi = {
  create: (productSlug: string, payload: { threadType: string; title: string; body: string }) =>
    apiClient.post<DiscussionThread>(`/api/v1/products/${productSlug}/discussions`, payload),

  get: (id: string) =>
    apiClient.get<ThreadDetailResponse>(`/api/v1/discussions/${id}`),

  reply: (threadId: string, body: string, parentReplyId?: string) =>
    apiClient.post<DiscussionReply>(`/api/v1/discussions/${threadId}/replies`, { body, parentReplyId }),

  voteThread: (id: string, vote: 1 | -1) =>
    apiClient.post<VoteResponse>(`/api/v1/discussions/${id}/vote`, { vote }),

  voteReply: (id: string, vote: 1 | -1) =>
    apiClient.post<VoteResponse>(`/api/v1/discussions/replies/${id}/vote`, { vote }),

  acceptReply: (replyId: string) =>
    apiClient.post<DiscussionReply>(`/api/v1/discussions/replies/${replyId}/accept`),
};
