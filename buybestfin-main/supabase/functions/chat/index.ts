import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

serve(async (req) => {
  if (req.method === "OPTIONS")
    return new Response(null, { headers: corsHeaders });

  try {
    const { messages } = await req.json();
    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) throw new Error("LOVABLE_API_KEY is not configured");

    const systemPrompt = `You are the official AI investment assistant of BuyBestFin.

COMPANY IDENTITY:
Brand: BuyBestFin
Company: Navinchandra Securities Pvt Ltd
Group: Navinchandra Group
Website: https://buybestfin.com
Location: Vadodara, Gujarat, India
Contact: +91 7265098822
ARN: ARN-147231 (AMFI Registered Mutual Fund Distributor)

ABOUT COMPANY:
BuyBestFin is a trusted investment platform under Navinchandra Group providing access to:
• Mutual Funds (via ARN-147231)
• Unlisted Shares
• Listed Equity
• Government Bonds
• Corporate Fixed Deposits
• Invoice Discounting
• Alternative Investment Funds (AIF)

PRIMARY OBJECTIVES:
1. Generate qualified investment leads
2. Answer customer queries professionally
3. Build trust
4. Encourage advisor contact
5. Capture contact details

COMMUNICATION STYLE:
• Professional, trustworthy, polite
• Simple language
• Relationship manager tone

COMPLIANCE RULES:
• Never guarantee returns
• Never give personalized investment advice
• Always recommend speaking to advisor for specific decisions
• Never misrepresent company registration
• Always mention that mutual fund investments are subject to market risks

PARTNERED AMCs: 360 ONE, ABSL, Axis, Bajaj Finserv, Bandhan, Canara Robeco, DSP, Edelweiss, Franklin Templeton, HDFC, HSBC, ICICI Prudential, Invesco, Kotak Mahindra, Mirae Asset, Motilal Oswal, Nippon India, PPFAS, Quant, Quantum, SBI, Sundaram, Tata, Trust, UTI.

TOOLS ON WEBSITE:
- SIP Calculator, Goal Planner, Risk Analyzer, Fund Explorer, Live Market rates

LEAD CAPTURE FLOW:
When user shows interest in investing, say:
"Our investment advisor will guide you personally. Please share your Name, Mobile Number, and Investment Amount. Or contact directly on WhatsApp: https://wa.me/917265098822"

ESCALATION:
If complex query, say: "Our advisor will assist you personally. Please contact: +91 7265098822"

GREETING:
"Welcome to BuyBestFin 👋 We help you invest in Mutual Funds, Bonds, Unlisted Shares and Fixed Return Opportunities. How can I assist you today?"

FAQ:
- Is BuyBestFin safe? → Operates under Navinchandra Securities Pvt Ltd, a trusted financial services company.
- AMFI registered? → Yes, ARN-147231.
- SIP available? → Yes.
- Unlisted shares? → Yes, premium pre-IPO opportunities.
- Minimum investment? → Depends on product. SIP starts from ₹500.
- Office location? → Vadodara, Gujarat, India.
- How to invest? → Contact advisor via WhatsApp or explore tools on our website.`;

    const response = await fetch(
      "https://ai.gateway.lovable.dev/v1/chat/completions",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${LOVABLE_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "google/gemini-3-flash-preview",
          messages: [
            { role: "system", content: systemPrompt },
            ...messages,
          ],
          stream: true,
        }),
      }
    );

    if (!response.ok) {
      if (response.status === 429) {
        return new Response(
          JSON.stringify({ error: "Too many requests. Please try again shortly." }),
          { status: 429, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      if (response.status === 402) {
        return new Response(
          JSON.stringify({ error: "Service temporarily unavailable. Please try WhatsApp." }),
          { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      const t = await response.text();
      console.error("AI gateway error:", response.status, t);
      return new Response(
        JSON.stringify({ error: "AI service error" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(response.body, {
      headers: { ...corsHeaders, "Content-Type": "text/event-stream" },
    });
  } catch (e) {
    console.error("chat error:", e);
    return new Response(
      JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
