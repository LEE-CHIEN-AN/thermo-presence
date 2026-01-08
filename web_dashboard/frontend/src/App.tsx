import React, { useState } from "react";
import { Dashboard } from "./pages/Dashboard";
import { History } from "./pages/History";
import { Statistics } from "./pages/Statistics";

type View = "realtime" | "history" | "statistics";

export const App: React.FC = () => {
  const [view, setView] = useState<View>("realtime");

  return (
    <div className="min-h-screen bg-black text-slate-50">
      <nav className="flex items-center justify-between px-4 md:px-8 py-3 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="text-sm md:text-base font-semibold">
          Thermal Presence Dashboard
        </div>
        <div className="flex gap-2 text-xs md:text-sm">
          <button
            onClick={() => setView("realtime")}
            className={`px-3 py-1 rounded-md border ${
              view === "realtime"
                ? "bg-sky-600 border-sky-500"
                : "bg-slate-900 border-slate-700 hover:border-slate-500"
            }`}
          >
            Realtime
          </button>
          <button
            onClick={() => setView("history")}
            className={`px-3 py-1 rounded-md border ${
              view === "history"
                ? "bg-sky-600 border-sky-500"
                : "bg-slate-900 border-slate-700 hover:border-slate-500"
            }`}
          >
            History
          </button>
          <button
            onClick={() => setView("statistics")}
            className={`px-3 py-1 rounded-md border ${
              view === "statistics"
                ? "bg-sky-600 border-sky-500"
                : "bg-slate-900 border-slate-700 hover:border-slate-500"
            }`}
          >
            Statistics
          </button>
        </div>
      </nav>
      {view === "realtime" ? (
        <Dashboard />
      ) : view === "history" ? (
        <History />
      ) : (
        <Statistics />
      )}
    </div>
  );
};

