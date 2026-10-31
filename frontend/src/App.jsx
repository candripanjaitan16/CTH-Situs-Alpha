import { useEffect, useState } from "react";
import Sidebar, { menus } from "./components/Sidebar";
import Header from "./components/Header";
import { WorkspaceProvider, useWorkspace } from "./context/WorkspaceContext";
import Beranda from "./pages/Beranda";
import Datasets from "./pages/Datasets";
import TrainingWorkspace from "./pages/TrainingWorkspace";
import ModelTesting from "./pages/ModelTesting";
import Deployments from "./pages/Deployments";
import GoogleDrive from "./pages/GoogleDrive";
import ColabConnection from "./pages/ColabConnection";
import "./styles/cth.css";
function currentPage() {
  const page = window.location.hash.slice(1);
  return menus.some(menu => menu.id === page) ? page : "overview";
}
function Dashboard() {
  const [page, setPage] = useState(currentPage);
  const [menuOpen, setMenuOpen] = useState(false);
  const { selectedProject } = useWorkspace();
  useEffect(() => {
    const onHash = () => setPage(currentPage());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  function navigate(next) {
    if (!menus.some(menu => menu.id === next)) return;
    window.location.hash = next; setPage(next); setMenuOpen(false);
  }
  const pages = { overview: Beranda, datasets: Datasets, training: TrainingWorkspace,
    testing: ModelTesting, deployments: Deployments, drive: GoogleDrive, colab: ColabConnection };
  const Page = pages[page];
  return <div className="cth-app"><Sidebar activePage={page} onNavigate={navigate} open={menuOpen} onClose={() => setMenuOpen(false)} /><main className="cth-main"><Header title={menus.find(menu => menu.id === page)?.label} onMenu={() => setMenuOpen(true)} /><div className="cth-content"><Page key={page === "drive" || page === "overview" ? page : `${page}-${selectedProject?.id || "none"}`} onNavigate={navigate} /></div></main></div>;
}
export default function App() { return <WorkspaceProvider><Dashboard /></WorkspaceProvider>; }
