/*
 Gọi API về sau 
 */
import axiosClient from "../api/axiosClient";

const chatApi = {
  sendMessage: (prompt) => {
    return axiosClient.post("/chat", { prompt });
  },
};

export default chatApi;
