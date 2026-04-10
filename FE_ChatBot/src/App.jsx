import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./ui/AppLayout";
import ChatArea from "./ui/ChatArea";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate replace to="home" />} />
          <Route path="home" element={<ChatArea />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
export default App;
