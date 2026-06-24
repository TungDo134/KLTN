import axiosClient from "../api/axiosClient";

export const fetchConversations = async () => {
  const response = await axiosClient.get("/conversations");
  return response.data;
};

// TOng so messages dua vao conversation id
export const fetchMessages = async (conversationId) => {
  const response = await axiosClient.get(
    `/conversations/${conversationId}/messages`,
  );
  return response.data;
};

export const deleteConversation = async (conversationId) => {
  await axiosClient.delete(`/conversations/${conversationId}`);
};
