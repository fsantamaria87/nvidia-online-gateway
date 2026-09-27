import http from "node:http";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const PORT = Number(process.env.PORT || 8787);
const MCP_PATH = "/mcp";
const NVIDIA_API_KEY = process.env.NVIDIA_API_KEY || "";
const NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions";

const MODEL_BY_PROFILE = {
  fast: "nvidia/nemotron-3.5-lightning-30b-a3b",
  balanced: "nvidia/nemotron-3-super-120b-a12b",
  deep: "nvidia/nemotron-3-ultra-550b-a55b",
  auto: "nvidia/nemotron-3.5-lightning-30b-a3b"
};

const SAFE_CLASSES = new Set(["PUBLIC", "SYNTHETIC"]);
const MAX_OPTIONAL_PROVIDER_CALLS_PER_STAGE = 1;
const MAX_SYNTHETIC_CASES_NORMAL = 30;

function jsonResult(data) {
  return {
    content: [{ type: "text", text: JSON.stringify(data) }],
    structuredContent: data
  };
}

function dataClassDecision(dataClassification, externalProviderApproved = false) {
  if (SAFE_CLASSES.has(dataClassification)) {
    return { allowed: true, reason: null };
  }

  if (dataClassification === "INTERNAL_NON_SENSITIVE" && externalProviderApproved === true) {
    return { allowed: true, reason: null };
  }

  if (dataClassification === "INTERNAL_NON_SENSITIVE") {
    return { allowed: false, reason: "external_provider_approval_required" };
  }

  return { allowed: false, reason: "sensitive_or_unapproved_data_class" };
}

function budgetDecision(optionalProviderCallsUsed = 0) {
  if (optionalProviderCallsUsed >= MAX_OPTIONAL_PROVIDER_CALLS_PER_STAGE) {
    return { allowed: false, reason: "optional_provider_stage_budget_exhausted" };
  }
  return { allowed: true, reason: null };
}

function routingMetadata(profile) {
  return {
    profile,
    routing_backend: "static_policy_v1",
    switchyard_active: false
  };
}

async function nvidiaChat({ model, messages, maxTokens = 4096, temperature = 0.2 }) {
  if (!NVIDIA_API_KEY) {
    throw new Error("NVIDIA_API_KEY is not configured on the server");
  }

  const response = await fetch(NVIDIA_BASE_URL, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${NVIDIA_API_KEY}`,
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    body: JSON.stringify({
      model,
      messages,
      max_tokens: maxTokens,
      temperature,
      top_p: 0.95,
      stream: false
    })
  });

  const raw = await response.text();
  if (!response.ok) {
    const err = new Error(`NVIDIA API ${response.status}: ${raw.slice(0, 500)}`);
    err.status = response.status;
    throw err;
  }

  const body = JSON.parse(raw);
  const message = body?.choices?.[0]?.message || {};
  return {
    model,
    content: message.content ?? "",
    reasoning_content: message.reasoning_content ?? null,
    usage: body.usage ?? null
  };
}

function createServer() {
  const server = new McpServer(
    { name: "nvidia-online-gateway", version: "0.2.0" },
    {
      instructions:
        "Use only for PUBLIC, SYNTHETIC, or explicitly approved minimized INTERNAL_NON_SENSITIVE content. Never send Hilex confidential data, customer pricing, credentials, personnel data, or sensitive operational datasets. NVIDIA is advisory and fail-open; protected release/safety/security decisions stay with deterministic gates."
    }
  );

  server.registerTool(
    "nvidia_infer",
    {
      title: "NVIDIA model inference",
      description:
        "Run an optional NVIDIA specialist model. Use fast for worker tasks, balanced for a stronger second model, deep for independent technical review, and auto for conservative server policy. auto is not Switchyard until switchyard_active=true is explicitly reported.",
      inputSchema: {
        profile: z.enum(["fast", "balanced", "deep", "auto"]),
        task: z.string().min(1).max(30000),
        context_summary: z.string().max(30000).optional(),
        data_classification: z.enum([
          "PUBLIC",
          "SYNTHETIC",
          "INTERNAL_NON_SENSITIVE",
          "INTERNAL_SENSITIVE",
          "UNKNOWN"
        ]).default("UNKNOWN"),
        external_provider_approved: z.boolean().default(false),
        optional_provider_calls_used: z.number().int().min(0).max(10).default(0),
        stage_id: z.string().max(200).optional(),
        output_mode: z.enum(["text", "json"]).default("text")
      }
    },
    async ({
      profile,
      task,
      context_summary,
      data_classification,
      external_provider_approved,
      optional_provider_calls_used,
      stage_id,
      output_mode
    }) => {
      const dc = dataClassDecision(data_classification, external_provider_approved);
      if (!dc.allowed) {
        return jsonResult({
          status: "BYPASSED",
          reason: dc.reason,
          data_classification,
          stage_id: stage_id ?? null
        });
      }

      const budget = budgetDecision(optional_provider_calls_used);
      if (!budget.allowed) {
        return jsonResult({
          status: "BYPASSED",
          reason: budget.reason,
          optional_provider_calls_used,
          stage_id: stage_id ?? null
        });
      }

      const model = MODEL_BY_PROFILE[profile];
      const metadata = routingMetadata(profile);
      const system = [
        "You are an advisory specialist model inside a larger engineering workflow.",
        "Do not claim release authority.",
        "Be precise and concise.",
        output_mode === "json" ? "Return valid JSON only." : ""
      ].filter(Boolean).join(" ");

      try {
        const result = await nvidiaChat({
          model,
          messages: [
            { role: "system", content: system },
            {
              role: "user",
              content: `${context_summary ? `Context summary:\n${context_summary}\n\n` : ""}Task:\n${task}`
            }
          ],
          maxTokens: 4096
        });

        return jsonResult({
          status: "OK",
          provider: "nvidia_build",
          ...metadata,
          model: result.model,
          stage_id: stage_id ?? null,
          optional_provider_calls_used: optional_provider_calls_used + 1,
          content: result.content,
          reasoning_content: result.reasoning_content,
          usage: result.usage
        });
      } catch (error) {
        return jsonResult({
          status: "ERROR",
          provider: "nvidia_build",
          ...metadata,
          stage_id: stage_id ?? null,
          optional_provider_calls_used: optional_provider_calls_used + 1,
          error: String(error?.message || error)
        });
      }
    }
  );

  server.registerTool(
    "nvidia_generate_evalset",
    {
      title: "Generate synthetic skill evaluation cases",
      description:
        "Generate synthetic PUBLIC/SYNTHETIC test cases for an agent skill or workflow. Generated cases are advisory test inputs, not ground truth.",
      inputSchema: {
        spec: z.string().min(1).max(30000),
        count: z.number().int().min(3).max(30).default(12),
        data_classification: z.enum(["PUBLIC", "SYNTHETIC"]).default("SYNTHETIC"),
        optional_provider_calls_used: z.number().int().min(0).max(10).default(0),
        stage_id: z.string().max(200).optional()
      }
    },
    async ({ spec, count, data_classification, optional_provider_calls_used, stage_id }) => {
      const budget = budgetDecision(optional_provider_calls_used);
      if (!budget.allowed) {
        return jsonResult({
          status: "BYPASSED",
          reason: budget.reason,
          optional_provider_calls_used,
          stage_id: stage_id ?? null
        });
      }

      const effectiveCount = Math.min(count, MAX_SYNTHETIC_CASES_NORMAL);
      const prompt = `Create ${effectiveCount} synthetic evaluation cases for the following agent skill/workflow specification.
Include positive triggers, negative triggers, ambiguous cases, missing-tool cases, contradictory-evidence cases, shortcut-pressure cases, and regressions.
Return JSON with a top-level "cases" array. Each case must include: id, category, input, expected_behavior, must_not_do.

Specification:
${spec}`;

      try {
        const result = await nvidiaChat({
          model: MODEL_BY_PROFILE.fast,
          messages: [
            {
              role: "system",
              content:
                "Return valid JSON only. Generate synthetic evaluation data; do not invent proprietary real-world facts."
            },
            { role: "user", content: prompt }
          ],
          maxTokens: 4096,
          temperature: 0.5
        });

        let parsed = null;
        try {
          parsed = JSON.parse(result.content);
        } catch {}

        return jsonResult({
          status: "OK",
          provider: "nvidia_build",
          profile: "fast",
          model: result.model,
          routing_backend: "static_policy_v1",
          switchyard_active: false,
          data_classification,
          stage_id: stage_id ?? null,
          optional_provider_calls_used: optional_provider_calls_used + 1,
          requested_count: count,
          effective_count: effectiveCount,
          evalset: parsed,
          raw_content: parsed ? undefined : result.content
        });
      } catch (error) {
        return jsonResult({
          status: "ERROR",
          provider: "nvidia_build",
          profile: "fast",
          routing_backend: "static_policy_v1",
          switchyard_active: false,
          stage_id: stage_id ?? null,
          optional_provider_calls_used: optional_provider_calls_used + 1,
          error: String(error?.message || error)
        });
      }
    }
  );

  server.registerTool(
    "nvidia_review",
    {
      title: "Independent NVIDIA review",
      description:
        "Get a second-model review of a candidate against an explicit rubric. Advisory only; it cannot grant release approval.",
      inputSchema: {
        subject: z.string().min(1).max(30000),
        candidate: z.string().min(1).max(50000),
        rubric: z.string().min(1).max(20000),
        data_classification: z.enum([
          "PUBLIC",
          "SYNTHETIC",
          "INTERNAL_NON_SENSITIVE",
          "INTERNAL_SENSITIVE",
          "UNKNOWN"
        ]).default("UNKNOWN"),
        external_provider_approved: z.boolean().default(false),
        optional_provider_calls_used: z.number().int().min(0).max(10).default(0),
        stage_id: z.string().max(200).optional()
      }
    },
    async ({
      subject,
      candidate,
      rubric,
      data_classification,
      external_provider_approved,
      optional_provider_calls_used,
      stage_id
    }) => {
      const dc = dataClassDecision(data_classification, external_provider_approved);
      if (!dc.allowed) {
        return jsonResult({
          status: "BYPASSED",
          reason: dc.reason,
          data_classification,
          stage_id: stage_id ?? null
        });
      }

      const budget = budgetDecision(optional_provider_calls_used);
      if (!budget.allowed) {
        return jsonResult({
          status: "BYPASSED",
          reason: budget.reason,
          optional_provider_calls_used,
          stage_id: stage_id ?? null
        });
      }

      const prompt = `Review the candidate independently against the rubric.
Return JSON with: findings[], critical_issues[], disagreements_or_uncertainties[], suggested_next_checks[].
Do not claim release approval.

Subject:
${subject}

Rubric:
${rubric}

Candidate:
${candidate}`;

      try {
        const result = await nvidiaChat({
          model: MODEL_BY_PROFILE.deep,
          messages: [
            {
              role: "system",
              content:
                "You are an independent engineering reviewer. Return valid JSON only. Your result is advisory."
            },
            { role: "user", content: prompt }
          ],
          maxTokens: 8192,
          temperature: 0.2
        });

        let parsed = null;
        try {
          parsed = JSON.parse(result.content);
        } catch {}

        return jsonResult({
          status: "OK",
          provider: "nvidia_build",
          profile: "deep",
          model: result.model,
          routing_backend: "static_policy_v1",
          switchyard_active: false,
          stage_id: stage_id ?? null,
          optional_provider_calls_used: optional_provider_calls_used + 1,
          review: parsed,
          raw_content: parsed ? undefined : result.content
        });
      } catch (error) {
        return jsonResult({
          status: "ERROR",
          provider: "nvidia_build",
          profile: "deep",
          routing_backend: "static_policy_v1",
          switchyard_active: false,
          stage_id: stage_id ?? null,
          optional_provider_calls_used: optional_provider_calls_used + 1,
          error: String(error?.message || error)
        });
      }
    }
  );

  return server;
}

const httpServer = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);

  if (req.method === "GET" && url.pathname === "/") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(
      JSON.stringify({
        name: "nvidia-online-gateway",
        version: "0.2.0",
        mcp_path: MCP_PATH,
        api_key_configured: Boolean(NVIDIA_API_KEY),
        routing_backend: "static_policy_v1",
        switchyard_active: false,
        max_optional_provider_calls_per_stage: MAX_OPTIONAL_PROVIDER_CALLS_PER_STAGE
      })
    );
    return;
  }

  if (req.method === "OPTIONS" && url.pathname === MCP_PATH) {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, GET, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "content-type, mcp-session-id",
      "Access-Control-Expose-Headers": "Mcp-Session-Id"
    });
    res.end();
    return;
  }

  if (url.pathname === MCP_PATH && ["POST", "GET", "DELETE"].includes(req.method || "")) {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Expose-Headers", "Mcp-Session-Id");

    const server = createServer();
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true
    });

    res.on("close", () => {
      transport.close();
      server.close();
    });

    try {
      await server.connect(transport);
      await transport.handleRequest(req, res);
    } catch (error) {
      console.error(error);
      if (!res.headersSent) {
        res.writeHead(500, { "content-type": "application/json" });
        res.end(JSON.stringify({ error: "internal_server_error" }));
      }
    }
    return;
  }

  res.writeHead(404, { "content-type": "text/plain" });
  res.end("Not Found");
});

httpServer.listen(PORT, () => {
  console.log(`NVIDIA Online MCP listening on :${PORT}${MCP_PATH}`);
});
