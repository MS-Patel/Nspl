import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Phone, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";

type Msg = { role: "user" | "assistant"; content: string };

const WHATSAPP_URL = "https://wa.me/917265098822?text=Hi";

const QUICK_REPLIES = [
  "Mutual Funds",
  "Unlisted Shares",
  "Fixed Returns",
  "Bonds",
  "Speak to Advisor",
];

const INITIAL_MESSAGE: Msg = {
  role: "assistant",
  content:
    "Welcome to BuyBestFin 👋\n\nWe help you invest in Mutual Funds, Bonds, Unlisted Shares and Fixed Return Opportunities.\n\nHow can I assist you today?",
};

const ChatWidget = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showLeadForm, setShowLeadForm] = useState(false);
  const [leadData, setLeadData] = useState({ name: "", phone: "", interest: "Mutual Funds", amount: "" });
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const sendMessage = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg || isLoading) return;

    // Handle "Speak to Advisor" quick reply
    if (msg === "Speak to Advisor") {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: msg },
        {
          role: "assistant",
          content:
            "Our investment advisor will guide you personally.\n\nPlease fill the form below or contact directly:\n\n📱 WhatsApp: [+91 7265098822](https://wa.me/917265098822)\n📞 Call: +91 7265098822",
        },
      ]);
      setInput("");
      setShowLeadForm(true);
      return;
    }

    const userMsg: Msg = { role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    let assistantSoFar = "";
    const allMessages = [...messages, userMsg].filter(
      (m) => m.role === "user" || m.role === "assistant"
    );

    try {
      const resp = await fetch(
        `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
          },
          body: JSON.stringify({ messages: allMessages }),
        }
      );

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Something went wrong");
      }

      if (!resp.body) throw new Error("No stream");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let textBuffer = "";

      const upsert = (chunk: string) => {
        assistantSoFar += chunk;
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && assistantSoFar.length > chunk.length) {
            return prev.map((m, i) =>
              i === prev.length - 1 ? { ...m, content: assistantSoFar } : m
            );
          }
          if (last?.role === "assistant" && assistantSoFar === chunk) {
            return prev.map((m, i) =>
              i === prev.length - 1 ? { ...m, content: assistantSoFar } : m
            );
          }
          return [...prev, { role: "assistant", content: assistantSoFar }];
        });
      };

      let streamDone = false;
      while (!streamDone) {
        const { done, value } = await reader.read();
        if (done) break;
        textBuffer += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = textBuffer.indexOf("\n")) !== -1) {
          let line = textBuffer.slice(0, idx);
          textBuffer = textBuffer.slice(idx + 1);
          if (line.endsWith("\r")) line = line.slice(0, -1);
          if (line.startsWith(":") || !line.trim()) continue;
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6).trim();
          if (json === "[DONE]") {
            streamDone = true;
            break;
          }
          try {
            const parsed = JSON.parse(json);
            const c = parsed.choices?.[0]?.delta?.content;
            if (c) upsert(c);
          } catch {
            /* partial */
          }
        }
      }

      // Check if AI response suggests contacting advisor → show lead form
      if (
        assistantSoFar.toLowerCase().includes("share your name") ||
        assistantSoFar.toLowerCase().includes("contact directly") ||
        assistantSoFar.toLowerCase().includes("advisor will guide")
      ) {
        setShowLeadForm(true);
      }
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, I couldn't process that. Please try again or reach us on [WhatsApp](${WHATSAPP_URL}). (${e.message})`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const submitLead = () => {
    const { name, phone, interest, amount } = leadData;
    if (!name || !phone) return;
    const msg = `New Investment Lead:\nName: ${name}\nPhone: ${phone}\nInterest: ${interest}${amount ? `\nAmount: ${amount}` : ""}`;
    const waUrl = `https://wa.me/917265098822?text=${encodeURIComponent(msg)}`;
    window.open(waUrl, "_blank");
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `Thank you ${name}! 🎉 Our advisor will contact you shortly on ${phone}.\n\nYou can also chat directly on [WhatsApp](${WHATSAPP_URL}).`,
      },
    ]);
    setShowLeadForm(false);
    setLeadData({ name: "", phone: "", interest: "Mutual Funds", amount: "" });
  };

  return (
    <>
      {/* WhatsApp FAB */}
      <a
        href={WHATSAPP_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="fixed bottom-24 right-6 z-50 w-14 h-14 rounded-full bg-[#25D366] text-white flex items-center justify-center shadow-lg hover:scale-110 transition-transform animate-fade-up"
        title="Chat on WhatsApp"
      >
        <Phone className="w-6 h-6" />
      </a>

      {/* Chat FAB */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full gradient-primary text-white flex items-center justify-center shadow-lg hover:scale-110 transition-transform animate-fade-up"
        title="Chat with AI"
      >
        {open ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
      </button>

      {/* Chat Window */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[370px] max-w-[calc(100vw-2rem)] h-[540px] max-h-[75vh] rounded-2xl border border-border bg-card shadow-2xl flex flex-col overflow-hidden animate-scale-in">
          {/* Header */}
          <div className="gradient-primary px-4 py-3 flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <p className="text-white font-semibold text-sm">BuyBestFin AI Advisor</p>
              <p className="text-white/70 text-xs">Your investment assistant</p>
            </div>
            <a
              href={WHATSAPP_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center hover:bg-white/30 transition"
              title="WhatsApp"
            >
              <Phone className="w-4 h-4 text-white" />
            </a>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm ${
                    m.role === "user"
                      ? "gradient-primary text-white rounded-br-md"
                      : "bg-muted text-foreground rounded-bl-md"
                  }`}
                >
                  {m.role === "assistant" ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none [&_p]:m-0 [&_ul]:m-0 [&_ol]:m-0 [&_li]:m-0">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  ) : (
                    m.content
                  )}
                </div>
              </div>
            ))}

            {/* Quick Replies - show after initial or when not loading */}
            {!isLoading && !showLeadForm && messages.length <= 2 && (
              <div className="flex flex-wrap gap-2 pt-1">
                {QUICK_REPLIES.map((qr) => (
                  <button
                    key={qr}
                    onClick={() => sendMessage(qr)}
                    className="px-3 py-1.5 text-xs font-medium rounded-full border border-primary/30 text-primary bg-primary/5 hover:bg-primary/10 transition-colors"
                  >
                    {qr}
                  </button>
                ))}
              </div>
            )}

            {/* Lead Capture Form */}
            {showLeadForm && (
              <div className="bg-muted/50 rounded-xl p-3 space-y-2 border border-border">
                <p className="text-xs font-semibold flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-primary" /> Share your details
                </p>
                <input
                  className="w-full bg-background rounded-lg px-3 py-1.5 text-xs outline-none border border-border focus:ring-1 focus:ring-primary/50"
                  placeholder="Your Name *"
                  value={leadData.name}
                  onChange={(e) => setLeadData({ ...leadData, name: e.target.value })}
                />
                <input
                  className="w-full bg-background rounded-lg px-3 py-1.5 text-xs outline-none border border-border focus:ring-1 focus:ring-primary/50"
                  placeholder="Mobile Number *"
                  value={leadData.phone}
                  onChange={(e) => setLeadData({ ...leadData, phone: e.target.value })}
                />
                <select
                  className="w-full bg-background rounded-lg px-3 py-1.5 text-xs outline-none border border-border focus:ring-1 focus:ring-primary/50"
                  value={leadData.interest}
                  onChange={(e) => setLeadData({ ...leadData, interest: e.target.value })}
                >
                  <option>Mutual Funds</option>
                  <option>Unlisted Shares</option>
                  <option>Bonds</option>
                  <option>Corporate FD</option>
                  <option>Invoice Discounting</option>
                </select>
                <select
                  className="w-full bg-background rounded-lg px-3 py-1.5 text-xs outline-none border border-border focus:ring-1 focus:ring-primary/50"
                  value={leadData.amount}
                  onChange={(e) => setLeadData({ ...leadData, amount: e.target.value })}
                >
                  <option value="">Investment Amount</option>
                  <option>Below ₹50,000</option>
                  <option>₹50,000 - ₹2 Lakhs</option>
                  <option>₹2 Lakhs - ₹10 Lakhs</option>
                  <option>₹10 Lakhs+</option>
                </select>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    className="flex-1 gradient-primary text-white text-xs h-8"
                    onClick={submitLead}
                    disabled={!leadData.name || !leadData.phone}
                  >
                    Submit & WhatsApp
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-xs h-8"
                    onClick={() => setShowLeadForm(false)}
                  >
                    Skip
                  </Button>
                </div>
              </div>
            )}

            {isLoading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex justify-start">
                <div className="bg-muted px-4 py-2 rounded-2xl rounded-bl-md text-sm text-muted-foreground">
                  <span className="animate-pulse">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-border p-3 flex gap-2">
            <input
              className="flex-1 bg-muted rounded-full px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/50 text-foreground placeholder:text-muted-foreground"
              placeholder="Ask about investments..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              disabled={isLoading}
            />
            <Button
              size="icon"
              className="rounded-full gradient-primary border-0 text-white h-9 w-9"
              onClick={() => sendMessage()}
              disabled={isLoading || !input.trim()}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </>
  );
};

export default ChatWidget;
