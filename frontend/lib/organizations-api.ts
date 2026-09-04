import { api } from "@/lib/api";
import type { ApiSuccess } from "@/types/auth";
import type { Member } from "@/types/organization";

export async function listMembers(): Promise<Member[]> {
  const res = await api.get<ApiSuccess<Member[]>>("/organizations/me/members");
  return res.data.data;
}
