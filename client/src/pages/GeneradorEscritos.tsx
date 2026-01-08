import { useLocation } from "wouter";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Download, FileText } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

const PLANTILLAS = {
  habilitacion_feria: {
    titulo: "Solicitud de Habilitación de Feria",
    contenido: `SOLICITA HABILITACIÓN DE FERIA JUDICIAL

EXCMA. CÁMARA DE APELACIONES EN LO CIVIL Y COMERCIAL / JUZGADO DE FERIA

[NOMBRE DEL ABOGADO], D.N.I. Nº [DNI], por derecho propio, con domicilio real en [DOMICILIO] y constituyendo domicilio procesal electrónico en [EMAIL], en los autos caratulados: "[CARÁTULA]", Expte. Nº [NÚMERO], a V.E. respetuosamente digo:

I. OBJETO

Que, en legal tiempo y forma, vengo a solicitar la habilitación de la feria judicial para el presente expediente, en virtud de las razones de urgencia que a continuación se exponen.

II. HECHOS Y URGENCIA

[DESCRIBA LOS HECHOS QUE JUSTIFICAN LA URGENCIA]

La naturaleza del asunto, que busca una solución urgente y definitiva a una situación de hecho que no admite dilaciones, sumado a [FUNDAMENTOS ADICIONALES], demuestran la urgencia impostergable de su resolución. La dilación en el despacho durante la feria judicial agrava la situación de vulnerabilidad de esta parte, configurando un peligro en la demora que justifica plenamente la habilitación de este período.

III. FUNDAMENTO LEGAL

La habilitación de la feria judicial encuentra su fundamento en el Art. 153 del Código Procesal Civil y Comercial de la Provincia de Misiones y en el Reglamento para el Poder Judicial de Misiones, que prevén la posibilidad de habilitar días y horas inhábiles en casos de urgencia que no admitan dilación.

IV. PETITORIO

Por todo lo expuesto, a V.E. solicito:

1. Se tenga por presentado el presente escrito en tiempo y forma.
2. Se haga lugar a la habilitación de la feria judicial para el expediente Nº [NÚMERO].
3. Se ordene el pronto despacho y resolución del presente asunto.

PROVEER DE CONFORMIDAD, SERÁ JUSTICIA.

[FIRMA DEL ABOGADO]`,
  },
  apelacion: {
    titulo: "Recurso de Apelación",
    contenido: `INTERPONE RECURSO DE APELACIÓN

EXCMA. CÁMARA DE APELACIONES EN LO [FUERO]

[NOMBRE DEL ABOGADO], D.N.I. Nº [DNI], en mi carácter de letrado apoderado de [PARTE], con domicilio real en [DOMICILIO] y constituyendo domicilio procesal electrónico en [EMAIL], en los autos caratulados: "[CARÁTULA]", Expte. Nº [NÚMERO], a V.E. respetuosamente digo:

I. OBJETO

Que, en legal tiempo y forma, vengo a interponer RECURSO DE APELACIÓN contra la resolución de fecha [FECHA DE LA RESOLUCIÓN], que [BREVE DESCRIPCIÓN DE LO RESUELTO], por considerarla arbitraria, injusta y contraria a derecho.

II. AGRAVIOS

[DESARROLLE LOS AGRAVIOS CONTRA LA RESOLUCIÓN IMPUGNADA]

La resolución apelada incurre en los siguientes vicios:

1. [PRIMER AGRAVIO]
2. [SEGUNDO AGRAVIO]
3. [TERCER AGRAVIO]

III. FUNDAMENTO LEGAL

[CITE LOS ARTÍCULOS Y JURISPRUDENCIA APLICABLE]

IV. PETITORIO

Por todo lo expuesto, a V.E. solicito:

1. Se tenga por interpuesto el presente recurso en tiempo y forma.
2. Se admita el recurso de apelación interpuesto.
3. Se revoque la resolución de fecha [FECHA] y se dicte una nueva resolución acogiendo las pretensiones de esta parte.

PROVEER DE CONFORMIDAD, SERÁ JUSTICIA.

[FIRMA DEL ABOGADO]`,
  },
  medida_cautelar: {
    titulo: "Solicitud de Medida Cautelar",
    contenido: `SOLICITA MEDIDA CAUTELAR

EXCMA. CÁMARA DE APELACIONES EN LO [FUERO] / JUZGADO DE FERIA

[NOMBRE DEL ABOGADO], D.N.I. Nº [DNI], por derecho propio, con domicilio real en [DOMICILIO] y constituyendo domicilio procesal electrónico en [EMAIL], en los autos caratulados: "[CARÁTULA]", Expte. Nº [NÚMERO], a V.E. respetuosamente digo:

I. OBJETO

Que, en legal tiempo y forma, vengo a solicitar la adopción de una medida cautelar de [TIPO DE MEDIDA], en virtud de los requisitos que a continuación se exponen.

II. REQUISITOS DE LA MEDIDA CAUTELAR

A. Peligro en la Demora (Periculum in Mora)

[DESCRIBA EL RIESGO DE QUE LA DEMORA CAUSE DAÑO IRREPARABLE]

B. Verosimilitud del Derecho (Fumus Boni Iuris)

[DEMUESTRE LA PROBABILIDAD DE ÉXITO EN LA PRETENSIÓN PRINCIPAL]

C. Proporcionalidad

[EXPLIQUE POR QUÉ LA MEDIDA ES PROPORCIONAL AL DAÑO QUE SE PRETENDE EVITAR]

III. FUNDAMENTO LEGAL

[CITE LOS ARTÍCULOS DEL CÓDIGO PROCESAL Y JURISPRUDENCIA APLICABLE]

IV. PETITORIO

Por todo lo expuesto, a V.E. solicito:

1. Se tenga por presentado el presente escrito en tiempo y forma.
2. Se ordene la adopción de la medida cautelar de [TIPO DE MEDIDA].
3. Se notifique a la contraparte de la medida adoptada.

PROVEER DE CONFORMIDAD, SERÁ JUSTICIA.

[FIRMA DEL ABOGADO]`,
  },
};

export default function GeneradorEscritos() {
  const [, navigate] = useLocation();
  const [tipoEscrito, setTipoEscrito] = useState<keyof typeof PLANTILLAS>("habilitacion_feria");
  const [titulo, setTitulo] = useState("");
  const [contenido, setContenido] = useState("");
  const [expedienteId, setExpedienteId] = useState<number | null>(null);

  const createMutation = trpc.escritos.create.useMutation({
    onSuccess: () => {
      toast.success("Escrito guardado exitosamente");
      setContenido("");
      setTitulo("");
    },
    onError: (error) => {
      toast.error(`Error: ${error.message}`);
    },
  });

  const handleSelectPlantilla = (tipo: keyof typeof PLANTILLAS) => {
    setTipoEscrito(tipo);
    setContenido(PLANTILLAS[tipo].contenido);
    setTitulo(PLANTILLAS[tipo].titulo);
  };

  const handleGuardar = () => {
    if (!titulo || !contenido) {
      toast.error("Por favor completa todos los campos");
      return;
    }

    createMutation.mutate({
      titulo,
      tipo: tipoEscrito,
      contenido,
      expedienteId: expedienteId || undefined,
    });
  };

  const handleDescargar = () => {
    const element = document.createElement("a");
    const file = new Blob([contenido], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = `${titulo.replace(/\s+/g, "_")}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-6xl mx-auto">
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
            Generador de Escritos Judiciales
          </h1>
          <p className="text-slate-600">
            Utiliza plantillas predefinidas para crear escritos judicales profesionales
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Panel de Plantillas */}
          <div className="lg:col-span-1">
            <Card className="sticky top-8">
              <CardHeader>
                <CardTitle className="text-lg">Plantillas</CardTitle>
                <CardDescription>Selecciona un tipo de escrito</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {Object.entries(PLANTILLAS).map(([key, value]) => (
                  <button
                    key={key}
                    onClick={() => handleSelectPlantilla(key as keyof typeof PLANTILLAS)}
                    className={`w-full text-left p-3 rounded-lg border transition ${
                      tipoEscrito === key
                        ? "bg-blue-50 border-blue-300"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <FileText className="w-4 h-4 mt-1 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-sm text-slate-900">{value.titulo}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Panel de Edición */}
          <div className="lg:col-span-3 space-y-6">
            {/* Información del Escrito */}
            <Card>
              <CardHeader>
                <CardTitle>Información del Escrito</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="titulo" className="text-sm font-medium">
                    Título del Escrito
                  </Label>
                  <Input
                    id="titulo"
                    value={titulo}
                    onChange={(e) => setTitulo(e.target.value)}
                    className="mt-1"
                    placeholder="ej: Solicitud de Habilitación de Feria"
                  />
                </div>

                <div>
                  <Label htmlFor="expedienteId" className="text-sm font-medium">
                    Expediente (Opcional)
                  </Label>
                  <Input
                    id="expedienteId"
                    type="number"
                    value={expedienteId || ""}
                    onChange={(e) => setExpedienteId(e.target.value ? parseInt(e.target.value) : null)}
                    className="mt-1"
                    placeholder="ID del expediente"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Editor de Contenido */}
            <Card>
              <CardHeader>
                <CardTitle>Contenido del Escrito</CardTitle>
                <CardDescription>
                  Edita el contenido de la plantilla. Reemplaza los campos entre corchetes con información específica.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={contenido}
                  onChange={(e) => setContenido(e.target.value)}
                  className="font-mono text-sm min-h-96"
                  placeholder="Contenido del escrito..."
                />
              </CardContent>
            </Card>

            {/* Acciones */}
            <div className="flex gap-4">
              <Button
                onClick={handleDescargar}
                variant="outline"
                className="flex-1"
                disabled={!contenido}
              >
                <Download className="w-4 h-4 mr-2" />
                Descargar TXT
              </Button>
              <Button
                onClick={handleGuardar}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
                disabled={createMutation.isPending || !titulo || !contenido}
              >
                {createMutation.isPending ? "Guardando..." : "Guardar Escrito"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
