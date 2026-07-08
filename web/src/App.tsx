import { Route, Routes } from "react-router-dom";
import { Nav } from "./components/Nav";
import { Footer } from "./components/Footer";
import { useLenis } from "./lib/useLenis";
import { Overview } from "./pages/Overview";
import { Results } from "./pages/Results";
import { Info } from "./pages/Info";

function App() {
  useLenis();

  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/results" element={<Results />} />
        <Route path="/info" element={<Info />} />
      </Routes>
      <Footer />
    </>
  );
}

export default App;
