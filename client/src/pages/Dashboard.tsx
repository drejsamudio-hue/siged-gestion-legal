import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, FileText, Clock, CheckCircle2, MessageSquare } from "lucide-react";
import { useState } from "react";
import { Link } from "wouter";

export default function Dashboard() {
  const { user } = useAuth();
  const { data: expedientes, isLoading } = trpc.expedientes.list.useQuery();
  const [filtro, setFiltro] = useState<"todas" | "alta_feria" | "media" | "baja">("todas");

  const expedientesFiltrados = expedientes?.filter((exp) => {
    if (filtro === "todas") return true;
    return exp.prioridad === filtro;
  });

  const estadisticas = {
    total: expedientes?.length || 0,
    altaFeria: expedientes?.filter((e) => e.prioridad === "alta_feria").length || 0,
    media: expedientes?.filter((e) => e.prioridad === "media").length || 0,
    baja: expedientes?.filter((e) => e.prioridad === "baja").length || 0,
  };

  const getPrioridadColor = (prioridad: string) => {
    switch (prioridad) {
      case "alta_feria":
        return "bg-red-100 text-red-800 border-red-300";
      case "media":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "baja":
        return "bg-green-100 text-green-800 border-green-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getPrioridadLabel = (prioridad: string) => {
    switch (prioridad) {
      case "alta_feria":
        return "Alta Prioridad (Feria)";
      case "media":
        return "Media Prioridad";
      case "baja":
        return "Baja Prioridad";
      default:
        return "Sin clasificar";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">
            SIGED Gestión Legal
          </h1>
          <p className="text-slate-600">
            Bienvenido, {user?.name || "Abogado"}. Gestiona tus expedientes judicales de forma eficiente.
          </p>
        </div>

        {/* Estadísticas */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="border-l-4 border-l-slate-400">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-600">Total Expedientes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-slate-900">{estadisticas.total}</div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-red-500">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-red-600">Alta Prioridad (Feria)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{estadisticas.altaFeria}</div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-yellow-500">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-yellow-600">Media Prioridad</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">{estadisticas.media}</div>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-green-500">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-green-600">Baja Prioridad</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{estadisticas.baja}</div>
            </CardContent>
          </Card>
        </div>

        {/* Accesos Rápidos */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Link href="/escritos">
            <Card className="cursor-pointer hover:shadow-lg transition">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Generador de Escritos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-slate-600">Crea escritos judicales con plantillas</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/chatbot">
            <Card className="cursor-pointer hover:shadow-lg transition">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  Asistente Legal IA
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-slate-600">Consulta sobre estrategias legales</p>
              </CardContent>
            </Card>
          </Link>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Alertas Pendientes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-slate-600">Próximamente: Sistema de alertas por email</p>
            </CardContent>
          </Card>
        </div>

        {/* Filtros y Acciones */}
        <div className="flex flex-col md:flex-row gap-4 mb-8 items-center justify-between">
          <div className="flex gap-2">
            {["todas", "alta_feria", "media", "baja"].map((f) => (
              <Button
                key={f}
                variant={filtro === f ? "default" : "outline"}
                onClick={() => setFiltro(f as any)}
                className="text-sm"
              >
                {f === "todas" ? "Todas" : f === "alta_feria" ? "Alta (Feria)" : f === "media" ? "Media" : "Baja"}
              </Button>
            ))}
          </div>
          <Link href="/expedientes/nuevo">
            <Button className="bg-blue-600 hover:bg-blue-700">
              <FileText className="w-4 h-4 mr-2" />
              Nuevo Expediente
            </Button>
          </Link>
        </div>

        {/* Listado de Expedientes */}
        <Card>
          <CardHeader>
            <CardTitle>Expedientes ({expedientesFiltrados?.length || 0})</CardTitle>
            <CardDescription>
              Gestiona y monitorea el estado de tus expedientes judicales
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-slate-500">Cargando expedientes...</div>
            ) : expedientesFiltrados && expedientesFiltrados.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Número</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Carátula</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Dependencia</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Tipo</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Estado</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Prioridad</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expedientesFiltrados.map((exp) => (
                      <tr key={exp.id} className="border-b border-slate-100 hover:bg-slate-50 transition">
                        <td className="py-3 px-4 font-mono text-blue-600">{exp.numero}</td>
                        <td className="py-3 px-4 text-slate-900 font-medium">{exp.caratula}</td>
                        <td className="py-3 px-4 text-slate-600 text-xs">{exp.dependencia}</td>
                        <td className="py-3 px-4">
                          <Badge variant="outline" className="text-xs">
                            {exp.tipoProc}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="secondary" className="text-xs">
                            {exp.estadoProcesal}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <Badge className={`text-xs border ${getPrioridadColor(exp.prioridad)}`}>
                            {getPrioridadLabel(exp.prioridad)}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <Link href={`/expedientes/${exp.id}`}>
                            <Button variant="ghost" size="sm" className="text-blue-600 hover:text-blue-800">
                              Ver
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 mb-4">No hay expedientes registrados</p>
                <Link href="/expedientes/nuevo">
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    Crear Primer Expediente
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
