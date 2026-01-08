import { useLocation } from "wouter";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Send, MessageCircle, Loader } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatbotLegal() {
  const [, navigate] = useLocation();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "¡Hola! Soy tu asistente legal especializado en expedientes judiciales de Misiones. Puedo ayudarte a:\n\n• Analizar el estado procesal de tus expedientes\n• Sugerir estrategias legales según el tipo de proceso\n• Identificar plazos críticos y urgencias\n• Proporcionar referencias a la jurisprudencia de Misiones\n• Recomendar escritos judicales apropiados\n\n¿En qué puedo ayudarte hoy?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      // Simulación de respuesta del chatbot
      // En una implementación real, esto llamaría a un endpoint tRPC que invoca el LLM
      const respuestaBot = generarRespuestaBot(userMessage);

      setMessages((prev) => [...prev, { role: "assistant", content: respuestaBot }]);
    } catch (error) {
      toast.error("Error al procesar tu mensaje");
    } finally {
      setIsLoading(false);
    }
  };

  const generarRespuestaBot = (pregunta: string): string => {
    const preguntaLower = pregunta.toLowerCase();

    if (
      preguntaLower.includes("feria") ||
      preguntaLower.includes("urgencia") ||
      preguntaLower.includes("habilitación")
    ) {
      return `Entiendo que necesitas información sobre habilitación de feria. Según el Reglamento para el Poder Judicial de Misiones:

**Procesos que admiten habilitación de feria:**
- Procesos de familia (alimentos, guarda, etc.)
- Procesos penales (libertad, integridad física)
- Procesos laborales (carácter alimentario)
- Medidas cautelares y autosatisfactivas

**Requisitos para solicitar habilitación:**
1. Demostrar urgencia impostergable
2. Acreditar peligro en la demora (periculum in mora)
3. Presentar escrito fundamentado ante el Juzgado de Feria

¿Necesitas ayuda para redactar una solicitud de habilitación de feria?`;
    }

    if (
      preguntaLower.includes("plazo") ||
      preguntaLower.includes("vencimiento") ||
      preguntaLower.includes("recurso")
    ) {
      return `Respecto a plazos y recursos en Misiones:

**Plazos procesales comunes:**
- Apelación: 10 días hábiles desde la notificación
- Reposición: 5 días hábiles
- Recurso de queja: Sin plazo específico (urgencia)

**Recomendaciones:**
1. Registra todos los plazos en el sistema para alertas automáticas
2. Calcula el vencimiento considerando días hábiles
3. Prepara recursos con anticipación

¿Tienes un plazo específico que necesites monitorear?`;
    }

    if (preguntaLower.includes("estrategia") || preguntaLower.includes("recomendación")) {
      return `Para definir una estrategia legal efectiva, necesito más información:

1. **Tipo de proceso:** ¿Civil, laboral, familia, penal?
2. **Estado actual:** ¿En qué etapa se encuentra?
3. **Parte:** ¿Eres demandante o demandado?
4. **Urgencia:** ¿Hay plazos próximos a vencer?

Con esta información podré sugerirte:
- Recursos procesales más efectivos
- Escritos judiciales apropiados
- Estrategias basadas en jurisprudencia de Misiones

¿Puedes proporcionar estos detalles?`;
    }

    if (preguntaLower.includes("escrito") || preguntaLower.includes("documento")) {
      return `Tengo plantillas disponibles para los siguientes escritos:

📄 **Habilitación de Feria** - Para procesos urgentes durante receso judicial
📄 **Recurso de Apelación** - Para impugnar sentencias
📄 **Recurso de Reposición** - Para impugnar resoluciones
📄 **Medida Cautelar** - Para medidas preventivas
📄 **Medida Autosatisfactiva** - Para soluciones urgentes

Puedo ayudarte a:
1. Seleccionar el escrito apropiado
2. Completar los campos específicos
3. Adaptar la plantilla a tu caso

¿Qué tipo de escrito necesitas?`;
    }

    return `Gracias por tu pregunta. Aunque soy un asistente especializado en gestión de expedientes judicales, para consultas legales específicas te recomiendo:

1. **Revisar la base de conocimiento** del sistema con referencias al Código Procesal Civil y Penal de Misiones
2. **Usar el generador de escritos** para plantillas predefinidas
3. **Consultar con colegas** para estrategias complejas

¿Hay algo más en lo que pueda asistirte respecto a la gestión de tus expedientes?`;
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

          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            Asistente Legal IA
          </h1>
          <p className="text-slate-600">
            Consulta sobre estrategias legales, plazos y procedimientos judiciales
          </p>
        </div>

        {/* Chat */}
        <Card className="flex flex-col h-[600px]">
          <CardHeader className="border-b">
            <div className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5 text-blue-600" />
              <CardTitle>Chat Legal</CardTitle>
            </div>
            <CardDescription>
              Asistente especializado en procedimientos judicales de Misiones
            </CardDescription>
          </CardHeader>

          {/* Mensajes */}
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white rounded-br-none"
                      : "bg-slate-100 text-slate-900 rounded-bl-none"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 text-slate-900 px-4 py-3 rounded-lg rounded-bl-none">
                  <Loader className="w-5 h-5 animate-spin" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </CardContent>

          {/* Input */}
          <div className="border-t p-4 bg-white">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter" && !isLoading) {
                    handleSendMessage();
                  }
                }}
                placeholder="Escribe tu pregunta..."
                disabled={isLoading}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={isLoading || !input.trim()}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>

        {/* Sugerencias */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Preguntas Frecuentes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <button
                onClick={() => setInput("¿Cómo solicito habilitación de feria?")}
                className="w-full text-left text-sm text-blue-600 hover:text-blue-800 p-2 hover:bg-blue-50 rounded transition"
              >
                ¿Cómo solicito habilitación de feria?
              </button>
              <button
                onClick={() => setInput("¿Cuáles son los plazos para recursos?")}
                className="w-full text-left text-sm text-blue-600 hover:text-blue-800 p-2 hover:bg-blue-50 rounded transition"
              >
                ¿Cuáles son los plazos para recursos?
              </button>
              <button
                onClick={() => setInput("¿Qué estrategia me recomiendas?")}
                className="w-full text-left text-sm text-blue-600 hover:text-blue-800 p-2 hover:bg-blue-50 rounded transition"
              >
                ¿Qué estrategia me recomiendas?
              </button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Recursos Disponibles</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <a href="/escritos" className="block text-sm text-blue-600 hover:text-blue-800 p-2 hover:bg-blue-50 rounded transition">
                📄 Generador de Escritos
              </a>
              <button className="w-full text-left text-sm text-blue-600 hover:text-blue-800 p-2 hover:bg-blue-50 rounded transition">
                📚 Base de Conocimiento Legal
              </button>
              <button className="w-full text-left text-sm text-blue-600 hover:text-blue-800 p-2 hover:bg-blue-50 rounded transition">
                ⚖️ Jurisprudencia de Misiones
              </button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
