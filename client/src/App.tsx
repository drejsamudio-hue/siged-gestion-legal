import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import Dashboard from "@/pages/Dashboard";
import ExpedienteDetalle from "@/pages/ExpedienteDetalle";
import NuevoExpediente from "@/pages/NuevoExpediente";
import GeneradorEscritos from "@/pages/GeneradorEscritos";
import ChatbotLegal from "@/pages/ChatbotLegal";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { useAuth } from "./_core/hooks/useAuth";
import { getLoginUrl } from "./const";
import { Button } from "./components/ui/button";
import { LogOut } from "lucide-react";

function ProtectedRoute({ component: Component }: { component: React.ComponentType }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-slate-600">Cargando...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-8">
        <div className="max-w-md text-center">
          <h1 className="text-3xl font-bold text-slate-900 mb-4">SIGED Gestión Legal</h1>
          <p className="text-slate-600 mb-8">
            Sistema de gestión de expedientes judicales para abogados litigantes en Misiones, Argentina.
          </p>
          <a href={getLoginUrl()}>
            <Button className="bg-blue-600 hover:bg-blue-700 w-full">
              Iniciar Sesión
            </Button>
          </a>
        </div>
      </div>
    );
  }

  return <Component />;
}

function AppHeader() {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">SL</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">SIGED Gestión Legal</h1>
        </div>
        {user && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">{user.name}</span>
            <button
              onClick={() => logout()}
              className="text-slate-600 hover:text-slate-900 transition"
              title="Cerrar sesión"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

function Router() {
  const { isAuthenticated } = useAuth();

  return (
    <>
      {isAuthenticated && <AppHeader />}
      <Switch>
        <Route path="/" component={() => <ProtectedRoute component={Dashboard} />} />
        <Route path="/expedientes/nuevo" component={() => <ProtectedRoute component={NuevoExpediente} />} />
        <Route path="/expedientes/:id" component={() => <ProtectedRoute component={ExpedienteDetalle} />} />
        <Route path="/escritos" component={() => <ProtectedRoute component={GeneradorEscritos} />} />
        <Route path="/chatbot" component={() => <ProtectedRoute component={ChatbotLegal} />} />
        <Route path="/404" component={NotFound} />
        {/* Final fallback route */}
        <Route component={NotFound} />
      </Switch>
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
