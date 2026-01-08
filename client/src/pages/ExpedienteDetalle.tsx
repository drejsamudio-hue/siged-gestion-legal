import { useRoute, useLocation } from "wouter";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, FileText, MessageSquare, AlertCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "wouter";

export default function ExpedienteDetalle() {
  const [, params] = useRoute("/expedientes/:id");
  const [, navigate] = useLocation();
  const expedienteId = params?.id ? parseInt(params.id) : null;

  const { data: expediente, isLoading } = trpc.expedientes.get.useQuery(
    { id: expedienteId! },
    { enabled: !!expedienteId }
  );

  const { data: notas } = trpc.notas.list.useQuery(
    { expedienteId: expedienteId! },
    { enabled: !!expedienteId }
  );

  const { data: escritos } = trpc.escritos.getByExpediente.useQuery(
    { expedienteId: expedienteId! },
    { enabled: !!expedienteId }
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12 text-slate-500">Cargando expediente...</div>
        </div>
      </div>
    );
  }

  if (!expediente) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">Expediente no encontrado</p>
          </div>
        </div>
      </div>
    );
  }

  const getPrioridadColor = (prioridad: string) => {
    switch (prioridad) {
      case "alta_feria":
        return "bg-red-100 text-red-800";
      case "media":
        return "bg-yellow-100 text-yellow-800";
      case "baja":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => navigate("/")}
            className="mb-4 text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver al Dashboard
          </Button>

          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 mb-2">
                Expte. {expediente.numero}
              </h1>
              <p className="text-slate-600 mb-4">{expediente.caratula}</p>
              <div className="flex gap-2 flex-wrap">
                <Badge className={getPrioridadColor(expediente.prioridad)}>
                  {expediente.prioridad === "alta_feria"
                    ? "Alta Prioridad (Feria)"
                    : expediente.prioridad === "media"
                    ? "Media Prioridad"
                    : "Baja Prioridad"}
                </Badge>
                <Badge variant="outline">{expediente.tipoProc}</Badge>
                <Badge variant="secondary">{expediente.estadoProcesal}</Badge>
              </div>
            </div>
            <Link href={`/expedientes/${expediente.id}/editar`}>
              <Button className="bg-blue-600 hover:bg-blue-700">Editar</Button>
            </Link>
          </div>
        </div>

        {/* Información General */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-lg">Información General</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-slate-600 font-medium">Dependencia</p>
                <p className="text-slate-900">{expediente.dependencia}</p>
              </div>
              <div>
                <p className="text-sm text-slate-600 font-medium">Tipo de Proceso</p>
                <p className="text-slate-900 capitalize">{expediente.tipoProc}</p>
              </div>
              <div>
                <p className="text-sm text-slate-600 font-medium">Estado Procesal</p>
                <p className="text-slate-900 capitalize">{expediente.estadoProcesal}</p>
              </div>
              <div>
                <p className="text-sm text-slate-600 font-medium">Último Movimiento</p>
                <p className="text-slate-900">
                  {expediente.fechaUltimoMovimiento
                    ? new Date(expediente.fechaUltimoMovimiento).toLocaleDateString("es-AR")
                    : "Sin registrar"}
                </p>
              </div>
              {expediente.proximoPlazo && (
                <div>
                  <p className="text-sm text-slate-600 font-medium">Próximo Plazo</p>
                  <p className="text-red-600 font-semibold">
                    {new Date(expediente.proximoPlazo).toLocaleDateString("es-AR")}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="notas" className="space-y-4">
          <TabsList>
            <TabsTrigger value="notas">
              <MessageSquare className="w-4 h-4 mr-2" />
              Notas ({notas?.length || 0})
            </TabsTrigger>
            <TabsTrigger value="escritos">
              <FileText className="w-4 h-4 mr-2" />
              Escritos ({escritos?.length || 0})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="notas">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Notas y Observaciones</CardTitle>
                  <Link href={`/expedientes/${expediente.id}/notas/nueva`}>
                    <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                      Nueva Nota
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {notas && notas.length > 0 ? (
                  <div className="space-y-4">
                    {notas.map((nota: any) => (
                      <div
                        key={nota.id}
                        className="p-4 border border-slate-200 rounded-lg bg-slate-50"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <Badge variant="outline" className="text-xs">
                            {nota.tipo}
                          </Badge>
                          <span className="text-xs text-slate-500">
                            {new Date(nota.createdAt).toLocaleDateString("es-AR")}
                          </span>
                        </div>
                        <p className="text-slate-900">{nota.contenido}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 text-center py-8">No hay notas registradas</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="escritos">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Escritos Guardados</CardTitle>
                  <Link href={`/expedientes/${expediente.id}/escritos/nuevo`}>
                    <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                      Nuevo Escrito
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {escritos && escritos.length > 0 ? (
                  <div className="space-y-4">
                    {escritos.map((escrito) => (
                      <div
                        key={escrito.id}
                        className="p-4 border border-slate-200 rounded-lg hover:bg-slate-50 transition"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h4 className="font-semibold text-slate-900">{escrito.titulo}</h4>
                            <Badge variant="outline" className="text-xs mt-1">
                              {escrito.tipo}
                            </Badge>
                          </div>
                          <Badge
                            variant={
                              escrito.estado === "completado"
                                ? "default"
                                : escrito.estado === "presentado"
                                ? "secondary"
                                : "outline"
                            }
                            className="text-xs"
                          >
                            {escrito.estado}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-600 line-clamp-2 mb-3">
                          {escrito.contenido}
                        </p>
                        <Link href={`/escritos/${escrito.id}`}>
                          <Button variant="ghost" size="sm" className="text-blue-600">
                            Ver Escrito
                          </Button>
                        </Link>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 text-center py-8">No hay escritos guardados</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
