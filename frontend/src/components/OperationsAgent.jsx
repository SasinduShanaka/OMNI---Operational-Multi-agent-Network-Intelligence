import React, { useEffect, useRef, useState } from 'react'
import { supplyChainApi } from '../api/supplyChainApi'
import { createChatReportPreview, isReportRequest, isFollowupReport, reportSource, reportQuery, isManagementReportRequest, isReportNavigationRequest, managementReportScope } from './chatReports'
import ManagementReport from './ManagementReport'
import ForecastPdfPreview from './ForecastPdfPreview'
import { ScenePage } from './FactoryScene'
import { OmniAvatar } from './OmniMark'
import PlanningEvidence, { MaterialEvidence } from './PlanningEvidence'
import { apiFetch } from '../api/http'
import { focusChatComposer } from './chatFocus'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`

function compactWorkflow(workflow) {
  const internalSupplyChainSteps = new Set([
    'Sourcing Agent',
    'Purchasing Agent',
    'Freight Agent',
    'Tracking Agent',
  ])
  const compacted = []

  workflow.forEach((step) => {
    if (internalSupplyChainSteps.has(step)) {
      if (!compacted.includes('Supply Chain Agent')) {
        compacted.push('Supply Chain Agent')
      }
      return
    }

    if (!compacted.includes(step)) {
      compacted.push(step)
    }
  })

  return compacted
}

function OperationsAgent({ chatState, setChatState, setActivePage, setScQuery }) {
  const [sessionId, setSessionId] = useState(() => chatState.sessionId || crypto.randomUUID())
  const [requestId, setRequestId] = useState(null)
  const [progress, setProgress] = useState(null)
  const messagesEndRef = useRef(null)
  const composerRef = useRef(null)
  const { draft, messages, isAsking, error } = chatState

  useEffect(() => {
    focusChatComposer(composerRef.current, isAsking)
  }, [isAsking])

  useEffect(() => {
    if (!isAsking || !requestId) return undefined
    const controller = new AbortController()
    let timer
    async function poll() {
      try {
        const response = await apiFetch(`${API_BASE_URL}/ask/progress/${requestId}`, { signal: controller.signal })
        if (response.ok) {
          const update = await response.json()
          if (!controller.signal.aborted && update.agent) setProgress(update)
        }
      } catch {
        // The chat request can finish even if a progress update is unavailable.
      } finally {
        if (!controller.signal.aborted) timer = window.setTimeout(poll, 700)
      }
    }
    poll()
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [isAsking, requestId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
    })
  }, [messages, isAsking, progress?.agent, error])

  function updateChatState(patch) {
    setChatState((previous) => ({
      ...previous,
      ...patch,
    }))
  }

  async function handleSend(actionText = null, payload = null) {
    const userMessage = typeof actionText === 'string' ? actionText : draft.trim()
    if (!userMessage || isAsking) {
      return
    }

    const currentRequestId = crypto.randomUUID()
    setRequestId(currentRequestId)
    setProgress(null)

    updateChatState({
      sessionId,
      messages: [
        ...messages,
        {
          type: 'user',
          text: userMessage,
        },
      ],
      draft: '',
      isAsking: true,
      error: '',
    })

    try {
      if (isReportNavigationRequest(userMessage)) {
        updateChatState({
          messages: [...messages, { type: 'user', text: userMessage }, { type: 'agent', data: {
            intent: 'report_navigation', status: 'success',
            answer: 'Open Factory reports to view saved reports or set up a daily or monthly schedule with your preferred scope and time.',
          } }],
          isAsking: false,
        })
        return
      }
      const managementReport = isManagementReportRequest(userMessage)
      if (!managementReport && isFollowupReport(userMessage)) {
        const source = reportSource(messages)
        updateChatState({
          messages: [...messages, { type: 'user', text: userMessage }, {
            type: 'agent',
            data: {
              intent: 'report_download',
              status: source ? 'success' : 'needs_information',
              answer: source
                ? 'Your report is ready. Use Download PDF below to save the previous response, including its details and any data-quality issues.'
                : 'Ask for an inventory, forecast, or production result first, or try "Download inventory report".',
              reportSource: source,
            },
          }],
          isAsking: false,
        })
        return
      }
      const response = await apiFetch(`${API_BASE_URL}${managementReport ? '/reports/generate' : '/ask'}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(managementReport ? managementReportScope(userMessage) : {
          message: isReportRequest(userMessage) ? reportQuery(userMessage) || userMessage : userMessage,
          session_id: sessionId,
          request_id: currentRequestId,
          payload: payload,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data?.detail?.message || data?.detail || `Request failed: ${response.status}`
        )
      }
      
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id)
      }
      if (data.intent === 'approval_followup') {
        window.dispatchEvent(new Event('omni:purchase-order-updated'))
      }

      if (isReportRequest(userMessage) && data.intent !== 'unknown') {
        data.reportRequested = true
      }

      updateChatState({
        sessionId: data.session_id || sessionId,
        messages: [
          ...messages,
          {
            type: 'user',
            text: userMessage,
          },
          {
            type: 'agent',
            data,
          },
        ],
        isAsking: false,
      })
    } catch (requestError) {
      console.error(requestError)

      updateChatState({
        error: requestError.message ||
          'I could not connect to the Operations Agent. Please make sure the backend is running.',
        isAsking: false,
      })
    }
  }

  // Keep the newest message in view without yanking the page when the
  // user has scrolled back to read something.
  const scrollRef = useRef(null)
  const endRef = useRef(null)

  useEffect(() => {
    const container = scrollRef.current
    if (!container) return
    const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 220
    if (nearBottom || isAsking) {
      endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [messages.length, isAsking])

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const promptGroups = [
    {
      label: 'Stock',
      icon: '◇',
      prompts: [
        'Show me the full fabric stock list',
        'Which materials are below safety stock?',
      ],
    },
    {
      label: 'Demand',
      icon: '⌁',
      prompts: [
        'Forecast demand for GAR-003 next month',
        'What is the demand outlook for GAR-001?',
      ],
    },
    {
      label: 'Production',
      icon: '⚙',
      prompts: [
        'Can we make 6000 grey hoodies by 20 December 2026?',
        'Which lines are at capacity?',
      ],
    },
    {
      label: 'Sourcing',
      icon: '▱',
      prompts: [
        'I need 400 meters of organic cotton',
        'Which suppliers have the fastest lead times?',
      ],
    },
  ]

  return (
    <ScenePage
      scene="overview"
      bannerMaxHeight="7.5rem"
      contentPull="-mt-3"
      banner={
        <div className="mx-auto flex w-full max-w-[1280px] flex-wrap items-end justify-between gap-3 px-5 pb-3">

          <div className="flex items-center gap-2.5 rounded-xl border border-white/60 bg-white/85 px-3 py-2 backdrop-blur-xl">

            <OmniAvatar size={32} />

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-[17px] font-semibold tracking-tight text-slate-900">Ask Omni</h1>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  Online
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-[#64748b]">
                One question reaches every agent — stock, demand, production and sourcing.
              </p>
            </div>

          </div>

          {messages.length > 0 && (
            <button
              onClick={() => {
                const newSessionId = crypto.randomUUID()
                setSessionId(newSessionId)
                setRequestId(null)
                setProgress(null)
                updateChatState({ sessionId: newSessionId, messages: [], error: '', draft: '' })
                focusChatComposer(composerRef.current, false)
              }}
              disabled={isAsking}
              className="rounded-lg border border-white/70 bg-white/90 px-3 py-2 text-[11px] font-medium text-slate-700 backdrop-blur-md transition hover:bg-white"
            >
              New conversation
            </button>
          )}

        </div>
      }
    >

    <section className="mx-auto flex h-[calc(100dvh-4rem-6.5rem)] min-h-[440px] w-full max-w-[1280px] flex-col px-5 pb-4">

      {/* ==================================================== */}
      {/* CHAT SURFACE                                         */}
      {/* ==================================================== */}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-20px_rgba(15,23,42,0.35)]">

        {/* Conversation */}
        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-5 py-5">

          {messages.length === 0 && (
            <div className="mx-auto flex h-full max-w-[900px] flex-col justify-center py-6">

              <div className="text-center">
                <OmniAvatar size={48} className="mx-auto mb-3" />
                <h3 className="text-[15px] font-semibold text-slate-900">How can I help today?</h3>
                <p className="mx-auto mt-1.5 max-w-sm text-[12px] leading-6 text-slate-500">
                  Ask in plain language. I route the question to the right agent and show you
                  the evidence behind the answer.
                </p>
              </div>

              <div className="mt-6 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
                {promptGroups.map((group) => (
                  <div key={group.label} className="rounded-lg border border-slate-200/80 bg-slate-50/60 p-3">
                    <p className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
                      <span className="text-[11px] text-[#1d4ed8]">{group.icon}</span>
                      {group.label}
                    </p>
                    <div className="mt-2 space-y-1.5">
                      {group.prompts.map((prompt) => (
                        <button
                          key={prompt}
                          onClick={() => handleSend(prompt)}
                          className="block w-full rounded-md bg-white px-2.5 py-1.5 text-left text-[12px] text-slate-600 ring-1 ring-slate-200/80 transition hover:text-[#1d4ed8] hover:ring-[#93c5fd]"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

            </div>
          )}

          <div className="space-y-5">

            {messages.map((item, index) => (

              <div key={index}>

                {item.type === 'user' && (
                  <UserMessage text={item.text} />
                )}

                {item.type === 'agent' && (
                  <AgentResponse
                    data={item.data}
                    setActivePage={setActivePage}
                    setScQuery={setScQuery}
                    handleSend={handleSend}
                    isLatest={index === messages.length - 1 && !isAsking}
                    isAsking={isAsking}
                  />
                )}

              </div>

            ))}

            {isAsking && <ThinkingBubble progress={progress} />}

            <div ref={endRef} />

          </div>

          {error && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-[12px] text-red-700">
              <span className="mt-[2px] text-[13px]">⚠</span>
              <span>{error}</span>
            </div>
          )}

          <div ref={messagesEndRef} />

        </div>


        {/* Composer */}
        <div className="flex-shrink-0 border-t border-slate-100 bg-white p-3">

          <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 transition focus-within:border-[#2563eb] focus-within:bg-white focus-within:ring-2 focus-within:ring-[#3b82f6]/15">

            <textarea
              ref={composerRef}
              rows={1}
              value={draft}
              onChange={(event) => updateChatState({ draft: event.target.value })}
              onKeyDown={handleKeyDown}
              disabled={isAsking}
              placeholder="Ask about demand, fabric, shortages, sourcing or production planning…"
              className="max-h-32 min-h-[24px] flex-1 resize-none bg-transparent py-1 text-[13px] leading-6 text-slate-800 placeholder-slate-400 outline-none disabled:opacity-60"
            />

            <button
              onClick={() => handleSend()}
              disabled={isAsking || !draft.trim()}
              aria-label="Send message"
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-[#1d4ed8] text-white transition hover:bg-[#1e40af] disabled:opacity-40"
            >
              {isAsking
                ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                : <span className="text-[13px] leading-none">↑</span>}
            </button>

          </div>

          <div className="mt-1.5 flex items-center justify-between px-1">
            <p className="text-[10px] text-slate-400">
              <kbd className="rounded border border-slate-200 bg-white px-1 py-px text-[9px]">Enter</kbd> to send ·
              <kbd className="ml-1 rounded border border-slate-200 bg-white px-1 py-px text-[9px]">Shift</kbd> +
              <kbd className="rounded border border-slate-200 bg-white px-1 py-px text-[9px]">Enter</kbd> for a new line
            </p>
            <p className="text-[10px] text-slate-400">{messages.filter((item) => item.type === 'user').length} asked</p>
          </div>

        </div>

      </div>

    </section>

    </ScenePage>
  )
}


/* ============================================================
   THINKING INDICATOR
============================================================ */

function ThinkingBubble({ progress }) {
  const agent = progress?.agent || 'Operations Agent'
  const detail = progress?.detail || 'Checking factory data and supplier status'

  return (
    <div className="flex gap-2.5">

      <AgentAvatar />

      <div>
        <p className="mb-1 text-[11px] font-medium text-slate-500">Ask Omni</p>
        <div
          role="status"
          aria-live="polite"
          className="inline-flex items-center gap-2 rounded-xl rounded-tl-sm border border-slate-200 bg-slate-50 px-3.5 py-2.5"
        >
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#3b82f6] [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#3b82f6] [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#3b82f6]" />
          </span>
          <span className="text-[12px] text-slate-500">
            <span className="font-semibold text-slate-700">{agent}</span>
            <span aria-hidden="true"> · </span>
            {detail}...
          </span>
        </div>
      </div>

    </div>
  )
}


function AgentAvatar() {
  return <OmniAvatar size={28} className="mt-5 !rounded-lg" />
}


/* ============================================================
   USER MESSAGE
============================================================ */

function UserMessage({ text }) {
  return (
    <div className="flex justify-end gap-2.5">

      <div className="max-w-[min(76%,620px)]">
        <p className="mb-1 text-right text-[11px] text-slate-400">You</p>
        <div className="rounded-xl rounded-tr-sm bg-[#1d4ed8] px-3.5 py-2.5 text-[13px] leading-6 text-white shadow-[0_8px_20px_-12px_rgba(29,78,216,0.9)]">
          {text}
        </div>
      </div>

      <div className="mt-5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-slate-200 text-[11px] font-semibold text-slate-600">
        You
      </div>

    </div>
  )
}


/* ============================================================
   ANSWER TEXT — turns one long paragraph into something
   scannable: bullets become a list, "Label: value" pairs become
   rows, and everything else stays a short paragraph.
============================================================ */

function AnswerText({ text }) {

  if (!text) return null

  const blocks = String(text)
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)

  return (
    <div className="space-y-2.5">
      {blocks.map((block, index) => {

        const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
        const bulletLines = lines.filter((line) => /^([-•*]|\d+[.)])\s+/.test(line))

        // a block is a list when most of its lines are bulleted
        if (bulletLines.length >= 2 && bulletLines.length >= lines.length - 1) {
          return (
            <ul key={index} className="space-y-1.5">
              {lines.map((line, lineIndex) => {
                const clean = line.replace(/^([-•*]|\d+[.)])\s+/, '')
                return (
                  <li key={lineIndex} className="flex gap-2 text-[13px] leading-6 text-slate-700">
                    <span className="mt-[9px] h-1 w-1 flex-shrink-0 rounded-full bg-[#3b82f6]" />
                    <span><InlineEmphasis text={clean} /></span>
                  </li>
                )
              })}
            </ul>
          )
        }

        return (
          <p key={index} className="text-[13px] leading-6 text-slate-700">
            <InlineEmphasis text={block.replace(/\n/g, ' ')} />
          </p>
        )
      })}
    </div>
  )
}


// Numbers and quantities carry the weight in an operations answer,
// so they are the one thing set apart from the running text.
function InlineEmphasis({ text }) {

  const parts = String(text).split(/(\*\*[^*]+\*\*|\b\d[\d,.]*\s?(?:units|m|kg|pieces|meters|days|%)\b|\b[A-Z]{2,4}-\d{3,4}\b)/g)

  return (
    <>
      {parts.map((part, index) => {

        if (/^\*\*[^*]+\*\*$/.test(part)) {
          return <strong key={index} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong>
        }

        if (/^\b[A-Z]{2,4}-\d{3,4}\b$/.test(part)) {
          return (
            <code key={index} className="rounded border border-slate-200 bg-slate-50 px-1 py-px font-mono text-[11px] text-slate-700">
              {part}
            </code>
          )
        }

        if (/\d/.test(part) && /(units|m|kg|pieces|meters|days|%)\s*$/.test(part)) {
          return <span key={index} className="font-semibold tabular-nums text-slate-900">{part}</span>
        }

        return <React.Fragment key={index}>{part}</React.Fragment>
      })}
    </>
  )
}


/* ============================================================
   COPY BUTTON
============================================================ */

function CopyButton({ value }) {

  const [copied, setCopied] = useState(false)

  if (!value) return null

  return (
    <button
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value)
          setCopied(true)
          setTimeout(() => setCopied(false), 1600)
        } catch {
          setCopied(false)
        }
      }}
      className="rounded-md px-1.5 py-0.5 text-[10px] text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}


/* ============================================================
   AGENT RESPONSE
============================================================ */

function AgentResponse({ data, setActivePage, handleSend, isLatest, isAsking }) {
  if (!data) {
    return null
  }

  const workflow = compactWorkflow(data.workflow || [])
  const answerShownInForecastCard = data.intent === 'demand_forecast'
    && data.result
    && isForecastUnavailable(data.result)
    && data.answer?.trim() === data.result.message?.trim()

  const followUps = followUpsFor(data)

  return (
    <div className="flex gap-2.5">

      <AgentAvatar />

      <div className="min-w-0 flex-1">

      <div className="mb-1 flex items-center gap-2">
        <p className="text-[11px] font-medium text-slate-500">Ask Omni</p>
        {data.intent && (
          <span className="rounded-full bg-slate-100 px-1.5 py-px text-[9px] font-medium uppercase tracking-[0.1em] text-slate-500">
            {String(data.intent).replace(/_/g, ' ')}
          </span>
        )}
        {data.answer && <CopyButton value={data.answer} />}
      </div>


      {/* ======================================================
          WORKFLOW
      ====================================================== */}

      {workflow.length > 0 && (

        <div className="mb-3">

          <div className="flex flex-wrap items-center gap-2">

            {workflow.map((agent, index) => (

              <React.Fragment key={`${agent}-${index}`}>

                <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-600">
                  <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-100 text-[8px] font-bold text-emerald-700">✓</span>
                  {index === 0 ? 'Operations Agent' : agent}
                </span>

                {index < workflow.length - 1 && (
                  <span className="text-[10px] text-slate-300">→</span>
                )}

              </React.Fragment>

            ))}

          </div>

        </div>

      )}


      {/* ======================================================
          ANSWER
      ====================================================== */}

      {data.answer && !answerShownInForecastCard && !data.sections && (

        <div className="rounded-xl rounded-tl-sm border border-slate-200 bg-slate-50 px-4 py-3">

          <AnswerText text={data.answer} />

        </div>

      )}

      {data.intent === 'demand_forecast' && data.suggested_products?.length > 0 && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-sm font-semibold text-slate-700">{data.forecast_mode === 'comparison' ? 'Choose products to compare' : 'Choose a product to forecast'}</p>
          <div className="flex flex-wrap gap-3">
            <button type="button" disabled={isAsking}
              onClick={() => handleSend(data.forecast_mode === 'comparison' ? 'Compare predicted demand with actual demand last month for all products' : `Forecast demand for all products for the next ${data.forecast_periods || 1} months`)}
              className="rounded-xl border border-blue-700 bg-blue-700 px-4 py-3 text-left text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50">
              <span className="block text-sm font-semibold">All products</span>
              <span className="mt-1 block text-xs text-blue-100">Entire product catalog</span>
            </button>
            {data.suggested_products.map((product) => (
              <button key={product.sku} type="button" disabled={isAsking}
                onClick={() => handleSend(data.forecast_mode === 'comparison' ? `Compare predicted demand with actual demand last month for ${product.product_name} (${product.sku})` : `Forecast demand for ${product.product_name} (${product.sku}) for the next ${data.forecast_periods || 1} months`)}
                className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-left transition hover:border-blue-500 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50">
                <span className="block text-sm font-semibold text-blue-900">{product.product_name}</span>
                <span className="mt-1 block text-xs text-blue-600">{product.sku}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {data.comparisons && <div className="mt-4 space-y-3">{data.comparisons.map((row) => <div key={row.sku} className="rounded-xl border border-slate-200 p-4 text-sm">
        {row.prediction_source && <p className="mb-2 text-xs font-semibold text-blue-700">{row.prediction_source}</p>}
        <p className="font-semibold">{row.product_name || row.sku} · {row.period.slice(0, 7)}</p>
        <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">{[['Actual units', row.actual], ['Predicted units', row.predicted], ['Error (predicted − actual)', row.error], ['Absolute error (%)', row.percentage_error]].map(([label, value]) => <div key={label}><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 font-semibold">{value == null ? 'N/A' : Number(value).toLocaleString()}</dd></div>)}</dl>
        <p className="mt-3 text-xs text-slate-500">{row.note}</p>
      </div>)}</div>}

      {data.intent === 'report_navigation' && (
        <button type="button" onClick={() => setActivePage('reports')} className="mt-3 rounded-lg bg-[#1f3a36] px-4 py-2 text-sm font-semibold text-white">Open Factory reports</button>
      )}

      {data.sections && <div className="mt-4"><ManagementReport report={data} compact /></div>}

      {(data.reportRequested || data.intent === 'report_download') && data.intent !== 'unknown' && (data.reportSource || (data.intent !== 'report_download' && data.answer)) && (
        <ReportDownload data={data.reportSource || data} requested={data.reportRequested || data.intent === 'report_download'} />
      )}

      {/* ======================================================
          SHADE SELECTION
      ====================================================== */}

      {data.status === 'needs_shade_selection' && (
        <div className="mt-4 p-4 border border-[#e2e8f0] rounded-xl bg-white shadow-sm max-w-sm">
          <ColorPalette 
            question={data.answer} 
            onSelect={(shade) => handleSend && handleSend(shade)} 
          />
        </div>
      )}

      {/* ======================================================
          SELECTING (SUPPLIERS)
      ====================================================== */}

      {data.status === 'selecting' && data.suppliers && (
        <div className="mt-4 max-w-md space-y-2">
          {data.suppliers.map((sup, idx) => (
            <SupplierCard 
              key={idx} 
              supplier={sup} 
              onSelect={(supplier) => handleSend && handleSend(`Selected supplier: ${supplier.name}`, { supplier })}
            />
          ))}
        </div>
      )}

      {/* ======================================================
          PROCUREMENT
      ====================================================== */}

      {['operational_plan', 'production_feasibility'].includes(data.intent) && data.result && (
        <PlanningEvidence result={data.result} setActivePage={setActivePage} />
      )}

      {data.intent === 'product_materials' && data.result && <MaterialEvidence result={data.result} />}

      {data.intent === 'approval_followup' && data.results?.map((item) => (
        <OmniProcurementCard key={item.run_id} data={item.approval || item} />
      ))}
      {data.intent === 'approval_followup' && data.errors?.map((item, index) => (
        <p role="alert" key={index} className="mt-3 text-sm text-red-700">PO #{item.po_id}: {item.error}</p>
      ))}

      {data.intent === 'procurement' && data.data && (
        <OmniProcurementCard data={data.data} />
      )}

      {data.intent === 'low_stock_procurement' && data.results && (
        <LowStockList results={data.results} />
      )}

      {data.intent === 'low_stock_procurement' && data.procurement && (
        <div className="mt-4 space-y-4">
          {data.procurement.map((item, index) => (
            item.run ? (
              <OmniProcurementCard
                key={item.run.run_id || index}
                data={item.run}
                material={item.material}
              />
            ) : (
              <SupplierSuggestionCard
                key={`${item.material?.material_code || 'material'}-${index}`}
                item={item}
              />
            )
          ))}
        </div>
      )}

      {data.intent === 'operational_plan' && data.result?.procurement?.length > 0 && (
        <div className="mt-4 space-y-4">
          {data.result.procurement.map((item, index) => (
            item.run ? (
              <OmniProcurementCard
                key={item.run.run_id || index}
                data={item.run}
                material={item}
              />
            ) : (
              <div
                key={`${item.material_code || 'procurement'}-${index}`}
                className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700"
              >
                {item.material_name || item.material_code || 'Material'} needs manual review: {item.error || 'purchase order was not drafted.'}
              </div>
            )
          ))}
        </div>
      )}

      {/* ======================================================
          DEMAND FORECAST
      ====================================================== */}

      {data.intent === 'demand_forecast' && data.result && (
        <ForecastCard result={data.result} />
      )}

      {data.intent === 'demand_forecast' && data.results && (
        <ForecastList results={data.results} />
      )}


      {/* ======================================================
          INVENTORY LIST
      ====================================================== */}

      {data.intent === 'inventory_list' &&
        data.results && (

          <InventoryList
            results={data.results}
          />

        )}


      {/* ======================================================
          LOW STOCK
      ====================================================== */}

      {data.intent === 'low_stock' &&
        data.results && (

          <LowStockList
            results={data.results}
          />

        )}


      {/* ======================================================
          OUT OF STOCK
      ====================================================== */}

      {data.intent === 'out_of_stock' &&
        data.results && (

          <LowStockList
            results={data.results}
            outOfStock
          />

        )}


      {/* ======================================================
          HEALTHY STOCK
      ====================================================== */}

      {data.intent === 'healthy_stock' &&
        data.results && (

          <HealthyStockList
            results={data.results}
          />

        )}


      {/* ======================================================
          REORDER
      ====================================================== */}

      {data.intent === 'reorder_requirements' &&
        data.results && (

          <ReorderList
            results={data.results}
          />

        )}


      {/* ======================================================
          MATERIAL STATUS
      ====================================================== */}

      {data.intent === 'material_status' &&
        data.result && (

          <MaterialCard
            result={data.result}
          />

        )}


      {/* ======================================================
          INVENTORY REQUIREMENT
      ====================================================== */}

      {data.intent === 'inventory_requirement' &&
        data.result && (

          <RequirementCard
            result={data.result}
          />

        )}


      {/* ======================================================
          INVENTORY SUMMARY
      ====================================================== */}

      {data.intent === 'inventory_summary' &&
        data.result && (

          <SummaryCard
            result={data.result}
          />

        )}


      {/* ======================================================
          TOTAL STOCK
      ====================================================== */}

      {data.intent === 'total_stock' &&
        data.result && (

          <TotalStockCard
            result={data.result}
          />

        )}


      {/* ======================================================
          KPI
      ====================================================== */}

      {data.intent === 'inventory_kpis' &&
        data.result && (

          <KpiCard
            result={data.result}
          />

        )}


      {/* ======================================================
          METADATA
      ====================================================== */}

      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-xs text-slate-400">

        {data.intent && (
          <span>
            Intent: {formatIntent(data.intent)}
          </span>
        )}

        {data.delegated_to && (
          <span>
            Delegated to: {data.delegated_to}
          </span>
        )}

        {data.status && (
          <span className={
            data.status === 'success'
              ? 'text-emerald-600'
              : 'text-amber-600'
          }>
            {data.intent === 'operational_plan' && data.status === 'success' ? 'Assessment complete' : formatStatus(data.status)}
          </span>
        )}

      </div>

      {isLatest && followUps.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-[0.14em] text-slate-400">Next</span>
          {followUps.map((prompt) => (
            <button
              key={prompt}
              onClick={() => handleSend(prompt)}
              className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 transition hover:border-[#93c5fd] hover:text-[#1d4ed8]"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      </div>

    </div>
  )
}


/* ============================================================
   FOLLOW-UPS — what a planner usually asks next, chosen from
   the intent that just came back rather than a fixed list.
============================================================ */

function followUpsFor(data) {

  const sku = data?.result?.sku || data?.result?.[0]?.sku

  switch (data?.intent) {

    case 'demand_forecast':
      return [
        sku ? `Can we produce the forecast quantity of ${sku}?` : 'Can we produce that quantity?',
        'Do we have the materials in stock?',
        'Download this as a report',
      ]

    case 'inventory_check':
    case 'low_stock':
    case 'inventory_list':
      return ['Which of these need reordering?', 'Find suppliers for the short items', 'Download inventory report']

    case 'production_feasibility':
    case 'operational_plan':
      return ['What is blocking it?', 'Suggest a reallocation', 'Show the supplier options']

    case 'procurement':
      return ['Compare supplier lead times', 'Show me the purchase orders']

    default:
      return ['Show me the fabric stock list', 'Which lines are at capacity?']
  }
}


/* ============================================================
   FORECAST RESULTS
============================================================ */

function ReportDownload({ data, requested }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(null)
  async function download() {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      setPreview(await createChatReportPreview(data))
    } catch {
      setError('Could not create the PDF. Please try downloading again.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3">
      {requested && <p className="mb-2 text-sm text-slate-600">Report ready to download</p>}
      <button type="button" onClick={download} disabled={busy} className="rounded-lg bg-[#1f3a36] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
        {busy ? 'Preparing PDF...' : 'Download PDF'}
      </button>
      <p className="mt-2 text-xs text-slate-500">Preview this report, then download or print it.</p>
      {error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
      {preview && <ForecastPdfPreview report={preview} onClose={() => setPreview(null)} />}
    </div>
  )
}

function isForecastUnavailable(result) {
  return result.status === 'error' || typeof result.forecast !== 'number' || !Number.isFinite(result.forecast)
}

function ForecastCard({ result }) {
  if (isForecastUnavailable(result)) {
    return (
      <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">{result.sku || 'Demand'}: forecast unavailable</p>
        <p className="mt-2">{result.message || 'There is not enough valid data to calculate a forecast.'}</p>
      </div>
    )
  }
  return (
    <div className="mt-4 rounded-xl border border-[#3b82f6]/30 bg-[#ffffff] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-800">{result.product_name}</p>
          <p className="mt-1 text-xs text-slate-500">{result.sku} · {result.model}</p>
        </div>
        <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">{result.trend}</span>
      </div>
      <ForecastMonths result={result} />
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div><p className="text-xs text-slate-500">Next-month forecast</p><p className="mt-1 text-lg font-semibold text-slate-900">{Number(result.forecast).toLocaleString()} units</p></div>
        <div><p className="text-xs text-slate-500">History analyzed</p><p className="mt-1 text-lg font-semibold text-slate-900">{result.history_points} periods</p></div>
      </div>
    </div>
  )
}


function ForecastMonths({ result }) {
  if (!result.predictions || result.predictions.length < 2) return null
  return <div className="mt-4 w-full overflow-hidden rounded-lg border border-slate-200">
    <p className="bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-900">{result.predictions.length}-month demand outlook</p>
    <table className="w-full text-left text-sm">
      <thead><tr className="text-slate-500"><th className="px-3 py-2">Month</th><th className="px-3 py-2 text-right">Predicted units</th></tr></thead>
      <tbody>{result.predictions.map((point) => <tr key={point.date} className="border-t border-slate-100"><td className="px-3 py-2">{new Date(`${point.date.slice(0, 10)}T00:00:00`).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</td><td className="px-3 py-2 text-right">{Number(point.quantity).toLocaleString()}</td></tr>)}</tbody>
    </table>
    <p className="px-3 py-2 text-xs text-slate-500">Forecast periods follow the latest recorded demand month.</p>
  </div>
}

function ForecastList({ results }) {
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-4 py-3"><p className="text-sm font-semibold text-slate-800">Demand Forecast Agent results</p></div>
      <div className="divide-y divide-slate-100">
        {results.map((result) => (
          <div key={result.sku} className="flex flex-wrap items-center justify-between gap-4 px-4 py-3">
            <div><p className="text-sm font-medium text-slate-800">{result.product_name}</p><p className="mt-1 text-xs text-slate-500">{result.sku} · {result.trend}</p></div>
            <div className="text-right"><p className="text-sm font-semibold text-slate-900">{Number(result.forecast).toLocaleString()} units</p><p className="mt-1 text-xs text-slate-500">next month</p></div>
            <ForecastMonths result={result} />
          </div>
        ))}
      </div>
    </div>
  )
}


/* ============================================================
   INVENTORY LIST
============================================================ */

function InventoryList({ results }) {

  return (
    <div className="mt-4 border border-slate-200 rounded-xl overflow-hidden bg-white">

      <div className="px-4 py-3 border-b border-slate-100">

        <h3 className="font-semibold text-slate-800 text-sm">
          Inventory details
        </h3>

        <p className="text-xs text-slate-400 mt-1">
          {results.length} materials currently recorded
        </p>

      </div>


      <div className="divide-y divide-slate-100">

        {results.map((item) => (

          <InventoryRow
            key={item.material_code}
            item={item}
          />

        ))}

      </div>

    </div>
  )
}


/* ============================================================
   INVENTORY ROW
============================================================ */

function InventoryRow({ item }) {

  const lowStock = item.status === 'LOW_STOCK'
  const outOfStock = item.status === 'OUT_OF_STOCK'

  return (
    <div className="px-4 py-4">

      <div className="flex items-center justify-between gap-4">

        <div>

          <p className="text-sm font-medium text-slate-800">
            {item.material_name}
          </p>

          <p className="text-xs text-slate-400 mt-1">
            {item.material_code}
          </p>

        </div>


        <span className={

          outOfStock
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs font-medium'
            : lowStock
              ? 'px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 text-xs font-medium'
              : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs font-medium'

        }>

          {outOfStock
            ? 'Out of stock'
            : lowStock
              ? 'Low stock'
              : 'Healthy'}

        </span>

      </div>


      <div className="grid grid-cols-3 gap-4 mt-4">

        <Detail
          label="Current stock"
          value={`${item.current_stock} ${item.unit}`}
        />

        <Detail
          label="Reorder level"
          value={`${item.reorder_level} ${item.unit}`}
        />

        <Detail
          label="Shortage"
          value={`${item.shortage} ${item.unit}`}
          danger={lowStock || outOfStock}
        />

      </div>

    </div>
  )
}


/* ============================================================
   LOW STOCK
============================================================ */

function LowStockList({ results, outOfStock = false }) {

  if (results.length === 0) {

    return (
      <div className="mt-4 p-4 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm">
        {outOfStock
          ? 'There are currently no materials completely out of stock.'
          : 'Good news — there are currently no materials below their reorder levels.'
        }
      </div>
    )

  }


  return (
    <div className="mt-4 space-y-2">

      {results.map((item) => (

        <InventoryRow
          key={item.material_code}
          item={item}
        />

      ))}

    </div>
  )
}


/* ============================================================
   HEALTHY STOCK
============================================================ */

function HealthyStockList({ results }) {

  return (
    <div className="mt-4 border border-emerald-100 rounded-xl overflow-hidden">

      <div className="px-4 py-3 bg-emerald-50">

        <p className="text-sm font-semibold text-emerald-700">
          Healthy inventory
        </p>

        <p className="text-xs text-emerald-600 mt-1">
          {results.length} materials are currently at or above
          their reorder levels.
        </p>

      </div>

      {results.map((item) => (

        <InventoryRow
          key={item.material_code}
          item={item}
        />

      ))}

    </div>
  )
}


/* ============================================================
   REORDER LIST
============================================================ */

function ReorderList({ results }) {

  return (
    <div className="mt-4 border border-slate-200 rounded-xl overflow-hidden">

      <div className="px-4 py-3 bg-slate-50 border-b border-slate-100">

        <p className="text-sm font-semibold text-slate-800">
          Replenishment requirements
        </p>

      </div>


      <div className="divide-y divide-slate-100">

        {results.map((item) => (

          <div
            key={item.material_code}
            className="px-4 py-4"
          >

            <p className="text-sm font-medium text-slate-800">
              {item.material_name}
            </p>

            <div className="grid grid-cols-3 gap-4 mt-3">

              <Detail
                label="Current"
                value={`${item.current_stock} ${item.unit}`}
              />

              <Detail
                label="Reorder level"
                value={`${item.reorder_level} ${item.unit}`}
              />

              <Detail
                label="Replenish"
                value={`${item.reorder_quantity} ${item.unit}`}
                danger
              />

            </div>

          </div>

        ))}

      </div>

    </div>
  )
}


/* ============================================================
   MATERIAL CARD
============================================================ */

function MaterialCard({ result }) {

  const lowStock = result.status === 'LOW_STOCK'
  const outOfStock = result.status === 'OUT_OF_STOCK'

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <div className="flex justify-between items-start gap-3 mb-4">

        <div>

          <h3 className="text-sm font-semibold text-slate-800">
            {result.material_name}
          </h3>

          <p className="text-xs text-slate-400 mt-1">
            {result.material_code}
          </p>

        </div>


        <span className={
          outOfStock
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs'
            : lowStock
              ? 'px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 text-xs'
              : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs'
        }>
          {outOfStock
            ? 'Out of stock'
            : lowStock
              ? 'Low stock'
              : 'Healthy'
          }
        </span>

      </div>


      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Current stock"
          value={`${result.current_stock} ${result.unit}`}
        />

        <Detail
          label="Reorder level"
          value={`${result.reorder_level} ${result.unit}`}
        />

        <Detail
          label="Shortage"
          value={`${result.shortage} ${result.unit}`}
          danger={lowStock || outOfStock}
        />

        <Detail
          label="Recommendation"
          value={result.recommendation}
        />

      </div>

    </div>
  )
}


/* ============================================================
   REQUIREMENT CARD
============================================================ */

function RequirementCard({ result }) {

  const shortage = result.status === 'SHORTAGE'

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <div className="flex justify-between items-center mb-4">

        <h3 className="text-sm font-semibold text-slate-800">
          Inventory requirement
        </h3>

        <span className={
          shortage
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs font-medium'
            : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs font-medium'
        }>
          {shortage ? 'Shortage' : 'Sufficient stock'}
        </span>

      </div>


      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Material"
          value={result.material_name}
        />

        <Detail
          label="Available"
          value={`${result.available_quantity} ${result.unit}`}
        />

        <Detail
          label="Required"
          value={`${result.required_quantity} ${result.unit}`}
        />

        <Detail
          label="Shortage"
          value={`${result.shortage} ${result.unit}`}
          danger={shortage}
        />

      </div>


      {result.message && (
        <div className={
          shortage
            ? 'mt-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm'
            : 'mt-4 p-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm'
        }>
          {result.message}
        </div>
      )}

    </div>
  )
}


/* ============================================================
   SUMMARY CARD
============================================================ */

function SummaryCard({ result }) {

  const critical = result.inventory_health === 'CRITICAL'
  const needsAttention = result.inventory_health === 'NEEDS_ATTENTION'

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <div className="flex justify-between items-center mb-4">

        <h3 className="text-sm font-semibold text-slate-800">
          Inventory health
        </h3>

        <span className={
          critical
            ? 'px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs'
            : needsAttention
              ? 'px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 text-xs'
              : 'px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs'
        }>
          {result.inventory_health}
        </span>

      </div>


      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Total materials"
          value={result.total_materials}
        />

        <Detail
          label="Healthy"
          value={result.healthy_materials}
        />

        <Detail
          label="Low stock"
          value={result.low_stock_materials}
          danger={result.low_stock_materials > 0}
        />

        <Detail
          label="Out of stock"
          value={result.out_of_stock_materials}
          danger={result.out_of_stock_materials > 0}
        />

      </div>

    </div>
  )
}


/* ============================================================
   TOTAL STOCK CARD
============================================================ */

function TotalStockCard({ result }) {

  const units = result.units?.join(', ') || ''

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <h3 className="text-sm font-semibold text-slate-800 mb-4">
        Total inventory
      </h3>

      <div className="grid grid-cols-2 gap-4">

        <Detail
          label="Total stock"
          value={`${result.total_stock} ${units}`}
        />

        <Detail
          label="Materials"
          value={result.material_count}
        />

      </div>

    </div>
  )
}


/* ============================================================
   KPI CARD
============================================================ */

function KpiCard({ result }) {

  return (
    <div className="mt-4 border border-slate-200 rounded-xl p-4">

      <h3 className="text-sm font-semibold text-slate-800 mb-4">
        Inventory KPIs
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <Detail
          label="Total materials"
          value={result.total_materials}
        />

        <Detail
          label="Healthy"
          value={`${result.healthy_percentage}%`}
        />

        <Detail
          label="Low stock"
          value={`${result.low_stock_percentage}%`}
        />

        <Detail
          label="Out of stock"
          value={`${result.out_of_stock_percentage}%`}
          danger={result.out_of_stock_percentage > 0}
        />

      </div>

    </div>
  )
}


/* ============================================================
   DETAIL
============================================================ */

function Detail({
  label,
  value,
  danger = false,
}) {

  return (
    <div>

      <p className="text-xs text-slate-400 mb-1">
        {label}
      </p>

      <p className={
        danger
          ? 'text-sm font-semibold text-red-600'
          : 'text-sm font-medium text-slate-800'
      }>
        {value}
      </p>

    </div>
  )
}


/* ============================================================
   HELPERS
============================================================ */

function formatIntent(intent) {

  return intent
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}


function formatStatus(status) {

  return status
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}


/* ============================================================
   OMNI PROCUREMENT CARD

   NOTE: this component was left unfinished on the dev branch — the
   file ended mid-comment here with no implementation, and
   OmniProcurementCard was referenced above without ever being
   imported or defined. This is a minimal fallback so a procurement
   response renders instead of crashing with a ReferenceError.
   Replace with the real UI once the intended design is available.
============================================================ */

function SupplierSuggestionCard({ item }) {
  const material = item.material || {}
  const supplier = item.supplier || {}

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white text-sm text-slate-700 shadow-sm">
      <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
        <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Supplier match</p>
        <p className="mt-1 font-semibold text-slate-900">{material.material_name || 'Low-stock material'}</p>
      </div>
      {item.error ? (
        <div className="px-4 py-3 text-xs text-red-700">{item.error}</div>
      ) : (
        <div className="grid gap-3 p-4 md:grid-cols-2">
          <Detail label="Suggested Supplier" value={supplier.supplier_name || '-'} />
          <Detail label="Country" value={supplier.country || '-'} />
          <Detail label="Rating" value={supplier.rating !== undefined ? Number(supplier.rating).toFixed(1) : '-'} />
          <Detail label="Lead Time" value={supplier.lead_time_days ? `${supplier.lead_time_days} days` : '-'} />
          <Detail label="Shortage" value={material.shortage ? `${Number(material.shortage).toLocaleString()} ${material.unit || 'units'}` : '-'} />
          <Detail label="Category" value={formatStatus(item.material_type || 'unknown')} />
        </div>
      )}
    </div>
  )
}


function OmniProcurementCard({ data, material }) {
  const [current, setCurrent] = useState(data)
  const supplier = current.supplier || {}
  const po = current.po || {}
  const [status, setStatus] = useState(data.status || 'unknown')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [actionResult, setActionResult] = useState(null)
  const [actionError, setActionError] = useState('')
  const isAwaitingApproval = status === 'awaiting_approval' && Boolean(po.po_id)

  useEffect(() => {
    if (!data.run_id) return undefined
    let active = true
    async function refresh() {
      try {
        const result = await supplyChainApi.getPipelineStatus(data.run_id)
        if (active) {
          setCurrent(result)
          setStatus(result.status)
          setActionError('')
        }
      } catch (error) {
        if (active) setActionError(error.message)
      }
    }
    refresh()
    window.addEventListener('focus', refresh)
    window.addEventListener('omni:purchase-order-updated', refresh)
    const interval = ['awaiting_approval', 'approving'].includes(status) ? window.setInterval(refresh, 5000) : null
    return () => {
      active = false
      window.clearInterval(interval)
      window.removeEventListener('focus', refresh)
      window.removeEventListener('omni:purchase-order-updated', refresh)
    }
  }, [data.run_id, status])

  async function handleApprove() {
    if (!data.run_id || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setActionError('')

    try {
      const result = await supplyChainApi.approvePo(data.run_id, 'Human Manager')
      const emailMessage = result.email_sent
        ? ` PO email sent to ${result.email_recipient}.`
        : result.email_error
          ? ` Email not sent: ${result.email_error}`
          : ''
      setStatus('completed')
      setActionResult({
        type: 'approved',
        message: `Approved.${result.shipment_id ? ` Shipment #${result.shipment_id} created.` : ' No shipment was returned.'}${emailMessage}`,
        details: result,
      })
    } catch (error) {
      setActionError(error.message || 'Could not approve this purchase order.')
    } finally {
      window.dispatchEvent(new Event('omni:purchase-order-updated'))
      setIsSubmitting(false)
    }
  }

  async function handleReject() {
    if (!data.run_id || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setActionError('')

    try {
      await supplyChainApi.rejectPo(data.run_id)
      setStatus('rejected')
      setActionResult({
        type: 'rejected',
        message: 'Rejected. I stopped this procurement pipeline.',
      })
    } catch (error) {
      setActionError(error.message || 'Could not reject this purchase order.')
    } finally {
      window.dispatchEvent(new Event('omni:purchase-order-updated'))
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mt-4 min-w-0 overflow-hidden rounded-lg border border-[#e2e8f0] bg-white text-sm text-slate-700 shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-slate-100 bg-[#ffffff] px-4 py-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-[#0369a1]">Procurement run</p>
          <p className="mt-1 font-semibold text-slate-900">
            {material?.material_name
              ? `${material.material_name} -> ${supplier.supplier_name || 'Supplier selected'}`
              : supplier.supplier_name || 'Supplier selected'}
          </p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
          isAwaitingApproval
            ? 'bg-amber-100 text-amber-700'
            : status === 'failed'
              ? 'bg-red-100 text-red-700'
              : status === 'completed' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'
        }`}>
          {formatStatus(status)}
        </span>
      </div>

      <div className="grid gap-3 p-4 md:grid-cols-2">
        <Detail label="Run ID" value={data.run_id || '-'} />
        <Detail label="Material Type" value={formatStatus(current.material_type || 'unknown')} />
        <Detail label="Supplier" value={supplier.supplier_name || '-'} />
        <Detail label="Country" value={supplier.country || '-'} />
        <Detail label="Rating" value={supplier.rating !== undefined ? Number(supplier.rating).toFixed(1) : '-'} />
        <Detail label="Lead Time" value={supplier.lead_time_days ? `${supplier.lead_time_days} days` : '-'} />
        <Detail label="PO ID" value={po.po_id ? `#${po.po_id}` : '-'} />
        <Detail label="PO Status" value={formatStatus(status === 'completed' ? 'approved' : status === 'rejected' ? 'rejected' : po.status || status)} />
        <Detail label="Quantity" value={`${current.qty != null ? Number(current.qty).toLocaleString() : po.qty != null ? Number(po.qty).toLocaleString() : '-'} ${current.po_details?.unit || material?.unit || ''}`} />
        <Detail label={current.po_details?.price_basis === 'planning_estimate' ? 'Estimated total (verify before approval)' : 'Total value'} value={current.total_value != null ? `LKR ${Number(current.total_value).toLocaleString()}` : '-'} />
      </div>

      <dl className="grid gap-3 border-t border-slate-100 px-4 py-3 text-xs sm:grid-cols-3" aria-label="Order action status">
        <div><dt className="text-slate-500">Purchase order</dt><dd className="mt-1 font-medium">{po.po_id ? `#${po.po_id} - ${formatStatus(status === 'completed' ? 'approved' : status === 'rejected' ? 'rejected' : po.status || status)}` : 'Not drafted'}</dd></div>
        <div><dt className="text-slate-500">Freight</dt><dd className="mt-1 font-medium">{current.shipment?.shipment_id ? `Shipment #${current.shipment.shipment_id} created` : isAwaitingApproval ? 'Waiting for approval' : 'No shipment recorded'}</dd></div>
        <div><dt className="text-slate-500">Supplier email</dt><dd className={`mt-1 break-words font-medium ${current.email_error ? 'text-amber-800' : ''}`}>{current.email_sent ? `Sent to ${current.email_recipient}` : current.email_error || (isAwaitingApproval ? 'Waiting for approval' : 'Not sent')}</dd></div>
      </dl>

      {supplier.compliance_proof && (
        <div className="border-t border-slate-100 px-4 py-3">
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Compliance proof</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">{supplier.compliance_proof}</p>
        </div>
      )}

      {isAwaitingApproval && (
        <div className="border-t border-slate-100 bg-[#ffffff] px-4 py-4">
          <p className="text-sm font-semibold text-slate-900">
            Manual approval required
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            This purchase order is only a draft. Authorize it to continue with freight booking, or reject it to stop the pipeline.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleApprove}
              disabled={isSubmitting}
              className="rounded-lg bg-[#1d4ed8] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#1e40af] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? 'Working...' : 'Authorize PO'}
            </button>
            <button
              type="button"
              onClick={handleReject}
              disabled={isSubmitting}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {actionResult && (
        <div className={`border-t px-4 py-3 text-xs ${
          actionResult.type === 'approved'
            ? 'border-emerald-100 bg-emerald-50 text-emerald-800'
            : 'border-red-100 bg-red-50 text-red-700'
        }`}>
          <p className="font-semibold">{actionResult.message}</p>
          {actionResult.details?.shipment_id && (
            <p className="mt-1">
              Shipment #{actionResult.details.shipment_id}
              {actionResult.details.carrier ? ` with ${actionResult.details.carrier}` : ''}
              {actionResult.details.eta ? `, ETA ${actionResult.details.eta}` : ''}.
            </p>
          )}
        </div>
      )}

      {actionError && (
        <div className="border-t border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700">
          {actionError}
        </div>
      )}

      {current.error && (
        <div className="border-t border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700">
          {current.error}
        </div>
      )}
    </div>
  )
}

export default OperationsAgent

// ── Shared Supplier UI Components ──────────────────────────────────────

const FLAGS = {
  'Sri Lanka': '🇱🇰', 'India': '🇮🇳', 'Bangladesh': '🇧🇩',
  'Turkey': '🇹🇷', 'Pakistan': '🇵🇰', 'China': '🇨🇳',
  'Vietnam': '🇻🇳', 'Indonesia': '🇮🇩',
}

const COLOUR_PALETTE = [
  { name: 'Ivory White',       hex: '#FFFFF0', base: 'White' },
  { name: 'Natural White',     hex: '#F5F5DC', base: 'White' },
  { name: 'Optical White',     hex: '#F8F8FF', base: 'White' },
  { name: 'Light Grey',        hex: '#D3D3D3', base: 'Grey' },
  { name: 'Stone Grey',        hex: '#A9A9A9', base: 'Grey' },
  { name: 'Charcoal',          hex: '#36454F', base: 'Grey' },
  { name: 'Black',             hex: '#111111', base: 'Black' },
  { name: 'Sky Blue',          hex: '#87CEEB', base: 'Blue' },
  { name: 'Royal Blue',        hex: '#4169E1', base: 'Blue' },
  { name: 'Navy Blue',         hex: '#1E3A8A', base: 'Blue' },
  { name: 'Midnight Blue',     hex: '#191970', base: 'Blue' },
  { name: 'Teal',              hex: '#008080', base: 'Green' },
  { name: 'Mint Green',        hex: '#98FF98', base: 'Green' },
  { name: 'Olive Green',       hex: '#6B8E23', base: 'Green' },
  { name: 'Forest Green',      hex: '#228B22', base: 'Green' },
  { name: 'Dark Green',        hex: '#006400', base: 'Green' },
  { name: 'Burgundy',          hex: '#800020', base: 'Red' },
  { name: 'Rose Red',          hex: '#FF007F', base: 'Red' },
  { name: 'Tomato Red',        hex: '#FF6347', base: 'Red' },
  { name: 'Coral',             hex: '#FF7F50', base: 'Orange' },
  { name: 'Orange',            hex: '#FF8C00', base: 'Orange' },
  { name: 'Mustard Yellow',    hex: '#FFDB58', base: 'Yellow' },
  { name: 'Sand Beige',        hex: '#F5DEB3', base: 'Brown' },
  { name: 'Caramel Brown',     hex: '#C68642', base: 'Brown' },
  { name: 'Chocolate Brown',   hex: '#7B3F00', base: 'Brown' },
  { name: 'Lavender',          hex: '#E6E6FA', base: 'Purple' },
  { name: 'Purple',            hex: '#800080', base: 'Purple' },
  { name: 'Fuchsia',           hex: '#FF00FF', base: 'Purple' },
  { name: 'Dusty Rose',        hex: '#DCAE96', base: 'Pink' },
  { name: 'Natural / Undyed',  hex: '#EDE0C8', base: 'Other' },
]

function generateShades(baseName) {
  const hues = {
    red: 0, orange: 30, yellow: 60, green: 120, teal: 180,
    blue: 215, navy: 230, purple: 270, pink: 330, brown: 25,
    olive: 80, mint: 150, beige: 35, khaki: 45, maroon: 345
  };
  
  const b = baseName.toLowerCase();
  let hue = 215; // default to blue
  let isAchromatic = false;
  
  if (b.includes('white') || b.includes('grey') || b.includes('gray') || b.includes('black')) {
    isAchromatic = true;
  } else {
    for (const [k, v] of Object.entries(hues)) {
      if (b.includes(k)) { hue = v; break; }
    }
  }

  const shades = [];
  const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const baseDisplay = b.split(' ').map(capitalize).join(' ');
  
  if (isAchromatic) {
    for (let i = 0; i < 25; i++) {
      const l = 98 - (i * 3.8); // 98 down to ~6.8
      let name = `Monochrome Shade ${i+1}`;
      if (i === 0) name = 'Pure White';
      else if (i === 12) name = 'Medium Grey';
      else if (i === 24) name = 'Deep Black';
      else if (i < 5) name = `Light Grey ${i}`;
      else if (i > 20) name = `Dark Grey ${i}`;
      shades.push({ name, hex: `hsl(0, 0%, ${l.toFixed(1)}%)` });
    }
  } else {
    const l_vals = [85, 70, 50, 35, 20];
    const s_vals = [20, 40, 60, 80, 100];
    const l_names = ['Very Light', 'Light', 'Medium', 'Dark', 'Very Dark'];
    const s_names = ['Muted', 'Soft', 'Standard', 'Vibrant', 'Neon'];
    
    for (let i = 0; i < 5; i++) {
      for (let j = 0; j < 5; j++) {
        let l = l_vals[i];
        let s = s_vals[j];
        if (b.includes('brown')) l = l * 0.7; // Brown needs to be darker
        let name = `${l_names[i]} ${s_names[j]} ${baseDisplay}`;
        shades.push({ name, hex: `hsl(${hue}, ${s}%, ${l}%)` });
      }
    }
  }
  return shades;
}

function ColorPalette({ onSelect, disabled, question }) {
  const [hovered, setHovered] = useState(null)
  
  let baseColor = null;
  const match = (question || "").match(/shade of ([a-zA-Z\s]+)/i);
  if (match) {
    baseColor = match[1].trim();
  }
  
  const displayColors = baseColor ? generateShades(baseColor) : COLOUR_PALETTE;

  return (
    <div className="mt-2">
      <p className="text-xs text-gray-400 mb-2">Click to select a colour:</p>
      <div className={`grid gap-1.5 ${baseColor ? 'grid-cols-5' : 'grid-cols-6'}`}>
        {displayColors.map(c => (
          <button
            key={c.name}
            title={c.name}
            disabled={disabled}
            onClick={() => onSelect(c.name)}
            onMouseEnter={() => setHovered(c.name)}
            onMouseLeave={() => setHovered(null)}
            className="w-full aspect-square rounded-md border-2 border-transparent hover:border-gray-700 transition-all duration-100 relative focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:cursor-not-allowed"
            style={{ backgroundColor: c.hex }}
          />
        ))}
      </div>
      {hovered && (
        <p className="text-xs text-gray-500 mt-1.5 text-center">{hovered}</p>
      )}
    </div>
  )
}

function SupplierCard({ supplier, onSelect, disabled, selected }) {
  return (
    <button
      onClick={() => onSelect(supplier)}
      disabled={disabled}
      className={`w-full text-left rounded-xl p-3 border transition-all duration-150 group
        ${selected
          ? 'border-amber-400 bg-amber-50 shadow-md'
          : disabled
            ? 'border-gray-100 opacity-40 cursor-not-allowed'
            : 'border-gray-200 bg-white hover:border-amber-400 hover:shadow-md'
        }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
            <span className="font-semibold text-sm text-gray-800 group-hover:text-amber-700">
              {FLAGS[supplier.country] || '🏭'} {supplier.name}
            </span>
            {selected && <span className="text-amber-600 text-xs font-semibold">✓ Selected</span>}
            {supplier.badge_fastest && !selected && (
              <span className="text-[9px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">⚡ Fastest</span>
            )}
            {supplier.badge_best_price && !selected && (
              <span className="text-[9px] font-bold bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">💰 Best Price</span>
            )}
          </div>
          <p className="text-xs text-gray-400">{supplier.country}</p>
          {supplier.rating !== undefined && (
            <div className="flex items-center gap-1 mt-1">
              <span className="text-xs font-medium text-amber-500">★ {Number(supplier.rating).toFixed(1)}</span>
            </div>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-gray-400">Lead time</p>
          <p className="text-sm font-semibold text-gray-700">{supplier.lead_time_days}d</p>
          {supplier.price_per_unit && (
            <p className="text-xs text-gray-400 mt-0.5">LKR {Number(supplier.price_per_unit).toLocaleString()}/unit</p>
          )}
          {supplier.estimated_total && (
            <p className="text-xs font-bold text-emerald-700">LKR {Number(supplier.estimated_total).toLocaleString()}</p>
          )}
        </div>
      </div>
    </button>
  )
}
