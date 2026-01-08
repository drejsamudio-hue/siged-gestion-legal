import { useLocation } from "wouter";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export default function NuevoExpediente() {
  const [, navigate] = useLocation();
  const [formData, setFormData] = useState({
    numero: "",
    caratula: "",
    dependencia: "",
    tipoProc: "civil_comercial",
    estadoProcesal: "inicio",
    ultimoMovimiento: "",
  });

  const createMutation = trpc.expedientes.create.useMutation({
    onSuccess: () => {
      toast.success("Expediente creado exitosamente");
      navigate("/");
    },
    onError: (error) => {
      toast.error(`Error: ${error.message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      ...formData,
      tipoProc: formData.tipoProc as any,
      estadoProcesal: formData.estadoProcesal as any,
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-2xl mx-auto">
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

          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            Registrar Nuevo Expediente
          </h1>
          <p className="text-slate-600">
            Ingresa los datos del expediente judicial para comenzar a gestionarlo
          </p>
        </div>

        {/* Formulario */}
        <Card>
          <CardHeader>
            <CardTitle>Información del Expediente</CardTitle>
            <CardDescription>
              Completa todos los campos requeridos para registrar el expediente
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Número de Expediente */}
              <div>
                <Label htmlFor="numero" className="text-sm font-medium">
                  Número de Expediente *
                </Label>
                <Input
                  id="numero"
                  placeholder="ej: 117906/2025"
                  value={formData.numero}
                  onChange={(e) => setFormData({ ...formData, numero: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>

              {/* Carátula */}
              <div>
                <Label htmlFor="caratula" className="text-sm font-medium">
                  Carátula del Expediente *
                </Label>
                <Textarea
                  id="caratula"
                  placeholder="ej: Samudio Estanislao Javier c/ SAMSA s/ Medida Autosatisfactiva"
                  value={formData.caratula}
                  onChange={(e) => setFormData({ ...formData, caratula: e.target.value })}
                  required
                  className="mt-1"
                  rows={3}
                />
              </div>

              {/* Dependencia */}
              <div>
                <Label htmlFor="dependencia" className="text-sm font-medium">
                  Dependencia / Juzgado *
                </Label>
                <Input
                  id="dependencia"
                  placeholder="ej: Juzgado Civil y Comercial Nº 7"
                  value={formData.dependencia}
                  onChange={(e) => setFormData({ ...formData, dependencia: e.target.value })}
                  required
                  className="mt-1"
                />
              </div>

              {/* Tipo de Proceso */}
              <div>
                <Label htmlFor="tipoProc" className="text-sm font-medium">
                  Tipo de Proceso *
                </Label>
                <Select value={formData.tipoProc} onValueChange={(value) => setFormData({ ...formData, tipoProc: value })}>
                  <SelectTrigger id="tipoProc" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="civil_comercial">Civil y Comercial</SelectItem>
                    <SelectItem value="laboral">Laboral</SelectItem>
                    <SelectItem value="familia">Familia</SelectItem>
                    <SelectItem value="penal">Penal</SelectItem>
                    <SelectItem value="administrativo">Administrativo</SelectItem>
                    <SelectItem value="otro">Otro</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Estado Procesal */}
              <div>
                <Label htmlFor="estadoProcesal" className="text-sm font-medium">
                  Estado Procesal *
                </Label>
                <Select value={formData.estadoProcesal} onValueChange={(value) => setFormData({ ...formData, estadoProcesal: value })}>
                  <SelectTrigger id="estadoProcesal" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="inicio">Inicio</SelectItem>
                    <SelectItem value="demanda_contestada">Demanda Contestada</SelectItem>
                    <SelectItem value="prueba">Prueba</SelectItem>
                    <SelectItem value="alegatos">Alegatos</SelectItem>
                    <SelectItem value="sentencia">Sentencia</SelectItem>
                    <SelectItem value="recurso">Recurso</SelectItem>
                    <SelectItem value="ejecucion">Ejecución</SelectItem>
                    <SelectItem value="finalizado">Finalizado</SelectItem>
                    <SelectItem value="otro">Otro</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Último Movimiento */}
              <div>
                <Label htmlFor="ultimoMovimiento" className="text-sm font-medium">
                  Último Movimiento
                </Label>
                <Textarea
                  id="ultimoMovimiento"
                  placeholder="Describe el último movimiento procesal registrado"
                  value={formData.ultimoMovimiento}
                  onChange={(e) => setFormData({ ...formData, ultimoMovimiento: e.target.value })}
                  className="mt-1"
                  rows={2}
                />
              </div>

              {/* Botones */}
              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/")}
                  className="flex-1"
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                  disabled={createMutation.isPending}
                >
                  {createMutation.isPending ? "Guardando..." : "Registrar Expediente"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
