/*
 Gọi API về sau 
 */
import axiosClient from "../api/axiosClient";

// =============== FAKE RESPONSES ===============
const mockResponses = [
  "Chào bạn! Tôi có thể giúp gì cho chuyến đi sắp tới của bạn?",
  "Đà Lạt mùa này thời tiết khá đẹp, ban ngày nắng ấm, ban đêm se lạnh. Bạn có muốn tôi gợi ý một vài lịch trình không?",
  "Để đi du lịch Thái Lan, bạn không cần visa nếu đi dưới 30 ngày nhé. Bạn định đi mấy ngày?",
  "Tuyệt vời! Nếu bạn thích biển, Nha Trang hay Phú Quốc đều là những lựa chọn tuyệt vời. Bạn thích không khí sôi động hay yên tĩnh hơn?",
  "Dưới đây là một số món ăn bạn nhất định phải thử khi đến Huế: Bún bò Huế, bánh nậm, bánh lọc, và chè heo quay...",
  "Theo kinh nghiệm của tôi, thời điểm lý tưởng nhất để du lịch Sapa là từ tháng 9 đến tháng 11 khi có lúa chín vàng.",
];

// =============== FAKE TRIP PLANS ===============
const mockTripPlans = [
  `Chắc chắn rồi, đây là gợi ý lịch trình chi tiết dành cho bạn:

**Ngày 1: Đến Đà Lạt - Khám phá trung tâm**
Sáng đến nơi, nhận phòng khách sạn. Trưa thưởng thức lẩu gà lá é đặc sản. Chiều tham quan Quảng trường Lâm Viên, đạp vịt ở Hồ Xuân Hương. Tối đi dạo chợ đêm Đà Lạt và uống sữa đậu nành nóng.

**Ngày 2: Săn mây - Hoà mình vào thiên nhiên**
4h sáng dậy sớm đi săn mây ở Đồi chè Cầu Đất. Trưa ăn cơm niêu sườn nướng. Chiều tham quan thác Datanla, trải nghiệm máng trượt siêu tốc. Tối nghe nhạc ở quán cafe Acoustic giữa đồi thông.

**Ngày 3: Check-in sống ảo - Mua đặc sản**
Sáng đi Ga Đà Lạt, tham quan kiến trúc Pháp cổ tại trường Cao đẳng Sư phạm. Trưa ăn bánh ướt lòng gà. Chiều đi mua dâu tây, Atiso về làm quà rồi di chuyển ra sân bay.

\`\`\`json
{
  "title": "Lịch trình Đà Lạt 3 ngày 2 đêm",
  "days": [
    {
      "day": "Ngày 1",
      "title": "Đến Đà Lạt - Khám phá trung tâm",
      "description": "Sáng đến nơi, nhận phòng khách sạn. Trưa ăn lẩu gà lá é. Chiều tham quan Quảng trường Lâm Viên, Hồ Xuân Hương. Tối đi chợ đêm Đà Lạt."
    },
    {
      "day": "Ngày 2",
      "title": "Săn mây - Hoà mình vào thiên nhiên",
      "description": "4h sáng đi săn mây ở Đồi chè Cầu Đất. Trưa ăn cơm niêu. Chiều tham quan thác Datanla, trải nghiệm máng trượt. Tối uống cafe Acoustic."
    },
    {
      "day": "Ngày 3",
      "title": "Check-in sống ảo - Mua đặc sản",
      "description": "Sáng đi Ga Đà Lạt, tham quan trường Cao đẳng Sư phạm. Trưa ăn bánh ướt lòng gà. Chiều đi mua dâu tây, Atiso về làm quà và ra sân bay."
    }
  ]
}
\`\`\`
`,
  `Tuyệt vời, đây là lịch trình vi vu Phú Quốc mà mình gợi ý cho bạn:

**Ngày 1: Đến Đảo Ngọc**
Đến sân bay, xe đưa về resort nghỉ ngơi. Chiều tắm biển bãi Trường, ngắm hoàng hôn đẹp nhất Phú Quốc. Tối thưởng thức hải sản tươi sống ở chợ đêm Dinh Cậu.

**Ngày 2: Tour 4 đảo - Lặn ngắm san hô**
Tham gia tour cano đi Hòn Móng Tay, Hòn Gầm Ghì, Hòn May Rút. Lặn ngắm san hô bãi đá ngầm và quay video flycam bằng SUP trong suốt.

**Ngày 3: Khám phá Bắc Đảo - VinWonders**
Vui chơi thoả thích tại VinWonders Phú Quốc, tham quan thuỷ cung hình rùa khổng lồ. Tối xem show diễn thực cảnh "Sắc màu Venice" tại Grand World.

**Ngày 4: Mua sắm - Tạm biệt**
Sáng đi chợ Dương Đông mua hải sản khô, nước mắm, tiêu sọ về làm quà. Trưa trả phòng và di chuyển ra sân bay.

\`\`\`json
{
  "title": "Khám phá Phú Quốc 4 ngày 3 đêm",
  "days": [
    {
      "day": "Ngày 1",
      "title": "Đến Đảo Ngọc",
      "description": "Đến sân bay, xe đưa về resort nghỉ ngơi. Chiều tắm biển, ngắm hoàng hôn. Tối ăn hải sản ở chợ đêm Dinh Cậu."
    },
    {
      "day": "Ngày 2",
      "title": "Tour 4 đảo - Lặn ngắm san hô",
      "description": "Tham gia tour cano đi Hòn Móng Tay, Hòn Gầm Ghì, Hòn May Rút. Lặn ngắm san hô và quay video flycam."
    },
    {
      "day": "Ngày 3",
      "title": "Khám phá Bắc Đảo - VinWonders",
      "description": "Vui chơi tại VinWonders Phú Quốc, tham quan thuỷ cung. Tối xem show sắc màu Venice tại Grand World."
    }
  ]
}
\`\`\`
`,
];

const chatApi = {
  // Hàm giả lập streaming response (chuẩn bị cho FastAPI SSE)
  sendMessageStream: async (prompt, onProgress) => {
    console.log("User Input: ", prompt);

    let randomText = "";
    const promptLower = prompt.toLowerCase();
    if (
      promptLower.includes("lịch trình") ||
      promptLower.includes("kế hoạch") ||
      promptLower.includes("chuyến đi")
    ) {
      randomText =
        mockTripPlans[Math.floor(Math.random() * mockTripPlans.length)];
    } else {
      randomText =
        mockResponses[Math.floor(Math.random() * mockResponses.length)];
    }

    // Giả lập độ trễ mạng ban đầu (TTFB - Time To First Byte)
    await new Promise((resolve) => setTimeout(resolve, 600));

    // Giả lập streaming từng chunk (placeholder cho FastAPI StreamingResponse)
    // Gợi ý khi tích hợp thật: Dùng fetch() và response.body.getReader()
    const chunkSize = 3;
    let currentText = "";
    let isStreamingJson = false;

    for (let i = 0; i < randomText.length; i += chunkSize) {
      const chunk = randomText.slice(i, i + chunkSize);
      currentText += chunk;
      onProgress(chunk, currentText);

      // Nếu bắt đầu stream vào khối json thì đẩy tốc độ lên tối đa để tránh bị "đơ" UI
      if (currentText.includes("```json")) {
        isStreamingJson = true;
      }

      // Thời gian trễ ngẫu nhiên giữa các token (chữ bình thường thì chậm, json thì cực nhanh)
      const delay = isStreamingJson ? 2 : 15 + Math.random() * 30;
      await new Promise((resolve) => setTimeout(resolve, delay));
    }

    return { data: { response: randomText } };
  },
};

export default chatApi;
