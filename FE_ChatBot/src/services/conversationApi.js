import axiosClient from "../api/axiosClient";

// TOng so messages dua vao conversation id
export const fetchMessages = async (conversationId) => {
  const response = await axiosClient.get(
    `/conversations/${conversationId}/messages`,
  );
  return response.data;
};
